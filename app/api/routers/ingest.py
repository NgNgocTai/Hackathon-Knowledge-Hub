import asyncio
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.api.jobs import job_registry, utc_now
from app.api.schemas.ingest import IngestRequest, IngestResponse, IngestStatusResponse
from app.embedding.chunker import Chunker
from app.api.dependencies import get_chunk_indexer, get_graph_indexer, get_parser_registry
from app.graph.extractor import EntityExtractor
from app.parser.exceptions import ParseError, UnsupportedFileTypeError

router = APIRouter(tags=["ingest"])


@router.post("/ingest", response_model=IngestResponse, status_code=202)
async def ingest(request: IngestRequest) -> IngestResponse:
    files = _resolve_sources(request)
    if not files:
        raise HTTPException(status_code=400, detail="No supported files found for ingest")

    job = job_registry.submit(files)
    asyncio.create_task(_process_job(job.job_id))
    return IngestResponse(
        job_id=job.job_id,
        status=job.status,
        estimated_files=len(files),
        message=f"Ingest job queued. Poll /ingest/{job.job_id} for status.",
    )


@router.get("/ingest/{job_id}", response_model=IngestStatusResponse)
def ingest_status(job_id: str) -> IngestStatusResponse:
    job = job_registry.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return IngestStatusResponse(
        job_id=job.job_id,
        status=job.status,
        files_processed=job.files_processed,
        files_failed=job.files_failed,
        failed_files=job.failed_files,
        chunks_created=job.chunks_created,
        nodes_created=job.nodes_created,
        edges_created=job.edges_created,
        error=job.error,
    )


async def _process_job(job_id: str) -> None:
    job = job_registry.get(job_id)
    if job is None:
        return

    parser_registry = get_parser_registry()
    chunker = Chunker()
    chunk_indexer = get_chunk_indexer()
    graph_indexer = get_graph_indexer()
    extractor = EntityExtractor()

    job_registry.update(job_id, status="processing", started_at=utc_now())
    try:
        for file_path in job.files:
            try:
                source_hash = _source_hash(file_path)
                parser = parser_registry.get_parser(file_path)
                ir = parser.parse(file_path, source_hash)
                chunks = chunker.chunk(ir, version="dev")
                indexed_chunks = await asyncio.to_thread(chunk_indexer.index, chunks)
                nodes, edges = extractor.extract(ir)
                await asyncio.to_thread(graph_indexer.index, nodes, edges)
                chunk_mapping = {chunk.entity_name: chunk.chunk_id for chunk in indexed_chunks}
                await asyncio.to_thread(graph_indexer.link_chunk_ids, chunk_mapping)
                job.files_processed += 1
                job.chunks_created += len(indexed_chunks)
                job.nodes_created += len(nodes)
                job.edges_created += len(edges)
            except (ParseError, UnsupportedFileTypeError, FileNotFoundError) as exc:
                job.files_failed += 1
                job.failed_files.append({"path": file_path, "error": str(exc)})
        job_registry.update(job_id, status="completed", finished_at=utc_now())
    except Exception as exc:
        job_registry.update(job_id, status="failed", error=str(exc), finished_at=utc_now())


def _resolve_sources(request: IngestRequest) -> list[str]:
    files: list[str] = []
    for source in request.sources:
        path = Path(source.path)
        if source.type == "file" and path.exists():
            files.append(str(path))
        elif source.type == "directory" and path.exists():
            patterns = source.include_patterns or ["*.py", "*.md", "*.pdf"]
            for pattern in patterns:
                files.extend(str(candidate) for candidate in path.rglob(pattern) if candidate.is_file())
        elif source.type == "git_repo" and path.exists():
            files.extend(str(candidate) for candidate in path.rglob("*.py") if candidate.is_file())
            files.extend(str(candidate) for candidate in path.rglob("*.md") if candidate.is_file())
            if source.include_git_log:
                files.append(str(path / ".git"))
    return list(dict.fromkeys(files))


def _source_hash(file_path: str) -> str:
    import hashlib

    path = Path(file_path)
    if path.name == ".git":
        return "git-log"
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
