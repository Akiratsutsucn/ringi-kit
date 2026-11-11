#!/usr/bin/env python3
"""new_project.py：按项目类型生成带注释的 project.yaml 骨架。

所有必填字段填 <待填写>，anchors 预填 02 第 9 节最小集。不生成任何真实客户信息。
退出码：0 成功；2 参数或文件错误。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render  # noqa: E402

P = render.PLACEHOLDER
Q = f'"{P}"'


def _gate_block(ptype: str) -> str:
    gid, name, checks = render.GATE_CHECKS[ptype]
    lines = [f'  - id: "{gid}"', f'    name: "{name}"', "    checks:            # 02 第 6 节固定检查项，不得删减"]
    lines += [f'      - "{c}"' for c in checks]
    lines.append(f"    fail_action: {Q}")
    return "\n".join(lines)


def _anchor_block() -> str:
    return "\n".join(
        f'  - {{id: "{aid}", topic: "{topic}", source: "{src}", value: "", verified_on: ""}}'
        for aid, topic, src in render.MIN_ANCHORS)


def _network_block(ptype: str) -> str:
    if ptype != "entraconnect":
        return ""
    return f"""
network:                           # 项目 C 必填：1.3 网络要件
  outbound_endpoints:              # 按 AN-06 核实结果逐行填写（域名 + 用途 + 是否经代理）
    - {{domain: {Q}, purpose: {Q}, via_proxy: {Q}}}
  dc_connectivity: {Q}             # 云主机到本地域控的连通方式（不止 443）
  proxy: {Q}

review:                            # 项目 C 必填：1.2 安全审查要件
  process: {Q}
  materials: [{Q}]
  duration_estimate: {Q}
  likely_questions: [{Q}]
"""


def skeleton(ptype: str, client_name: str) -> str:
    letter = render.TYPE_META[ptype]["letter"]
    return f"""# ringi-kit project.yaml 骨架（{render.TYPE_META[ptype]['label']}）
# 由 new_project.py 生成。所有 {P} 必须替换；S0 的 12 项必填字段缺一即停止，不得用默认值填充。
# 用户明确授权假设时：render.py --assume，或设 assumptions_mode: true，缺失项自动标注 [假设]。

project:
  code: {Q}                        # 文件名前缀，如 PRJ-{letter}-001
  client_name: {client_name}     # [S0-1] 客户名（可脱敏代号）
  client_display_name: {Q}         # 封面收件方：正式名称 + 敬称（御中/様）
  issuer: {Q}                      # 封面发文方：自社名 + 部署名 + 担当者名
  industry: {Q}                    # [S0-2]
  employee_range: {Q}              # [S0-3] 如 1000-3000
  sites_count: {Q}                 # [S0-4] 整数
  sites_distribution: {Q}          # [S0-4]
  project_type: "{ptype}"
  confidentiality: {Q}             # 社外秘 / 関係者限り / 社内限り

jp:
  fiscal_year_start_month: 4       # [S0-7] 固定 4
  budget_period: {Q}               # [S0-7] 预算期，如「2028年度上半期预算」
  approval_buffer_days: 10         # 每个承认节点前的缓冲工作日（规格默认 10）
  approval_nodes: ["内部评审", "客户评审", "再承认"]
  freeze_windows:                  # [S0-11] 至少一条；工作日计算会排除这些日期
    - {{name: {Q}, start: {Q}, end: {Q}}}
  fiscal_boundary_months: [3, 9]
  security_review: {Q}             # [S0-10] required / optional
  consumer_side_check_sheet: {Q}   # true / false
  multi_tier_vendors: {Q}          # true / false
  vendor_tiers: {Q}                # 2 / 3 / 4
  decision_path:                   # [S0-8]
    proposer: {Q}
    approver: {Q}
    signer: {Q}
  vendors:                         # [S0-9] 既有供应商与作业边界；tier 从 1 开始
    - {{tier: 1, name: {Q}, role: {Q}, scope: {Q}, not_doing: {Q}, contact_role: {Q}}}

