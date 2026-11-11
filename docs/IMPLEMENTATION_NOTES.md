# ringi-kit 实现说明（IMPLEMENTATION_NOTES）

> 来源：Claude Code CLI 按 `spec-src/jp-delivery-kit-spec/07-实施指令-给ClaudeCode.md` 实现  
> 日期：2026-11-11　机器：Desktop　Skill 版本：v0.1.0  
> 规格包：`jp-delivery-kit-spec.zip`（00–07 + 附录 A/B），解压于 `spec-src/`

## 1. 基本信息

| 项 | 内容 |
|---|---|
| Skill 名称 | `ringi-kit`。规格中的名称为 `jp-delivery-kit`，2026-11-11 My Lord 指示改名；目录名、frontmatter `name`、schema `$id` 与脚本说明已全部改为 ringi-kit |
| 源码仓库 | `Code/ringi-kit/`（git 工作副本，GitHub `Akiratsutsucn/ringi-kit` 为真相）；仓库根目录即 Skill 根目录，另含 `tests/`、`docs/` |
| 共享安装 | `skills/ringi-kit/`（从仓库固定提交复制的发布副本，不含 tests/docs），8 个客户端目录以 Junction 指向它 |
| 验收记录 | `projects/微软方案书制作skill/`：`TEST_REPORT.md`、`IMPLEMENTATION_NOTES.md`、`work/`（渲染与测试输出） |
| 运行环境 | Python 3.12.10 + Jinja2 3.1.6 + PyYAML 6.0.3；Windows PowerShell 5.1.26100 与 PowerShell 7.6.1 |
| 测试结果 | 67/67 通过（06 规定用例 59 项 + 审查回归 8 项），见 `TEST_REPORT.md` |

## 2. 七阶段执行记录

| 阶段 | 产出 | 阶段验证 | 结果 |
|---|---|---|---|
| 1 骨架与 schema | 目录树、`schema/project.schema.json`、`new_project.py` | 三种类型骨架生成成功且通过 schema；`--type network` 被拒绝 | 通过 |
| 2 references | 七份参考文件 | failure-modes 42 条（A17/B14/C11）；glossary 149 组；静态扫描无日期/版本/IP/域名 | 通过 |
| 3 模板 | 8 主模板 + 5 partial + 5 个 `.mmd.j2` | 模板无硬编码客户名、版本号、IP（S-01 扫描覆盖 templates 与 assets） | 通过 |
| 4 渲染管线 | `render.py`、`lint.py`、`calendar_check.py` | 三份示例 render / lint / calendar_check 均退出码 0 | 通过 |
| 5 PowerShell | `common/` 模块 + `sccm/` `ad/` `entraconnect/` 各 3 个脚本 | `Parser::ParseFile` 在 5.1 与 7 下均无错误；冒烟运行（边界差集、`-WhatIf`）两版本一致 | 通过 |
| 6 图表与实验室 | `diagram.py`、`labgen.py` | 无 mermaid-cli 时降级输出 `.mmd` 并 WARN、退出码 0；labgen 拒绝 /0，口令随机 | 通过 |
| 7 示例与自测 | 三份 `examples/*/project.yaml`、`tests/`、本文件、`TEST_REPORT.md` | 正例 7/7、负例 25/25、边界 8/8、验收清单 19/19、回归 8/8 | 通过 |

阶段 2 的三份项目参考（sccm / ad / entra）由子 Agent 按 04 的下限清单并行撰写，之后统一做了条目计数与静态扫描；`failure-modes.md` 由三份项目参考的失败模式库机械汇编，保证 ID 与内容一致。

阶段 4 的验证需要示例配置，因此示例在阶段 4 编写，阶段 7 只做最终核对。这是对生成顺序的唯一调整。

## 3. 规格未覆盖处的处理（按同风格补足）

### 3.1 schema 扩展键

02 第 5 节的键名全部保留且未改名。以下键为实现模板必写小节、S0 必填字段或边界用例所需而新增：

