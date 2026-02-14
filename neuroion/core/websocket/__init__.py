"""
WebSocket layer for chat, heartbeat, proactive messages, and agenda sync.

One connection per user (MVP). Heartbeat every 60s; timeout 90s.
"""

from neuroion.core.websocket.manager import connection_manager

__all__ = ["connection_manager"]
