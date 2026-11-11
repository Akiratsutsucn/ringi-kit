"""边界用例 B-01..B-08。"""
from __future__ import annotations

import os
import re
import shutil
import subprocess

from tlib import C, ENV, EXAMPLES, ROOT, dump, lint_only, load, pipeline, record, run

A = EXAMPLES["a-sccm"]


def b01():
    skill = (C.kit / "SKILL.md").read_text(encoding="utf-8")
    cfg = load(A)
    cfg["project"]["project_type"] = "sccm+entraconnect"
    rc, out = run("render.py", "--config", dump(cfg, "B-01"), "--out", C.work / "B-01" / "build")
    record("B-01", "边界", "项目同时涉及 A 与 C",
           [("SKILL.md 要求拆成两份配置", "拆成两份 project.yaml" in skill and "不得合并" in skill),
            ("schema 拒绝复合类型（退出码 2）", rc == 2), ("未生成方案书", not (C.work / "B-01" / "build" / "01_提案書.md").exists())], out)


def b02():
    cfg = load(A)
    cfg["deliverables"]["language"] = "ja"
    path = dump(cfg, "B-02")
    build, r, lint, _c = pipeline(path, "B-02")
    text = (build / "01_提案書.md").read_text(encoding="utf-8") if r[0] == 0 else ""
    (build / "01_提案書.md").write_text(text.replace("A社 御中", "A社 敬启", 1), encoding="utf-8")
    tampered = lint_only(path, build)
    record("B-02", "边界", "客户要求日文正文（language: ja）",
           [("渲染成功", r[0] == 0), ("章节标题切换为日文", "## 1 前提と制約" in text and "## 9 切り戻し計画" in text),
            ("固定版式字段仍存在", "以上" in text and "| 版数 | 日付 | 変更内容 | 作成者 | 承認者 |" in text),
            ("L-17 术语规则自动失效（无 L-17）", "L-17" not in lint[1]),
            ("L-10 仍校验版式字段（篡改御中后阻断）", tampered[0] == 1 and "L-10" in tampered[1]),
            ("未篡改时 lint 退出码 0", lint[0] == 0)],
           "已知限制：长段正文仍为中文模板文字，需 Agent 翻译\n" + tampered[1][:300])


def b03():
    d = C.work / "B-03"
    d.mkdir(parents=True, exist_ok=True)
    tpl = (C.kit / "templates" / "proposal.md.j2").read_text(encoding="utf-8")
    custom = tpl.replace('{% include "_partials/cover.md.j2" %}', "# 客户模板封面（客户自有格式）\n\n{{ project.client_name }} 様向け\n\n{{ doc.lint_status }}", 1)
    (d / "customer-proposal.md.j2").write_text(custom, encoding="utf-8")
    cfg = load(A)
    cfg["template_override"] = "customer-proposal.md.j2"
    path = dump(cfg, "B-03")
    build, r, lint, _c = pipeline(path, "B-03")
    text = (build / "01_提案書.md").read_text(encoding="utf-8") if r[0] == 0 else ""
    record("B-03", "边界", "客户提供自有模板（template_override）",
           [("渲染使用客户模板", "客户模板封面" in text), ("版式规则降级为提示（L-10 [提示]）", "L-10 [提示]" in lint[1]),
            ("无 L-10 阻断", "L-10 [阻断]" not in lint[1]), ("lint 退出码 0", lint[0] == 0)], lint[1][:600])


def b04():
    cfg = load(A)
    cfg["jp"]["vendor_tiers"] = 2
    cfg["jp"]["vendors"] = [v for v in cfg["jp"]["vendors"] if v["tier"] <= 2]
    path = dump(cfg, "B-04")
    build, r, lint, _c = pipeline(path, "B-04")
    mmd = (build / "figures" / "org-structure.mmd").read_text(encoding="utf-8") if r[0] == 0 else ""
    layers = len(re.findall(r"^\s*subgraph TIER\d", mmd, re.M))
    # 篡改为三层后 L-16 应报层数不一致
    (build / "figures" / "org-structure.mmd").write_text(mmd + '\n  subgraph TIER3["多余层"]\n  end\n', encoding="utf-8")
    bad = lint_only(path, build)
    record("B-04", "边界", "jp.vendor_tiers: 2",
           [("体制图按两层渲染", layers == 2), ("L-16 校验两层存在：lint 退出码 0", lint[0] == 0),
            ("层数与配置不一致时 L-16 阻断", bad[0] == 1 and "L-16" in bad[1])], f"层数={layers}\n" + bad[1][:300])


