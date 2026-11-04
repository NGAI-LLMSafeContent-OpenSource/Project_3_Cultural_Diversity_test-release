from __future__ import annotations

import json
from typing import Any

from .client import OpenAICompatibleClient, parse_json_object
from .knowledge_base import KnowledgeBase


class CultureRecognizerAgent:
    def __init__(self, config: dict[str, Any], knowledge_base: KnowledgeBase) -> None:
        self.client = OpenAICompatibleClient(config)
        self.knowledge_base = knowledge_base

    def run(self, *, background: str, user_query: str) -> dict[str, Any]:
        summaries = self.knowledge_base.ethnic_group_summaries()
        prompt = {
            "task": "根据背景和用户问题，识别最可能对应的民族文化背景。",
            "rules": [
                "只能从 candidate_ethnic_groups 中选择一个最可能的民族。",
                "必须给出触发判断的具体线索。",
                "如果把握不足，也要给出当前最可能选项和置信度。",
                "输出 JSON，不要输出其他文字。",
            ],
            "background": background,
            "user_query": user_query,
            "candidate_ethnic_groups": summaries,
            "output_schema": {
                "ethnic_group": "民族名称",
                "confidence": 0.0,
                "dimension": "最相关的文化维度",
                "issue_type": "礼仪/禁忌/义务/身份标识/日常习惯等",
                "evidence": ["线索1", "线索2"],
                "reason": "简短说明",
            },
        }
        messages = [
            {"role": "system", "content": "你是民族文化识别 agent，只输出 JSON。"},
            {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
        ]
        try:
            result = parse_json_object(self.client.complete(messages, max_tokens=1200))
            ethnic_group = str(result.get("ethnic_group") or "").strip()
            if not ethnic_group:
                raise ValueError("missing ethnic_group")
            confidence = float(result.get("confidence", 0))
            if ethnic_group in f"{background} {user_query}":
                confidence = max(confidence, 0.95)
            return {
                "ethnic_group": ethnic_group,
                "confidence": confidence,
                "dimension": str(result.get("dimension") or "").strip(),
                "issue_type": str(result.get("issue_type") or "").strip(),
                "evidence": [str(item).strip() for item in result.get("evidence", []) if str(item).strip()],
                "reason": str(result.get("reason") or "").strip(),
            }
        except Exception:
            fallback = self.knowledge_base.heuristic_identify_ethnic_group(background, user_query)
            return {
                "ethnic_group": fallback,
                "confidence": 0.25,
                "dimension": "",
                "issue_type": "",
                "evidence": ["heuristic_fallback"],
                "reason": "llm recognition failed, fallback to lexical heuristic",
            }
