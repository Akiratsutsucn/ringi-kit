# ringi-kit 测试报告（TEST_REPORT）

> 来源：Claude Code CLI 按规格 `06-验收标准与测试用例.md` 执行 `tests/run_tests.py` 自动生成  
> 日期：2026-11-11　机器：Desktop　Skill 版本：v0.1.0

## 执行环境

- 执行日期：2026-11-11
- 操作系统：Windows-11-10.0.26100-SP0
- Python：3.12.10；Jinja2 3.1.6；PyYAML 6.0.3
- Windows PowerShell：5.1.26100.2161；PowerShell 7：7.6.1
- mermaid-cli：12.2.0（.bin）（B-06 始终用不存在的路径测试降级）
- Terraform：Terraform v1.17.2（terraform）

执行命令：`python tests/run_tests.py`（在仓库根目录）。全部输出在 `.work/tests/<用例ID>/`（已加入 .gitignore）。

## 汇总

| 分组 | 通过 | 跳过 | 合计 |
|---|---|---|---|
| 正例 | 7 | 0 | 7 |
| 负例 | 25 | 0 | 25 |
| 边界 | 8 | 0 | 8 |
| 验收清单·结构 | 8 | 0 | 8 |
| 验收清单·行为 | 1 | 0 | 1 |
| 验收清单·内容 | 6 | 0 | 6 |
| 验收清单·语言与合规 | 4 | 0 | 4 |
| 回归 | 8 | 0 | 8 |
| 工具链 | 3 | 0 | 3 |
| **合计** | **70** | **0** | **70** |

未通过用例：无
跳过用例：无

## 正例

| 用例 | 内容 | 结果 | 断言 |
|---|---|---|---|
| C-01 | 项目 A 完整渲染 | 通过 | ✔ render.py 退出码 0<br>✔ 8 个交付物齐全<br>✔ figures/ 目录存在且含 .mmd<br>✔ evidence/ 目录存在<br>✔ lint.py 退出码 0<br>✔ calendar_check.py 退出码 0<br>✔ LINT_STATUS.txt 首行为 PASS |
| C-02 | 项目 B 完整渲染 | 通过 | ✔ render.py 退出码 0<br>✔ 8 个交付物齐全<br>✔ figures/ 目录存在且含 .mmd<br>✔ evidence/ 目录存在<br>✔ lint.py 退出码 0<br>✔ calendar_check.py 退出码 0<br>✔ LINT_STATUS.txt 首行为 PASS<br>✔ 第 1 章含「云侧身份状态声明」且 ≥200 字（实测 382）<br>✔ 第 4 章含三方式对比表<br>✔ 第 4 章含两段否决理由<br>✔ 第 9 章含「T+○○分钟」回退判据 |
| C-03 | 项目 C 完整渲染 | 通过 | ✔ render.py 退出码 0<br>✔ 8 个交付物齐全<br>✔ figures/ 目录存在且含 .mmd<br>✔ evidence/ 目录存在<br>✔ lint.py 退出码 0<br>✔ calendar_check.py 退出码 0<br>✔ LINT_STATUS.txt 首行为 PASS<br>✔ 第 1 章含出站端点清单表（域名/用途/是否经代理）<br>✔ 第 4 章含身份同步方式论证<br>✔ 第 4 章明文「暂存模式不是备份」 |
| C-04 | 假设模式 | 通过 | ✔ 未授权假设时 render 退出码 2（S0 停止）<br>✔ --assume 渲染成功<br>✔ 方案书含「前提假设清单」章节<br>✔ 缺失的 4 项（共 6 个键）均以 [假设] 列出（实测 6 条）<br>✔ lint 校验该章节存在：章节完整时无 L-14<br>✔ 删除该章节后 lint 报 L-14 |
| C-05 | 裁决摘要篇幅 | 通过 | ✔ 正文字数 ≤1200（实测 731）<br>✔ 不含代码块<br>✔ 不含命令行 |
| C-06 | 锚点填写完整 | 通过 | ✔ L-13 通过（无 L-13 报告）<br>✔ 页脚出现「信息核实时点：YYYY-MM-DD」 |
| C-07 | 冻结窗口覆盖 | 通过 | ✔ render 退出码 0<br>✔ calendar_check 退出码 0（R1 降级为提示）<br>✔ calendar_check 输出 R1 [提示]<br>✔ 风险台账含「已获批准覆盖」条目<br>✔ 方案书风险章节标注「已获批准覆盖」<br>✔ lint 退出码 0 |

<details><summary>输出摘录</summary>

**C-01**

```text
[lint] 阻断 0 / 警告 0 / 提示 0（显示级别 ≥ 提示）
未发现违规。

[calendar_check] 阻断 0 / 提示 2
R3 [提示]
  违规对象：M-04「全拠点铺装完了」× 2028年9月末（2028-09-18～2028-10-13）
  问题：上线/切换落在期末前后 10 个工作日内（提示，不阻断）
  修复建议：确认无法改期；风险台账已派生 R-FB 条目
R3 [提示]
  违规对象：W-03「关东」× 2028年9月末（2028-09-18～2028-10-13）
  问题：上线/切换落在期末前后 10 个工作日内（提示，不阻断）
  修复建议：确认无法改期；风险台账已派生 R-FB 条目
```

