# 文化多样性独立评测工具

提供独立命令行评测器及共享Agent实现，用于比较直接模型与文化知识检索回答。

发布单位：NGAI-LLMSafeContent。发布分支：`release/1.0`；更新日期：2026-11-21；自研代码许可：Apache-2.0，第三方保留原许可。

## 功能

- 去民族化对照、双裁判与成对参考答案
- OpenAI兼容模型目标与Python Agent目标
- 逐条结果、评估汇总及可配置输出目录

## 安装与快速开始

Python 3.12；核心代码使用标准库。需要自己的目标模型/裁判服务；Agent路线另需合法知识库。

从公开仓下载同一发布分支：

```bash
git clone --branch release/1.0 https://github.com/NGAI-LLMSafeContent-OpenSource/Project_3_Cultural_Diversity_test-release.git
cd Project_3_Cultural_Diversity_test-release
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell改用 .venv\Scripts\Activate.ps1
```

以下命令均以仓库根目录为起点，注释中的外部条件需先准备：

```bash
python culture_diversity/benchmark/run_evaluation.py --help
# 复制并编辑原配置，填入自己的输入数据与服务
python culture_diversity/benchmark/run_evaluation.py --config culture_diversity/configs/baseline_openai_compatible.json
```

## 使用与输出

输入JSONL字段与配置结构见 `examples/fictional.jsonl`、`examples/evaluation.example.json` 和 `culture_diversity/configs/`。后者保留原仓默认路径，应在运行环境中准备相应资产，或用自己的配置文件传入实际路径。检查逐条结果及summary；本仓不额外捆绑主系统的网页控制台。

## 配置与外部依赖

原始2000条数据、模型、知识库与历史结果不在最小源码包中；这些是运行者需准备的输入资产，不是被改写成演示实现的功能。

真实凭据只在自己的运行环境或平台Secrets中配置，不提交.env、用户上传、模型权重或运行结果。原仓文件中的内网服务地址经发布负责人确认按原样保留，使用者应在本地配置自己的可达服务。

## 验证与已知问题

完成对应依赖准备后运行：

```bash
python tools/release_check.py
```

检查包含发布文件完整性、原仓文件一致性与声明的最小测试。它不会自动下载模型或申请API，也不代表全部真实业务/准确率验收。保留的原仓错误、未运行项及外部依赖见 [KNOWN_ISSUES.md](KNOWN_ISSUES.md)。

## 发布版本与文件清单

本版本以原开发仓主分支提交 `0d92d7c805552bd3932682ff0e2040cf2ef6dc2f` 为源。功能实现与对应原文件保持一致；README、许可说明和发布辅助材料单独登记。当前功能的必要源码、配置、界面与运行资源保留，明确弃用的原型、历史结果和开发缓存不捆绑。

- [逐文件发布清单](RELEASE_FILES.md)
- [原仓文件与Git对象对应关系](SOURCE_ALIGNMENT.json)
- [完整文件SHA-256及权限](RELEASE_MANIFEST.json)，校验表为SHA256SUMS

校验值按Git存储字节生成；若原.gitattributes规定检出换行转换，请用Git对象或发布检查脚本校验，避免将LF/CRLF误认为源码变化。各公开平台release/1.0使用同一个提交，平台生成的运行分支不属于此发布清单。

## 反馈、贡献与许可证

请通过 [公开仓Issues](https://github.com/NGAI-LLMSafeContent-OpenSource/Project_3_Cultural_Diversity_test-release/issues) 提交复现步骤、环境和日志摘要，勿附真实凭据或用户数据。代码问题由课题维护者在原开发仓处理，发布负责人同步审核后的版本；不要仅修一个平台造成分歧。

自研代码采用[Apache-2.0](LICENSE)。模型、数据集、外部服务和第三方代码遵循各自许可与使用条件，见[第三方说明](THIRD_PARTY_NOTICES.md)。
