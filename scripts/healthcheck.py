import sys

import httpx


def main() -> int:
    try:
        response = httpx.get("http://localhost:8000/health", timeout=5.0)
        response.raise_for_status()
    except Exception as exc:
        print(f"Health check failed: {exc}")
        return 1

    print(response.text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
