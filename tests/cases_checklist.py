"""06 第 5 节验收清单：结构 / 行为（--json）/ 内容 / 语言与合规。"""
from __future__ import annotations

import json
import re

from tlib import C, EXAMPLES, cjk, record, run, section

TREE = [
    "SKILL.md",
    *[f"references/{n}" for n in ("jp-business-practice.md", "proposal-writing.md", "sccm-deployment.md", "ad-consolidation.md",
                                  "entra-connect-cloud.md", "failure-modes.md", "glossary.md")],
    *[f"templates/{n}" for n in ("proposal.md.j2", "approval-summary.md.j2", "runbook.md.j2", "wbs.csv.j2", "risk-register.csv.j2",
                                 "test-matrix.csv.j2", "meeting-minutes.md.j2", "anticipated-qa.md.j2")],
    *[f"templates/_partials/{n}" for n in ("cover.md.j2", "revision-history.md.j2", "approval-block.md.j2", "closing.md.j2", "anchors.md.j2")],
    *[f"assets/{n}" for n in ("ad-topology.mmd.j2", "boundary-collection.mmd.j2", "sync-flow.mmd.j2", "rollout-phases.mmd.j2", "org-structure.mmd.j2")],
    "schema/project.schema.json",
    *[f"scripts/{n}" for n in ("new_project.py", "render.py", "lint.py", "calendar_check.py", "diagram.py", "labgen.py")],
    "powershell/common", "powershell/sccm", "powershell/ad", "powershell/entraconnect",
    *[f"examples/{e}/project.yaml" for e in EXAMPLES.values()],
]
S0_KEYS = ["project.client_name", "project.industry", "project.employee_range", "project.sites_count", "current_state.domains",
           "current_state.cloud_tenants", "jp.budget_period", "jp.decision_path", "jp.vendors", "jp.security_review",
           "jp.freeze_windows", "deliverables.language"]


def _read(rel: str) -> str:
    return (C.kit / rel).read_text(encoding="utf-8")


def structure() -> None:
    missing = [p for p in TREE if not (C.kit / p).exists()]
    record("S-01", "验收清单·结构", "目录树与 02 第 1 节一致", [(f"缺失项：{missing or '无'}", not missing)])
    skill = _read("SKILL.md")
    lines = skill.count("\n") + 1
    record("S-02", "验收清单·结构", "SKILL.md ≤300 行且含 S0–S5 与 12 项必填字段",
           [(f"行数 {lines} ≤300", lines <= 300), ("含 YAML frontmatter（name/description）", skill.startswith("---\nname: ringi-kit\ndescription:")),
            ("含 S0–S5 六阶段", all(f"### S{i}" in skill for i in range(6))),
            ("含 12 项必填字段", all(k in skill for k in S0_KEYS)),
            ("含 reference 路由表", "何时读哪份 reference" in skill),
            ("含人工复核清单八条", len(re.findall(r"^- \[ \]", skill, re.M)) == 8),
            ("声明语言约定（正文中文、6 处固定日文）", "正文为中文" in skill and "6 处固定版式字段" in skill)])
    refs = sorted((C.kit / "references").glob("*.md"))
    heads = {p.name: "何时读" in "\n".join(p.read_text(encoding="utf-8").splitlines()[:20]) for p in refs}
    sizes = {p.name: p.read_text(encoding="utf-8").count("\n") + 1 for p in refs}
    record("S-03", "验收清单·结构", "七份 references 存在且首部 20 行内有「何时读」",
           [(f"文件数 {len(refs)} = 7", len(refs) == 7), (f"首部摘要：{heads}", all(heads.values())),
            (f"每份 ≤800 行：{sizes}", all(v <= 800 for v in sizes.values()))])
    mains = list((C.kit / "templates").glob("*.j2"))
    parts = list((C.kit / "templates" / "_partials").glob("*.j2"))
    record("S-04", "验收清单·结构", "主模板 + 5 个 partial 存在",
           [(f"主模板 {len(mains)} 个（02 第 1 节列 8 个；06 清单写 9 个，按 02 执行）", len(mains) == 8),
            (f"partial {len(parts)} 个", len(parts) == 5)])
    record("S-05", "验收清单·结构", "5 个图表模板存在", [(f"图表模板 {len(list((C.kit / 'assets').glob('*.mmd.j2')))} 个",
                                                    len(list((C.kit / "assets").glob("*.mmd.j2"))) == 5)])
    import sys
    sys.path.insert(0, str(C.kit / "scripts"))
    import render
    schema = render.load_schema()
    errs = {e: render.validate(render.load_yaml(C.kit / "examples" / e / "project.yaml"), schema, schema) for e in EXAMPLES.values()}
    record("S-06", "验收清单·结构", "schema 存在且可校验三份示例", [(f"{k} 校验错误 {len(v)} 条", not v) for k, v in errs.items()])
    helps = {n: run(n, "--help")[0] for n in ("new_project.py", "render.py", "lint.py", "calendar_check.py", "diagram.py", "labgen.py")}
    record("S-07", "验收清单·结构", "6 个 Python 脚本可执行", [(f"{k} --help 退出码 {v}", v == 0) for k, v in helps.items()])
    ps = sorted((C.kit / "powershell").rglob("*.ps*1"))
    req = {p.name: p.read_text(encoding="utf-8-sig").startswith("#Requires -Version 5.1") for p in ps}
    dirs = [d for d in ("common", "sccm", "ad", "entraconnect") if any((C.kit / "powershell" / d).iterdir())]
    record("S-08", "验收清单·结构", "PowerShell 四目录存在，脚本含 #Requires -Version 5.1",
           [(f"非空目录 {dirs}", len(dirs) == 4), (f"脚本 {len(ps)} 个，全部含 #Requires", all(req.values()))])


