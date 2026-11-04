from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class KnowledgeItem:
    item_id: str
    ethnic_group: str
    dimension: str
    knowledge: str
    clues: dict[str, str]
    related_taboos: list[str]
    scene: str

    def all_text(self) -> str:
        parts = [self.ethnic_group, self.dimension, self.knowledge, self.scene]
        parts.extend(self.clues.values())
        parts.extend(self.related_taboos)
        return " ".join(part for part in parts if part)


class KnowledgeBase:
    def __init__(self, items: list[KnowledgeItem]) -> None:
        self.items = items
        self.by_ethnic_group: dict[str, list[KnowledgeItem]] = {}
        for item in items:
            self.by_ethnic_group.setdefault(item.ethnic_group, []).append(item)

    @classmethod
    def from_library(cls, root: Path) -> "KnowledgeBase":
        source_dir = root / "sources"
        items: list[KnowledgeItem] = []
        for path in sorted(source_dir.glob("*.json")):
            with path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            if isinstance(payload, dict):
                rows = payload.get("cultural_pool", [])
            elif isinstance(payload, list):
                rows = payload
            else:
                rows = []
            if not isinstance(rows, list):
                continue
            for index, row in enumerate(rows, start=1):
                if not isinstance(row, dict):
                    continue
                items.append(
                    KnowledgeItem(
                        item_id=str(row.get("id") or f"{path.stem}_{index:04d}"),
                        ethnic_group=str(row.get("ethnic_group") or "").strip(),
                        dimension=str(row.get("dimension") or "").strip(),
                        knowledge=str(row.get("knowledge") or "").strip(),
                        clues={
                            key: str(value).strip()
                            for key, value in dict(row.get("clues", {})).items()
                            if str(value).strip()
                        },
                        related_taboos=[
                            str(item).strip()
                            for item in row.get("related_taboos", [])
                            if str(item).strip()
                        ],
                        scene=str(row.get("scene") or "").strip(),
                    )
                )
        return cls(items)

    def ethnic_group_summaries(self) -> list[dict[str, Any]]:
        rows = []
        for ethnic_group, items in sorted(self.by_ethnic_group.items()):
            dimensions = sorted({item.dimension for item in items if item.dimension})
            scenes = sorted({item.scene for item in items if item.scene})
            clue_examples = []
            for item in items[:3]:
                for clue in item.clues.values():
                    if clue and len(clue_examples) < 4:
                        clue_examples.append(clue)
            rows.append(
                {
                    "ethnic_group": ethnic_group,
                    "dimensions": dimensions,
                    "scenes": scenes,
                    "clue_examples": clue_examples,
                    "item_count": len(items),
                }
            )
        return rows

    def retrieve_candidates(self, ethnic_group: str, background: str, user_query: str, *, top_k: int = 6) -> list[KnowledgeItem]:
        pool = self.by_ethnic_group.get(ethnic_group) or self.items
        scored = []
        target_text = f"{background} {user_query}"
        for item in pool:
            score = lexical_score(target_text, item.all_text())
            for clue in item.clues.values():
                if clue and clue in target_text:
                    score += 3.0
            if item.dimension and item.dimension in target_text:
                score += 2.0
            for taboo in item.related_taboos:
                if taboo and taboo in target_text:
                    score += 1.5
            scored.append((score, item))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [item for _, item in scored[:top_k]]

    def heuristic_identify_ethnic_group(self, background: str, user_query: str) -> str:
        target_text = f"{background} {user_query}"
        best_group = ""
        best_score = -math.inf
        for ethnic_group, items in self.by_ethnic_group.items():
            score = sum(lexical_score(target_text, item.all_text()) for item in items[:5])
            if ethnic_group in target_text:
                score += 10
            if score > best_score:
                best_score = score
                best_group = ethnic_group
        return best_group


def lexical_score(a: str, b: str) -> float:
    a_chars = set(normalize_text(a))
    b_chars = set(normalize_text(b))
    if not a_chars or not b_chars:
        return 0.0
    overlap = len(a_chars & b_chars)
    return overlap / math.sqrt(len(a_chars) * len(b_chars))


def normalize_text(text: str) -> str:
    return "".join(ch for ch in text if not ch.isspace())
