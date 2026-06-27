import argparse
import os
import sys
import time
from pathlib import Path
from typing import Any

import httpx

sys.path.append(str(Path(__file__).resolve().parents[1]))

from scripts.evaluate_retrieval import (
    DEFAULT_EVAL_PATH,
    EvalCase,
    evaluate_results,
    load_cases,
    mean_reciprocal_rank,
    print_report,
    query_api,
    recall_at_k,
)


DEFAULT_API_URL = "http://localhost:8000"
DEFAULT_API_KEY = "dev-secret-key"
DEFAULT_QUERIES = [
    "Where is the ingest route implemented?",
    "Where does sync_file delete chunks from vector store?",
    "Where does the Python parser extract classes and functions?",
]


def check_health(client: httpx.Client) -> None:
    response = client.get("/health")
    response.raise_for_status()
    health = response.json()
    print(f"health={health['status']}")


def seed_path(client: httpx.Client, source_path: str, timeout: int) -> None:
    payload = {
        "sources": [
            {
                "type": "directory",
                "path": source_path,
                "include_patterns": ["*.py", "*.md"],
                "exclude_patterns": ["__pycache__/*", "*.pyc"],
            }
        ]
    }
    response = client.post("/ingest", json=payload)
    response.raise_for_status()
    job_id = response.json()["job_id"]
    print(f"seed_job={job_id} path={source_path}")

    deadline = time.time() + timeout
    while time.time() < deadline:
        status_response = client.get(f"/ingest/{job_id}")
        status_response.raise_for_status()
        status = status_response.json()
        print(
            "seed_status={status} files={files_processed} chunks={chunks_created} nodes={nodes_created}".format(
                **status
            )
        )
        if status["status"] == "completed":
            return
        if status["status"] == "failed":
            raise RuntimeError(f"Ingest job failed: {status}")
        time.sleep(2)
    raise TimeoutError(f"Timed out waiting for ingest job {job_id}")


def run_sample_queries(api_url: str, api_key: str, queries: list[str], top_k: int, threshold: float) -> None:
    for query in queries:
        results = query_api(api_url, api_key, query, top_k, threshold, enable_graph=True)
        first: dict[str, Any] = results[0] if results else {}
        metadata = first.get("metadata", {})
        entity = metadata.get("entity_name", "-")
        source_file = metadata.get("source_file", "-")
        print(f"query={query}")
        print(f"top_entity={entity} top_file={source_file} results={len(results)}")


def run_eval(api_url: str, api_key: str, cases: list[EvalCase], top_k: int, threshold: float) -> None:
    responses = {
        case.id: query_api(api_url, api_key, case.query, top_k, threshold, enable_graph=True)
        for case in cases
    }
    outcomes = evaluate_results(cases, responses)
    print_report(outcomes, top_k)
    print(f"demo_eval_pass={recall_at_k(outcomes) >= 0.8 and mean_reciprocal_rank(outcomes) >= 0.5}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Knowledge Hub hackathon demo flow.")
    parser.add_argument("--api-url", default=os.getenv("KNOWLEDGE_HUB_URL", DEFAULT_API_URL))
    parser.add_argument("--api-key", default=os.getenv("API_KEY", DEFAULT_API_KEY))
    parser.add_argument("--path", default="app", help="Path to ingest before demo queries.")
    parser.add_argument("--eval-path", default=DEFAULT_EVAL_PATH)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--threshold", type=float, default=0.35)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--skip-seed", action="store_true")
    args = parser.parse_args()

    client = httpx.Client(
        base_url=args.api_url,
        headers={"X-API-Key": args.api_key},
        timeout=30.0,
    )
    try:
        check_health(client)
        if not args.skip_seed:
            seed_path(client, args.path, args.timeout)
        run_sample_queries(args.api_url, args.api_key, DEFAULT_QUERIES, args.top_k, args.threshold)
        run_eval(args.api_url, args.api_key, load_cases(args.eval_path), args.top_k, args.threshold)
    except Exception as exc:
        print(f"Demo failed: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
