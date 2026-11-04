from __future__ import annotations

import json
from typing import Any

from .client import OpenAICompatibleClient, parse_json_object
from .knowledge_base import KnowledgeItem


class ResponseComposerAgent:
    def __init__(self, config: dict[str, Any]) -> None:
        self.client = OpenAICompatibleClient(config)
        self.low_confidence_threshold = float(config.get("low_confidence_threshold", 0.55))

    def run(
        self,
        *,
        background: str,
        user_query: str,
        recognition: dict[str, Any],
        knowledge_items: list[KnowledgeItem],
    ) -> dict[str, Any]:
        confidence = float(recognition.get("confidence", 0))
        if confidence < self.low_confidence_threshold:
            return {
                "text": low_confidence_answer(background=background, user_query=user_query),
                "support_points": ["文化线索不足，避免强行判定民族", "先确认具体习俗来源再给文化性建议"],
            }
        knowledge_payload = [serialize_item(item) for item in knowledge_items]
        prompt = {
            "task": "生成一个能体现深度文化理解的回答。",
            "background": background,
            "user_query": user_query,
            "recognized_ethnic_group": recognition["ethnic_group"],
            "recognition_confidence": confidence,
            "recognized_dimension": recognition.get("dimension", ""),
            "recognized_issue_type": recognition.get("issue_type", ""),
            "recognized_evidence": recognition.get("evidence", []),
            "retrieved_knowledge": knowledge_payload,
            "requirements": [
                "开头要明确指出最可能涉及的民族或文化场景，不要用模糊表述带过。",
                "必须解释相关习俗为什么在该文化中成立，不能只说这是传统。",
                "必须判断当前冲突在该文化中属于礼仪、禁忌、义务、身份标识还是可协商习惯，并说明严重程度。",
                "必须说明该文化里是否存在不可退让的底线，以及提问者应做出的具体调整。",
                "最后给出可执行的沟通或行动建议。",
                "避免空泛地说互相理解、各退一步，除非你已经说明为什么可以退让。",
                "输出中文，只输出 JSON。",
            ],
            "output_schema": {
                "answer": "最终回答正文",
                "support_points": ["知识点1", "知识点2"],
            },
        }
        messages = [
            {"role": "system", "content": "你是回答生成 agent，只输出 JSON。"},
            {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
        ]
        try:
            result = parse_json_object(self.client.complete(messages, max_tokens=1600))
            answer = str(result.get("answer") or "").strip()
            if not answer:
                raise ValueError("answer is empty")
            return {
                "text": answer,
                "support_points": [str(item).strip() for item in result.get("support_points", []) if str(item).strip()],
            }
        except Exception:
            return {
                "text": fallback_answer(
                    ethnic_group=recognition["ethnic_group"],
                    issue_type=str(recognition.get("issue_type") or "文化礼仪"),
                    knowledge_items=knowledge_items,
                ),
                "support_points": [item.knowledge for item in knowledge_items[:2]],
            }


def serialize_item(item: KnowledgeItem) -> dict[str, Any]:
    return {
        "id": item.item_id,
        "dimension": item.dimension,
        "knowledge": item.knowledge,
        "related_taboos": item.related_taboos,
        "scene": item.scene,
    }


def fallback_answer(*, ethnic_group: str, issue_type: str, knowledge_items: list[KnowledgeItem]) -> str:
    first = knowledge_items[0] if knowledge_items else None
    second = knowledge_items[1] if len(knowledge_items) > 1 else None
    lines = [f"从你描述的细节看，这更像是{ethnic_group}的文化场景。"]
    if first:
        lines.append(f"这里不是单纯的个人口味问题，核心点在于：{first.knowledge}")
    if second:
        lines.append(f"同时还涉及另一层文化要求：{second.knowledge}")
    lines.append(f"因此，这件事在当地更接近“{issue_type}”，不能简单当成普通生活习惯。")
    if first and first.related_taboos:
        lines.append(f"尤其要避免：{'、'.join(first.related_taboos[:3])}。")
    lines.append("更稳妥的做法是先承认这项做法在对方文化里的意义，再说明你当前不适应的具体点，询问是否有不冒犯礼仪的替代做法。")
    lines.append("如果它属于原则性礼仪或禁忌，优先调整自己的行为，不要直接把它当成可以随意商量的小习惯。")
    return "".join(lines)


def low_confidence_answer(*, background: str, user_query: str) -> str:
    return (
        "从你现在提供的描述看，我能判断这背后可能有特定的家庭或地方习惯，但还不足以负责任地断定是哪一类民族文化。"
        "在文化线索不够明确时，最稳妥的做法不是先下文化结论，而是先确认这件事对对方到底意味着什么："
        "它只是个人偏好，还是家里默认必须遵守的习惯。你可以先肯定对方的用心，再具体说明自己哪里不适应，"
        "然后问清楚有没有不冒犯的替代做法。如果对方把它看成必须遵守的规矩，你再根据对方解释决定是否需要调整自己的行为。"
    )
