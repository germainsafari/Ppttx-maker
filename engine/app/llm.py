"""Minimal client for an OpenAI-compatible local server (vLLM). No data leaves the LAN."""
import asyncio
import base64
import json
import logging
import re
import time
from typing import Any, Optional

import httpx
from pydantic import BaseModel, ValidationError

from .config import settings

log = logging.getLogger("llm")


class LLMError(RuntimeError):
    pass


class LLM:
    def __init__(self, base_url: str | None = None, model: str | None = None):
        self.base_url = (base_url or settings.llm_base_url).rstrip("/")
        self.model = model or settings.llm_model
        self.max_model_len: int = 8192
        self.sem = asyncio.Semaphore(settings.llm_concurrency)
        self.client = httpx.AsyncClient(
            timeout=settings.llm_timeout,
            headers={"Authorization": f"Bearer {settings.llm_api_key}"},
        )
        self.stats = {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "seconds": 0.0}

    async def init(self) -> dict:
        r = await self.client.get(f"{self.base_url}/models")
        r.raise_for_status()
        models = r.json()["data"]
        if not models:
            raise LLMError("LLM server has no models loaded")
        chosen = next((m for m in models if m["id"] == self.model), models[0])
        self.model = chosen["id"]
        self.max_model_len = int(chosen.get("max_model_len") or 8192)
        return {"model": self.model, "max_model_len": self.max_model_len}

    @property
    def supports_vision(self) -> bool:
        return bool(re.search(r"VL|vl-|Qwen3\.[5-9]|Qwen3-?[5-9]|gemma-[34]|llava|pixtral", self.model, re.I))

    async def chat(
        self,
        messages: list[dict],
        *,
        schema: Optional[type[BaseModel]] = None,
        max_tokens: int = 2048,
        temperature: float = 0.4,
    ) -> str:
        body: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": 0.9,
        }
        if settings.llm_disable_thinking:
            body["chat_template_kwargs"] = {"enable_thinking": False}
        if schema is not None:
            body["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": schema.__name__, "schema": schema.model_json_schema(), "strict": True},
            }
        async with self.sem:
            t0 = time.perf_counter()
            r = await self.client.post(f"{self.base_url}/chat/completions", json=body)
            dt = time.perf_counter() - t0
        if r.status_code != 200:
            raise LLMError(f"LLM HTTP {r.status_code}: {r.text[:500]}")
        data = r.json()
        usage = data.get("usage") or {}
        self.stats["calls"] += 1
        self.stats["prompt_tokens"] += usage.get("prompt_tokens", 0)
        self.stats["completion_tokens"] += usage.get("completion_tokens", 0)
        self.stats["seconds"] += dt
        log.info("llm %s: %s prompt / %s completion tokens in %.1fs", schema.__name__ if schema else "text",
                 usage.get("prompt_tokens"), usage.get("completion_tokens"), dt)
        return data["choices"][0]["message"]["content"] or ""

    async def structured(self, messages: list[dict], schema: type[BaseModel], max_tokens: int = 2048,
                         retries: int = 2, temperature: float = 0.4) -> BaseModel:
        last_err: Exception | None = None
        for attempt in range(retries + 1):
            text = await self.chat(messages, schema=schema, max_tokens=max_tokens,
                                   temperature=temperature if attempt == 0 else 0.2)
            try:
                return schema.model_validate_json(_strip_fences(text))
            except (ValidationError, json.JSONDecodeError) as e:
                last_err = e
                log.warning("schema %s invalid (attempt %d): %s", schema.__name__, attempt + 1, str(e)[:300])
                messages = messages + [
                    {"role": "assistant", "content": text},
                    {"role": "user", "content": f"That JSON was invalid: {str(e)[:400]}. Return corrected JSON only."},
                ]
        raise LLMError(f"Could not get valid {schema.__name__}: {last_err}")

    async def close(self):
        await self.client.aclose()


def _strip_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^<think>.*?</think>", "", text, flags=re.S).strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    return text


def image_part(png_bytes: bytes, mime: str = "image/png") -> dict:
    return {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{base64.b64encode(png_bytes).decode()}"}}


CHARS_PER_TOKEN = 2.8  # conservative: tables/numbers/non-English text tokenize densely


def approx_tokens(text: str) -> int:
    return int(len(text) / CHARS_PER_TOKEN) + 1