def behavior_json() -> None:
    build = C.work / "C-01" / "build"
    cfg = C.kit / "examples" / EXAMPLES["a-sccm"] / "project.yaml"
    outs = {
        "lint --json": run("lint.py", "--build", build, "--config", cfg, "--json"),
        "lint --format json": run("lint.py", "--build", build, "--config", cfg, "--format", "json"),
        "calendar_check --json": run("calendar_check.py", "--config", cfg, "--build", build, "--json"),
        "render --json": run("render.py", "--config", cfg, "--out", C.work / "J-01" / "build", "--json"),
        "diagram --json": run("diagram.py", "--src", build / "figures", "--out", C.work / "J-01" / "fig", "--json"),
    }
    checks = []
    for k, (_rc, out) in outs.items():
        try:
            json.loads(out)
            checks.append((f"{k} 输出可被 json 解析", True))
        except json.JSONDecodeError:
            checks.append((f"{k} 输出可被 json 解析", False))
    rc_min, out_min = run("lint.py", "--build", build, "--config", cfg, "--min-severity", "error")
    checks.append(("lint --min-severity error 可用", rc_min == 0 and "显示级别 ≥ 阻断" in out_min))
    rc_only, out_only = run("render.py", "--config", cfg, "--out", C.work / "J-01" / "only", "--only", "proposal,runbook")
    only_files = sorted(p.name for p in (C.work / "J-01" / "only").glob("0*"))
    checks.append((f"render --only proposal,runbook 只输出两份（{only_files}）", rc_only == 0 and only_files == ["01_提案書.md", "03_実施手順書.md"]))
    record("J-01", "验收清单·行为", "--json 输出可被程序解析；--only / --min-severity 可用", checks)


def _fm_counts():
    t = _read("references/failure-modes.md")
    ids = re.findall(r"^### (F-\d{3}) \| (项目[ABC])", t, re.M)
    by = {p: sum(1 for _i, x in ids if x == p) for p in ("项目A", "项目B", "项目C")}
    return len(ids), by


