"""
Ollama LLM client implementation.

Connects to local Ollama instance for LLM inference.
"""
import requests
from typing import List, Dict, Optional, Iterator
import time

from neuralion.core.config import settings
from neuralion.core.llm.base import LLMClient


class OllamaClient(LLMClient):
    """Ollama LLM client."""
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        """
        Initialize Ollama client.
        
        Args:
            base_url: Ollama base URL (defaults to config)
            model: Model name (defaults to config)
            timeout: Request timeout in seconds (defaults to config)
        """
        self.base_url = base_url or settings.ollama_url
        self.model = model or settings.ollama_model
        self.timeout = timeout or settings.ollama_timeout
        self.chat_url = f"{self.base_url}/api/chat"
        self.generate_url = f"{self.base_url}/api/generate"
    
    def _make_request(
        self,
        url: str,
        payload: Dict,
        stream: bool = False,
    ) -> requests.Response:
        """
        Make HTTP request to Ollama with retry logic.
        
        Args:
            url: API endpoint URL
            payload: Request payload
            stream: Whether to stream response
        
        Returns:
            Response object
        
        Raises:
            requests.RequestException on failure
        """
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    url,
                    json=payload,
                    timeout=self.timeout,
                    stream=stream,
                )
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                raise
    
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
            max_tokens: Maximum tokens in response (Ollama uses num_predict)
        
        Returns:
            Generated text response
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }
        
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens
        
        response = self._make_request(self.chat_url, payload)
        data = response.json()
        
        # Ollama returns: {"message": {"role": "assistant", "content": "..."}, ...}
        return data.get("message", {}).get("content", "")
    
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
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }
        
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens
        
        response = self._make_request(self.generate_url, payload)
        data = response.json()
        
        # Ollama returns: {"response": "...", ...}
        return data.get("response", "")
    
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
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": temperature,
            },
        }
        
        response = self._make_request(self.chat_url, payload, stream=True)
        
        for line in response.iter_lines():
            if line:
                try:
                    import json
                    data = json.loads(line)
                    content = data.get("message", {}).get("content", "")
                    if content:
                        yield content
                except json.JSONDecodeError:
                    continue


# Global LLM client instance
_llm_client: Optional[OllamaClient] = None


def get_llm_client() -> OllamaClient:
    """Get or create the global LLM client instance."""
    global _llm_client
    if _llm_client is None:
        _llm_client = OllamaClient()
    return _llm_client
