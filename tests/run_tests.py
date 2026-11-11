#!/usr/bin/env python3
"""ringi-kit 自测入口：执行全部用例，写 results.json 并生成 TEST_REPORT.md。

用法：python tests/run_tests.py [--kit .] [--work .work/tests] [--report docs/TEST_REPORT.md]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True  # 不在 Skill 目录内留下 __pycache__
sys.path.insert(0, str(HERE))

import tlib  # noqa: E402
import cases_bound  # noqa: E402
import cases_checklist  # noqa: E402
import cases_neg  # noqa: E402
import cases_pos  # noqa: E402
import cases_regress  # noqa: E402
import cases_tools  # noqa: E402

GROUPS = ["正例", "负例", "边界", "验收清单·结构", "验收清单·行为", "验收清单·内容", "验收清单·语言与合规", "回归", "工具链"]


def _status(r: dict) -> str:
    if r.get("skipped"):
        return f"跳过：{r['skipped']}"
    return "通过" if r["passed"] else "**未通过**"


def env_info() -> list[str]:
    import jinja2
    import yaml
    ps = {}
    for exe in ("powershell", "pwsh"):
        path = tlib.ps_exe(exe)
        if path:
            p = subprocess.run([path, "-NoProfile", "-Command", "$PSVersionTable.PSVersion.ToString()"],
                               capture_output=True, text=True, check=False)
            ps[exe] = p.stdout.strip()
    return [f"- 执行日期：{dt.date.today().isoformat()}",
            f"- 操作系统：{platform.platform()}",
            f"- Python：{platform.python_version()}；Jinja2 {jinja2.__version__}；PyYAML {yaml.__version__}",
            f"- Windows PowerShell：{ps.get('powershell', '未安装')}；PowerShell 7：{ps.get('pwsh', '未安装')}",
            f"- mermaid-cli：{_tool_desc('RINGI_MMDC', 'mmdc')}（B-06 始终用不存在的路径测试降级）",
            f"- Terraform：{_tool_desc('RINGI_TERRAFORM', 'terraform')}"]


def _tool_desc(env_key: str, name: str) -> str:
    import os
    path = os.environ.get(env_key) or shutil.which(name)
    if not path:
        return "未找到（工具链用例跳过）"
    flag = "--version" if name == "mmdc" else "version"
    p = subprocess.run([path, flag], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
    return f"{(p.stdout.strip().splitlines() or ['?'])[0]}（{Path(path).parent.name}）"


def write_report(results: list[dict], path: Path) -> None:
    groups = GROUPS
    lines = ["# ringi-kit 测试报告（TEST_REPORT）", "",
             "> 来源：Claude Code CLI 按规格 `06-验收标准与测试用例.md` 执行 `tests/run_tests.py` 自动生成  ",
             f"> 日期：{dt.date.today().isoformat()}　机器：Desktop　Skill 版本：v0.1.0", "",
             "## 执行环境", "", *env_info(), "",
             "执行命令：`python tests/run_tests.py`（在仓库根目录）。全部输出在 `.work/tests/<用例ID>/`（已加入 .gitignore）。", "",
             "## 汇总", "", "| 分组 | 通过 | 跳过 | 合计 |", "|---|---|---|---|"]
    for g in groups:
        rs = [r for r in results if r["group"] == g]
        lines.append(f"| {g} | {sum(r['passed'] for r in rs)} | {sum(bool(r.get('skipped')) for r in rs)} | {len(rs)} |")
    total_ok = sum(r["passed"] for r in results)
    skipped = [r for r in results if r.get("skipped")]
    lines += [f"| **合计** | **{total_ok}** | **{len(skipped)}** | **{len(results)}** |", ""]
    failed = [r for r in results if not r["passed"] and not r.get("skipped")]
    lines += ["未通过用例：" + ("无" if not failed else "、".join(r["id"] for r in failed)),
              "跳过用例：" + ("无" if not skipped else "、".join(f"{r['id']}（{r['skipped']}）" for r in skipped)), ""]
    for g in groups:
        rs = [r for r in results if r["group"] == g]
        if not rs:
            continue
        lines += [f"## {g}", "", "| 用例 | 内容 | 结果 | 断言 |", "|---|---|---|---|"]
        for r in rs:
            asserts = "<br>".join(("✔ " if c["ok"] else "✘ ") + c["desc"].replace("|", "／") for c in r["checks"])
            lines.append(f"| {r['id']} | {r['title']} | {_status(r)} | {asserts} |")
        lines.append("")
        ev = [r for r in rs if r["evidence"]]
        if ev:
            lines += ["<details><summary>输出摘录</summary>", ""]
            for r in ev:
                lines += [f"**{r['id']}**", "", "```text", r["evidence"], "```", ""]
            lines += ["</details>", ""]
    lines += ["## 说明", "",
              "- 负例断言均同时检查退出码、规则 ID 与对象名（06 第 3 节要求），不只校验退出码。",
              "- N-04、N-11、N-12、N-16、N-17、N-18 通过修改已渲染的交付物构造；N-03、N-24 在 Skill 的临时副本上修改模板或参考文件构造，不改动正式 Skill。",
              "- N-05、N-09 的构造输入同时违反 schema（缺键 / 少于三项），`render.py` 以退出码 2 拒绝渲染，`lint.py` 仍对配置执行规则并报出 L-04 / L-09。",
              "- B-02 只验证规格要求的三点（开关生效、L-10 仍校验、L-17 失效）；长段正文的日文化不在模板内实现，见 IMPLEMENTATION_NOTES 已知限制。",
              "- R3（财年边界）在三份示例中均有提示级输出，属设计内行为，不阻断；对应风险条目由渲染自动派生。",
              "- 工具链 X-03 用测试替身模块代替 ActiveDirectory / ConfigurationManager / ADSync，验证的是脚本逻辑、判定与 CSV 列名，"
              "不等于在真实客户环境实测。",
              "- 示例配置中的锚点值为 2026-11-11 在微软官方文档核实的结果，90 天后（2027-02-09 起）L-13 会判为过期，须重新核实。", ""]
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kit", default=str(HERE.parent))
    ap.add_argument("--work", default=str(HERE.parent / ".work" / "tests"))
    ap.add_argument("--report", default=str(HERE.parent / "docs" / "TEST_REPORT.md"))
    args = ap.parse_args()
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    tlib.C.kit = Path(args.kit).resolve()
    tlib.C.work = Path(args.work).resolve()
    if tlib.C.work.exists():
        shutil.rmtree(tlib.C.work)
    tlib.C.work.mkdir(parents=True)
    cases_pos.run_all()
    cases_neg.run_all()
    cases_bound.run_all()
    cases_checklist.run_all()
    cases_regress.run_all()
    cases_tools.run_all()
    (tlib.C.work / "results.json").write_text(json.dumps(tlib.RESULTS, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(tlib.RESULTS, Path(args.report))
    failed = [r["id"] for r in tlib.RESULTS if not r["passed"] and not r.get("skipped")]
    skipped = [r["id"] for r in tlib.RESULTS if r.get("skipped")]
    passed = len(tlib.RESULTS) - len(failed) - len(skipped)
    print(f"\n合计 {passed}/{len(tlib.RESULTS)} 通过；未通过：{failed or '无'}；跳过：{skipped or '无'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
