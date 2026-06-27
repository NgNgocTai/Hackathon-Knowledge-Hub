import argparse
import json
import os
import sys

import httpx


DEFAULT_API_URL = "http://localhost:8000"
DEFAULT_API_KEY = "dev-secret-key"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a demo query against Knowledge Hub.")
    parser.add_argument("query", nargs="?", default="How does the ingest pipeline work?")
    parser.add_argument("--api-url", default=os.getenv("KNOWLEDGE_HUB_URL", DEFAULT_API_URL))
    parser.add_argument("--api-key", default=os.getenv("API_KEY", DEFAULT_API_KEY))
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--no-graph", action="store_true", help="Disable graph expansion for comparison.")
    args = parser.parse_args()

    payload = {
        "query": args.query,
        "top_k": args.top_k,
        "options": {"enable_graph_expansion": not args.no_graph, "max_hops": 2},
    }
    try:
        response = httpx.post(
            f"{args.api_url.rstrip('/')}/query",
            headers={"X-API-Key": args.api_key},
            json=payload,
            timeout=30.0,
        )
        response.raise_for_status()
    except Exception as exc:
        print(f"Query failed: {exc}")
        return 1

    print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
