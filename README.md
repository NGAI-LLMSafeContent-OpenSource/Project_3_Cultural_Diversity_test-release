# 文化多样性独立命令行评测包

发布方 NGAI-LLMSafeContent；版本 1.0；日期 2026-11-04；Apache-2.0。
源仓库 NGAI-LLMSafeContent/Project_3_Cultural_Diversity_test，固定提交 0d92d7c805552bd3932682ff0e2040cf2ef6dc2f。

此仓仅发布独立命令行评测器与 Agent 源码，不包含主控制台、原始 2000 条数据、文化知识库或历史结果。配套控制台由文化多样性评估主仓提供，避免重复捆绑数据和界面。

## 前置条件与使用

Python >=3.12，仅使用标准库，无 pip 第三方依赖。从根目录执行：

```sh
python tools/release_smoke.py
python culture_diversity/benchmark/run_evaluation.py --help
```

examples/fictional.jsonl 为本次新编写的一条虚构样例，不代表真实民族文化。准备自己的兼容 OpenAI 模型服务，将 examples/evaluation.example.json 中地址、模型名称改为实际值，并通过用户环境变量 CULTURE_MODEL_API_KEY 提供自己的凭据，然后运行：

```sh
python culture_diversity/benchmark/run_evaluation.py --config examples/evaluation.example.json
```

Agent 路线还需自行提供有权使用的知识库，按 python_factory target 的配置读取，未随包发布。运行结果在 runs/ 下，不应提交。

自动测试实际启动本地假裁判 HTTP 服务，使用自编成对参考答案驱动完整评测器产生逐条结果和汇总，仅验证协议与结果写出；所有假裁判分值固定为 0，不是模型或文化准确性结果。真实模型推理、Agent 知识检索与文化评测效果未验证。

完整文件、源提交与校验见 RELEASE_MANIFEST.json、SHA256SUMS；第三方条件见 THIRD_PARTY_NOTICES.md。