def b05():
    cfg = load(A)
    cfg["project"]["project_type"] = "network"
    rc, out = run("render.py", "--config", dump(cfg, "B-05"), "--out", C.work / "B-05" / "build")
    rc2, out2 = run("new_project.py", "--type", "network", "--out", C.work / "B-05" / "skeleton.yaml")
    record("B-05", "边界", "项目类型为三类之外",
           [("render 明确提示「骨架可复用，领域知识需自补」", "骨架可复用，领域知识需自补" in out),
            ("new_project 同样提示并退出码 2", rc2 == 2 and "骨架可复用，领域知识需自补" in out2),
            ("不生成完整方案书", rc == 2 and not (C.work / "B-05" / "build" / "01_提案書.md").exists())], out)


def b06():
    src = C.work / "C-01" / "build" / "figures"
    out_dir = C.work / "B-06" / "figures"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    env = {**ENV, "PATH": os.pathsep.join(p for p in ENV.get("PATH", "").split(os.pathsep) if "npm" not in p.lower())}
    rc, out = run("diagram.py", "--src", src, "--out", out_dir, "--mmdc", str(C.work / "no-such-mmdc.exe"), env=env)
    record("B-06", "边界", "mermaid-cli 不存在",
           [("退出码 0", rc == 0), ("报告含 WARN 与「需手工渲染」", "WARN" in out and "需手工渲染" in out),
            ("输出 .mmd 源码", len(list(out_dir.glob("*.mmd"))) == 3)], out)


def b07():
    banned = re.compile(r"^\s*(import|from)\s+(socket|urllib|http|requests|ftplib|smtplib)\b", re.M)
    hits = [p.name for p in (C.kit / "scripts").glob("*.py") if banned.search(p.read_text(encoding="utf-8"))]
    env = {**ENV, "HTTP_PROXY": "http://127.0.0.1:9", "HTTPS_PROXY": "http://127.0.0.1:9", "NO_PROXY": ""}
    cfg = C.kit / "examples" / EXAMPLES["c-entraconnect"] / "project.yaml"
    build, r, lint, cal = pipeline(cfg, "B-07", env=env)
    record("B-07", "边界", "无网络",
           [("脚本未导入任何网络库", not hits), ("代理指向不可达地址时全流程仍通过", r[0] == 0 and lint[0] == 0 and cal[0] == 0)],
           f"网络库导入：{hits or '无'}")


def b08():
    script = ROOT / "tests" / "ps_parse.ps1"
    target = str(C.kit / "powershell")
    res = {}
    for exe in ("powershell", "pwsh"):
        path = shutil.which(exe)
        if not path:
            res[exe] = (None, "未安装")
            continue
        args = [path, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script), "-Root", target]
        p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
        res[exe] = (p.returncode, p.stdout.strip().splitlines()[-1] if p.stdout.strip() else p.stderr[:200])
    smoke = ROOT / "tests" / "ps_smoke.ps1"
    smoke_res = {}
    for exe in ("powershell", "pwsh"):
        path = shutil.which(exe)
        if path:
            p = subprocess.run([path, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(smoke), "-Kit", target,
                                "-Out", str(C.work / "B-08" / exe)], capture_output=True, text=True, encoding="utf-8",
                               errors="replace", check=False)
            smoke_res[exe] = p.returncode
    record("B-08", "边界", "PowerShell 5.1 与 7 双环境",
           [("Windows PowerShell 5.1 静态解析无错误且含 #Requires -Version 5.1", res["powershell"][0] == 0),
            ("PowerShell 7 静态解析无错误且含 #Requires -Version 5.1", res["pwsh"][0] == 0),
            ("5.1 冒烟运行（边界差集 + -WhatIf）通过", smoke_res.get("powershell") == 0),
            ("7 冒烟运行（边界差集 + -WhatIf）通过", smoke_res.get("pwsh") == 0)],
           f"5.1：{res['powershell'][1]}\n7：{res['pwsh'][1]}")


def run_all() -> None:
    for fn in (b01, b02, b03, b04, b05, b06, b07, b08):
        fn()