def content() -> None:
    total, by = _fm_counts()
    record("K-01", "验收清单·内容", "failure-modes.md ≥40 条，三段分布达标",
           [(f"合计 {total} ≥40", total >= 40), (f"分布 {by}（≥12/12/10）", by["项目A"] >= 12 and by["项目B"] >= 12 and by["项目C"] >= 10)])
    g = [ln for ln in _read("references/glossary.md").splitlines()
         if ln.startswith("|") and not ln.startswith("| 中文") and not ln.startswith("|---")]
    record("K-02", "验收清单·内容", "glossary.md ≥120 组", [(f"术语 {len(g)} 组，四列", len(g) >= 120 and all(ln.count("|") == 5 for ln in g))])
    jbp = _read("references/jp-business-practice.md")
    friction = len(re.findall(r"^\| \d+ \|", section(jbp, "1.5 常见文化摩擦与应对"), re.M))
    returns = len(re.findall(r"^\| \d+ \|", section(jbp, "1.2 决策流程"), re.M))
    record("K-03", "验收清单·内容", "jp-business-practice.md 五节齐全，文化摩擦 ≥10 条，退回原因 ≥8 条",
           [("五节齐全", all(f"## 1.{i}" in jbp for i in range(1, 6))), (f"文化摩擦 {friction} 条", friction >= 10),
            (f"退回原因 {returns} 条", returns >= 8)])
    counts = {n: len(re.findall(r"^#### F-\d{3}", _read(f"references/{n}"), re.M))
              for n in ("sccm-deployment.md", "ad-consolidation.md", "entra-connect-cloud.md")}
    q = len(re.findall(r"^\| Q-\d+", _read("references/entra-connect-cloud.md"), re.M))
    record("K-04", "验收清单·内容", "三份项目参考的失败模式条目数达标（12/12/10），审查问题 ≥15",
           [(f"{counts}", counts["sccm-deployment.md"] >= 12 and counts["ad-consolidation.md"] >= 12 and counts["entra-connect-cloud.md"] >= 10),
            (f"审查问题 {q} 条", q >= 15),
            ("各参考七节齐全", all(all(f"## {s}.{i}" in _read(f"references/{n}") for i in range(1, 8))
                                for s, n in (("3", "sccm-deployment.md"), ("4", "ad-consolidation.md"), ("5", "entra-connect-cloud.md"))))])
    _proposal_lengths()
    _proposal_sections()


def _proposal_lengths() -> None:
    import render
    checks, evid = [], []
    for case, (key, ptype) in {"C-01": ("a-sccm", "sccm"), "C-02": ("b-admerge", "admerge"), "C-03": ("c-entraconnect", "entraconnect")}.items():
        text = (C.work / case / "build" / "01_提案書.md").read_text(encoding="utf-8")
        mins = render.CHAPTER_MIN[ptype]
        got = []
        for title, _s, body in render.split_sections(text):
            m = re.match(r"(\d+) ", title)
            if m:
                got.append(render.count_chars(body))
        ok = len(got) == 11 and all(g >= mn for g, mn in zip(got, mins))
        checks.append((f"{key}：各章 {got} ≥ {mins}；合计 {sum(got)} ≥ {sum(mins)}", ok))
        evid.append(f"{key} 合计 {sum(got)}/{sum(mins)}")
    record("K-05", "验收清单·内容", "三份成品方案书满足 03 第 3 节篇幅下限", checks, "\n".join(evid))


REQUIRED = {
    "C-01": ["7.2 拠点别铺装波次表", "7.3 用户侧动作说明", "5.3 试点策略", "8.2 「装上了但不汇报」专项", "9.1 两级回退的定义"],
    "C-02": ["1.2 云侧身份状态声明", "4.2 三方式逐项对比", "4.4 不采用方式的理由", "7.1 用户可见变化清单", "8.2 历史 SID 到期专项", "9.2 以 T 为基准的时间轴"],
    "C-03": ["1.2 安全审查要件", "1.3 网络要件", "4.2 部署形态与身份同步方式论证", "8.4 「暂存模式不是备份」的澄清与替代恢复方案", "9.1 两种回退的区分"],
}