| 新增键 | 理由 |
|---|---|
| `jp.budget_period` | S0 #7「财年与预算期」中的预算期没有对应键 |
| `jp.decision_path {proposer, approver, signer}` | S0 #8 决策路径没有对应键 |
| `jp.vendors[]` | S0 #9 既有供应商与作业边界；同时是体制图与责任分界表的数据源 |
| `jp.vendor_tiers` | 05 第 8 节与附录 A 已使用，02 第 5 节未列 |
| `deliverables` 改为 `{items, language, format}` | 02 第 5 节为数组，但 02 第 3.1 节 S0 #12 要求语言与格式且禁止默认值，06 B-02 与 05 使用 `deliverables.language`。两处同属 02，取能同时满足 S0 #12 与 B-02 的对象形式 |
| `schedule.milestones[].id / kind` | R1/R3 需要区分上线、切换、大范围变更类任务；`kind` 缺省为 normal |
| `schedule.override_freeze` | 02 第 7 节定义，第 5 节未列；按 02 的单对象形式实现，同时接受对象列表（一个配置中多个任务需要覆盖时） |
| `rollout[]` | 波次/分批/切换窗口：A 的拠点别铺装波次表、B 的分批迁移排期、R1 的大范围变更对象 |
| `comparison.client_profile` | 02 第 3.2 节的两档权重需要选择依据 |
| `current_state.pain_points / unquantified` | 03 第 2 节「痛点证据」「未量化项单列」 |
| `impact`、`cutover`、`escalation`、`pilot`、`phases` | 第 5/7/9/10 章必写内容（影响矩阵、用户可见变化、T+分钟检查点、两级回退、联络路径、试点策略） |
| `network`、`review`（项目 C 必填） | 第 1 章网络要件（出站清单三列）与安全审查要件 |
| `pre_communication[]` | 事前沟通记录（L-12）的数据源 |
| `open_items[]` | 待确认事项登记表（内容/负责人/确认时点/影响章节） |
| `revision_history[]` | S5 修订履历的数据源 |
| `glossary_overrides`、`template_override`、`assumptions_mode` | 04 第 7 节客户用语覆盖、05 第 8 节客户模板、06 C-04 |

内容完备性（非空、可判定）不放进 schema，由 lint 判定；schema 只管结构与类型。原因：若 schema 要求非空，N-05/N-07/N-08 等负例会在渲染阶段以 schema 错误退出，lint 就报不出规定的规则 ID。

### 3.2 其他补足

