"""
LLM Client for Ollama Qwen Integration
Provides robust synchronous, asynchronous, and streaming interfaces for local LLM inference.
"""
import json
import logging
from typing import AsyncGenerator, Dict, Any, Optional
import httpx
from .config import settings

logger = logging.getLogger("localgpt.llm")

class OllamaClient:
    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.model = model or settings.ollama_model
        self.timeout = settings.llm_timeout

    def check_health(self) -> Dict[str, Any]:
        """Check if Ollama is running and the target model is available."""
        try:
            with httpx.Client(timeout=5.0) as client:
                res = client.get(f"{self.base_url}/api/tags")
                if res.status_code == 200:
                    data = res.json()
                    models = [m.get("name") for m in data.get("models", [])]
                    model_available = any(self.model in m for m in models)
                    return {
                        "online": True,
                        "available_models": models,
                        "target_model": self.model,
                        "model_ready": model_available
                    }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"online": False, "error": str(e), "target_model": self.model, "model_ready": False}
        return {"online": False, "target_model": self.model, "model_ready": False}

    def generate(self, prompt: str, system: Optional[str] = None, format_json: bool = False, temperature: float = 0.2) -> str:
        """Synchronous completion generation."""
        payload: Dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
            }
        }
        if system:
            payload["system"] = system
        if format_json:
            payload["format"] = "json"

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(f"{self.base_url}/api/generate", json=payload)
                response.raise_for_status()
                data = response.json()
                return data.get("response", "").strip()
        except Exception as e:
            logger.error(f"Error calling Ollama generate: {e}")
            raise RuntimeError(f"Ollama generation failed: {e}")

    async def generate_async(self, prompt: str, system: Optional[str] = None, format_json: bool = False, temperature: float = 0.2) -> str:
        """Asynchronous completion generation."""
        payload: Dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
            }
        }
        if system:
            payload["system"] = system
        if format_json:
            payload["format"] = "json"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(f"{self.base_url}/api/generate", json=payload)
                response.raise_for_status()
                data = response.json()
                return data.get("response", "").strip()
        except Exception as e:
            logger.error(f"Error in generate_async: {e}")
            raise RuntimeError(f"Ollama async generation failed: {e}")

    async def stream_generate(self, prompt: str, system: Optional[str] = None, temperature: float = 0.2) -> AsyncGenerator[str, None]:
        """Stream generated tokens from Ollama."""
        payload: Dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": temperature,
            }
        }
        if system:
            payload["system"] = system

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream("POST", f"{self.base_url}/api/generate", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        chunk_data = json.loads(line)
                        token = chunk_data.get("response", "")
                        if token:
                            yield token
                        if chunk_data.get("done", False):
                            break
                    except Exception:
                        continue

ollama_client = OllamaClient()