def _proposal_sections() -> None:
    checks = []
    for case, heads in REQUIRED.items():
        text = (C.work / case / "build" / "01_提案書.md").read_text(encoding="utf-8")
        missing = [h for h in heads if f"### {h}" not in text]
        checks.append((f"{case} 必写小节缺失：{missing or '无'}", not missing))
    a = (C.work / "C-01" / "build" / "01_提案書.md").read_text(encoding="utf-8")
    checks.append(("A 第 9 章区分「停止后续波次」与「客户端卸载」", "停止后续波次" in section(a, "9 回退计划") and "客户端卸载" in section(a, "9 回退计划")))
    c = (C.work / "C-03" / "build" / "01_提案書.md").read_text(encoding="utf-8")
    checks.append(("C 第 9 章区分「暂存模式切换回退」与「同步方式回退」", "暂存模式切换回退" in section(c, "9 回退计划") and "同步方式回退" in section(c, "9 回退计划")))
    record("K-06", "验收清单·内容", "三份成品方案书各自的必写小节齐全", checks)


def language() -> None:
    import render
    checks = []
    for case in ("C-01", "C-02", "C-03"):
        text = (C.work / case / "build" / "01_提案書.md").read_text(encoding="utf-8")
        marks = re.findall(r"<!-- FIELD:(\w+) -->", text)
        body = "".join(ln for _n, ln in render.prose_lines(text))
        kana = len(render.KANA_RE.findall(body))
        checks.append((f"{case} 固定版式字段 {sorted(set(marks))}", set(marks) == {"confidentiality", "recipient", "date", "issuer",
                                                                            "approval_header", "revision_header", "closing"}))
        checks.append((f"{case} 正文假名占比 {kana}/{len(body)}（仅术语注释）", kana / max(len(body), 1) < 0.15))
    record("L-01", "验收清单·语言与合规", "正文中文，仅 6 类固定版式字段为日文", checks)
    lint = run("lint.py", "--build", C.work / "C-01" / "build", "--config", C.kit / "examples" / EXAMPLES["a-sccm"] / "project.yaml")
    record("L-02", "验收清单·语言与合规", "无硬编码版本号、生命周期日期、端点域名（静态扫描 S-01）", [("S-01 无报告", "S-01" not in lint[1])])
    real = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b|株式会社(?!（代号）)")
    leaks = []
    for p in list((C.kit / "examples").rglob("*.yaml")) + list((C.kit / "templates").rglob("*.j2")) + list((C.kit / "references").glob("*.md")):
        for no, ln in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if real.search(ln):
                leaks.append(f"{p.name}:{no}")
    record("L-03", "验收清单·语言与合规", "无真实客户名、真实 IP、真实域名",
           [(f"命中 {leaks or '无'}（示例客户名均为代号；示例出站端点用保留后缀 .example）", not leaks)])
    lab = C.work / "L-04" / "lab"
    rc, _o = run("labgen.py", "--type", "entraconnect", "--out", lab, "--mgmt-cidr", "192.0.2.0/24")
    rc0, out0 = run("labgen.py", "--type", "entraconnect", "--out", C.work / "L-04" / "lab0", "--mgmt-cidr", "0.0.0.0/0")
    alltext = "\n".join(p.read_text(encoding="utf-8") for p in lab.rglob("*") if p.is_file()) if rc == 0 else ""
    record("L-04", "验收清单·语言与合规", "labgen.py 产物：随机口令、无 0.0.0.0/0 入站、README 首行声明",
           [("生成成功", rc == 0), ("口令由 random_password 生成，无固定口令", "random_password" in alltext and not re.search(r'admin_password\s*=\s*"', alltext)),
            ("入站源仅为 var.mgmt_cidr", 'source_address_prefix      = var.mgmt_cidr' in alltext),
            ("--mgmt-cidr 0.0.0.0/0 被拒绝（退出码 2）", rc0 == 2 and "/0" in out0),
            ("README 首行有「仅用于验证」声明", (lab / "README.md").read_text(encoding="utf-8").splitlines()[0].startswith("仅用于验证") if rc == 0 else False)])


def run_all() -> None:
    structure()
    behavior_json()
    content()
    language()