| 事项 | 处理 |
|---|---|
| 核查锚点 ID 分配 | 采用附录 A 的六个 ID：AN-01 配置管理器版本、AN-02 客户端支持 OS、AN-03 功能级别、AN-04 迁移工具、AN-05 历史 SID、AN-06 出站端点与服务器 OS。02 第 9 节最小集中「出站端点」与「服务器 OS」两项按附录 A-3 合并在 AN-06 |
| 工作日与区间 | 工作日排除周末与 `jp.freeze_windows`；R2 的「间隔」= 两承认节点之间开区间 (前节点, 后节点) 内的工作日数，与 WBS 承认缓冲行一致（审查后修正，原为半开区间，差一天）；R3 窗口 = 3 月/9 月月末向前、向后各数 10 个工作日 |
| WBS 来源 | 由里程碑、承认缓冲、`rollout` 波次与上线日派生；承认缓冲 = 承认节点前 `approval_buffer_days` 个工作日。步骤级耗时留在实施手册 |
| R3 风险条目 | 渲染自动派生 `R-FB-##`；冻结窗口覆盖派生 `R-FZ-##`（状态「已获批准覆盖」）。calendar_check 校验风险台账中存在对应条目 |
| 加权最高分 ≠ 所选方式 | 第 4 章与稟议摘要自动写明最高分方式及其不满足硬性要求的事实，问答集同步说明 |
| 术语首次出现 | `render.py` 按 glossary 自动为正文首次出现补注日文原文，术语集章节自动列出正文用到的术语；中日同形的术语（期末、年末年始）不注 |
| 图题格式 | 03 的「図1-1 目標構成」是编号样式示例；为遵守「正文中文」写作「图3-1 目标架构…」，章-序编号不变 |
| 图的分配 | A：边界组图（兼影响面，含拠点终端数与波次）、推进图、体制图；B：现状与目标差异图、推进图、体制图；C：对象归属差异图、同步链路图、推进图、体制图 |
| 03 禁用表述的拦截 | 规则表无独立 ID，归入 L-05 作为警告级（正文出现「等等」「业界最佳实践」等时提示） |
| 静态扫描 | 规则 ID 记为 S-01（不占 L-01～L-21），扫描 SKILL.md、references、templates、assets：日期、20xx 四位数、x.y.z 版本号、IP、常见后缀域名；锚点注释行豁免 |
| 完备性状态 | `LINT_STATUS.txt` 首行为总状态；lint 与 calendar_check 各写一行，两者均 PASS 才为 PASS，并同步改写方案书首页的完备性标注 |
| 证据目录 | `evidence/README.md` 列出每个 Gate 检查项对应的证据文件名与 PowerShell 脚本 |
| PowerShell 证据 CSV 列名 | 采用 02 第 4.5 节验收矩阵列名（验收ID…结果），由 `Export-AuditCsv` 强制检查 |
| PowerShell 文件编码 | UTF-8 带 BOM + CRLF，Windows PowerShell 5.1 才能正确读取中文 |
| labgen 口令 | 用 Terraform `random_password` 在 apply 时生成，生成文件中不含任何口令（遵守全局规则「不写入明文密码」） |
| 渲染参数 | 增加 `--assume`（06 C-04）与 `--as-of`（指定信息核实时点，便于复现）；lint 增加 `--skill-root`（N-24 在副本上扫描） |

## 4. 规格冲突与选择

| 冲突 | 选择 | 理由 |
|---|---|---|
| 06 验收清单写「9 个模板」，02 第 1 节与 07 DoD 为 8 个主模板 | 8 个 | 优先级 02 > 06 |
| `deliverables` 数组形式（02 §5）与 `deliverables.language`（02 §3.1 S0 #12、06 B-02） | 对象形式 | 见 3.1；数组形式无法表达 S0 #12 且不允许默认值 |
| 02 第 8 节写「20 条规则」，07 写 21 条（含 L-21） | 21 条 | 07 与 04 第 6 节一致新增 L-21 |
| 02 §9 示例锚点 AN-03 为配置管理器，附录 A 中 AN-01 为配置管理器 | 附录 A 的分配 | 02 §9 只是格式示例，未规定 ID 分配；附录 A 是唯一完整分配 |
| L-05 禁止「正常」，02 §6 的固定 Gate 检查项含「时间同步正常」 | L-05 只检查步骤前置条件；Gate 固定项按 02 §6 原文保留，L-08 只对自定义检查项做模糊词检查 | 不改写规格给定的 Gate 原文 |

## 5. 对附录示例数据所做的修正

| 位置 | 原值 | 修正 | 理由 |
|---|---|---|---|
| 附录 A-1 `rejected_reasons` | 键「混合加入并行」 | 改为与方式名一致的「混合加入并行（Intune 协同）」 | L-09 按方式名精确匹配；否则报缺否决理由 |
| 附录 A-3 `C-03-01.preconditions` | 「云主机已就绪且网络策略已配置」 | 「云主机已创建且网络安全组规则已按 1.3 节清单配置」 | 含「就绪」，违反 L-05，示例须能通过 lint |
| 三份示例 `anchors` | 「【示例】…待核实填写」，verified_on 2026-11-01 | 「【示例】形式占位值…」，verified_on 2026-11-10 | 附录 A-4 推荐做法：示例须填形式合法的占位串才能通过 L-13；该值是形式占位，不是真实核实结果 |
| 附录 A-3 出站端点 | 未给出 | 使用保留后缀 `.example` 的示例域名 | 不写真实端点；真实使用按 AN-06 核实结果填写 |
| 三份示例 | — | 补充 3.1 的扩展键数据（数字均为假设值） | 必写小节需要数据 |

