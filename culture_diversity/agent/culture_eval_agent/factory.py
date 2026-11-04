from __future__ import annotations

from pathlib import Path
from typing import Any

from .pipeline import build_agent


class AgentTargetAdapter:
    def __init__(self, config_path: str | Path) -> None:
        self.agent = build_agent(config_path)

    def respond(
        self,
        *,
        background: str,
        user_query: str,
        question_text: str,
        request_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        result = self.agent.answer(background=background, user_query=user_query)
        return {
            "text": result["text"],
            "trace": result["trace"],
            "request_metadata": request_metadata or {},
            "question_text": question_text,
        }


def build_target_adapter(*, config_path: str) -> AgentTargetAdapter:
    return AgentTargetAdapter(config_path)