**C-02**

```text
云侧身份状态声明字数=382
```

**C-04**

```text
- [假设] 
- [假设] 
- [假设] 
[lint] 阻断 2 / 警告 0 / 提示 0（显示级别 ≥ 提示）
L-14 [阻断]
  违规对象：01_提案書.md：前提假设清单
  问题：授权假设模式下缺少前提假设清单或条目未标注 [假设]
  修复建议：以 --assume 重新渲染
SCHEMA [阻断]
  违规对象：jp.decision_path
  问题：schema 校验失败：jp.decision_path：缺少必填键
  修复建议：按 schema/project.schema.json 修正
```

**C-05**

```text
字数=731
```

**C-06**

```text
信息核实时点：2026-11-11
```

**C-07**

```text
[calendar_check] 阻断 0 / 提示 3
R1 [提示]
  违规对象：W-01「试点」（2028-08-14～2028-08-24）× お盆（2028-08-13～2028-08-16）
  问题：冻结窗口冲突已获批准覆盖（批准人：客户信息系统部 部长；理由：试点拠点仅お盆期间停产可接受变更），降级为提示
  修复建议：方案书第 6 章与风险台账已标注「已获批准覆盖」，确认冻结期值班与升级联系人
R3 [提示]
  违规对象：M-04「全拠点铺装完了」× 2028年9月末（2028-09-18～2028-10-13）
  问题：上线/切换落在期末前后 10 个工作日内（提示，不阻断）
  修复建议：确认无法改期；风险台账已派生 R-FB 条目
R3 [提示]
  违规对象：W-03「关东」× 2028年9月末（2028-09-18～2028-10-13）
  问题：上线/切换落在期末前后 10 个工作日内（提示，不阻断）
  修复建议：确认无法改期；风险台账已派生 R-FB 条目
```

</details>

## 负例

