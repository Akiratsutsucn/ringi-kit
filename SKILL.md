---
name: ringi-kit
description: 面向日本企业客户的 IT 基础设施交付套件。为三类项目生成客户可签字的方案书（提案書）、稟议用摘要、预想问答集与可照着执行的实施手册，并用 lint.py / calendar_check.py 校验完备性：A 终端管理平台（配置管理器 SCCM/MECM）部署与客户端铺装；B 多家企业 Active Directory 域合并；C 云端 Entra Connect 同步服务器搭建。用户提到日本客户、稟議、提案書、方案书、实施手册、域合并、客户端铺装、Entra Connect 同步服务器上云时使用。
---

# ringi-kit

一个 Skill 覆盖三类项目。三类项目骨架同构（现状 → 目标 → 方式比较 → 分步实施 → Gate → 回退 → 验收），差异只在领域知识。方案书与实施手册从同一份 fact model 渲染，校验器不可跳过。

## 语言约定（必须遵守）

- 交付物**正文为中文**。只有以下 6 处固定版式字段保留日文原文，不得翻译、不得改写：封面收件敬称（御中/様）、封面发文方、封面日期（公历与年号并列）、机密等级（社外秘/関係者限り/社内限り）、修订履历表头与审批栏表头（版数・日付・変更内容・作成者・承認者／承認・確認・作成）、文末结句（以上）。
- 输出文件名用日文形态（如 `01_提案書.md`），是为了与客户既有文档体系对齐；**文件名是日文不代表正文写日文**。
- 术语首次出现写成「中文（日文原文）」，取自 `references/glossary.md`；`render.py` 自动补注，`lint.py` L-17 复查。
- 客户要求日文正文时设 `deliverables.language: ja`：章节标题切换为日文，L-10 仍校验版式字段，L-17 自动失效；长段正文须由 Agent 在渲染后译为日文（见「已知限制」）。

## 适用范围

| 情形 | 处理 |
|---|---|
| 项目属于 A / B / C 之一 | 按本文件流程执行 |
| 一个需求同时涉及两类（例如 A 与 C） | **拆成两份 project.yaml 分别生成**，不得合并为一份方案书 |
| 三类之外（网络重构、邮件迁移等） | 明确告知用户：骨架可复用，领域知识需自补；不生成完整方案书（schema 只接受三类，会以退出码 2 拒绝） |
| 实际变更客户环境、报价、合同法务 | 不在本 Skill 范围内 |

## 目录

| 路径 | 内容 |
|---|---|
| `references/` | 七份知识文件，按下方路由表按需读取，不预加载 |
| `templates/` | 8 个主模板 + `_partials/` 5 个固定区块；只消费 fact model |
| `assets/` | 5 个 mermaid 图模板 |
| `schema/project.schema.json` | project.yaml 结构约束 |
| `scripts/` | `new_project.py` `render.py` `lint.py` `calendar_check.py` `diagram.py` `labgen.py` |
| `powershell/` | 只读盘点与前置检查脚本（common / sccm / ad / entraconnect），输出 Gate 证据 CSV |
| `examples/` | 三类项目的完整示例配置 |

脚本只依赖 Python 标准库 + Jinja2 + PyYAML，不访问网络。调用时使用脚本的绝对路径，输出目录显式指定到当前项目目录内。

## 主流程：S0 → S5（严格顺序，不可跳步）

### S0 上下文锁定

进入条件：用户提出需求。先用 `new_project.py --type <sccm|admerge|entraconnect> --out <项目目录>/project.yaml` 生成骨架，再逐项向用户确认下表 12 项。

