"""Simple script to test the configured SearXNG endpoint using the project's settings.

Run from project root (PowerShell):
    python scripts/test_searx.py "Python programming language definition"

This script adds the project root to `sys.path` so `src` can be imported
when running the script directly from `scripts/` in Windows PowerShell.
"""

from pathlib import Path
import sys
import asyncio
import httpx
import json
import traceback

# Ensure project root is on sys.path so `src` package imports work
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import get_settings


async def main():
    try:
        settings = get_settings()
        base = settings.search.base_url
        timeout = settings.search.timeout or 20.0

        q = sys.argv[1] if len(sys.argv) > 1 else "What is the Python programming language?"
        params = {
            "q": q,
            "format": "json",
            "categories": ",".join(settings.search.categories),
            "language": settings.search.language,
        }

        url = f"{base.rstrip('/')}/search"
        print("REQUEST:", url)
        print("PARAMS:", params)

        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url, params=params)

            print("STATUS:", resp.status_code)
            print("HEADERS:", dict(resp.headers))

            # Try to parse JSON, otherwise print raw text
            try:
                data = resp.json()
                print("RESULTS COUNT:", len(data.get("results", [])))
                print(json.dumps(data, indent=2)[:10000])
            except Exception as e:
                print("Failed to parse JSON:", e)
                print("RESPONSE TEXT (first 2000 chars):")
                print(resp.text[:2000])

    except Exception:
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