current_state:
  domains:                         # [S0-5]
    - {{name: {Q}, forest: {Q}, dc_count: {Q}, functional_level: {Q}}}
  cloud_tenants:                   # [S0-6] 无租户时写 []
    - {{name: {Q}, user_count: {Q}, sync_method: {Q}}}
  endpoints:
    total: {Q}
    by_site: {{"{P}": {Q}}}
  existing_tools: [{Q}]
  pain_points:
    - {{point: {Q}, evidence: {Q}}}
  unquantified:
    - {{item: {Q}, impact: {Q}}}

targets:
  scope: {Q}
  out_of_scope: [{Q}]
  success_criteria: [{Q}]

schedule:
  start: {Q}
  go_live: {Q}
  milestones:                      # approval: true 为承认节点；kind: normal/cutover/go_live/mass_change
    - {{name: {Q}, date: {Q}, approval: true, kind: "normal"}}
  # override_freeze: {{task_id: "", reason: "", approved_by: ""}}   # 冻结窗口显式覆盖时才填写

rollout:                           # 波次/分批/切换窗口；id 形如 W-01
  - {{id: "W-01", name: {Q}, scope: {Q}, count: {Q}, start: {Q}, end: {Q}, business_impact: {Q}, exit_criteria: {Q}}}

comparison:
  client_profile: {Q}              # conservative（保守型）/ balanced（平衡型）
  options:                         # 至少三种方式，五维 1–5 分
    - {{name: {Q}, scores: {{cost: {Q}, risk: {Q}, duration: {Q}, impact: {Q}, scalability: {Q}}}}}
    - {{name: {Q}, scores: {{cost: {Q}, risk: {Q}, duration: {Q}, impact: {Q}, scalability: {Q}}}}}
    - {{name: {Q}, scores: {{cost: {Q}, risk: {Q}, duration: {Q}, impact: {Q}, scalability: {Q}}}}}
  chosen: {Q}
  rejected_reasons:                # 每个未选方式一条，须与客户规模/现状相关
    {Q}: {Q}
  sensitivity_note: {Q}

risks:
  - {{id: "R-01", category: {Q}, description: {Q}, trigger: {Q}, impact: {Q}, likelihood: {Q}, mitigation: {Q}, owner: {Q}, related_task: {Q}, status: "未处理"}}

steps:                             # 九字段缺一即 lint 失败；on_fail 引用 references/failure-modes.md 的 F-###
  - id: "{letter}-01-01"
    phase: {Q}
    name: {Q}
    preconditions: [{Q}]           # 可判定条件，禁止「环境已就绪」类空话
    action: {Q}
    expected: {Q}
    verify: {Q}
    on_fail: {Q}
    rollback: {Q}                  # 精确到步骤，禁止「视情况回退」
    minutes: {Q}
    owner_role: {Q}

gates:
{_gate_block(ptype)}

acceptance:
  - {{id: "T-01", requirement: {Q}, content: {Q}, method: {Q}, criteria: {Q}, evidence: {Q}, client_confirmer: {Q}, result: ""}}

impact:
  matrix:
    - {{unit: {Q}, department: {Q}, count: {Q}, change: {Q}, downtime_minutes: {Q}, wave: "W-01"}}
  user_visible_changes:
    - {{item: {Q}, changed: {Q}, detail: {Q}}}
  user_actions: [{Q}]
  user_no_actions: [{Q}]
  downtime_basis: {Q}

cutover:
  t_definition: {Q}                # 切换开始时刻 T 的定义
  checkpoints:                     # T+x 分钟未达成即触发回退
    - {{t_plus_minutes: {Q}, expected_state: {Q}, on_miss: {Q}}}
  decision_role: {Q}
  rollback_levels:
    - {{name: {Q}, trigger: {Q}, deadline: {Q}, steps: [{Q}], minutes: {Q}, end_state: {Q}}}

