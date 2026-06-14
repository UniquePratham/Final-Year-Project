import json
from typing import Generator, Optional
import httpx
from backend.shared.utils import get_logger, get_config

logger = get_logger("AIAdapter")

class AIAdapter:
    def __init__(self, provider: str, model: str, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.provider = provider.lower()
        self.model = model
        self.api_key = api_key or get_config(f"{self.provider.upper()}_API_KEY")
        self.base_url = base_url

        # Establish defaults
        if self.provider == "openai" and not self.base_url:
            self.base_url = "https://api.openai.com/v1"
        elif self.provider == "groq" and not self.base_url:
            self.base_url = "https://api.groq.com/openai/v1"
        elif self.provider == "openrouter" and not self.base_url:
            self.base_url = "https://openrouter.ai/api/v1"
        elif self.provider == "ollama" and not self.base_url:
            self.base_url = "http://localhost:11434/v1"
        elif self.provider == "anthropic" and not self.base_url:
            self.base_url = "https://api.anthropic.com/v1"

    def generate(self, prompt: str, system_instruction: str = "", temperature: float = 0.7, max_tokens: int = 4096) -> str:
        """Synchronously generate text response from LLM with automatic retries for rate limits or timeouts."""
        import time
        logger.info(f"Generating content using provider={self.provider}, model={self.model}")
        
        max_retries = 3
        backoff = 2.0
        
        for attempt in range(max_retries + 1):
            try:
                if self.provider == "gemini":
                    return self._generate_gemini(prompt, system_instruction)
                elif self.provider in ["openai", "groq", "openrouter", "ollama", "custom"]:
                    return self._generate_openai_compatible(prompt, system_instruction, temperature, max_tokens)
                elif self.provider == "anthropic":
                    return self._generate_anthropic(prompt, system_instruction, temperature, max_tokens)
                else:
                    raise ValueError(f"Unsupported provider: {self.provider}")
            except Exception as e:
                err_str = str(e).lower()
                is_rate_limit = "429" in err_str or "resourceexhausted" in err_str or "rate limit" in err_str or "quota" in err_str
                is_timeout = isinstance(e, (httpx.TimeoutException, httpx.NetworkError)) or "timeout" in err_str
                
                if attempt < max_retries and (is_rate_limit or is_timeout):
                    sleep_time = backoff * (2 ** attempt)
                    logger.warning(f"Attempt {attempt + 1} failed for {self.provider} due to rate limit/timeout. Retrying in {sleep_time:.1f}s... Error: {e}")
                    time.sleep(sleep_time)
                else:
                    logger.error(f"Error generating from {self.provider} after {attempt + 1} attempts: {e}")
                    raise

    def stream(self, prompt: str, system_instruction: str = "", temperature: float = 0.7, max_tokens: int = 4096) -> Generator[str, None, None]:
        """Stream token-by-token response from LLM."""
        logger.info(f"Streaming content using provider={self.provider}, model={self.model}")
        try:
            if self.provider == "gemini":
                yield from self._stream_gemini(prompt, system_instruction)
            elif self.provider in ["openai", "groq", "openrouter", "ollama", "custom"]:
                yield from self._stream_openai_compatible(prompt, system_instruction, temperature, max_tokens)
            elif self.provider == "anthropic":
                yield from self._stream_anthropic(prompt, system_instruction, temperature, max_tokens)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")
        except Exception as e:
            logger.error(f"Error streaming from {self.provider}: {e}")
            raise

    def _generate_gemini(self, prompt: str, system_instruction: str) -> str:
        import google.generativeai as genai
        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel(
            model_name=self.model,
            system_instruction=system_instruction if system_instruction else None
        )
        response = model.generate_content(prompt)
        return response.text

    def _stream_gemini(self, prompt: str, system_instruction: str) -> Generator[str, None, None]:
        import google.generativeai as genai
        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel(
            model_name=self.model,
            system_instruction=system_instruction if system_instruction else None
        )
        response = model.generate_content(prompt, stream=True)
        for chunk in response:
            yield chunk.text

    def _generate_openai_compatible(self, prompt: str, system_instruction: str, temperature: float = 0.7, max_tokens: int = 4096) -> str:
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        timeout = 180.0 if self.provider in ("ollama", "custom") else 90.0
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    def _stream_openai_compatible(self, prompt: str, system_instruction: str, temperature: float = 0.7, max_tokens: int = 4096) -> Generator[str, None, None]:
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        timeout = 180.0 if self.provider in ("ollama", "custom") else 90.0
        with httpx.Client(timeout=timeout) as client:
            with client.stream("POST", f"{self.base_url}/chat/completions", headers=headers, json=payload) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line:
                        continue
                    if line.startswith("data: "):
                        line_content = line[6:]
                        if line_content == "[DONE]":
                            break
                        try:
                            chunk_data = json.loads(line_content)
                            delta = chunk_data["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except Exception:
                            continue

    def _generate_anthropic(self, prompt: str, system_instruction: str, temperature: float = 0.7, max_tokens: int = 4096) -> str:
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system_instruction:
            payload["system"] = system_instruction

        with httpx.Client(timeout=90.0) as client:
            resp = client.post(f"{self.base_url}/messages", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["content"][0]["text"]

    def _stream_anthropic(self, prompt: str, system_instruction: str, temperature: float = 0.7, max_tokens: int = 4096) -> Generator[str, None, None]:
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "stream": True,
            "temperature": temperature,
        }
        if system_instruction:
            payload["system"] = system_instruction

        with httpx.Client(timeout=90.0) as client:
            with client.stream("POST", f"{self.base_url}/messages", headers=headers, json=payload) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line:
                        continue
                    if line.startswith("data: "):
                        try:
                            event_data = json.loads(line[6:])
                            if event_data.get("type") == "content_block_delta":
                                text = event_data["delta"].get("text", "")
                                if text:
                                    yield text
                        except Exception:
                            continue