| 用例 | 内容 | 结果 | 断言 |
|---|---|---|---|
| N-01 | 缺必填字段 | 通过 | ✔ render 退出码 2<br>✔ S0 停止<br>✔ 列出缺失字段名 project.client_name<br>✔ 未输出交付物 |
| N-02 | 占位符未替换 | 通过 | ✔ render 退出码 0（实测 0）<br>✔ lint 退出码 1（实测 1）<br>✔ 报告含规则 ID L-01<br>✔ 报告含对象「targets.scope」<br>✔ 报告含对象「01_提案書.md:第」 |
| N-03 | 缺方案书章节 | 通过 | ✔ 模板已删除第 9 章且渲染成功<br>✔ lint 退出码 1<br>✔ 报告含 L-02<br>✔ 报「缺章：9 回退计划」 |
| N-04 | 章节篇幅不足（项目 B 第 4 章） | 通过 | ✔ 基线渲染成功<br>✔ lint 退出码 1（实测 1）<br>✔ 报告含规则 ID L-03<br>✔ 报告含「第4章 200/900」 |
| N-05 | 步骤缺字段 | 通过 | ✔ render 退出码 ≠0（实测 2）<br>✔ lint 退出码 1（实测 1）<br>✔ 报告含规则 ID L-04<br>✔ 报告含对象「A-03-01」<br>✔ 报告含对象「rollback」 |
| N-06 | 前置条件含糊 | 通过 | ✔ render 退出码 0（实测 0）<br>✔ lint 退出码 1（实测 1）<br>✔ 报告含规则 ID L-05<br>✔ 报告含对象「环境已就绪」 |
| N-07 | 风险缺缓解措施 | 通过 | ✔ render 退出码 0（实测 0）<br>✔ lint 退出码 1（实测 1）<br>✔ 报告含规则 ID L-06<br>✔ 报告含对象「R-01」 |
| N-08 | 验收缺证据形式 | 通过 | ✔ render 退出码 0（实测 0）<br>✔ lint 退出码 1（实测 1）<br>✔ 报告含规则 ID L-07<br>✔ 报告含对象「T-01」 |
| N-09 | 方式比较不足三种 | 通过 | ✔ render 退出码 ≠0（实测 2）<br>✔ lint 退出码 1（实测 1）<br>✔ 报告含规则 ID L-09<br>✔ 报告含对象「comparison.options」 |
| N-10 | 缺否决理由 | 通过 | ✔ render 退出码 0（实测 0）<br>✔ lint 退出码 1（实测 1）<br>✔ 报告含规则 ID L-09<br>✔ 报告含对象「缺否决理由：一次性全量推送」 |
| N-11 | 日文版式字段被翻译 | 通过 | ✔ 基线渲染成功<br>✔ lint 退出码 1（实测 1）<br>✔ 报告含规则 ID L-10<br>✔ 报告含「第」<br>✔ 报告含「敬启」 |
| N-12 | 孤图 | 通过 | ✔ 基线渲染成功<br>✔ lint 退出码 1（实测 1）<br>✔ 报告含规则 ID L-11<br>✔ 报告含「rollout-phases」 |
| N-13 | 事前沟通记录为空 | 通过 | ✔ render 退出码 0（实测 0）<br>✔ lint 退出码 1（实测 1）<br>✔ 报告含规则 ID L-12<br>✔ 报告含对象「事前沟通记录」 |
| N-14 | 锚点未填 | 通过 | ✔ render 退出码 0（实测 0）<br>✔ lint 退出码 1（实测 1）<br>✔ 报告含规则 ID L-13<br>✔ 报告含对象「AN-01」<br>✔ 报告含对象「value 未填写」 |
| N-15 | 锚点过期（200 天前） | 通过 | ✔ render 退出码 0（实测 0）<br>✔ lint 退出码 1（实测 1）<br>✔ 报告含规则 ID L-13<br>✔ 报告含对象「AN-01」<br>✔ 报告含对象「距今 200 天」 |
| N-16 | 缺页脚时点 | 通过 | ✔ 基线渲染成功<br>✔ lint 退出码 1（实测 1）<br>✔ 报告含规则 ID L-15<br>✔ 报告含「01_提案書.md」 |
| N-17 | 缺体制图（multi_tier_vendors: true） | 通过 | ✔ lint 退出码 1<br>✔ 报告含 L-16<br>✔ 指出缺少体制图 |
| N-18 | 摘要超长（≥1500 字） | 通过 | ✔ lint 退出码 1<br>✔ 报告含 L-18<br>✔ 报字数（实测 2231，≥1500） |
| N-19 | 回退含糊 | 通过 | ✔ render 退出码 0（实测 0）<br>✔ lint 退出码 1（实测 1）<br>✔ 报告含规则 ID L-19<br>✔ 报告含对象「A-04-01」 |
| N-20 | WBS 无缓冲（approval_buffer_days: 0） | 通过 | ✔ render 退出码 0（实测 0）<br>✔ lint 退出码 1（实测 1）<br>✔ 报告含规则 ID L-20<br>✔ 报告含对象「M-01」<br>✔ 报告含对象「要件定義完了」 |
| N-21 | 失败模式引用失效 | 通过 | ✔ render 退出码 0（实测 0）<br>✔ lint 退出码 1（实测 1）<br>✔ 报告含规则 ID L-21<br>✔ 报告含对象「F-999」<br>✔ 报告含对象「A-02-01」 |
| N-22 | 冻结窗口冲突（上线日在年末年始） | 通过 | ✔ render 退出码 0（实测 0）<br>✔ cal 退出码 1（实测 1）<br>✔ 报告含规则 ID R1<br>✔ 报告含对象「M-GL」<br>✔ 报告含对象「年末年始」 |
| N-23 | 审批缓冲不足（相邻承认节点间隔 3 工作日） | 通过 | ✔ render 退出码 0（实测 0）<br>✔ cal 退出码 1（实测 1）<br>✔ 报告含规则 ID R2<br>✔ 报告含对象「缺 7 天」<br>✔ 报告含对象「间隔 3 个工作日」 |
| N-24 | references 中出现硬编码版本号 | 通过 | ✔ lint 退出码 1<br>✔ 静态扫描规则 S-01 告警并阻断<br>✔ 指出文件与行<br>✔ 指出命中值 2022 |
| N-25 | schema 不符（project_type: network） | 通过 | ✔ render 退出码 2<br>✔ schema 校验失败<br>✔ 提示仅支持三类 |

<details><summary>输出摘录</summary>

**N-01**

```text
[render] error：S0 停止：12 项必填字段缺失，不得用默认值填充
  - #1 客户名（可脱敏代号）：project.client_name
```

**N-02**

```text
L-01 [阻断]
  违规对象：project.yaml:targets.scope
  问题：存在未替换占位符 <待填写>
  修复建议：替换为真实值
```

**N-03**

```text
L-02 [阻断]
  违规对象：01_提案書.md
  问题：缺章：9 回退计划
  修复建议：恢复模板中的该章节，章节顺序固定为 11 章
```

**N-04**

```text
L-03 [阻断]
  违规对象：01_提案書.md 第4章
  问题：篇幅不足：第4章 200/900
  修复建议：补写本章依据、影响与待确认项；表格与代码不计入字数
```

**N-05**

```text
L-04 [阻断]
  违规对象：A-03-01
  问题：步骤缺字段：回退动作（rollback）
  修复建议：补齐九字段：前置条件、操作、预期结果、验证方法、失败处置、回退动作、预计耗时、责任人角色
```

**N-06**

```text
L-05 [阻断]
  违规对象：A-02-01 前置条件「环境已就绪」
  问题：含模糊词：就绪
  修复建议：改写为可验证的条件，例如「云主机已创建且网络规则已按 1.3 节清单配置」
```

**N-07**

```text
L-06 [阻断]
  违规对象：R-01
  问题：风险缺：缓解措施
  修复建议：补写缓解措施、责任人与触发条件
```

**N-08**

```text
L-07 [阻断]
  违规对象：T-01
  问题：验收项缺：证据形式
  修复建议：补写判定基准与证据形式
```

**N-09**

