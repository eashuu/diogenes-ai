"""
API Endpoint Verification Script

Verifies that all API endpoints are accessible and respond correctly.
Run this after starting the backend to diagnose connection issues.
"""

import asyncio
import httpx
import json
from datetime import datetime


API_BASE = "http://localhost:8000"
TIMEOUT = 10.0


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'


def print_success(msg):
    print(f"{Colors.GREEN}✓{Colors.RESET} {msg}")


def print_error(msg):
    print(f"{Colors.RED}✗{Colors.RESET} {msg}")


def print_info(msg):
    print(f"{Colors.BLUE}ℹ{Colors.RESET} {msg}")


def print_warning(msg):
    print(f"{Colors.YELLOW}⚠{Colors.RESET} {msg}")


async def check_endpoint(client: httpx.AsyncClient, method: str, path: str, expected_status: int = 200, data: dict = None):
    """Check a single endpoint."""
    url = f"{API_BASE}{path}"
    try:
        if method == "GET":
            response = await client.get(url)
        elif method == "POST":
            response = await client.post(url, json=data or {})
        elif method == "PUT":
            response = await client.put(url, json=data or {})
        elif method == "DELETE":
            response = await client.delete(url)
        else:
            print_error(f"Unknown method: {method}")
            return False
        
        if response.status_code == expected_status:
            print_success(f"{method} {path} → {response.status_code}")
            return True
        else:
            print_error(f"{method} {path} → {response.status_code} (expected {expected_status})")
            return False
    except httpx.ConnectError:
        print_error(f"{method} {path} → Connection refused")
        return False
    except httpx.TimeoutException:
        print_error(f"{method} {path} → Timeout")
        return False
    except Exception as e:
        print_error(f"{method} {path} → {type(e).__name__}: {e}")
        return False


async def main():
    print("=" * 70)
    print("Diogenes API Endpoint Verification")
    print("=" * 70)
    print(f"Testing API at: {API_BASE}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        results = []
        
        # ===================================================================
        # Health Endpoints
        # ===================================================================
        print_info("Health Endpoints")
        results.append(await check_endpoint(client, "GET", "/health/"))
        results.append(await check_endpoint(client, "GET", "/health/live"))
        results.append(await check_endpoint(client, "GET", "/health/ready"))
        results.append(await check_endpoint(client, "GET", "/health/metrics"))
        print()
        
        # ===================================================================
        # Research Endpoints
        # ===================================================================
        print_info("Research Endpoints")
        results.append(await check_endpoint(client, "GET", "/api/v1/research/profiles"))
        results.append(await check_endpoint(client, "GET", "/api/v1/research/health"))
        results.append(await check_endpoint(client, "GET", "/api/v1/research/sessions"))
        
        # POST research (expecting 422 for empty data, but confirms endpoint exists)
        results.append(await check_endpoint(
            client, "POST", "/api/v1/research/",
            expected_status=422,  # Missing required fields
            data={}
        ))
        print()
        
        # ===================================================================
        # Settings Endpoints
        # ===================================================================
        print_info("Settings Endpoints")
        results.append(await check_endpoint(client, "GET", "/api/v1/settings/"))
        results.append(await check_endpoint(client, "GET", "/api/v1/settings/llm/models"))
        results.append(await check_endpoint(client, "GET", "/api/v1/settings/status"))
        print()
        
        # ===================================================================
        # Memory Endpoints
        # ===================================================================
        print_info("Memory Endpoints")
        results.append(await check_endpoint(client, "GET", "/api/v1/memory/"))
        
        # POST memory (expecting 422 for empty data, but confirms endpoint exists)
        results.append(await check_endpoint(
            client, "POST", "/api/v1/memory/",
            expected_status=422,  # Missing required fields
            data={}
        ))
        print()
        
        # ===================================================================
        # Summary
        # ===================================================================
        print("=" * 70)
        passed = sum(results)
        total = len(results)
        success_rate = (passed / total * 100) if total > 0 else 0
        
        if passed == total:
            print_success(f"All {total} endpoints passed!")
        else:
            print_warning(f"{passed}/{total} endpoints passed ({success_rate:.0f}%)")
            print_error(f"{total - passed} endpoints failed")
        
        print("=" * 70)
        
        # Detailed service status
        print()
        print_info("Service Status Check")
        try:
            response = await client.get(f"{API_BASE}/api/v1/settings/status")
            if response.status_code == 200:
                status = response.json()
                for service, info in status.items():
                    if info.get("healthy"):
                        print_success(f"{service}: {info.get('url', 'N/A')}")
                    else:
                        print_error(f"{service}: {info.get('error', 'Unknown error')}")
        except Exception as e:
            print_error(f"Could not fetch service status: {e}")
        
        print()
        return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    if not success:
        print()
        print_warning("Some endpoints failed. Common fixes:")
        print("  1. Ensure backend is running: python run_api.py")
        print("  2. Check Ollama is running: ollama serve")
        print("  3. Check SearXNG is running on port 8888")
        print("  4. Verify .env configuration")
        print()
        print("For detailed startup guide, see: STARTUP_GUIDE.md")
        exit(1)
    exit(0)
