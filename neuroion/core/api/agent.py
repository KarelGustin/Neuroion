"""
Agent API: status and future proxy to Neuroion Agent (OpenClaw).

All agent-related access goes through this API; no OpenClaw branding in responses.
"""
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api", tags=["agent"])


class AgentStatusResponse(BaseModel):
    """Neuroion Agent status (consumer-facing; no vendor names)."""
    name: str = "Neuroion Agent"
    running: bool


@router.get("/agent/status", response_model=AgentStatusResponse)
def get_agent_status() -> AgentStatusResponse:
    """
    Get Neuroion Agent status. Use this API as the single entry point for agent status.
    """
    try:
        from neuroion.core.services import openclaw_adapter
        running = openclaw_adapter.is_running()
    except Exception:
        running = False
    return AgentStatusResponse(name="Neuroion Agent", running=running)