## 6. 已决事项（2026-11-11 My Lord 授权由实现方决定 1、2，指定 5）

| # | 事项 | 决定 | 理由 |
|---|---|---|---|
| 1 | 附录 A 的评分与所选方式不一致：项目 B 加权最高为「资源林 + 林间信任」（保守型 3.55，所选「跨林迁移」2.75）；项目 C 最高为「本地部署单实例」（3.90，所选「云上单实例」3.65） | 不改附录评分；方案书第 4 章、稟议摘要、问答集如实写明「最高分方式不满足硬性要求」并引用否决理由 | 07 要求照抄规格数据、不做设计决策；如实呈现比改分更经得起客户追问。真实项目中若评分与结论不一致，应在否决理由里写明是哪条硬性要求 |
| 2 | 「历史 SID 约 180 天默认存活期限」的说法可能不准确 | 保留规格原文，同时在 AN-05 锚点要求核实「期限属于哪个机制、由哪个配置项控制」；无自动到期时由项目书面设定回收日 | 规格要求写入该值并锚点化；锚点机制正是为这类需要现查的事实设计的 |
| 3 | 示例中的 `.jp` 域名 | 沿用附录 A 原文 | 均为带 `example` 的代号；静态扫描只覆盖 Skill 正文，不覆盖示例 |
| 4 | 项目 C 的数据驻留与同步组件版本期限 | 以【待确认】登记，不新增锚点 ID | 02 第 9 节锚点最小集固定为 6 项 |
| 5 | 存放位置 | My Lord 指定：源码放 `Code/ringi-kit` 并托管到 GitHub；同时安装到共享 `skills/` | 见第 1 节。`skills/ringi-kit` 是发布副本（与其他共享 Skill 一样记录来源提交），更新时从仓库重新复制，不在 `skills/` 内直接修改 |

## 6.1 代码审查后的修正（2026-11-11）

实现完成后由审查子 Agent 静态通读脚本，报告 14 项，逐条核实后全部修正，并补充回归用例 R-01～R-08：

| # | 问题 | 修正 | 回归用例 |
|---|---|---|---|
| 1 | 非法或倒置的冻结窗口、任务日期被静默丢弃，R1/R3 漏判 | `check_config` 新增日程字段校验（合法日期、start≤end），不再吞异常 | R-01 |
| 2 | 重渲染中途失败可能留下旧的 PASS 状态 | 先写 FAIL，再经临时目录逐个原子替换；捕获 OSError | — |
| 3 | Terraform 侧 `mgmt_cidr` 校验可被 `*`、`Internet` 绕过 | 改为 `cidrhost` 合法性 + 前缀长度 >0 | R-08 |
| 4 | 假设模式整体覆盖已部分填写的列表 | 只替换缺失或空值；部分填写的列表由 S0 列出、逐条补全 | R-06 |
| 5 | 日程与评分字段为占位符时 build 阶段崩溃 | 渲染前统一报 ConfigError（退出码 2） | R-02 |
| 6 | R2 与 WBS 缓冲定义差一天 | R2 改为开区间；WBS 作业被缓冲挤占时 L-20 阻断；N-23 构造日期相应调整 | N-23 |
| 7 | 同日 go_live 里程碑与上线任务重复，单个覆盖无法消解全部冲突 | 去重；`override_freeze` 接受列表 | R-07 |
| 8 | `new_project.py` 客户名转义不全且先写后验 | JSON 转义 + 内存校验后再写 | — |
| 9 | `diagram.py` 模板异常未捕获、未遵循假设模式、空结果报成功 | 先渲染到内存；对齐 assume；空结果报错 | — |
| 10 | 修改配置后未重渲染，陈旧产物也能 PASS | fact_model 记录配置 sha256；lint 与 calendar_check 不一致即 BUILD 阻断 | R-03 |
| 11 | 若干 I/O 异常以 traceback 退出 | 编码、读写、损坏的 fact_model、`--as-of` 均转为退出码 2 | — |
| 12 | `template_override` 的目录遮蔽内置模板，且非沙箱执行 | 只加载指定的单个文件；渲染环境改为 SandboxedEnvironment | B-03 |
| 13 | S-01 对含锚点注释的整行豁免 | 只剔除锚点注释本身再扫描 | R-04 |
| 14 | `--only` 与 deliverables 无交集时报成功 | 报错退出码 2 | R-05 |

