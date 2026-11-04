from __future__ import annotations

import json
from typing import Any

from .client import OpenAICompatibleClient, parse_json_object
from .knowledge_base import KnowledgeBase, KnowledgeItem


class KnowledgeRetrieverAgent:
    def __init__(self, config: dict[str, Any], knowledge_base: KnowledgeBase) -> None:
        self.client = OpenAICompatibleClient(config)
        self.knowledge_base = knowledge_base
        self.top_k = int(config.get("top_k", 3))

    def run(
        self,
        *,
        background: str,
        user_query: str,
        recognition: dict[str, Any],
    ) -> dict[str, Any]:
        candidates = self.knowledge_base.retrieve_candidates(
            recognition["ethnic_group"],
            background,
            user_query,
            top_k=max(self.top_k + 2, 5),
        )
        prompt = {
            "task": "从候选知识中选出最能支持回答的知识点。",
            "recognized_ethnic_group": recognition["ethnic_group"],
            "recognized_dimension": recognition.get("dimension", ""),
            "recognized_issue_type": recognition.get("issue_type", ""),
            "background": background,
            "user_query": user_query,
            "candidates": [serialize_item(item) for item in candidates],
            "rules": [
                f"选择最相关的 {self.top_k} 条知识。",
                "优先选择能够解释文化逻辑、冲突性质和行为底线的知识。",
                "输出 JSON，不要输出其他内容。",
            ],
            "output_schema": {
                "selected_ids": ["knowledge_id_1", "knowledge_id_2"],
                "reason": "简短说明为什么这些知识最相关",
            },
        }
        messages = [
            {"role": "system", "content": "你是知识检索 agent，只输出 JSON。"},
            {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
        ]
        try:
            result = parse_json_object(self.client.complete(messages, max_tokens=1200))
            selected_ids = [str(item).strip() for item in result.get("selected_ids", []) if str(item).strip()]
            if not selected_ids:
                raise ValueError("selected_ids is empty")
            by_id = {item.item_id: item for item in candidates}
            selected_items = [by_id[item_id] for item_id in selected_ids if item_id in by_id][: self.top_k]
            if not selected_items:
                raise ValueError("no selected candidates matched")
            return {
                "items": selected_items,
                "reason": str(result.get("reason") or "").strip(),
            }
        except Exception:
            return {
                "items": candidates[: self.top_k],
                "reason": "llm retrieval failed, fallback to lexical ranking",
            }


def serialize_item(item: KnowledgeItem) -> dict[str, Any]:
    return {
        "id": item.item_id,
        "ethnic_group": item.ethnic_group,
        "dimension": item.dimension,
        "knowledge": item.knowledge,
        "clues": item.clues,
        "related_taboos": item.related_taboos,
        "scene": item.scene,
    }
