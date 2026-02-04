"""
Integration framework for external services.

Provides OAuth flows and integration management for services like Gmail.
"""
from neuroion.core.integrations.base import BaseIntegration
from neuroion.core.integrations.gmail import GmailIntegration

__all__ = ["BaseIntegration", "GmailIntegration"]
