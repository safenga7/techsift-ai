"""
Phase 0 - Test 4: FastAPI Server & Health Endpoint Feasibility Test
Starts a live uvicorn server instance, sends a real HTTP GET /health request,
and asserts HTTP 200 and expected JSON payload.
"""

import socket
import subprocess
import time
import sys
import httpx


def get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def run_fastapi_test() -> dict:
    port = get_free_port()
    url = f"http://127.0.0.1:{port}/health"

    # Start uvicorn server in a subprocess
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "src.api.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        # Wait briefly for server to bind
        time.sleep(1.5)

        # Send real HTTP request to root health
        with httpx.Client(timeout=5.0) as client:
            response = client.get(url)
            v1_response = client.get(f"http://127.0.0.1:{port}/api/v1/health")

        # Assertions
        assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
        assert v1_response.status_code == 200, f"Expected 200 OK on /api/v1/health, got {v1_response.status_code}"
        json_data = response.json()
        assert json_data.get("status") == "ok", f"Expected status 'ok', got {json_data.get('status')}"
        assert json_data.get("app") == "TechSift AI", f"Unexpected app name: {json_data.get('app')}"

        return {
            "status": "PASSED",
            "http_status_code": response.status_code,
            "response_json": json_data,
            "port_tested": port,
        }

    finally:
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()


if __name__ == "__main__":
    result = run_fastapi_test()
    print("--- FASTAPI HEALTH TEST RESULT ---")
    for k, v in result.items():
        print(f"{k}: {v}")
