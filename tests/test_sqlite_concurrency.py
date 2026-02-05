"""
Simple concurrency stress test for SQLite/SQLAlchemy usage.

This is not a formal test suite but a helper you can run manually against a
running Neuroion Homebase instance to verify that concurrent traffic and
shutdown do not trigger crashes or cross-thread session misuse.
"""
import asyncio
import os
from typing import List

import httpx


API_BASE_URL = os.getenv("NEUROION_API_BASE_URL", "http://localhost:8000")
CHAT_ENDPOINT = f"{API_BASE_URL}/chat"
DASHBOARD_STATS_ENDPOINT = f"{API_BASE_URL}/dashboard/stats"
EVENTS_ENDPOINT = f"{API_BASE_URL}/events"


async def _fire_chat_request(client: httpx.AsyncClient, token: str, message: str) -> None:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    await client.post(CHAT_ENDPOINT, json={"message": message}, headers=headers)


async def _fire_dashboard_stats_request(client: httpx.AsyncClient) -> None:
    await client.get(DASHBOARD_STATS_ENDPOINT)


async def _fire_event_request(client: httpx.AsyncClient, token: str) -> None:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    payload = {
        "event_type": "location",
        "location": {
            "event_type": "arriving_home",
            "metadata": {"source": "stress_test"},
        },
    }
    await client.post(EVENTS_ENDPOINT, json=payload, headers=headers)


async def run_stress_round(
    concurrent_requests: int = 50,
    token: str = "",
) -> None:
    """
    Run a single round of mixed concurrent requests against the API.

    Args:
        concurrent_requests: Total number of concurrent HTTP requests to fire.
        token: Optional bearer token for authenticated endpoints (chat/events).
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        tasks: List[asyncio.Task] = []
        for i in range(concurrent_requests):
            # Mix of chat, dashboard stats, and events
            if i % 3 == 0:
                tasks.append(
                    asyncio.create_task(
                        _fire_chat_request(client, token, f"stress test message {i}")
                    )
                )
            elif i % 3 == 1:
                tasks.append(
                    asyncio.create_task(_fire_dashboard_stats_request(client))
                )
            else:
                tasks.append(
                    asyncio.create_task(_fire_event_request(client, token))
                )

        await asyncio.gather(*tasks, return_exceptions=True)


async def main() -> None:
    """
    Entry point for manual stress testing.

    Usage:
        1. Start the Neuroion server (uvicorn neuroion.core.main:app ...).
        2. Export NEUROION_API_BASE_URL if not using http://localhost:8000.
        3. Optionally export NEUROION_TEST_TOKEN with a valid JWT for chat/events.
        4. Run: python -m tests.test_sqlite_concurrency
    """
    token = os.getenv("NEUROION_TEST_TOKEN", "")
    rounds = int(os.getenv("NEUROION_STRESS_ROUNDS", "5"))
    concurrent = int(os.getenv("NEUROION_STRESS_CONCURRENCY", "50"))

    for i in range(rounds):
        print(f"Running stress round {i + 1}/{rounds} with {concurrent} concurrent requests...")
        await run_stress_round(concurrent_requests=concurrent, token=token)

    print("Stress test completed. Check server logs for any RuntimeError from "
          "require_active_session or validate_session_owner_thread, and verify "
          "that no crashes (e.g., SIGSEGV) occurred.")


if __name__ == "__main__":
    asyncio.run(main())

