from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import httpx


@dataclass
class OllamaClient:
    base_url: str
    model: str
    timeout_seconds: float = 30.0

    def _client(self) -> httpx.Client:
        return httpx.Client(base_url=self.base_url, timeout=self.timeout_seconds)

    def extract_json(self, prompt: str, *, system: Optional[str] = None) -> dict[str, Any]:
        """
        Uses Ollama /api/chat for structured extraction.
        """
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "format": "json",
        }

        with self._client() as c:
            r = c.post("/api/chat", json=payload)
            r.raise_for_status()
            data = r.json()

        # Ollama returns something like: {"message":{"content":"{...json...}"}, ...}
        content = data.get("message", {}).get("content")
        if not content:
            raise ValueError("Ollama returned empty content")

        # content should already be JSON text because format=json
        import json
        return json.loads(content)