```text
L-09 [阻断]
  违规对象：comparison.options
  问题：方式比较仅 2 种，至少需要 3 种
  修复建议：补充第三种方式及其五维评分
```

**N-10**

```text
L-09 [阻断]
  违规对象：方式「一次性全量推送」
  问题：缺否决理由：一次性全量推送
  修复建议：在 rejected_reasons 中以完全相同的方式名写明理由
```

**N-11**

```text
L-10 [阻断]
  违规对象：01_提案書.md:第5行（recipient）
  问题：固定版式字段被替换：「A社 敬启」；封面收件方须为 client_display_name 且以「御中」或「様」结尾
  修复建议：恢复日文原文，不得翻译或改写
```

**N-12**

```text
L-11 [阻断]
  违规对象：figures/rollout-phases
  问题：孤图：rollout-phases（图5-1）在图前没有正文引用
  修复建议：在图前正文写「如图5-1所示」
```

**N-13**

```text
L-12 [阻断]
  违规对象：pre_communication
  问题：事前沟通记录为空
  修复建议：记录已与哪些部门/关键人说明、结论为何；为空不得交付
```

**N-14**

```text
L-13 [阻断]
  违规对象：AN-01
  问题：锚点 value 未填写（配置管理器 current branch 版本与生命周期）
  修复建议：访问 learn.microsoft.com/intune/configmgr/core/servers/manage/updates 核实后填写 value 与 verified_on
```

**N-15**

```text
L-13 [阻断]
  违规对象：AN-01
  问题：锚点 verified_on 距今 200 天，超过 90 天（配置管理器 current branch 版本与生命周期）
  修复建议：访问 learn.microsoft.com/intune/configmgr/core/servers/manage/updates 核实后填写 value 与 verified_on
```

**N-16**

```text
L-15 [阻断]
  违规对象：01_提案書.md
  问题：页脚缺少「信息核实时点：YYYY-MM-DD」
  修复建议：恢复模板页脚（_partials/anchors.md.j2）
```

**N-17**

```text
L-16 [阻断]
  违规对象：figures/org-structure.mmd
  问题：缺少体制图
  修复建议：deliverables 中保留 diagrams 并重新渲染
```

**N-18**

```text
L-18 [阻断]
  违规对象：02_稟議用サマリ.md
  问题：审批摘要超长：2231/1200 字
  修复建议：删减至 1200 字以内，细节引用方案书章节
```

**N-19**

```text
L-19 [阻断]
  违规对象：A-04-01
  问题：回退动作含糊：「视情况回退」
  修复建议：写明回退到哪一步之前的状态、如何执行、预计耗时
```

**N-20**

```text
L-20 [阻断]
  违规对象：M-01「要件定義完了」
  问题：承认节点前没有缓冲工作日
  修复建议：设置 jp.approval_buffer_days ≥1 并重新渲染；缓冲不得删除
```

**N-21**

```text
L-21 [阻断]
  违规对象：A-02-01 on_fail=F-999
  问题：失败模式引用失效：F-999 不存在于 failure-modes.md
  修复建议：改为 failure-modes.md 中存在的 F-### 条目，或先补写该条目
```

**N-22**

```text
R1 [阻断]
  违规对象：M-GL「上线（本番稼働）」（2028-12-30～2028-12-30）× 年末年始（2028-12-29～2029-01-03）
  问题：上线/切换/大范围变更类任务与冻结窗口重叠
  修复建议：改期；或在 schedule.override_freeze 中填写 {task_id, reason, approved_by} 显式覆盖
```

**N-23**

```text
R2 [阻断]
  违规对象：M-01「要件定義完了」→ M-02「基本設計完了」
  问题：相邻承认节点间隔 3 个工作日，要求 10 个，缺 7 天
  修复建议：后移后一个承认节点，或合并承认节点；不得降低 approval_buffer_days
```

**N-24**

```text
S-01 [阻断]
  违规对象：references/sccm-deployment.md:第437行
  问题：静态扫描：硬编码版本号「2022」
  修复建议：改写为核查锚点（02 第 9 节），或删除具体值
```

**N-25**

```text
[render] error：schema 校验失败
  - project.project_type：取值 'network' 不允许。project_type 仅支持三类：sccm（终端管理与客户端铺装）/ admerge（多企业 AD 合并）/ entraconnect（云端 Entra Connect）。三类之外的项目：骨架可复用，领域知识需自补，本 Skill 不生成完整方案书。
```

</details>

## 边界