| # | 必填字段 | 对应键 |
|---|---|---|
| 1 | 客户名（可脱敏代号） | `project.client_name` |
| 2 | 行业 | `project.industry` |
| 3 | 员工规模区间 | `project.employee_range` |
| 4 | 拠点数与地理分布 | `project.sites_count`、`project.sites_distribution` |
| 5 | 现有域数量与林结构 | `current_state.domains` |
| 6 | 现有云租户数量 | `current_state.cloud_tenants`（无租户写 `[]`） |
| 7 | 财年与预算期 | `jp.fiscal_year_start_month`（固定 4）、`jp.budget_period` |
| 8 | 决策路径（提案人/审批人/签字人） | `jp.decision_path` |
| 9 | 既有供应商与作业边界 | `jp.vendors` |
| 10 | 安全审查要求 | `jp.security_review` |
| 11 | 作业冻结窗口 | `jp.freeze_windows` |
| 12 | 交付物语言与格式 | `deliverables.language`、`deliverables.format` |

**门禁**：12 项齐备才进入 S1；缺一项即列出缺失并停止。**禁止用默认值填充。** 唯一例外：用户明确授权「按假设值生成」时，以 `render.py --assume`（或 `assumptions_mode: true`）渲染，缺失项标注 `[假设]` 并进入方案书「前提假设清单」，L-14 校验该章节存在。冻结窗口与交付语言不可假设。

### S1 现状与制约梳理

填写 `current_state`（含 `pain_points` 痛点与证据、`unquantified` 未量化项）、`targets`、`open_items`（待确认事项：内容 / 负责人 / 确认时点 / 影响章节）、`assumptions`。
**门禁**：现状清单、制约清单（第 1 章前提与 `out_of_scope`）、假设清单三份均非空；没有假设时在 `open_items` 中写明「无假设」的确认人。

### S2 方式比较与选型

在 `comparison` 中写至少三种方式，五维 1–5 分（成本、风险、工期、业务影响、可扩展性），`client_profile` 取 `conservative`（保守型）或 `balanced`（平衡型）。权重固定：

| 维度 | 保守型 | 平衡型 |
|---|---|---|
| 成本（初期+三年运维） | 0.15 | 0.25 |
| 风险（技术+组织） | 0.35 | 0.25 |
| 工期（含审批往返） | 0.20 | 0.20 |
| 业务影响（中断面） | 0.25 | 0.20 |
| 可扩展性（未来三年） | 0.05 | 0.10 |

**门禁**：对比表 + 逐项评分 + 每个未选方式的否决理由（键名与方式名完全一致，理由须与客户规模/现状相关）+ 一句敏感性说明。加权最高分不是所选方式时，方案书会自动写明「最高分方式不满足硬性要求」，否决理由必须说清是哪条硬性要求。

### S3 交付物生成

```
python3 scripts/render.py --config <项目>/project.yaml --out <项目>/build/<project.code>
python3 scripts/diagram.py --src <项目>/build/<code>/figures --out <项目>/build/<code>/figures
```

**门禁**：`deliverables.items` 声明的全部产物渲染成功（退出码 0）。模板变量缺失即报错退出，不输出半成品。`render.py` 写入 `LINT_STATUS.txt`（初始为 FAIL）与 `fact_model.json`。没有 mermaid-cli 时 `diagram.py` 输出 `.mmd` 并 WARN，需手工渲染为 svg 放回同一目录。用本机浏览器渲染时加 `--puppeteer-config <配置文件>`。

### S4 完备性校验

```
python3 scripts/lint.py --build <build 目录> --config <project.yaml>
python3 scripts/calendar_check.py --config <project.yaml> --build <build 目录>
```

**门禁**：两者均退出码 0。阻断项必须修正后重跑 S3/S4，**不得跳过 lint 直接标记可交付**。两者都通过后 `LINT_STATUS.txt` 首行变为 PASS，方案书首页标注「完备性校验：已通过」。首次使用可先用 `--min-severity error` 聚焦阻断项，但交付前须清零 L-17 警告。

### S5 版本与变更登记

在 `revision_history` 追加一行（版数从 V1.0 起，评审修正递增小版本），重新执行 S3、S4；页脚「信息核实时点」由渲染自动写入。
**门禁**：修订履历新增一行，页脚信息核实时点已写入，S4 再次全绿。

