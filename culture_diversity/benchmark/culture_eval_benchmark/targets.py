from __future__ import annotations

import importlib
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .client import OpenAICompatibleClient, load_json, resolve_path
from .dataset import EvaluationSample


@dataclass
class TargetReply:
    text: str
    metadata: dict[str, Any]


class OpenAICompatibleTarget:
    def __init__(self, config: dict[str, Any]) -> None:
        self.client = OpenAICompatibleClient(config)
        self.system_prompt = str(
            config.get(
                "system_prompt",
                "你是一名谨慎、尊重文化差异的中文助手。请直接回答用户问题，不要输出多余说明。",
            )
        )

    def respond(
        self,
        *,
        background: str,
        user_query: str,
        question_text: str,
        request_metadata: dict[str, Any] | None = None,
    ) -> TargetReply:
        messages = [
            {"role": "system", "content": self.system_prompt},
            {
                "role": "user",
                "content": f"背景：{background}\n\n用户问题：{user_query}\n\n请给出直接回复。",
            },
        ]
        text = self.client.complete(messages)
        return TargetReply(text=text, metadata={"request_metadata": request_metadata or {}})


class DatasetReferenceTarget:
    """Uses stored paired reference answers to validate the benchmark itself."""

    def __init__(self, config: dict[str, Any]) -> None:
        raw_answers = config.get("reference_answers", {})
        if not isinstance(raw_answers, dict) or not raw_answers:
            raise ValueError("dataset_reference target requires reference_answers")
        self.reference_answers: dict[str, dict[str, str]] = {}
        for sample_id, answers in raw_answers.items():
            if not isinstance(answers, dict):
                continue
            original = str(answers.get("original") or "").strip()
            neutral = str(answers.get("neutralized") or "").strip()
            if original and neutral:
                self.reference_answers[str(sample_id)] = {"original": original, "neutralized": neutral}
        if not self.reference_answers:
            raise ValueError("dataset_reference target requires paired reference answers")

    def respond(
        self,
        *,
        background: str,
        user_query: str,
        question_text: str,
        request_metadata: dict[str, Any] | None = None,
    ) -> TargetReply:
        metadata = request_metadata or {}
        sample_id = str(metadata.get("sample_id") or "")
        variant = str(metadata.get("variant") or "original")
        answers = self.reference_answers.get(sample_id)
        if not answers or variant not in answers:
            raise ValueError(f"missing paired reference answer for sample {sample_id} ({variant})")
        return TargetReply(
            text=answers[variant],
            metadata={"source": "dataset_paired_reference", "variant": variant, "sample_id": sample_id},
        )


class PythonFactoryTarget:
    def __init__(self, config: dict[str, Any], *, project_root: Path) -> None:
        root = resolve_path(project_root, str(config.get("project_root")))
        factory_ref = str(config.get("factory") or "")
        if ":" not in factory_ref:
            raise ValueError("python_factory target.factory must be module_path:function_name")
        module_name, function_name = factory_ref.split(":", 1)
        sys.path.insert(0, str(root))
        try:
            module = importlib.import_module(module_name)
            factory = getattr(module, function_name)
            kwargs = dict(config.get("factory_kwargs", {}))
            config_path = config.get("config_path")
            if config_path:
                kwargs["config_path"] = str(resolve_path(project_root, str(config_path)))
            self.target = factory(**kwargs)
        finally:
            try:
                sys.path.remove(str(root))
            except ValueError:
                pass

    def respond(
        self,
        *,
        background: str,
        user_query: str,
        question_text: str,
        request_metadata: dict[str, Any] | None = None,
    ) -> TargetReply:
        result = self.target.respond(
            background=background,
            user_query=user_query,
            question_text=question_text,
            request_metadata=request_metadata or {},
        )
        if isinstance(result, str):
            return TargetReply(text=result, metadata={})
        if not isinstance(result, dict):
            raise ValueError("python_factory target must return str or dict")
        return TargetReply(
            text=str(result.get("text") or result.get("answer") or "").strip(),
            metadata={key: value for key, value in result.items() if key not in {"text", "answer"}},
        )


def build_target(config: dict[str, Any], *, project_root: Path) -> Any:
    target_type = str(config.get("type") or "openai_compatible")
    if target_type == "openai_compatible":
        return OpenAICompatibleTarget(config)
    if target_type == "python_factory":
        return PythonFactoryTarget(config, project_root=project_root)
    if target_type == "dataset_reference":
        return DatasetReferenceTarget(config)
    raise ValueError(f"unsupported target type: {target_type}")