| 用例 | 内容 | 结果 | 断言 |
|---|---|---|---|
| B-01 | 项目同时涉及 A 与 C | 通过 | ✔ SKILL.md 要求拆成两份配置<br>✔ schema 拒绝复合类型（退出码 2）<br>✔ 未生成方案书 |
| B-02 | 客户要求日文正文（language: ja） | 通过 | ✔ 渲染成功<br>✔ 章节标题切换为日文<br>✔ 固定版式字段仍存在<br>✔ L-17 术语规则自动失效（无 L-17）<br>✔ L-10 仍校验版式字段（篡改御中后阻断）<br>✔ 未篡改时 lint 退出码 0 |
| B-03 | 客户提供自有模板（template_override） | 通过 | ✔ 渲染使用客户模板<br>✔ 版式规则降级为提示（L-10 [提示]）<br>✔ 无 L-10 阻断<br>✔ lint 退出码 0 |
| B-04 | jp.vendor_tiers: 2 | 通过 | ✔ 体制图按两层渲染<br>✔ L-16 校验两层存在：lint 退出码 0<br>✔ 层数与配置不一致时 L-16 阻断 |
| B-05 | 项目类型为三类之外 | 通过 | ✔ render 明确提示「骨架可复用，领域知识需自补」<br>✔ new_project 同样提示并退出码 2<br>✔ 不生成完整方案书 |
| B-06 | mermaid-cli 不存在 | 通过 | ✔ 退出码 0<br>✔ 报告含 WARN 与「需手工渲染」<br>✔ 输出 .mmd 源码 |
| B-07 | 无网络 | 通过 | ✔ 脚本未导入任何网络库<br>✔ 代理指向不可达地址时全流程仍通过 |
| B-08 | PowerShell 5.1 与 7 双环境 | 通过 | ✔ Windows PowerShell 5.1 静态解析无错误且含 #Requires -Version 5.1<br>✔ PowerShell 7 静态解析无错误且含 #Requires -Version 5.1<br>✔ 5.1 冒烟运行（边界差集 + -WhatIf）通过<br>✔ 7 冒烟运行（边界差集 + -WhatIf）通过 |

<details><summary>输出摘录</summary>

**B-01**

```text
[render] error：schema 校验失败
  - project.project_type：取值 'sccm+entraconnect' 不允许。project_type 仅支持三类：sccm（终端管理与客户端铺装）/ admerge（多企业 AD 合并）/ entraconnect（云端 Entra Connect）。三类之外的项目：骨架可复用，领域知识需自补，本 Skill 不生成完整方案书。
```

**B-02**

```text
已知限制：长段正文仍为中文模板文字，需 Agent 翻译
[lint] 阻断 1 / 警告 0 / 提示 0（显示级别 ≥ 提示）
L-10 [阻断]
  违规对象：01_提案書.md:第5行（recipient）
  问题：固定版式字段被替换：「A社 敬启」；封面收件方须为 client_display_name 且以「御中」或「様」结尾
  修复建议：恢复日文原文，不得翻译或改写
```

**B-03**

```text
[lint] 阻断 0 / 警告 0 / 提示 4（显示级别 ≥ 提示）
L-10 [提示]
  违规对象：01_提案書.md（confidentiality）
  问题：固定版式字段缺失（含勿改写注释）
  修复建议：恢复模板中的固定版式区块
L-10 [提示]
  违规对象：01_提案書.md（date）
  问题：固定版式字段缺失（含勿改写注释）
  修复建议：恢复模板中的固定版式区块
L-10 [提示]
  违规对象：01_提案書.md（issuer）
  问题：固定版式字段缺失（含勿改写注释）
  修复建议：恢复模板中的固定版式区块
L-10 [提示]
  违规对象：01_提案書.md（recipient）
  问题：固定版式字段缺失（含勿改写注释）
  修复建议：恢复模板中的固定版式区块
```

**B-04**

```text
层数=2
[lint] 阻断 1 / 警告 0 / 提示 0（显示级别 ≥ 提示）
L-16 [阻断]
  违规对象：figures/org-structure.mmd
  问题：体制图层数 3 与 vendor_tiers=2 不一致
  修复建议：按 jp.vendors 补齐各层
```

**B-05**

```text
[render] error：schema 校验失败
  - project.project_type：取值 'network' 不允许。project_type 仅支持三类：sccm（终端管理与客户端铺装）/ admerge（多企业 AD 合并）/ entraconnect（云端 Entra Connect）。三类之外的项目：骨架可复用，领域知识需自补，本 Skill 不生成完整方案书。
```

**B-06**

```text
[diagram] warn
  WARN：未找到 mermaid-cli（mmdc），已输出 3 个 .mmd 源码到 E:\Workspace_sync\[Workspace Sync]\Code\ringi-kit\.work\tests\B-06\figures，需手工渲染为 svg 后放回同一目录（文件名不变，仅扩展名改为 .svg）。
```

**B-07**

```text
网络库导入：无
```

**B-08**

```text
5.1：PSVersion=5.1.26100.2161 failures=0
7：PSVersion=7.6.1 failures=0
```

</details>

## 验收清单·结构

