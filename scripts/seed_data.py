import argparse
import os
import sys
import time

import httpx


DEFAULT_API_URL = "http://localhost:8000"
DEFAULT_API_KEY = "dev-secret-key"


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed Knowledge Hub with local project files.")
    parser.add_argument("--api-url", default=os.getenv("KNOWLEDGE_HUB_URL", DEFAULT_API_URL))
    parser.add_argument("--api-key", default=os.getenv("API_KEY", DEFAULT_API_KEY))
    parser.add_argument("--path", default="app", help="File or directory path to ingest.")
    parser.add_argument("--timeout", type=int, default=180, help="Seconds to wait for ingest completion.")
    args = parser.parse_args()

    client = httpx.Client(base_url=args.api_url, headers={"X-API-Key": args.api_key}, timeout=30.0)
    payload = {
        "sources": [
            {
                "type": "directory",
                "path": args.path,
                "include_patterns": ["*.py", "*.md"],
                "exclude_patterns": ["__pycache__/*", "*.pyc"],
            }
        ]
    }

    try:
        response = client.post("/ingest", json=payload)
        response.raise_for_status()
    except Exception as exc:
        print(f"Failed to submit ingest job: {exc}")
        return 1

    job = response.json()
    job_id = job["job_id"]
    print(f"Queued ingest job {job_id} for {args.path}")

    deadline = time.time() + args.timeout
    while time.time() < deadline:
        try:
            status_response = client.get(f"/ingest/{job_id}")
            status_response.raise_for_status()
        except Exception as exc:
            print(f"Failed to poll ingest job {job_id}: {exc}")
            return 1

        status = status_response.json()
        print(
            "status={status} files_processed={files_processed} "
            "files_failed={files_failed} chunks_created={chunks_created} nodes_created={nodes_created}".format(
                **status
            )
        )
        if status["status"] in {"completed", "failed"}:
            return 0 if status["status"] == "completed" else 1
        time.sleep(2)

    print(f"Timed out waiting for ingest job {job_id}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