escalation:
  - {{level: {Q}, condition: {Q}, contact_role: {Q}, within: {Q}}}

pilot:
  target: {Q}
  reason: {Q}
  representativeness: {Q}
  success_criteria: [{Q}]
  on_fail: {Q}

phases:
  - {{name: {Q}, goal: {Q}, gate: {Q}, exit_criteria: {Q}}}
{_network_block(ptype)}
pre_communication:                 # 事前沟通记录（根回し），为空不得交付
  - {{date: {Q}, department: {Q}, person_role: {Q}, content: {Q}, conclusion: {Q}, follow_up: {Q}}}

open_items:                        # 待确认事项：内容 / 负责人 / 确认时点 / 影响章节
  - {{content: {Q}, owner: {Q}, due: {Q}, chapter: {Q}}}

revision_history:                  # S5：每次修订新增一行
  - {{version: "V1.0", date: {Q}, change: "初版", author: {Q}, approver: {Q}}}

deliverables:
  items: ["proposal", "approval_summary", "runbook", "wbs", "risk", "test_matrix", "qa", "meeting_minutes", "diagrams"]
  language: {Q}                    # [S0-12] zh（正文中文）/ ja（正文日文）
  format: {Q}                      # [S0-12] 如「Markdown 源文件 + PDF 定稿」

anchors:                           # 02 第 9 节最小集；value 与 verified_on 须在 90 天内人工核实填写
{_anchor_block()}

# glossary_overrides: {{域控: "DC"}}   # 客户用语覆盖（可选）
# template_override: "path/to/customer-proposal.md.j2"   # 客户自有模板（可选，版式规则降级为提示）
assumptions: []                    # 授权假设时，每条以 [假设] 开头
"""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="生成 project.yaml 骨架")
    ap.add_argument("--type", required=True, help="sccm|admerge|entraconnect")
    ap.add_argument("--out", required=True)
    ap.add_argument("--client-name", default=P)
    ap.add_argument("--force", action="store_true", help="覆盖已存在的文件")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    if args.type not in render.TYPE_META:
        msg = (f"不支持的项目类型：{args.type}。仅支持 sccm / admerge / entraconnect 三类；"
               "三类之外的项目：骨架可复用，领域知识需自补，本 Skill 不生成完整方案书。")
        render.emit("new_project", {"status": "error", "exit_code": 2, "message": msg}, args.json)
        return render.EXIT_ARG
    out = Path(args.out)
    if out.exists() and not args.force:
        render.emit("new_project", {"status": "error", "exit_code": 2,
                                    "message": f"文件已存在：{out}（如需覆盖请加 --force）"}, args.json)
        return render.EXIT_ARG
    # JSON 字符串是合法的 YAML 双引号标量，可正确转义引号、反斜杠与换行
    text = skeleton(args.type, json.dumps(args.client_name, ensure_ascii=False))
    try:  # 先在内存中解析与校验，通过后再写文件，避免 --force 覆盖后留下坏文件
        data = render._stringify_dates(yaml.safe_load(text))
    except yaml.YAMLError as exc:
        render.emit("new_project", {"status": "error", "exit_code": 2, "message": f"骨架 YAML 无效：{exc}"}, args.json)
        return render.EXIT_ARG
    schema = render.load_schema()
    errors = render.validate(data, schema, schema)
    if errors:
        render.emit("new_project", {"status": "error", "exit_code": 2, "message": "生成的骨架未通过 schema 校验",
                                    "details": errors}, args.json)
        return render.EXIT_ARG
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8", newline="\n")
    except OSError as exc:
        render.emit("new_project", {"status": "error", "exit_code": 2, "message": f"写出失败：{exc}"}, args.json)
        return render.EXIT_ARG
    render.emit("new_project", {"status": "ok", "exit_code": 0, "message": f"已生成骨架：{out}（schema 校验通过）",
                                "files": [str(out)]}, args.json)
    return render.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