## Gate 与校验规则速查

| 项目 | Gate | 检查项数 | 判定方法所在 |
|---|---|---|---|
| A | G-A-01 客户端铺装前检查 | 7 | `sccm-deployment.md` 3.3 |
| B | G-B-01 域合并切换前检查 | 7 | `ad-consolidation.md` 4.4 |
| C | G-C-01 同步服务器上云前检查 | 8 | `entra-connect-cloud.md` 5.4 |

`lint.py` 规则 L-01～L-21（阻断为主，L-17 为警告）与静态扫描 S-01；`calendar_check.py` 规则 R1 冻结窗口冲突（阻断，`schedule.override_freeze` 可显式覆盖为提示）、R2 审批缓冲不足（阻断）、R3 财年边界风险（提示，自动派生风险条目）。报告均为「规则 ID → 违规对象 → 修复建议」三段式，`--json` 输出机器可读结果。

## 何时读哪份 reference

| 正在做的事 | 读 |
|---|---|
| 排计划、定上线日、写稟议摘要与问答集、处理客户含糊反馈 | `references/jp-business-practice.md` |
| 写任一章节正文、处理 L-03 / L-05 / L-17 | `references/proposal-writing.md` |
| 项目 A 的概念、铺装方式、波次、回退 | `references/sccm-deployment.md` |
| 项目 B 的三方式论证、历史 SID、云侧身份声明、切换回退 | `references/ad-consolidation.md` |
| 项目 C 的部署形态、网络要件、同步方式、安全审查应答 | `references/entra-connect-cloud.md` |
| 填步骤的 `on_fail`、现场按症状检索 | `references/failure-modes.md` |
| 术语日文原文、客户用语覆盖 | `references/glossary.md` |

## 核查锚点（防止过时）

版本号、生命周期、受支持操作系统、迁移工具支持状态、历史 SID 期限、出站端点不写死在 Skill 内，统一用锚点 AN-01～AN-06 登记在 `anchors`。每次生成前打开锚点 `source` 所指官方页面核实，填写 `value` 与 `verified_on`；未填、含「待核实填写」或超过 90 天，L-13 阻断。

## 其他开关

| 键 | 作用 |
|---|---|
| `schedule.override_freeze` | `{task_id, reason, approved_by}`：冻结窗口冲突降级为提示，风险台账标注「已获批准覆盖」 |
| `template_override` | 指向客户自有方案书模板；版式规则 L-10 降级为提示，内容规则照常阻断 |
| `glossary_overrides` | 客户内部叫法，渲染为「术语（日文；贵司称「X」）」 |
| `jp.vendor_tiers` | 承包层数 2/3/4，体制图按层数渲染，L-16 校验层数 |

实验环境：`labgen.py --type <类型> --out <项目>/lab/<类型> --mgmt-cidr <管理网段>`，口令随机生成、禁止 /0 入站、README 首行注明仅用于验证。

## 交付前人工复核清单（逐项打勾）

lint 能查结构，查不了「读起来是否可信」。交付前逐项确认：

- [ ] 第 1 章能让完全不懂技术的部长看懂「为什么有风险」
- [ ] 第 4 章能让技术负责人复述「为什么不选另外两个」
- [ ] 第 7 章能让现场主管说出「我这周要做什么」
- [ ] 第 9 章能让任何人说出「出事了在几点之前决定退」
- [ ] 图与表数字一致（lint 不校验数字一致性）
- [ ] 全文无「等等」「视情况」「酌情」
- [ ] 每个「待确认」都有负责人与确认时点
- [ ] 术语集覆盖了正文所有日文原文术语

## 已知限制

- `language: ja` 只切换章节标题与结构标签，类型相关的长段正文仍为中文模板文字，需 Agent 渲染后翻译并重跑 lint。
- 年号换算内置令和/平成两个年号；改元时须更新 `render.py` 的 `wareki()`。
- lint 不校验图表数字与正文数字一致，靠上方人工复核。
