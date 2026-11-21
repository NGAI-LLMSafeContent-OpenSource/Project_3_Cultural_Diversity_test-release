# 发布文件清单

原仓：`NGAI-LLMSafeContent/Project_3_Cultural_Diversity_test`；源提交：`0d92d7c805552bd3932682ff0e2040cf2ef6dc2f`；分支：`release/1.0`。

本清单逐文件列出发布内容。原有非README实现/配置/资源保持Git对象字节和模式一致；README与发布新增材料单独登记。RELEASE_MANIFEST.json和SHA256SUMS由发布器生成，不形成自引用哈希。

## 来自原仓、原样保留的文件

- `culture_diversity/agent/agent_config.json`
- `culture_diversity/agent/culture_eval_agent/__init__.py`
- `culture_diversity/agent/culture_eval_agent/client.py`
- `culture_diversity/agent/culture_eval_agent/factory.py`
- `culture_diversity/agent/culture_eval_agent/knowledge_base.py`
- `culture_diversity/agent/culture_eval_agent/pipeline.py`
- `culture_diversity/agent/culture_eval_agent/recognizer.py`
- `culture_diversity/agent/culture_eval_agent/responder.py`
- `culture_diversity/agent/culture_eval_agent/retriever.py`
- `culture_diversity/benchmark/culture_eval_benchmark/__init__.py`
- `culture_diversity/benchmark/culture_eval_benchmark/client.py`
- `culture_diversity/benchmark/culture_eval_benchmark/dataset.py`
- `culture_diversity/benchmark/culture_eval_benchmark/evaluator.py`
- `culture_diversity/benchmark/culture_eval_benchmark/judges.py`
- `culture_diversity/benchmark/culture_eval_benchmark/neutralizer.py`
- `culture_diversity/benchmark/culture_eval_benchmark/targets.py`
- `culture_diversity/benchmark/prompts/cultural_difference_judge.txt`
- `culture_diversity/benchmark/run_evaluation.py`
- `culture_diversity/configs/agent_openai_compatible.json`
- `culture_diversity/configs/baseline_openai_compatible.json`

## README及发布新增材料

- `KNOWN_ISSUES.md`
- `LICENSE`
- `README.md`
- `RELEASE_FILES.md`
- `SOURCE_ALIGNMENT.json`
- `THIRD_PARTY_NOTICES.md`
- `examples/evaluation.example.json`
- `examples/fictional.jsonl`
- `release_checks.json`
- `requirements.txt`
- `tools/release_check.py`

## 生成的校验文件

- `RELEASE_MANIFEST.json`
- `SHA256SUMS`

## 排除范围

明确弃用的历史原型、旧版本快照、缓存、数据库、用户配置和预跑产物未发布。模型、原始数据/知识库和外部服务按README准备，不以缩减/改写同路径数据文件冒充完整交付。源码原有错误保留，见KNOWN_ISSUES.md。
