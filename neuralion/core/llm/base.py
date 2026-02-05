"""
Abstract LLM interface.

Defines the standard interface for LLM clients to allow model swapping.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Iterator


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