## 7. 已知限制

- `deliverables.language: ja` 只切换章节标题与附加章节标题，类型相关的长段正文仍是中文模板文字；L-03 在日文模式下计入假名。完整日文正文需 Agent 渲染后翻译，再重跑 lint。
- 年号换算内置令和、平成；改元时须更新 `render.py` 的 `wareki()`。
- lint 不校验图内数字与正文表格数字的一致性（03 第 7 节已明示，靠人工复核）。
- PowerShell 层只做了静态解析与不依赖客户环境的冒烟测试（边界差集、端口探测、`-WhatIf`）。依赖 ConfigurationManager、ActiveDirectory、ADSync 模块的脚本需在具备这些模块的环境中实测。
- `labgen.py` 只支持 Azure；Terraform 与 Ansible 文件未在本机执行 `terraform validate`（本机未安装 Terraform）。
- 本机没有 mermaid-cli，`figures/` 只有 `.mmd` 源码；方案书引用的 `.svg` 需安装 mermaid-cli 后执行 `diagram.py`，或手工渲染。
- `render.py` 约 1180 行，超过个人编码规范的 800 行建议；为保持 02 第 1 节目录树一致，没有拆出额外模块（lint、calendar_check 直接复用 render 中的公共函数）。

## 8. 待人工核实锚点（真实使用前必须逐项填写）

| 锚点 | 核实对象 | 核实来源 | 示例中的状态 |
|---|---|---|---|
| AN-01 | 配置管理器 current branch 版本与生命周期 | learn.microsoft.com/mem/configmgr | 形式占位（A 适用） |
| AN-02 | 客户端支持的操作系统版本矩阵 | learn.microsoft.com/mem/configmgr | 形式占位（A 适用） |
| AN-03 | 目录服务功能级别支持矩阵 | learn.microsoft.com | 形式占位（A/B/C 适用） |
| AN-04 | 移行工具官方支持状态与版本要求 | learn.microsoft.com | 形式占位（B 适用） |
| AN-05 | 历史 SID 默认存活期限与配置项（含所属机制） | learn.microsoft.com | 形式占位（B 适用） |
| AN-06 | 同步服务出站端点清单与支持的服务器操作系统 | learn.microsoft.com | 形式占位（C 适用） |

## 实现状态

```text
## 实现状态
- 目录结构：完成（与 02 第 1 节一致；Skill 根目录名按 My Lord 指示为 ringi-kit）
- references：7/7，失败模式 42 条（A17/B14/C11），术语 149 组
- templates：8 主 + 5 partial，完成；assets 5 个图表模板，完成
- scripts：6 个 Python + 4 类 PowerShell（common 模块 + sccm/ad/entraconnect 各 3 个脚本），完成
- 示例：3/3，均已通过 lint 与 calendar_check
- 用例：正例 7/7，负例 25/25，边界 8/8（验收清单 19/19，审查回归 8/8）
- 待人工核实锚点：6 项（见第 8 节）
- 已知限制：日文正文需 Agent 翻译；PowerShell 依赖模块的脚本未在真实环境实测；本机无 mermaid-cli 与 Terraform
```
