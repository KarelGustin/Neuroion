"""
Connection manager: map user_id to WebSocket, pending proactive queue, send_to_user.
"""
import asyncio
import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Max JSON frame size (bytes)
MAX_FRAME_SIZE = 256 * 1024


class ConnectionManager:
    """Maps user_id to a single WebSocket; holds pending proactive messages per user."""

    def __init__(self) -> None:
        self._connections: Dict[int, Any] = {}  # user_id -> WebSocket
        self._pending_proactive: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def register(self, user_id: int, websocket: Any) -> None:
        """Register or replace WebSocket for user. Close previous if any."""
        async with self._lock:
            old = self._connections.get(user_id)
            if old is not None and old != websocket:
                try:
                    await old.close(code=4000, reason="Replaced by new connection")
                except Exception as e:
                    logger.debug("Close old WebSocket for user %s: %s", user_id, e)
            self._connections[user_id] = websocket
            logger.info("WebSocket registered for user_id=%s", user_id)

    async def unregister(self, user_id: int, websocket: Any) -> None:
        """Remove WebSocket for user if it matches."""
        async with self._lock:
            if self._connections.get(user_id) is websocket:
                del self._connections[user_id]
                logger.info("WebSocket unregistered for user_id=%s", user_id)

    def is_connected(self, user_id: int) -> bool:
        """Return True if user has an active WebSocket."""
        return user_id in self._connections

    async def get_connected_user_ids(self) -> List[int]:
        """Return list of user_ids that currently have an active WebSocket."""
        async with self._lock:
            return list(self._connections.keys())

    async def send_to_user(self, user_id: int, obj: Dict[str, Any]) -> bool:
        """Send JSON-serializable object to user's WebSocket. Returns True if sent."""
        async with self._lock:
            ws = self._connections.get(user_id)
        if ws is None:
            return False
        try:
            await ws.send_json(obj)
            return True
        except Exception as e:
            logger.warning("Send to user %s failed: %s", user_id, e)
            async with self._lock:
                if self._connections.get(user_id) is ws:
                    del self._connections[user_id]
            return False

    def enqueue_proactive(self, user_id: int, message: str, ts: str) -> None:
        """Add a proactive message to the user's queue (thread-safe, in-memory)."""
        self._pending_proactive[user_id].append({"message": message, "ts": ts})

    async def flush_pending_proactive(self, user_id: int) -> None:
        """Send all pending proactive messages to user and clear queue."""
        while True:
            async with self._lock:
                queue = self._pending_proactive[user_id]
                if not queue:
                    return
                item = queue.pop(0)
            payload = {"type": "proactive_message", "message": item["message"], "ts": item["ts"]}
            sent = await self.send_to_user(user_id, payload)
            if not sent:
                # Re-queue so we can retry later
                self._pending_proactive[user_id].insert(0, item)
                return


connection_manager = ConnectionManager()
