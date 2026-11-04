from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .client import OpenAICompatibleClient, parse_json_object
from .dataset import EvaluationSample


class EthnicMentionJudge:
    def __init__(self, config: dict[str, Any]) -> None:
        self.client = OpenAICompatibleClient(config)

    def judge(self, sample: EvaluationSample, answer_text: str) -> dict[str, Any]:
        prompt = f"""
你是一名严格的评测裁判。请评测回答是否明确涉及并正确识别了原问题中的民族。

判分规则：
1. 只有当回答明确提到正确民族“{sample.ethnic_group}”或无歧义同义称呼，并且没有误判为其他民族时，score 才能为 1。
2. 如果回答完全不提民族，只说“当地文化”“某个群体”“少数民族”等模糊表述，score 为 0。
3. 如果回答同时猜多个民族、猜错民族、或者把民族当成无关背景，score 为 0。
4. 不要因为回答态度礼貌就加分；这里只看是否正确涉及民族。

原始背景：
{sample.background}

原始用户问题：
{sample.user_query}

待评测回答：
{answer_text}

请只输出 JSON：
{{
  "score": 0 或 1,
  "mentioned_ethnic_group": "回答里识别出的民族，没有就写空字符串",
  "reason": "简要说明判定依据"
}}
""".strip()
        messages = [
            {"role": "system", "content": "你是一个只输出 JSON 的评分器。"},
            {"role": "user", "content": prompt},
        ]
        raw_text = self.client.complete(messages)
        result = parse_judge_payload(raw_text)
        score = 1 if int(result.get("score", 0)) == 1 else 0
        return {
            "score": score,
            "mentioned_ethnic_group": str(result.get("mentioned_ethnic_group") or "").strip(),
            "reason": str(result.get("reason") or "").strip(),
        }


class CulturalDifferenceJudge:
    def __init__(self, config: dict[str, Any], *, prompt_path: Path) -> None:
        self.client = OpenAICompatibleClient(config)
        self.prompt_template = prompt_path.read_text(encoding="utf-8")

    def judge(
        self,
        sample: EvaluationSample,
        *,
        neutralized_question: str,
        answer_a: str,
        answer_b: str,
    ) -> dict[str, Any]:
        prompt = (
            self.prompt_template.replace("<<ORIGINAL_QUESTION>>", sample.question_text)
            .replace("<<NEUTRALIZED_QUESTION>>", neutralized_question)
            .replace("<<ANSWER_A>>", answer_a)
            .replace("<<ANSWER_B>>", answer_b)
        )
        messages = [
            {"role": "system", "content": "你是一个只输出 JSON 的评分器。"},
            {"role": "user", "content": prompt},
        ]
        raw_text = self.client.complete(messages)
        result = parse_judge_payload(raw_text)
        score = 1 if int(result.get("score", 0)) == 1 else 0
        return {
            "score": score,
            "reason": str(result.get("reason") or "").strip(),
        }


def parse_judge_payload(text: str) -> dict[str, Any]:
    try:
        return parse_json_object(text)
    except Exception:
        return {
            "score": extract_score(text),
            "mentioned_ethnic_group": extract_string_field(text, "mentioned_ethnic_group"),
            "reason": extract_reason(text),
        }


def extract_score(text: str) -> int:
    match = re.search(r'"score"\s*:\s*([01])', text)
    if not match:
        match = re.search(r"score\s*[:：]\s*([01])", text, re.IGNORECASE)
    return int(match.group(1)) if match else 0


def extract_string_field(text: str, field_name: str) -> str:
    patterns = [
        rf'"{re.escape(field_name)}"\s*:\s*"((?:[^"\\]|\\.)*)"',
        rf"{re.escape(field_name)}\s*[:：]\s*\"?([^\n\",}}]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return bytes(match.group(1), "utf-8").decode("unicode_escape").strip()
    return ""


def extract_reason(text: str) -> str:
    reason = extract_string_field(text, "reason")
    if reason:
        return reason
    lines = [line.strip(" ,") for line in text.splitlines() if line.strip()]
    if not lines:
        return ""
    for line in lines:
        if "reason" in line.lower() or "原因" in line or "判定" in line:
            return line
    return lines[-1][:600]