| 用例 | 内容 | 结果 | 断言 |
|---|---|---|---|
| S-01 | 目录树与 02 第 1 节一致 | 通过 | ✔ 缺失项：无 |
| S-02 | SKILL.md ≤300 行且含 S0–S5 与 12 项必填字段 | 通过 | ✔ 行数 160 ≤300<br>✔ 含 YAML frontmatter（name/description）<br>✔ 含 S0–S5 六阶段<br>✔ 含 12 项必填字段<br>✔ 含 reference 路由表<br>✔ 含人工复核清单八条<br>✔ 声明语言约定（正文中文、6 处固定日文） |
| S-03 | 七份 references 存在且首部 20 行内有「何时读」 | 通过 | ✔ 文件数 7 = 7<br>✔ 首部摘要：{'ad-consolidation.md': True, 'entra-connect-cloud.md': True, 'failure-modes.md': True, 'glossary.md': True, 'jp-business-practice.md': True, 'proposal-writing.md': True, 'sccm-deployment.md': True}<br>✔ 每份 ≤800 行：{'ad-consolidation.md': 426, 'entra-connect-cloud.md': 418, 'failure-modes.md': 313, 'glossary.md': 191, 'jp-business-practice.md': 210, 'proposal-writing.md': 144, 'sccm-deployment.md': 436} |
| S-04 | 主模板 + 5 个 partial 存在 | 通过 | ✔ 主模板 8 个（02 第 1 节列 8 个；06 清单写 9 个，按 02 执行）<br>✔ partial 5 个 |
| S-05 | 5 个图表模板存在 | 通过 | ✔ 图表模板 5 个 |
| S-06 | schema 存在且可校验三份示例 | 通过 | ✔ project-a-sccm 校验错误 0 条<br>✔ project-b-admerge 校验错误 0 条<br>✔ project-c-entraconnect 校验错误 0 条 |
| S-07 | 6 个 Python 脚本可执行 | 通过 | ✔ new_project.py --help 退出码 0<br>✔ render.py --help 退出码 0<br>✔ lint.py --help 退出码 0<br>✔ calendar_check.py --help 退出码 0<br>✔ diagram.py --help 退出码 0<br>✔ labgen.py --help 退出码 0 |
| S-08 | PowerShell 四目录存在，脚本含 #Requires -Version 5.1 | 通过 | ✔ 非空目录 ['common', 'sccm', 'ad', 'entraconnect']<br>✔ 脚本 10 个，全部含 #Requires |

## 验收清单·行为

| 用例 | 内容 | 结果 | 断言 |
|---|---|---|---|
| J-01 | --json 输出可被程序解析；--only / --min-severity 可用 | 通过 | ✔ lint --json 输出可被 json 解析<br>✔ lint --format json 输出可被 json 解析<br>✔ calendar_check --json 输出可被 json 解析<br>✔ render --json 输出可被 json 解析<br>✔ diagram --json 输出可被 json 解析<br>✔ lint --min-severity error 可用<br>✔ render --only proposal,runbook 只输出两份（['01_提案書.md', '03_実施手順書.md']） |

## 验收清单·内容

| 用例 | 内容 | 结果 | 断言 |
|---|---|---|---|
| K-01 | failure-modes.md ≥40 条，三段分布达标 | 通过 | ✔ 合计 42 ≥40<br>✔ 分布 {'项目A': 17, '项目B': 14, '项目C': 11}（≥12/12/10） |
| K-02 | glossary.md ≥120 组 | 通过 | ✔ 术语 149 组，四列 |
| K-03 | jp-business-practice.md 五节齐全，文化摩擦 ≥10 条，退回原因 ≥8 条 | 通过 | ✔ 五节齐全<br>✔ 文化摩擦 12 条<br>✔ 退回原因 10 条 |
| K-04 | 三份项目参考的失败模式条目数达标（12/12/10），审查问题 ≥15 | 通过 | ✔ {'sccm-deployment.md': 17, 'ad-consolidation.md': 14, 'entra-connect-cloud.md': 11}<br>✔ 审查问题 20 条<br>✔ 各参考七节齐全 |
| K-05 | 三份成品方案书满足 03 第 3 节篇幅下限 | 通过 | ✔ a-sccm：各章 [850, 641, 543, 652, 778, 435, 738, 836, 694, 404, 393] ≥ [400, 500, 500, 600, 500, 300, 600, 500, 400, 300, 300]；合计 6964 ≥ 4900<br>✔ b-admerge：各章 [1443, 745, 626, 900, 743, 426, 729, 1014, 771, 407, 409] ≥ [700, 700, 600, 900, 600, 400, 700, 600, 700, 350, 350]；合计 8213 ≥ 6600<br>✔ c-entraconnect：各章 [1190, 585, 634, 909, 652, 440, 376, 744, 738, 406, 409] ≥ [600, 400, 500, 700, 400, 300, 350, 500, 500, 300, 300]；合计 7083 ≥ 4850 |
| K-06 | 三份成品方案书各自的必写小节齐全 | 通过 | ✔ C-01 必写小节缺失：无<br>✔ C-02 必写小节缺失：无<br>✔ C-03 必写小节缺失：无<br>✔ A 第 9 章区分「停止后续波次」与「客户端卸载」<br>✔ C 第 9 章区分「暂存模式切换回退」与「同步方式回退」 |

<details><summary>输出摘录</summary>

**K-05**

```text
a-sccm 合计 6964/4900
b-admerge 合计 8213/6600
c-entraconnect 合计 7083/4850
```

</details>

## 验收清单·语言与合规

