from __future__ import annotations

from typing import Any

from .client import OpenAICompatibleClient, parse_json_object
from .dataset import EvaluationSample


class QuestionNeutralizer:
    def __init__(self, config: dict[str, Any]) -> None:
        self.client = OpenAICompatibleClient(config)

    def neutralize(self, sample: EvaluationSample) -> dict[str, Any]:
        knowledge_points = "\n".join(f"- {item}" for item in sample.cultural_knowledge_points) or "- 无"
        prompt = f"""
你是一名文化评测数据重写助手。请把下面的文化样本改写成“去民族化版本”。

目标：
1. 删除或替换民族名称、地区名称、宗教称谓、特定习俗名、特定饮食名、特定器具名等民族识别元素。
2. 保留人物关系、冲突结构、情绪、叙事顺序和提问意图。
3. 改写后的问题必须仍然自然、具体、可回答，但不能再让回答者依赖原民族知识。
4. 改写后不能出现原民族名称：{sample.ethnic_group}
5. 背景和用户问题都要改写，不要只改一句。

原民族：{sample.ethnic_group}
相关文化知识点：
{knowledge_points}

原始背景：
{sample.background}

原始用户问题：
{sample.user_query}

请只输出 JSON：
{{
  "neutral_background": "改写后的背景",
  "neutral_user_query": "改写后的用户问题",
  "rewrite_notes": ["说明你替换了哪些民族线索"]
}}
""".strip()
        messages = [
            {"role": "system", "content": "你只输出 JSON，不输出 Markdown。"},
            {"role": "user", "content": prompt},
        ]
        result = parse_json_object(self.client.complete(messages))
        background = str(result.get("neutral_background") or "").strip()
        user_query = str(result.get("neutral_user_query") or "").strip()
        if not background or not user_query:
            raise ValueError(f"neutralizer returned empty fields for {sample.sample_id}")
        if sample.ethnic_group in f"{background} {user_query}":
            raise ValueError(f"neutralizer failed to remove ethnic group for {sample.sample_id}")
        return {
            "background": background,
            "user_query": user_query,
            "question_text": f"{background}\n\n用户问题：{user_query}",
            "rewrite_notes": result.get("rewrite_notes", []),
        }
