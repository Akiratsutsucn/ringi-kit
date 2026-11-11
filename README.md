# ringi-kit

面向日本企业客户的 IT 基础设施交付 Skill。为三类项目生成客户可签字的方案书（提案書）、稟议用摘要、预想问答集与可照着执行的实施手册，并用校验器保证产物完整。

| 类型 | 项目 | 主要交付物 |
|---|---|---|
| `sccm` | 终端管理平台（配置管理器）部署与客户端铺装 | 方案书 + 实施手册 + 分阶段铺装计划 |
| `admerge` | 多家企业 Active Directory 域合并 | 方案书 + 方式比较 + 切换与回退计划 |
| `entraconnect` | 云端 Entra Connect 同步服务器搭建 | 方案书 + 通信要件表 + 安全审查应答 |

交付物正文为中文；封面敬称、发文方、日期、机密等级、修订履历与审批栏表头、文末结句这几处固定版式字段保留日文原文。

## 使用

Agent 入口是 [`SKILL.md`](SKILL.md)，流程为 S0（12 项必填字段）→ S5（版本登记），阶段之间严格顺序。命令行最小示例：

```bash
python scripts/new_project.py --type sccm --out <项目>/project.yaml
python scripts/render.py --config <项目>/project.yaml --out <项目>/build/PRJ-A-001
python scripts/lint.py --build <项目>/build/PRJ-A-001 --config <项目>/project.yaml
python scripts/calendar_check.py --config <项目>/project.yaml --build <项目>/build/PRJ-A-001
```

`lint.py` 与 `calendar_check.py` 均退出码 0 后，`LINT_STATUS.txt` 首行才变为 PASS。

## 依赖

- Python 3.10+，仅标准库 + Jinja2 + PyYAML；不访问网络。
- PowerShell 层兼容 Windows PowerShell 5.1 与 PowerShell 7，全部为只读盘点与前置检查。
- 可选：mermaid-cli（`mmdc`）用于把 `figures/*.mmd` 渲染为 svg；缺失时 `diagram.py` 降级并提示。用本机 Edge/Chrome 渲染时以 `--puppeteer-config` 指定浏览器路径。
- 可选：Terraform，用于检查 `labgen.py` 生成的实验环境模板。
- 测试：`python tests/run_tests.py`。mermaid-cli、Terraform 可用环境变量 `RINGI_MMDC`、`RINGI_PUPPETEER_CONFIG`、`RINGI_TERRAFORM` 指定；找不到时工具链用例记为跳过。

## 目录

| 路径 | 内容 |
|---|---|
| `SKILL.md` | Skill 入口 |
| `references/` | 日本商务惯例、方案书写作规范、三类项目领域知识、失败模式库、术语集 |
| `templates/`、`assets/` | 交付物模板与 mermaid 图模板 |
| `schema/` | `project.yaml` 的 JSON Schema |
| `scripts/` | 渲染、校验、日程检查、图表、实验环境生成 |
| `powershell/` | Gate 证据采集脚本 |
| `examples/` | 三类项目的示例配置（全部为代号与假设值） |
| `tests/` | 自测（正例、负例、边界、验收清单、回归），`python tests/run_tests.py` |
| `docs/` | 实现说明与测试报告 |

## 版本事实不写死

产品版本、生命周期、受支持操作系统、迁移工具支持状态、出站端点等易变信息不写在 Skill 内，而是以核查锚点 AN-01～AN-06 登记在 `project.yaml`，每次生成前在官方文档核实；未核实或超过 90 天的锚点会被 `lint.py` 阻断。