| 用例 | 内容 | 结果 | 断言 |
|---|---|---|---|
| L-01 | 正文中文，仅 6 类固定版式字段为日文 | 通过 | ✔ C-01 固定版式字段 ['approval_header', 'closing', 'confidentiality', 'date', 'issuer', 'recipient', 'revision_header']<br>✔ C-01 正文假名占比 180/9964（仅术语注释）<br>✔ C-02 固定版式字段 ['approval_header', 'closing', 'confidentiality', 'date', 'issuer', 'recipient', 'revision_header']<br>✔ C-02 正文假名占比 241/11854（仅术语注释）<br>✔ C-03 固定版式字段 ['approval_header', 'closing', 'confidentiality', 'date', 'issuer', 'recipient', 'revision_header']<br>✔ C-03 正文假名占比 178/10309（仅术语注释） |
| L-02 | 无硬编码版本号、生命周期日期、端点域名（静态扫描 S-01） | 通过 | ✔ S-01 无报告 |
| L-03 | 无真实客户名、真实 IP、真实域名 | 通过 | ✔ 命中 无（示例客户名均为代号；示例出站端点为微软公开服务端点，非客户域名） |
| L-04 | labgen.py 产物：随机口令、无 0.0.0.0/0 入站、README 首行声明 | 通过 | ✔ 生成成功<br>✔ 口令由 random_password 生成，无固定口令<br>✔ 入站源仅为 var.mgmt_cidr<br>✔ --mgmt-cidr 0.0.0.0/0 被拒绝（退出码 2）<br>✔ README 首行有「仅用于验证」声明 |

## 回归

| 用例 | 内容 | 结果 | 断言 |
|---|---|---|---|
| R-01 | 非法或倒置的日期不被静默丢弃 | 通过 | ✔ 不存在的日期：render 退出码 2 并指出字段<br>✔ start 晚于 end：calendar_check 退出码 2 |
| R-02 | 日程与评分字段为占位符时给出明确错误而不崩溃 | 通过 | ✔ go_live 占位符：退出码 2，无 Traceback<br>✔ 评分占位符：退出码 2，无 Traceback |
| R-03 | 配置在渲染后被修改时拒绝陈旧产物 | 通过 | ✔ 基线全绿<br>✔ lint 报 BUILD 阻断<br>✔ calendar_check 报 BUILD 阻断<br>✔ LINT_STATUS.txt 回到 FAIL |
| R-04 | 锚点注释同一行的硬编码版本仍被扫描 | 通过 | ✔ S-01 命中 10.0.1 |
| R-05 | --only 与 deliverables 没有交集时报错 | 通过 | ✔ 单项 --only 正常<br>✔ 无交集：退出码 2 |
| R-06 | 假设模式不整体覆盖已部分填写的列表 | 通过 | ✔ 退出码 2，要求逐条补全 |
| R-07 | 同日上线去重，override_freeze 支持多个任务 | 通过 | ✔ calendar_check 退出码 0<br>✔ 无 M-GL 重复冲突<br>✔ 两项均为 R1 提示 |
| R-08 | Terraform 变量校验拒绝非 CIDR 与 /0 | 通过 | ✔ 使用 cidrhost 校验合法 CIDR<br>✔ 前缀长度须大于 0 |

<details><summary>输出摘录</summary>

**R-01**

```text
[render] error：日程与评分字段校验失败（渲染前必须为真实值）
  - jp.freeze_windows[0].start：不是有效日期 '2028-02-30'
[calendar_check] error：日程与评分字段校验失败（渲染前必须为真实值）
  - jp.freeze_windows[0]：start 2028-01-05 晚于 end 2027-12-29
```

**R-02**

```text
[render] error：日程与评分字段校验失败（渲染前必须为真实值）
  - schedule.go_live：仍为占位符 <待填写>
[calendar_check] error：日程与评分字段校验失败（渲染前必须为真实值）
  - comparison.options[0].scores：cost 仍为占位符或非整数
```

**R-03**

```text
[lint] 阻断 1 / 警告 0 / 提示 0（显示级别 ≥ 提示）
BUILD [阻断]
  违规对象：E:\Workspace_sync\[Workspace Sync]\Code\ringi-kit\.work\tests\R-03\build
  问题：project.yaml 在渲染后已被修改，构建产物已陈旧
  修复建议：重新执行 render.py 后再校验
```

**R-04**

```text
[lint] 阻断 1 / 警告 0 / 提示 0（显示级别 ≥ 提示）
S-01 [阻断]
  违规对象：references/sccm-deployment.md:第437行
  问题：静态扫描：硬编码版本号「10.0.1」
  修复建议：改写为核查锚点（02 第 9 节），或删除具体值
```

**R-05**

```text
[render] error：--only wbs 与 deliverables.items 没有交集，没有可渲染的交付物
```

**R-06**

```text
[render] error：S0 停止：12 项必填字段缺失，不得用默认值填充
  - #5 现有域数量与林结构：current_state.domains
  - 以上字段不可按假设值生成：日程与输出语言依赖其真实值，或该列表已部分填写，须逐条补全占位符
```

**R-07**

