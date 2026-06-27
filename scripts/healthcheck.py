import sys
import os

import httpx


def main() -> int:
    api_url = os.getenv("KNOWLEDGE_HUB_URL", "http://localhost:8000")
    try:
        response = httpx.get(f"{api_url.rstrip('/')}/health", timeout=5.0)
        response.raise_for_status()
    except Exception as exc:
        print(f"Health check failed: {exc}")
        return 1

    print(response.text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
