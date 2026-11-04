from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


class OpenAICompatibleClient:
    def __init__(self, config: dict[str, Any]) -> None:
        api_key_env = str(config.get("api_key_env", "DEEPSEEK_API_KEY"))
        self.api_base = str(config.get("api_base", "https://api.deepseek.com/v1")).rstrip("/")
        self.api_key = str(config.get("api_key") or os.environ.get(api_key_env, ""))
        self.model = str(config.get("model", "deepseek-chat"))
        self.temperature = float(config.get("temperature", 0))
        self.top_p = float(config.get("top_p", 1))
        self.max_tokens = int(config.get("max_tokens", 1024))
        self.timeout = int(config.get("timeout", 180))
        self.retries = int(config.get("retries", 2))
        self.retry_sleep = float(config.get("retry_sleep", 1.0))
        self.chat_template_kwargs = config.get("chat_template_kwargs")
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        seed: int | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature if temperature is None else temperature,
            "top_p": self.top_p,
            "max_tokens": self.max_tokens if max_tokens is None else max_tokens,
            "stream": False,
        }
        if seed is not None:
            payload["seed"] = seed
        if self.chat_template_kwargs:
            payload["chat_template_kwargs"] = self.chat_template_kwargs

        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        request = urllib.request.Request(
            f"{self.api_base}/chat/completions",
            data=body,
            headers=headers,
            method="POST",
        )

        last_error = None
        for attempt in range(self.retries + 1):
            try:
                with self.opener.open(request, timeout=self.timeout) as response:
                    data = json.loads(response.read().decode("utf-8"))
                content = data.get("choices", [{}])[0].get("message", {}).get("content")
                if not content:
                    raise RuntimeError(f"chat response has no content: {data}")
                return str(content).strip()
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")
                last_error = f"HTTP {exc.code}: {detail[:500]}"
            except Exception as exc:
                last_error = repr(exc)
            if attempt < self.retries:
                time.sleep(min(self.retry_sleep * (2**attempt), 30.0))
        raise RuntimeError(f"chat completion failed: {last_error}")


def parse_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = [line for line in cleaned.splitlines() if not line.strip().startswith("```")]
        cleaned = "\n".join(lines).strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start < 0 or end <= start:
            raise
        data = json.loads(cleaned[start : end + 1])
    if not isinstance(data, dict):
        raise ValueError("JSON root must be an object")
    return data


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return data


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def resolve_path(base_dir: Path, value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (base_dir / path).resolve()