```text
[calendar_check] 阻断 0 / 提示 4
R1 [提示]
  违规对象：M-03「盆期上线」（2028-08-15～2028-08-15）× お盆（2028-08-13～2028-08-16）
  问题：冻结窗口冲突已获批准覆盖（批准人：客户部长；理由：停产期上线），降级为提示
  修复建议：方案书第 6 章与风险台账已标注「已获批准覆盖」，确认冻结期值班与升级联系人
R1 [提示]
  违规对象：W-01「试点」（2028-08-14～2028-08-15）× お盆（2028-08-13～2028-08-16）
  问题：冻结窗口冲突已获批准覆盖（批准人：客户部长；理由：停产期作业），降级为提示
  修复建议：方案书第 6 章与风险台账已标注「已获批准覆盖」，确认冻结期值班与升级联系人
R3 [提示]
  违规对象：M-05「全拠点铺装完了」× 2028年9月末（2028-09-18～2028-10-13）
  问题：上线/切换落在期末前后 10 个工作日内（提示，不阻断）
  修复建议：确认无法改期；风险台账已派生 R-FB 条目
R3 [提示]
  违规对象：W-03「关东」× 2028年9月末（2028-09-18～2028-10-13）
  问题：上线/切换落在期末前后 10 个工作日内（提示，不阻断）
  修复建议：确认无法改期；风险台账已派生 R-FB 条目
```

</details>

## 工具链

| 用例 | 内容 | 结果 | 断言 |
|---|---|---|---|
| X-01 | mermaid-cli 实际渲染全部图表 | 通过 | ✔ C-01：3 张图全部生成 svg 且无语法错误（失败：无）<br>✔ C-02：3 张图全部生成 svg 且无语法错误（失败：无）<br>✔ C-03：4 张图全部生成 svg 且无语法错误（失败：无） |
| X-02 | labgen 产物通过 terraform validate，变量校验拒绝全网来源 | 通过 | ✔ sccm：init/validate/fmt 均成功<br>✔ admerge：init/validate/fmt 均成功<br>✔ entraconnect：init/validate/fmt 均成功<br>✔ mgmt_cidr=192.0.2.0/24 被接受<br>✔ mgmt_cidr=0.0.0.0/0 被拒绝<br>✔ mgmt_cidr=* 被拒绝<br>✔ mgmt_cidr=Internet 被拒绝 |
| X-03 | PowerShell 依赖模块脚本（替身模块，非真实环境） | 通过 | ✔ powershell：7 个脚本在替身模块下判定与 CSV 列名正确<br>✔ pwsh：7 个脚本在替身模块下判定与 CSV 列名正确 |

<details><summary>输出摘录</summary>

**X-01**

```text
[diagram] ok
  boundary-collection.mmd → boundary-collection.svg
  org-structure.mmd → org-structure.svg
  rollout-phases.mmd → rollout-phases.svg
[diagram] ok
  ad-topology.mmd → ad-topology.svg
  org-structure.mmd → org-structure.svg
  rollout-phases.mmd → rollout-phases.svg
[diagram] ok
  ad-topology.mmd → ad-topology.svg
  org-structure.mmd → org-structure.svg
  rollout-phases.mmd → rollout-phases.svg
  sync-flow.mmd → sync-flow.svg
```

**X-02**

```text
sccm: Success! The configuration is valid.
admerge: Success! The configuration is valid.
entraconnect: Success! The configuration is valid.
```

**X-03**

```text
[powershell]
OK   forest-inventory（2 行）
OK   account-mapping（3 行）
OK   sidhistory-audit（2 行）
OK   collection-members（2 行）
OK   client-push-readiness（1 行）
OK   sync-status（3 行）
OK   outbound-endpoints（1 行）
MOCK PSVersion=5.1.26100.2161 failures=0
[pwsh]
OK   forest-inventory（2 行）
OK   account-mapping（3 行）
OK   sidhistory-audit（2 行）
OK   collection-members（2 行）
OK   client-push-readiness（1 行）
OK   sync-status（3 行）
OK   outbound-endpoints（1 行）
MOCK PSVersion=7.6.1 failures=0
```

</details>

## 说明

- 负例断言均同时检查退出码、规则 ID 与对象名（06 第 3 节要求），不只校验退出码。
- N-04、N-11、N-12、N-16、N-17、N-18 通过修改已渲染的交付物构造；N-03、N-24 在 Skill 的临时副本上修改模板或参考文件构造，不改动正式 Skill。
- N-05、N-09 的构造输入同时违反 schema（缺键 / 少于三项），`render.py` 以退出码 2 拒绝渲染，`lint.py` 仍对配置执行规则并报出 L-04 / L-09。
- B-02 只验证规格要求的三点（开关生效、L-10 仍校验、L-17 失效）；长段正文的日文化不在模板内实现，见 IMPLEMENTATION_NOTES 已知限制。
- R3（财年边界）在三份示例中均有提示级输出，属设计内行为，不阻断；对应风险条目由渲染自动派生。
- 工具链 X-03 用测试替身模块代替 ActiveDirectory / ConfigurationManager / ADSync，验证的是脚本逻辑、判定与 CSV 列名，不等于在真实客户环境实测。
- 示例配置中的锚点值为 2026-11-11 在微软官方文档核实的结果，90 天后（2027-02-09 起）L-13 会判为过期，须重新核实。
