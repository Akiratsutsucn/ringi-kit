#!/usr/bin/env python3
"""lint.py：完备性校验（L-01 至 L-21 + Skill 静态扫描 S-01）。

每条规则一个独立函数，输入 LintContext，返回 Finding 列表。
报告按「规则 ID → 违规对象 → 修复建议」三段式输出。
退出码：0 通过；1 存在阻断项；2 参数或文件错误。
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render as R  # noqa: E402

ERROR, WARNING, INFO = "error", "warning", "info"
SEVERITY_RANK = {INFO: 0, WARNING: 1, ERROR: 2}
SEVERITY_LABEL = {ERROR: "阻断", WARNING: "警告", INFO: "提示"}

VAGUE_PRECONDITION = ["正常", "就绪", "适当", "适宜", "酌情", "视情况", "按需", "必要时", "妥善", "尽量"]
VAGUE_ROLLBACK = ["视情况", "按需", "酌情", "适当", "必要时", "看情况", "根据情况", "另行判断"]
BANNED_PROSE = ["业界最佳实践", "大幅提升", "风险可控", "业界标准方案", "视情况而定", "建议酌情", "等等",
                "保证零中断", "绝对安全"]
COMMAND_RE = re.compile(r"```|`[^`]+`|\b(?:Get|Set|New|Remove|Invoke|Test|Export|Import|Start|Stop)-[A-Z]\w+"
                        r"|\bpython3?\s+\S+\.py|^\s*(?:\$|>|PS>)\s", re.M)
SUMMARY_LIMIT = 1200
FIELD_RE = re.compile(r"<!--\s*FIELD:(\w+)\s*-->")
FIXED_EXPECT = {
    "revision_header": "| 版数 | 日付 | 変更内容 | 作成者 | 承認者 |",
    "approval_header": "| 承認 | 確認 | 作成 |",
    "closing": "以上",
}
CONFIDENTIALITY = {"社外秘", "関係者限り", "社内限り"}
DATE_FIELD_RE = re.compile(r"^\d{4}年\d{1,2}月\d{1,2}日（(令和|平成)(元|\d+)年\d{1,2}月\d{1,2}日）$")
FOOTER_RE = re.compile(r"信息核实时点：\d{4}-\d{2}-\d{2}")
PROPOSAL = "01_提案書.md"
SUMMARY = "02_稟議用サマリ.md"
RUNBOOK = "03_実施手順書.md"
WBS = "04_WBS.csv"
FAILURE_ID_RE = re.compile(r"^#{2,4}\s+(F-\d{3})\b", re.M)


@dataclass
class Finding:
    rule: str
    severity: str
    target: str
    message: str
    fix: str


@dataclass
class LintContext:
    config: dict
    config_path: Path
    build: Path | None
    skill_root: Path
    as_of: dt.date
    schema_errors: list[str] = field(default_factory=list)
    assumed_fields: list[str] = field(default_factory=list)
    assume_mode: bool = False
    docs: dict[str, str] = field(default_factory=dict)
    build_digest: str | None = None

    @property
    def ptype(self) -> str:
        return R.get_path(self.config, "project.project_type", "")

    @property
    def lang(self) -> str:
        return R.get_path(self.config, "deliverables.language", "zh")

    @property
    def override(self) -> bool:
        return bool(self.config.get("template_override"))

    def doc(self, name: str) -> str | None:
        return self.docs.get(name)


def _list(ctx: LintContext, key: str) -> list:
    value = ctx.config.get(key)
    return value if isinstance(value, list) else []


def _f(rule, sev, target, message, fix) -> Finding:
    return Finding(rule, sev, target, message, fix)


def _walk_strings(node, path=""):
    if isinstance(node, str):
        yield path, node
    elif isinstance(node, dict):
        for k, v in node.items():
            yield from _walk_strings(v, R._join(path, k))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _walk_strings(v, R._join(path, i))


def _section(text: str, prefix: str) -> tuple[int, str] | None:
    for title, start, body in R.split_sections(text):
        if title.startswith(prefix):
            return start, body
    return None


# ---------------------------------------------------------------- L-01 至 L-21

def rule_l01(ctx: LintContext) -> list[Finding]:
    """12 项必填字段齐全，且无未替换占位符。"""
    out = []
    for num, label, path in R.s0_missing(ctx.config):
        if path in ctx.assumed_fields:
            continue
        out.append(_f("L-01", ERROR, path, f"S0 必填字段 #{num}「{label}」缺失或为占位符",
                      "向客户确认后填写；用户授权假设时以 --assume 渲染，缺失项会标注 [假设]"))
    for path, text in _walk_strings(ctx.config):
        if R.PLACEHOLDER in text and not any(path.startswith(m[2]) for m in R.s0_missing(ctx.config)):
            out.append(_f("L-01", ERROR, f"project.yaml:{path}", f"存在未替换占位符 {R.PLACEHOLDER}", "替换为真实值"))
    for name, text in ctx.docs.items():
        for no, line in enumerate(text.splitlines(), 1):
            if R.PLACEHOLDER in line or "{{" in line:
                out.append(_f("L-01", ERROR, f"{name}:第{no}行", "交付物中存在未替换占位符", "修正 project.yaml 后重新渲染"))
    return out


def rule_l02(ctx: LintContext) -> list[Finding]:
    """方案书必含章节全部存在。"""
    text = ctx.doc(PROPOSAL)
    if text is None:
        return [_f("L-02", ERROR, PROPOSAL, "方案书不存在", "执行 render.py 生成方案书")]
    titles = [t for t, _s, _b in R.split_sections(text)]
    out = []
    for i, name in enumerate(R.CHAPTERS[ctx.lang], 1):
        if f"{i} {name}" not in titles:
            out.append(_f("L-02", ERROR, PROPOSAL, f"缺章：{i} {name}", "恢复模板中的该章节，章节顺序固定为 11 章"))
    front = R.FRONT[ctx.lang]
    for key in ("revision", "precomm", "glossary"):
        if front[key] not in titles:
            out.append(_f("L-02", ERROR, PROPOSAL, f"缺附加章节：{front[key]}", "恢复模板中的附加章节"))
    return out


def rule_l03(ctx: LintContext) -> list[Finding]:
    """每章篇幅达 03 第 3 节下限（中文字符数，不含表格与代码）。"""
    text = ctx.doc(PROPOSAL)
    if text is None or ctx.ptype not in R.CHAPTER_MIN:
        return []
    mins = R.CHAPTER_MIN[ctx.ptype]
    out = []
    for title, _start, body in R.split_sections(text):
        m = re.match(r"(\d+)\s", title)
        if not m or not 1 <= int(m.group(1)) <= 11:
            continue
        n = int(m.group(1))
        got = R.count_chars(body, ctx.lang)
        if got < mins[n - 1]:
            out.append(_f("L-03", ERROR, f"{PROPOSAL} 第{n}章", f"篇幅不足：第{n}章 {got}/{mins[n - 1]}",
                          "补写本章依据、影响与待确认项；表格与代码不计入字数"))
    return out


def rule_l04(ctx: LintContext) -> list[Finding]:
    """每个实施步骤九字段齐全且非空。"""
    out = []
    for i, step in enumerate(_list(ctx, "steps")):
        lacks = R.step_missing_fields(step) if isinstance(step, dict) else ["全部字段"]
        if lacks:
            sid = step.get("id") or f"steps[{i}]"
            keys = [k for k, label in R.NINE_FIELDS if label in lacks]
            out.append(_f("L-04", ERROR, sid, f"步骤缺字段：{'、'.join(lacks)}（{', '.join(keys)}）",
                          "补齐九字段：前置条件、操作、预期结果、验证方法、失败处置、回退动作、预计耗时、责任人角色"))
    return out


def rule_l05(ctx: LintContext) -> list[Finding]:
    """前置条件可判定（不含模糊词）；方案书正文禁用表述记警告。"""
    out = []
    for step in _list(ctx, "steps"):
        for cond in step.get("preconditions", []) if isinstance(step, dict) else []:
            hit = [w for w in VAGUE_PRECONDITION if w in str(cond)]
            if hit:
                out.append(_f("L-05", ERROR, f"{step.get('id')} 前置条件「{cond}」", f"含模糊词：{'、'.join(hit)}",
                              "改写为可验证的条件，例如「云主机已创建且网络规则已按 1.3 节清单配置」"))
    text = ctx.doc(PROPOSAL)
    if text:
        for no, line in R.prose_lines(text):
            for w in BANNED_PROSE:
                if w in line:
                    out.append(_f("L-05", WARNING, f"{PROPOSAL}:第{no}行", f"正文含禁用表述「{w}」",
                                  "按 references/proposal-writing.md 2.2 节替换"))
    return out


def rule_l06(ctx: LintContext) -> list[Finding]:
    """每个风险含缓解措施、责任人、触发条件。"""
    out = []
    for r in _list(ctx, "risks"):
        lacks = [lbl for k, lbl in (("mitigation", "缓解措施"), ("owner", "责任人"), ("trigger", "触发条件"))
                 if R.is_blank(r.get(k, R._MISSING))]
        if lacks:
            out.append(_f("L-06", ERROR, r.get("id", "?"), f"风险缺：{'、'.join(lacks)}", "补写缓解措施、责任人与触发条件"))
    return out


def rule_l07(ctx: LintContext) -> list[Finding]:
    """每个验收项含判定基准与证据形式。"""
    out = []
    for a in _list(ctx, "acceptance"):
        lacks = [lbl for k, lbl in (("criteria", "判定基准"), ("evidence", "证据形式")) if R.is_blank(a.get(k, R._MISSING))]
        if lacks:
            out.append(_f("L-07", ERROR, a.get("id", "?"), f"验收项缺：{'、'.join(lacks)}", "补写判定基准与证据形式"))
    return out


def rule_l08(ctx: LintContext) -> list[Finding]:
    """Gate 清单与项目类型匹配，且每项可判定。"""
    if ctx.ptype not in R.GATE_CHECKS:
        return []
    gid, _name, checks = R.GATE_CHECKS[ctx.ptype]
    gates = {g.get("id"): g for g in _list(ctx, "gates") if isinstance(g, dict)}
    if gid not in gates:
        return [_f("L-08", ERROR, gid, f"缺少与项目类型匹配的 Gate {gid}", "按 02 第 6 节补齐 Gate")]
    out = []
    have = gates[gid].get("checks", [])
    for c in checks:
        if c not in have:
            out.append(_f("L-08", ERROR, f"{gid}「{c}」", "缺少规格规定的检查项", "恢复该检查项（判定方法见对应 references 前置检查清单）"))
    for c in have:
        if c not in checks and any(w in c for w in VAGUE_PRECONDITION):
            out.append(_f("L-08", ERROR, f"{gid}「{c}」", "自定义检查项不可判定", "改写为可判定的检查项"))
    for g in gates.values():
        if g.get("id", "").split("-")[1:2] != [R.TYPE_META[ctx.ptype]["letter"]]:
            out.append(_f("L-08", ERROR, g.get("id", "?"), "Gate 编号与项目类型不匹配", f"使用 G-{R.TYPE_META[ctx.ptype]['letter']}-## 编号"))
    return out


def rule_l09(ctx: LintContext) -> list[Finding]:
    """方式比较含至少三种方式、五维评分、不选另外两个的理由。"""
    c = ctx.config.get("comparison") or {}
    options = c.get("options") or []
    out = []
    if len(options) < 3:
        out.append(_f("L-09", ERROR, "comparison.options", f"方式比较仅 {len(options)} 种，至少需要 3 种", "补充第三种方式及其五维评分"))
    names = []
    for o in options:
        names.append(o.get("name", "?"))
        scores = o.get("scores") or {}
        bad = [k for k in ("cost", "risk", "duration", "impact", "scalability")
               if not (isinstance(scores.get(k), int) and 1 <= scores[k] <= 5)]
        if bad:
            out.append(_f("L-09", ERROR, f"方式「{o.get('name')}」", f"五维评分缺失或越界：{', '.join(bad)}", "每维 1–5 分"))
    chosen = c.get("chosen")
    if chosen not in names:
        out.append(_f("L-09", ERROR, "comparison.chosen", f"选定方式「{chosen}」不在比较对象中", "chosen 须与 options[].name 完全一致"))
    reasons = c.get("rejected_reasons") or {}
    for n in names:
        if n != chosen and R.is_blank(reasons.get(n, R._MISSING)):
            out.append(_f("L-09", ERROR, f"方式「{n}」", f"缺否决理由：{n}", "在 rejected_reasons 中以完全相同的方式名写明理由"))
    if R.is_blank(c.get("sensitivity_note", R._MISSING)):
        out.append(_f("L-09", ERROR, "comparison.sensitivity_note", "缺敏感性说明", "写一句：权重大幅上调时结论是否翻转"))
    return out


def _check_fixed_line(ctx: LintContext, name: str, no: int, kind: str, line: str) -> str | None:
    cfg = ctx.config.get("project") or {}
    if kind == "recipient":
        if not (line.endswith("御中") or line.endswith("様")) or line != cfg.get("client_display_name"):
            return "封面收件方须为 client_display_name 且以「御中」或「様」结尾"
    elif kind == "issuer" and line != cfg.get("issuer"):
        return "封面发文方须与 project.issuer 一致"
    elif kind == "date" and not DATE_FIELD_RE.match(line):
        return "封面日期须为「公历（年号）」并列格式"
    elif kind == "confidentiality" and (line not in CONFIDENTIALITY or line != cfg.get("confidentiality")):
        return "机密等级须为 社外秘 / 関係者限り / 社内限り 之一，且与配置一致"
    elif kind in FIXED_EXPECT and line != FIXED_EXPECT[kind]:
        return f"须为「{FIXED_EXPECT[kind]}」"
    return None


def rule_l10(ctx: LintContext) -> list[Finding]:
    """固定日文版式字段存在且未被翻译替换。客户模板（template_override）时降级为提示。"""
    sev = INFO if ctx.override else ERROR
    out = []
    required = {PROPOSAL: {"recipient", "issuer", "date", "confidentiality", "revision_header", "approval_header", "closing"}}
    for name, text in ctx.docs.items():
        if not name.endswith(".md"):
            continue
        lines = text.splitlines()
        seen = set()
        for i, line in enumerate(lines):
            if R.FIXED_MARK not in line:
                continue
            m = FIELD_RE.search(line)
            kind = m.group(1) if m else "?"
            seen.add(kind)
            nxt = next((j for j in range(i + 1, len(lines)) if lines[j].strip()), None)
            value = lines[nxt].strip() if nxt is not None else ""
            problem = _check_fixed_line(ctx, name, nxt + 1 if nxt is not None else i + 1, kind, value)
            if problem:
                out.append(_f("L-10", sev, f"{name}:第{(nxt or i) + 1}行（{kind}）", f"固定版式字段被替换：「{value}」；{problem}",
                              "恢复日文原文，不得翻译或改写"))
        for kind in sorted(required.get(name, set()) - seen):
            out.append(_f("L-10", sev, f"{name}（{kind}）", "固定版式字段缺失（含勿改写注释）", "恢复模板中的固定版式区块"))
    text = ctx.doc(PROPOSAL)
    if text and ctx.lang == "zh":
        body = "".join(line for _no, line in R.prose_lines(text))
        kana = len(R.KANA_RE.findall(body))
        if body and kana / max(len(body), 1) > 0.15:
            out.append(_f("L-10", INFO, PROPOSAL, f"正文日文假名密度异常（{kana}/{len(body)}）", "正文应为中文，仅固定版式字段与术语注释为日文"))
    return out


def _figure_stems(ctx: LintContext) -> list[str]:
    if not ctx.build:
        return []
    return sorted(p.stem for p in (ctx.build / "figures").glob("*.mmd"))


def rule_l11(ctx: LintContext) -> list[Finding]:
    """每张图在正文有一次引用，且有图题与来源。"""
    text = ctx.doc(PROPOSAL)
    if text is None:
        return []
    lines = text.splitlines()
    out = []
    for stem in _figure_stems(ctx):
        idx = next((i for i, ln in enumerate(lines) if f"](figures/{stem}." in ln), None)
        if idx is None:
            out.append(_f("L-11", ERROR, f"figures/{stem}", f"孤图：{stem} 未嵌入方案书", "在对应章节嵌入该图并写图题与来源"))
            continue
        m = re.search(r"!\[(图\d+-\d+)", lines[idx])
        number = m.group(1) if m else None
        caption = next((ln for ln in lines[idx + 1:idx + 4] if ln.strip()), "")
        if not number or not caption.startswith(number) or "数据来源" not in caption:
            out.append(_f("L-11", ERROR, f"figures/{stem}", f"图题或数据来源缺失：{stem}", "图下一行写「图N-M 图题（数据来源：…）」"))
        prior = [ln for ln in lines[:idx] if number and number in ln and not ln.startswith(("!", number))]
        if number and not prior:
            out.append(_f("L-11", ERROR, f"figures/{stem}", f"孤图：{stem}（{number}）在图前没有正文引用", f"在图前正文写「如{number}所示」"))
    return out


def rule_l12(ctx: LintContext) -> list[Finding]:
    """「事前沟通记录」章节非空。"""
    if not _list(ctx, "pre_communication"):
        return [_f("L-12", ERROR, "pre_communication", "事前沟通记录为空", "记录已与哪些部门/关键人说明、结论为何；为空不得交付")]
    text = ctx.doc(PROPOSAL)
    if text is not None:
        sec = _section(text, R.FRONT[ctx.lang]["precomm"])
        rows = [ln for ln in (sec[1] if sec else "").splitlines() if ln.startswith("|") and "---" not in ln]
        if len(rows) < 2:
            return [_f("L-12", ERROR, f"{PROPOSAL}：{R.FRONT[ctx.lang]['precomm']}", "事前沟通记录章节为空", "重新渲染或补写记录")]
    return []


def rule_l13(ctx: LintContext) -> list[Finding]:
    """核查锚点全部已填写，且 verified_on 在 90 天内。"""
    out = []
    anchors = [a for a in _list(ctx, "anchors") if isinstance(a, dict)]
    for a in anchors:
        for p in R.anchor_problems(a, ctx.as_of):
            out.append(_f("L-13", ERROR, a.get("id", "?"), f"锚点 {p}（{a.get('topic', '')}）",
                          f"访问 {a.get('source', '官方文档')} 核实后填写 value 与 verified_on"))
    known = {a.get("id") for a in anchors}
    for rid in R.reference_anchor_ids(ctx.skill_root / "references"):
        if rid not in known:
            out.append(_f("L-13", ERROR, rid, "references 中的锚点未在 project.yaml 登记", "在 anchors 中补登该锚点"))
    return out


def rule_l14(ctx: LintContext) -> list[Finding]:
    """假设清单存在（仅在授权假设时要求）。"""
    if not (ctx.assume_mode or ctx.config.get("assumptions_mode") or ctx.assumed_fields):
        return []
    text = ctx.doc(PROPOSAL)
    title = R.FRONT[ctx.lang]["assumptions"]
    sec = _section(text or "", title)
    if not sec or "[假设]" not in sec[1]:
        return [_f("L-14", ERROR, f"{PROPOSAL}：{title}", "授权假设模式下缺少前提假设清单或条目未标注 [假设]", "以 --assume 重新渲染")]
    return []


def rule_l15(ctx: LintContext) -> list[Finding]:
    """页脚含信息核实时点。"""
    out = []
    for name in (PROPOSAL, SUMMARY, RUNBOOK):
        text = ctx.doc(name)
        if text is not None and not FOOTER_RE.search(text):
            out.append(_f("L-15", ERROR, name, "页脚缺少「信息核实时点：YYYY-MM-DD」", "恢复模板页脚（_partials/anchors.md.j2）"))
    return out


def rule_l16(ctx: LintContext) -> list[Finding]:
    """多层承包时，体制图与责任分界表存在，且层数与 jp.vendor_tiers 一致。"""
    jp = ctx.config.get("jp") or {}
    if jp.get("multi_tier_vendors") is not True:
        return []
    out = []
    tiers = jp.get("vendor_tiers")
    mmd = ctx.build / "figures" / "org-structure.mmd" if ctx.build else None
    if not mmd or not mmd.is_file():
        out.append(_f("L-16", ERROR, "figures/org-structure.mmd", "缺少体制图", "deliverables 中保留 diagrams 并重新渲染"))
    else:
        layers = len(re.findall(r"^\s*subgraph TIER\d", mmd.read_text(encoding="utf-8"), re.M))
        if layers != tiers:
            out.append(_f("L-16", ERROR, "figures/org-structure.mmd", f"体制图层数 {layers} 与 vendor_tiers={tiers} 不一致", "按 jp.vendors 补齐各层"))
    text = ctx.doc(PROPOSAL) or ""
    sec = _section(text, f"10 {R.CHAPTERS[ctx.lang][9]}")
    if not sec or "](figures/org-structure." not in sec[1]:
        out.append(_f("L-16", ERROR, f"{PROPOSAL} 第10章", "第 10 章未嵌入体制图", "恢复 10.1 体制图"))
    if not sec or "| 层 | 组织 | 角色 | 负责范围 | 不做的事项 | 窗口 |" not in sec[1]:
        out.append(_f("L-16", ERROR, f"{PROPOSAL} 第10章", "缺少责任分界表", "恢复 10.2 责任分界表"))
    return out


def rule_l17(ctx: LintContext) -> list[Finding]:
    """术语首次出现处附日文原文（警告）。正文为日文时自动失效。"""
    text = ctx.doc(PROPOSAL)
    if text is None or ctx.lang == "ja":
        return []
    glossary = R.load_glossary()
    by_zh = {g["zh"]: g for g in glossary}
    out = []
    for term, no, end, line in R.first_term_hits(text, glossary):
        if by_zh[term]["ja"] == term:
            continue
        if not line[end:].startswith(("（", "(")):
            out.append(_f("L-17", WARNING, f"{PROPOSAL}:第{no}行「{term}」", "术语首次出现未附日文原文",
                          f"写成「{term}（{by_zh[term]['ja']}）」"))
    return out


def rule_l18(ctx: LintContext) -> list[Finding]:
    """审批摘要 ≤1200 字且不含命令。"""
    text = ctx.doc(SUMMARY)
    if text is None:
        return []
    body = R.COMMENT_RE.sub("", text)
    body = re.sub(r"信息核实时点：\S+", "", body)
    count = len(re.sub(r"[\s|#*>\-]", "", body))
    out = []
    if count > SUMMARY_LIMIT:
        out.append(_f("L-18", ERROR, SUMMARY, f"审批摘要超长：{count}/{SUMMARY_LIMIT} 字", "删减至 1200 字以内，细节引用方案书章节"))
    m = COMMAND_RE.search(body)
    if m:
        out.append(_f("L-18", ERROR, SUMMARY, f"审批摘要含命令或代码：「{m.group(0).strip()}」", "命令下沉到实施手册"))
    return out


def rule_l19(ctx: LintContext) -> list[Finding]:
    """每步 rollback 不得为含糊表述。"""
    out = []
    for s in _list(ctx, "steps"):
        rb = str(s.get("rollback", "")) if isinstance(s, dict) else ""
        hit = [w for w in VAGUE_ROLLBACK if w in rb]
        if hit:
            out.append(_f("L-19", ERROR, s.get("id", "?"), f"回退动作含糊：「{rb}」", "写明回退到哪一步之前的状态、如何执行、预计耗时"))
    return out


def rule_l20(ctx: LintContext) -> list[Finding]:
    """WBS 中每个承认节点前存在缓冲工作日。"""
    if not ctx.build or not (ctx.build / WBS).is_file():
        return []
    rows = list(csv.DictReader(io.StringIO((ctx.build / WBS).read_text(encoding="utf-8"))))
    out = []
    for r in rows:
        if not r.get("承认节点"):
            continue
        buffers = [b for b in rows if b.get("任务名") == f"承认缓冲（{r.get('任务名')}）"
                   and b.get("结束", "") < r.get("开始", "") and re.match(r"[1-9]\d*", b.get("工期", ""))]
        if not buffers:
            out.append(_f("L-20", ERROR, f"{r.get('任务ID')}「{r.get('任务名')}」", "承认节点前没有缓冲工作日",
                          "设置 jp.approval_buffer_days ≥1 并重新渲染；缓冲不得删除"))
    for r in rows:
        if r.get("备注") == R.WBS_SHORT:
            out.append(_f("L-20", ERROR, f"{r.get('任务ID')}「{r.get('任务名')}」",
                          "承认缓冲挤占了前段作业，作业工期为负（缓冲与作业重叠）", "后移该承认节点或前移前一节点"))
    return out


def rule_l21(ctx: LintContext) -> list[Finding]:
    """步骤 on_fail 引用的失败模式存在。"""
    path = ctx.skill_root / "references" / "failure-modes.md"
    known = set(FAILURE_ID_RE.findall(path.read_text(encoding="utf-8"))) if path.is_file() else set()
    out = []
    for s in _list(ctx, "steps"):
        ref = s.get("on_fail") if isinstance(s, dict) else None
        if ref and not R.is_blank(ref) and ref not in known:
            out.append(_f("L-21", ERROR, f"{s.get('id')} on_fail={ref}", f"失败模式引用失效：{ref} 不存在于 failure-modes.md",
                          "改为 failure-modes.md 中存在的 F-### 条目，或先补写该条目"))
    return out


# ---------------------------------------------------------------- S-01 静态扫描（02 第 9 节第 4 条）

SCAN_PATTERNS = [
    ("硬编码日期", re.compile(r"20\d\d-\d\d-\d\d")),
    ("硬编码版本号", re.compile(r"(?<!\d)20\d{2}(?!\d)|(?<![\d.])\d+\.\d+\.\d+(?![\d.])")),
    ("硬编码 IP", re.compile(r"(?<![\d.])\d{1,3}(?:\.\d{1,3}){3}(?![\d.])")),
    ("硬编码域名", re.compile(r"\b[a-z0-9][a-z0-9-]*(?:\.[a-z0-9-]+)*\.(?:com|net|org|jp|io|cn|cloud|us|co|microsoft)\b")),
]


ANCHOR_COMMENT_RE = re.compile(r"<!--\s*/?ANCHOR\b.*?-->")


def scan_files(skill_root: Path) -> list[Path]:
    files = [skill_root / "SKILL.md"] + sorted((skill_root / "references").glob("*.md"))
    files += sorted((skill_root / "templates").rglob("*.j2")) + sorted((skill_root / "assets").glob("*.j2"))
    return [f for f in files if f.is_file()]


def rule_s01(ctx: LintContext) -> list[Finding]:
    """references / templates / assets / SKILL.md 中不得出现硬编码版本、日期、端点域名、IP。"""
    out = []
    for path in scan_files(ctx.skill_root):
        for no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            line = ANCHOR_COMMENT_RE.sub("", line)  # 只豁免锚点注释本身（含 source 属性），不豁免同行其他文字
            for label, rx in SCAN_PATTERNS:
                m = rx.search(line)
                if m:
                    rel = path.relative_to(ctx.skill_root).as_posix()
                    out.append(_f("S-01", ERROR, f"{rel}:第{no}行", f"静态扫描：{label}「{m.group(0)}」",
                                  "改写为核查锚点（02 第 9 节），或删除具体值"))
    return out


RULES = [rule_l01, rule_l02, rule_l03, rule_l04, rule_l05, rule_l06, rule_l07, rule_l08, rule_l09, rule_l10,
         rule_l11, rule_l12, rule_l13, rule_l14, rule_l15, rule_l16, rule_l17, rule_l18, rule_l19, rule_l20,
         rule_l21, rule_s01]


# ---------------------------------------------------------------- 驱动

def build_context(config_path: Path, build: Path | None, skill_root: Path, as_of: dt.date, assume: bool) -> LintContext:
    config = R.load_yaml(config_path)
    ctx = LintContext(config=config, config_path=config_path, build=build, skill_root=skill_root, as_of=as_of,
                      assume_mode=assume or bool(config.get("assumptions_mode")))
    if ctx.assume_mode:
        missing = R.s0_missing(config)
        ctx.assumed_fields = [p for _n, _l, p in missing if p not in R.NOT_ASSUMABLE]
    schema = R.load_schema()
    ctx.schema_errors = [e for e in R.validate(config, schema, schema)
                         if not any(e.startswith(p) for p in ctx.assumed_fields)]
    if build and build.is_dir():
        fm = load_fact_model(build)
        if fm is not None:
            ctx.assumed_fields = sorted(set(ctx.assumed_fields) | set(fm.get("assumptions", {}).get("assumed_fields", [])))
            ctx.assume_mode = ctx.assume_mode or bool(fm.get("assumptions", {}).get("mode"))
            ctx.build_digest = fm.get("doc", {}).get("config_sha256")
        for name, _tpl in R.OUTPUT_NAMES.values():
            p = build / name
            if p.is_file():
                try:
                    ctx.docs[name] = p.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError) as exc:
                    raise R.ConfigError(f"交付物无法以 UTF-8 读取：{p}") from exc
    return ctx


def load_fact_model(build: Path) -> dict | None:
    path = build / "fact_model.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise R.ConfigError(f"fact_model.json 损坏，请重新执行 render.py：{path}") from exc


def stale_build(config_path: Path, digest: str | None) -> str | None:
    """构建产物与当前配置不对应时返回原因。"""
    if digest is None:
        return "构建目录中没有 fact_model.json 或其中缺少配置哈希"
    if digest != R.config_digest(config_path):
        return "project.yaml 在渲染后已被修改，构建产物已陈旧"
    return None


def run_rules(ctx: LintContext) -> list[Finding]:
    findings = [_f("SCHEMA", ERROR, e.split("：")[0], f"schema 校验失败：{e}", "按 schema/project.schema.json 修正")
                for e in ctx.schema_errors]
    if ctx.build is None or not ctx.build.is_dir():
        findings.append(_f("L-02", ERROR, str(ctx.build), "构建目录不存在，交付物未渲染", "先执行 render.py"))
    elif ctx.docs and (reason := stale_build(ctx.config_path, ctx.build_digest)):
        findings.append(_f("BUILD", ERROR, str(ctx.build), reason, "重新执行 render.py 后再校验"))
    for rule in RULES:
        try:
            findings += rule(ctx)
        except (KeyError, TypeError, AttributeError, ValueError) as exc:
            findings.append(_f(rule.__name__.replace("rule_", "").upper().replace("L", "L-", 1), ERROR, "配置结构",
                               f"规则无法执行：{exc!r}", "先修正 schema 校验错误"))
    return findings


STATUS_FILE = "LINT_STATUS.txt"


def update_status(build: Path, tool: str, passed: bool, as_of: str) -> str:
    """更新 LINT_STATUS.txt 中本工具的一行，并重算总状态；同步更新方案书首页标注。"""
    path = build / STATUS_FILE
    lines = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
    tools = {}
    for ln in lines:
        m = re.match(r"^(lint\.py|calendar_check\.py)：(PASS|FAIL)", ln)
        if m:
            tools[m.group(1)] = ln
    tools[tool] = f"{tool}：{'PASS' if passed else 'FAIL'}（{as_of}）"
    overall = all(k in tools and "PASS" in tools[k] for k in ("lint.py", "calendar_check.py"))
    body = ["PASS" if overall else "FAIL"]
    body += [tools[k] for k in ("lint.py", "calendar_check.py") if k in tools]
    if not overall:
        body.append("原因：lint.py 与 calendar_check.py 须均退出码 0，产物方可标记为可交付。")
    path.write_text("\n".join(body) + "\n", encoding="utf-8")
    proposal = build / PROPOSAL
    if proposal.is_file():
        text = proposal.read_text(encoding="utf-8")
        label = (f"完备性校验：已通过（lint.py 与 calendar_check.py，{as_of}）" if overall
                 else "完备性校验：未通过完备性校验（lint.py 与 calendar_check.py 须均通过）")
        text = re.sub(re.escape(R.LINT_MARK) + r".*", R.LINT_MARK + label, text)
        proposal.write_text(text, encoding="utf-8", newline="\n")
    return body[0]


def report_text(findings: list[Finding], min_sev: str) -> str:
    shown = [f for f in findings if SEVERITY_RANK[f.severity] >= SEVERITY_RANK[min_sev]]
    errors = sum(f.severity == ERROR for f in findings)
    warns = sum(f.severity == WARNING for f in findings)
    infos = sum(f.severity == INFO for f in findings)
    out = [f"[lint] 阻断 {errors} / 警告 {warns} / 提示 {infos}（显示级别 ≥ {SEVERITY_LABEL[min_sev]}）"]
    for f in sorted(shown, key=lambda x: (x.rule, -SEVERITY_RANK[x.severity])):
        out.append(f"{f.rule} [{SEVERITY_LABEL[f.severity]}]")
        out.append(f"  违规对象：{f.target}")
        out.append(f"  问题：{f.message}")
        out.append(f"  修复建议：{f.fix}")
    if not shown:
        out.append("未发现违规。")
    return "\n".join(out)


def main(argv=None) -> int:
    R.utf8_stdout()
    ap = argparse.ArgumentParser(description="ringi-kit 完备性校验")
    ap.add_argument("--build", required=True)
    ap.add_argument("--config", required=True)
    ap.add_argument("--format", choices=["text", "json"], default="text")
    ap.add_argument("--json", action="store_true", help="等同 --format json")
    ap.add_argument("--min-severity", choices=["info", "warning", "error"], default="info")
    ap.add_argument("--assume", action="store_true")
    ap.add_argument("--as-of", default=None)
    ap.add_argument("--skill-root", default=str(R.SKILL_ROOT), help="被静态扫描的 Skill 根目录（默认本 Skill）")
    args = ap.parse_args(argv)
    as_json = args.json or args.format == "json"
    try:
        as_of = R.parse_as_of(args.as_of)
        ctx = build_context(Path(args.config).resolve(), Path(args.build), Path(args.skill_root), as_of, args.assume)
    except R.ConfigError as exc:
        payload = {"status": "error", "exit_code": R.EXIT_ARG, "message": str(exc), "findings": []}
        print(json.dumps(payload, ensure_ascii=False, indent=2) if as_json else f"[lint] error：{exc}")
        return R.EXIT_ARG
    findings = run_rules(ctx)
    blocked = any(f.severity == ERROR for f in findings)
    code = R.EXIT_BLOCK if blocked else R.EXIT_OK
    overall = update_status(ctx.build, "lint.py", not blocked, as_of.isoformat()) if ctx.build.is_dir() else "FAIL"
    if as_json:
        shown = [asdict(f) for f in findings if SEVERITY_RANK[f.severity] >= SEVERITY_RANK[args.min_severity]]
        print(json.dumps({"status": "fail" if blocked else "pass", "exit_code": code, "overall": overall,
                          "counts": {s: sum(f.severity == s for f in findings) for s in (ERROR, WARNING, INFO)},
                          "findings": shown}, ensure_ascii=False, indent=2))
    else:
        print(report_text(findings, args.min_severity))
    return code


if __name__ == "__main__":
    sys.exit(main())
