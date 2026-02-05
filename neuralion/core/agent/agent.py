"""
Main agent orchestrator.

Interprets user intent, decides on actions, and coordinates tool execution.
"""
import json
import re
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from neuralion.core.llm.ollama import get_llm_client
from neuralion.core.agent.tools import get_tool_registry
from neuralion.core.agent.planner import Planner
from neuralion.core.agent.prompts import build_chat_messages, build_reasoning_prompt
from neuralion.core.memory.repository import (
    ContextSnapshotRepository,
    PreferenceRepository,
)
from neuralion.core.security.audit import AuditLogger


class Agent:
    """Main agent orchestrator."""
    
    def __init__(self):
        """Initialize agent with LLM client and tool registry."""
        self.llm = get_llm_client()
        self.tool_registry = get_tool_registry()
        self.planner = Planner(self.tool_registry)
    
    def process_message(
        self,
        db: Session,
        household_id: int,
        user_id: Optional[int],
        message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        Process a user message and return structured response.
        
        Args:
            db: Database session
            household_id: Household ID
            user_id: User ID (optional)
            message: User message
            conversation_history: Previous messages
        
        Returns:
            Dict with 'message', 'reasoning', and 'actions' keys
        """
        # Get context
        context_snapshots = ContextSnapshotRepository.get_recent(
            db, household_id, limit=10, user_id=user_id
        )
        context_dicts = [
            {
                "timestamp": str(snap.timestamp),
                "event_type": snap.event_type,
                "summary": snap.summary,
            }
            for snap in context_snapshots
        ]
        
        # Get preferences
        prefs = PreferenceRepository.get_all(db, household_id)
        prefs_dict = {pref.key: pref.value for pref in prefs}
        
        # Build messages for LLM
        messages = build_chat_messages(
            user_message=message,
            context_snapshots=context_dicts,
            preferences=prefs_dict,
            conversation_history=conversation_history,
        )
        
        # Get LLM response
        llm_response = self.llm.chat(messages, temperature=0.7)
        
        # Determine if action is needed
        action_decision = self._decide_action(message, llm_response)
        
        if action_decision["needs_action"]:
            # Propose action
            action = self._prepare_action(
                db, household_id, user_id, action_decision, llm_response
            )
            
            return {
                "message": llm_response,
                "reasoning": action_decision.get("reasoning", ""),
                "actions": [action],
            }
        else:
            # Direct answer
            return {
                "message": llm_response,
                "reasoning": "",
                "actions": [],
            }
    
    def _decide_action(
        self,
        user_message: str,
        llm_response: str,
    ) -> Dict[str, Any]:
        """
        Decide if an action is needed based on user message and LLM response.
        
        Returns:
            Dict with 'needs_action', 'tool_name', 'parameters', 'reasoning'
        """
        # Simple heuristic: check if response mentions tools or actions
        # In production, use a more sophisticated approach with LLM reasoning
        
        available_tools = self.tool_registry.get_tools_for_llm()
        tool_keywords = {
            "menu": "generate_week_menu",
            "grocery": "create_grocery_list",
            "shopping": "create_grocery_list",
            "preferences": "summarize_family_preferences",
        }
        
        message_lower = user_message.lower()
        response_lower = llm_response.lower()
        
        for keyword, tool_name in tool_keywords.items():
            if keyword in message_lower or keyword in response_lower:
                return {
                    "needs_action": True,
                    "tool_name": tool_name,
                    "parameters": {},
                    "reasoning": f"User message suggests {tool_name} might be useful",
                }
        
        return {
            "needs_action": False,
            "reasoning": "No action needed, direct answer sufficient",
        }
    
    def _prepare_action(
        self,
        db: Session,
        household_id: int,
        user_id: Optional[int],
        action_decision: Dict[str, Any],
        llm_response: str,
    ) -> Dict[str, Any]:
        """
        Prepare an action proposal.
        
        Returns:
            Action dict with 'id', 'name', 'description', 'parameters', 'reasoning'
        """
        tool_name = action_decision["tool_name"]
        tool = self.tool_registry.get(tool_name)
        
        if not tool:
            return {
                "id": None,
                "name": tool_name,
                "description": f"Unknown tool: {tool_name}",
                "parameters": {},
                "reasoning": "Tool not found",
            }
        
        # Log suggestion
        audit_id = AuditLogger.log_suggestion(
            db=db,
            household_id=household_id,
            action_name=tool_name,
            reasoning=action_decision.get("reasoning", llm_response),
            input_data=action_decision.get("parameters", {}),
            user_id=user_id,
        )
        
        return {
            "id": audit_id,
            "name": tool_name,
            "description": tool.description,
            "parameters": action_decision.get("parameters", {}),
            "reasoning": action_decision.get("reasoning", ""),
        }
    
    def execute_action(
        self,
        db: Session,
        household_id: int,
        user_id: Optional[int],
        action_id: int,
    ) -> Dict[str, Any]:
        """
        Execute a confirmed action.
        
        Args:
            db: Database session
            household_id: Household ID
            user_id: User ID
            action_id: Audit log ID of the action
        
        Returns:
            Execution result
        """
        from neuralion.core.memory.models import AuditLog
        
        # Get audit log
        audit_log = db.query(AuditLog).filter(AuditLog.id == action_id).first()
        if not audit_log:
            return {"success": False, "error": "Action not found"}
        
        # Confirm action
        AuditLogger.log_confirmation(db, action_id, user_id)
        
        # Get tool
        tool = self.tool_registry.get(audit_log.action_name)
        if not tool:
            AuditLogger.log_failure(db, action_id, f"Tool not found: {audit_log.action_name}")
            return {"success": False, "error": f"Tool not found: {audit_log.action_name}"}
        
        # Execute tool
        try:
            params = audit_log.input_data or {}
            params["household_id"] = household_id
            
            result = tool.func(db=db, **params)
            
            # Log success
            AuditLogger.log_execution(db, action_id, output_data=result)
            
            return {
                "success": True,
                "result": result,
            }
        except Exception as e:
            AuditLogger.log_failure(db, action_id, str(e))
            return {
                "success": False,
                "error": str(e),
            }
