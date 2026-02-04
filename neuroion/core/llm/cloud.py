"""
Cloud LLM client implementation.

Connects to free cloud LLM providers (HuggingFace Inference API, Groq, etc.).
"""
import requests
from typing import List, Dict, Optional, Iterator
import time
import json

from neuroion.core.llm.base import LLMClient


class CloudLLMClient(LLMClient):
    """Free cloud LLM client using HuggingFace Inference API."""
    
    def __init__(
        self,
        model: str = "mistralai/Mixtral-8x7B-Instruct-v0.1",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 120,
    ):
        """
        Initialize cloud LLM client.
        
        Args:
            model: Model identifier (HuggingFace model path)
            api_key: Optional API key (for private models or rate limits)
            base_url: Optional custom base URL (defaults to HuggingFace Inference API)
            timeout: Request timeout in seconds
        """
        self.model = model
        self.api_key = api_key
        self.base_url = base_url or "https://api-inference.huggingface.co/models"
        self.timeout = timeout
        self.chat_url = f"{self.base_url}/{model}"
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers."""
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
    
    def _make_request(
        self,
        payload: Dict,
        stream: bool = False,
    ) -> requests.Response:
        """
        Make HTTP request to cloud LLM API with retry logic.
        
        Args:
            payload: Request payload
            stream: Whether to stream response
        
        Returns:
            Response object
        
        Raises:
            requests.RequestException on failure
        """
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    self.chat_url,
                    json=payload,
                    headers=self._get_headers(),
                    timeout=self.timeout,
                    stream=stream,
                )
                
                # Handle rate limiting and model loading
                if response.status_code == 503:
                    # Model is loading, wait and retry
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
    
    def _format_messages(self, messages: List[Dict[str, str]]) -> str:
        """
        Format messages for HuggingFace chat template.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
        
        Returns:
            Formatted prompt string
        """
        # HuggingFace models typically use a simple format
        formatted = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                formatted.append(f"System: {content}")
            elif role == "user":
                formatted.append(f"User: {content}")
            elif role == "assistant":
                formatted.append(f"Assistant: {content}")
        
        return "\n".join(formatted)
    
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
        # Format messages for the model
        prompt = self._format_messages(messages)
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "temperature": temperature,
                "return_full_text": False,
            },
        }
        
        if max_tokens:
            payload["parameters"]["max_new_tokens"] = max_tokens
        
        response = self._make_request(payload)
        data = response.json()
        
        # HuggingFace returns: [{"generated_text": "..."}]
        if isinstance(data, list) and len(data) > 0:
            return data[0].get("generated_text", "")
        elif isinstance(data, dict):
            return data.get("generated_text", data.get("text", ""))
        
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
        payload = {
            "inputs": prompt,
            "parameters": {
                "temperature": temperature,
                "return_full_text": False,
            },
        }
        
        if max_tokens:
            payload["parameters"]["max_new_tokens"] = max_tokens
        
        response = self._make_request(payload)
        data = response.json()
        
        # HuggingFace returns: [{"generated_text": "..."}]
        if isinstance(data, list) and len(data) > 0:
            return data[0].get("generated_text", "")
        elif isinstance(data, dict):
            return data.get("generated_text", data.get("text", ""))
        
        return ""
    
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
        prompt = self._format_messages(messages)
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "temperature": temperature,
                "return_full_text": False,
            },
            "options": {
                "wait_for_model": True,
            },
        }
        
        response = self._make_request(payload, stream=True)
        
        for line in response.iter_lines():
            if line:
                try:
                    data = json.loads(line)
                    text = data.get("generated_text", "")
                    if text:
                        yield text
                except json.JSONDecodeError:
                    continue
