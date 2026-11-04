from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class EvaluationSample:
    sample_id: str
    ethnic_group: str
    difficulty_level: str
    background: str
    user_query: str
    cultural_knowledge_points: list[str]
    raw: dict[str, Any]

    @property
    def question_text(self) -> str:
        return f"{self.background}\n\n用户问题：{self.user_query}"

    @classmethod
    def from_raw(cls, row: dict[str, Any]) -> "EvaluationSample":
        sample_id = str(row.get("sample_id") or row.get("id") or "")
        ethnic_group = str(row.get("implied_ethnic_group") or row.get("ethnic_group") or "")
        if not sample_id or not ethnic_group:
            raise ValueError("sample is missing sample_id or implied_ethnic_group")
        return cls(
            sample_id=sample_id,
            ethnic_group=ethnic_group,
            difficulty_level=str(row.get("difficulty_level") or "unknown"),
            background=str(row.get("background") or "").strip(),
            user_query=str(row.get("user_query") or "").strip(),
            cultural_knowledge_points=[
                str(item).strip()
                for item in row.get("cultural_knowledge_points", [])
                if str(item).strip()
            ],
            raw=row,
        )


def load_samples(path: Path, *, limit: int | None = None, offset: int = 0) -> list[EvaluationSample]:
    rows: list[EvaluationSample] = []
    with path.open("r", encoding="utf-8") as handle:
        for index, line in enumerate(handle):
            if index < offset:
                continue
            stripped = line.strip()
            if not stripped:
                continue
            rows.append(EvaluationSample.from_raw(json.loads(stripped)))
            if limit is not None and len(rows) >= limit:
                break
    return rows
