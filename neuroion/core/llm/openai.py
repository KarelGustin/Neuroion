"""
OpenAI-compatible LLM client implementation.

Supports OpenAI, Anthropic, and other OpenAI-compatible APIs.
"""
import requests
from typing import List, Dict, Optional, Iterator
import time
import json

from neuroion.core.llm.base import LLMClient


class OpenAILLMClient(LLMClient):
    """OpenAI-compatible API client (OpenAI, Anthropic, etc.)."""
    
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        timeout: int = 120,
    ):
        """
        Initialize OpenAI-compatible client.
        
        Args:
            api_key: API key for authentication
            base_url: Base URL for the API (e.g., https://api.openai.com/v1)
            model: Model identifier
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.chat_url = f"{self.base_url}/chat/completions"
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers."""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
    
    def _make_request(
        self,
        payload: Dict,
        stream: bool = False,
    ) -> requests.Response:
        """
        Make HTTP request to OpenAI-compatible API with retry logic.
        
        Args:
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
                    self.chat_url,
                    json=payload,
                    headers=self._get_headers(),
                    timeout=self.timeout,
                    stream=stream,
                )
                
                # Handle rate limiting
                if response.status_code == 429:
                    wait_time = retry_delay * (attempt + 1)
                    time.sleep(wait_time)
                    continue
                
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
            max_tokens: Maximum tokens in response
        
        Returns:
            Generated text response
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
        
        response = self._make_request(payload)
        data = response.json()
        
        # OpenAI returns: {"choices": [{"message": {"content": "..."}}]}
        if "choices" in data and len(data["choices"]) > 0:
            return data["choices"][0]["message"]["content"]
        
        return ""
    
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
        # Convert prompt to chat format
        messages = [{"role": "user", "content": prompt}]
        return self.chat(messages, temperature, max_tokens)
    
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
            "temperature": temperature,
            "stream": True,
        }
        
        response = self._make_request(payload, stream=True)
        
        for line in response.iter_lines():
            if line:
                line_str = line.decode("utf-8")
                if line_str.startswith("data: "):
                    data_str = line_str[6:]  # Remove "data: " prefix
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        if "choices" in data and len(data["choices"]) > 0:
                            delta = data["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                    except json.JSONDecodeError:
                        continue
