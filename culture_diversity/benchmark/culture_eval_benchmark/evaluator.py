from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from .client import append_jsonl, load_json, resolve_path, write_json, write_jsonl
from .dataset import load_samples
from .judges import CulturalDifferenceJudge, EthnicMentionJudge
from .neutralizer import QuestionNeutralizer
from .targets import build_target


class BenchmarkEvaluator:
    def __init__(self, config_path: str | Path) -> None:
        self.config_path = Path(config_path).resolve()
        self.config = load_json(self.config_path)
        configured_root = self.config.get("project_root")
        if configured_root:
            self.project_root = resolve_path(self.config_path.parent, str(configured_root))
        else:
            self.project_root = self.config_path.parent.parent

    def run(self) -> dict[str, Any]:
        dataset_config = dict(self.config.get("dataset", {}))
        dataset_path = resolve_path(self.project_root, str(dataset_config.get("path")))
        samples = load_samples(
            dataset_path,
            limit=dataset_config.get("limit"),
            offset=int(dataset_config.get("offset", 0)),
        )
        if not samples:
            raise ValueError(f"dataset has no samples: {dataset_path}")

        target_config = dict(self.config.get("target", {}))
        is_dataset_reference = target_config.get("type") == "dataset_reference"
        if is_dataset_reference:
            target_config["reference_answers"] = {
                sample.sample_id: {
                    "original": str(sample.raw.get("expected_answer") or "").strip(),
                    "neutralized": str(sample.raw.get("expected_neutral_answer") or "").strip(),
                }
                for sample in samples
            }
            missing_pairs = [
                sample.sample_id for sample in samples
                if not str(sample.raw.get("neutral_background") or "").strip()
                or not str(sample.raw.get("neutral_user_query") or "").strip()
                or not str(sample.raw.get("expected_neutral_answer") or "").strip()
            ]
            if missing_pairs:
                raise ValueError(f"dataset_reference requires stored paired references; missing: {', '.join(missing_pairs[:5])}")
        target = build_target(target_config, project_root=self.project_root)
        neutralizer = QuestionNeutralizer(dict(self.config.get("neutralizer", {})))
        judges_config = dict(self.config.get("judges", {}))
        ethnic_judge = EthnicMentionJudge(dict(judges_config.get("ethnic_group_judge", {})))
        prompt_path = resolve_path(
            self.project_root,
            str(judges_config.get("cultural_difference_prompt_path", "prompts/cultural_difference_judge.txt")),
        )
        cultural_judge = CulturalDifferenceJudge(
            dict(judges_config.get("cultural_difference_judge", {})),
            prompt_path=prompt_path,
        )

        run_id = str(self.config.get("run_id") or datetime.now().strftime("eval_%Y%m%d_%H%M%S"))
        output_dir = resolve_path(self.project_root, str(self.config.get("output_dir", f"runs/{run_id}")))
        output_dir.mkdir(parents=True, exist_ok=True)
        state_path = output_dir / "worker_state.json"
        results_path = output_dir / "sample_results.jsonl"
        # Static 500-sample evaluations can take a long time. Keep validated
        # per-sample rows so an interrupted run continues from its checkpoint.
        existing_results = self._load_existing_results(results_path, samples)
        completed_sample_ids = {str(row["sample_id"]) for row in existing_results}
        write_json(output_dir / "config.snapshot.json", self.config)
        self._write_state(
            state_path,
            {
                "status": "running",
                "run_id": run_id,
                "dataset_path": str(dataset_path),
                "total": len(samples),
                "completed": len(existing_results),
                "progress": round((len(existing_results) / len(samples)) * 100, 2),
                "current_sample_id": None,
                "message": "准备开始评测",
            },
        )
        results: list[dict[str, Any]] = list(existing_results)
        try:
            total = len(samples)
            for index, sample in enumerate(samples, start=1):
                if sample.sample_id in completed_sample_ids:
                    continue
                self._write_state(
                    state_path,
                    {
                        "status": "running",
                        "run_id": run_id,
                        "dataset_path": str(dataset_path),
                        "total": total,
                        "completed": len(results),
                        "progress": round((len(results) / total) * 100, 2),
                        "current_sample_id": sample.sample_id,
                        "message": f"正在评测第 {index}/{total} 条样本",
                    },
                )
                print(f"[{index}/{total}] evaluating {sample.sample_id}", flush=True)
                if is_dataset_reference:
                    neutral_background = str(sample.raw["neutral_background"])
                    neutral_user_query = str(sample.raw["neutral_user_query"])
                    neutralized = {
                        "background": neutral_background,
                        "user_query": neutral_user_query,
                        "question_text": f"背景：{neutral_background}\n\n用户问题：{neutral_user_query}",
                        "source": "dataset_paired_reference",
                    }
                else:
                    neutralized = neutralizer.neutralize(sample)
                original_reply = target.respond(
                    background=sample.background,
                    user_query=sample.user_query,
                    question_text=sample.question_text,
                    request_metadata={"variant": "original", "sample_id": sample.sample_id},
                )
                neutralized_reply = target.respond(
                    background=str(neutralized["background"]),
                    user_query=str(neutralized["user_query"]),
                    question_text=str(neutralized["question_text"]),
                    request_metadata={"variant": "neutralized", "sample_id": sample.sample_id},
                )
                ethnic_result = ethnic_judge.judge(sample, original_reply.text)
                cultural_result = cultural_judge.judge(
                    sample,
                    neutralized_question=str(neutralized["question_text"]),
                    answer_a=original_reply.text,
                    answer_b=neutralized_reply.text,
                )
                composite_score = 1 if ethnic_result["score"] == 1 and cultural_result["score"] == 1 else 0
                row = {
                    "sample_id": sample.sample_id,
                    "difficulty_level": sample.difficulty_level,
                    "expected_ethnic_group": sample.ethnic_group,
                    "original_question": sample.question_text,
                    "neutralized_question": neutralized["question_text"],
                    "neutralization": neutralized,
                    "answer_a": original_reply.text,
                    "answer_b": neutralized_reply.text,
                    "target_metadata": {
                        "answer_a": original_reply.metadata,
                        "answer_b": neutralized_reply.metadata,
                    },
                    "ethnic_group_judge": ethnic_result,
                    "cultural_difference_judge": cultural_result,
                    "composite_score": composite_score,
                }
                results.append(row)
                append_jsonl(results_path, row)
                print(
                    json.dumps(
                        {
                            "sample_id": sample.sample_id,
                            "ethnic_group_score": ethnic_result["score"],
                            "cultural_difference_score": cultural_result["score"],
                            "composite_score": composite_score,
                        },
                        ensure_ascii=False,
                    ),
                    flush=True,
                )

            summary = self._build_summary(results)
            write_json(output_dir / "summary.json", summary)
            self._write_state(
                state_path,
                {
                    "status": "completed",
                    "run_id": run_id,
                    "dataset_path": str(dataset_path),
                    "total": len(samples),
                    "completed": len(samples),
                    "progress": 100,
                    "current_sample_id": None,
                    "message": "评测完成",
                    "summary": summary,
                },
            )
            return summary
        except Exception as exc:
            self._write_state(
                state_path,
                {
                    "status": "failed",
                    "run_id": run_id,
                    "dataset_path": str(dataset_path),
                    "total": len(samples),
                    "completed": len(results),
                    "progress": round((len(results) / len(samples)) * 100, 2) if samples else 0,
                    "current_sample_id": None,
                    "message": f"评测失败: {exc}",
                },
            )
            raise

    @staticmethod
    def _load_existing_results(results_path: Path, samples: list[Any]) -> list[dict[str, Any]]:
        if not results_path.exists():
            return []
        allowed_ids = {sample.sample_id for sample in samples}
        rows: list[dict[str, Any]] = []
        seen: set[str] = set()
        for line in results_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            sample_id = str(row.get("sample_id") or "")
            if sample_id not in allowed_ids or sample_id in seen:
                continue
            rows.append(row)
            seen.add(sample_id)
        return rows

    def _build_summary(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        by_ethnic_group: dict[str, list[int]] = defaultdict(list)
        by_difficulty: dict[str, list[int]] = defaultdict(list)
        ethnic_scores = []
        cultural_scores = []
        composite_scores = []

        for row in rows:
            ethnic_scores.append(int(row["ethnic_group_judge"]["score"]))
            cultural_scores.append(int(row["cultural_difference_judge"]["score"]))
            composite_scores.append(int(row["composite_score"]))
            by_ethnic_group[str(row["expected_ethnic_group"])].append(int(row["composite_score"]))
            by_difficulty[str(row["difficulty_level"])].append(int(row["composite_score"]))

        return {
            "total_samples": len(rows),
            "ethnic_group_metric_rate": sum(ethnic_scores) / len(ethnic_scores),
            "cultural_difference_rate": sum(cultural_scores) / len(cultural_scores),
            "composite_pass_count": sum(composite_scores),
            "composite_pass_rate": sum(composite_scores) / len(composite_scores),
            "composite_percentage": round((sum(composite_scores) / len(composite_scores)) * 100, 2),
            "by_ethnic_group": {
                key: {"count": len(values), "pass_rate": sum(values) / len(values)}
                for key, values in sorted(by_ethnic_group.items())
            },
            "by_difficulty": {
                key: {"count": len(values), "pass_rate": sum(values) / len(values)}
                for key, values in sorted(by_difficulty.items())
            },
        }

    def _write_state(self, path: Path, payload: dict[str, Any]) -> None:
        write_json(path, payload)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run cultural evaluation benchmark.")
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args()
    summary = BenchmarkEvaluator(args.config).run()
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
