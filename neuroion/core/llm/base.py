"""
Abstract LLM interface.

Defines the standard interface for LLM clients to allow model swapping.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Optional, Iterator, Tuple, Any


@dataclass
class ToolCall:
    """A single tool call from the LLM."""
    id: str
    name: str
    arguments: Dict[str, Any]


class LLMClient(ABC):
    """Abstract base class for LLM clients."""
    
    @abstractmethod
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Send a chat completion request.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens in response
        
        Returns:
            Generated text response
        """
        pass

    def chat_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tool_choice: Optional[str] = None,
    ) -> Tuple[str, List[ToolCall]]:
        """
        Send a chat completion request with tools. Default: return (content, []).
        Override in clients that support tool_calls (e.g. OpenAI).
        """
        content = self.chat(messages, temperature=temperature, max_tokens=max_tokens)
        return (content or "", [])
    
    @abstractmethod
    def complete(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Send a simple completion request.
        
        Args:
            prompt: Input prompt text
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens in response
        
        Returns:
            Generated text response
        """
        pass
    
    @abstractmethod
    def stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
    ) -> Iterator[str]:
        """
        Stream a chat completion response.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (0.0-2.0)
        
        Yields:
            Text chunks as they are generated
        """
        pass
