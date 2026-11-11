"""正例 C-01..C-07。"""
from __future__ import annotations

import re

from tlib import C, DELIVERABLES, EXAMPLES, cjk, dump, has, lint_only, load, pipeline, record, section


def _base_checks(build, r, lint, cal) -> list:
    return [
        ("render.py 退出码 0", r[0] == 0),
        ("8 个交付物齐全", all((build / f).is_file() for f in DELIVERABLES)),
        ("figures/ 目录存在且含 .mmd", (build / "figures").is_dir() and any((build / "figures").glob("*.mmd"))),
        ("evidence/ 目录存在", (build / "evidence").is_dir()),
        ("lint.py 退出码 0", lint[0] == 0),
        ("calendar_check.py 退出码 0", cal[0] == 0),
        ("LINT_STATUS.txt 首行为 PASS", (build / "LINT_STATUS.txt").read_text(encoding="utf-8").startswith("PASS")),
    ]


def c01() -> None:
    cfg = C.kit / "examples" / EXAMPLES["a-sccm"] / "project.yaml"
    build, r, lint, cal = pipeline(cfg, "C-01")
    record("C-01", "正例", "项目 A 完整渲染", _base_checks(build, r, lint, cal), lint[1] + "\n" + cal[1])


def c02() -> None:
    cfg = C.kit / "examples" / EXAMPLES["b-admerge"] / "project.yaml"
    build, r, lint, cal = pipeline(cfg, "C-02")
    text = (build / "01_提案書.md").read_text(encoding="utf-8") if (build / "01_提案書.md").is_file() else ""
    decl = section(text, "1.2 云侧身份状态声明")
    ch4 = section(text, "4 方式比较与选型")
    ch9 = section(text, "9 回退计划")
    checks = _base_checks(build, r, lint, cal) + [
        (f"第 1 章含「云侧身份状态声明」且 ≥200 字（实测 {cjk(decl)}）", bool(decl) and cjk(decl) >= 200),
        ("第 4 章含三方式对比表", ch4.count("| 同林内重组 |") + ch4.count("| 跨林迁移（含历史 SID 迁移） |") + ch4.count("| 资源林 + 林间信任 |") >= 3),
        ("第 4 章含两段否决理由", len(re.findall(r"^- 不采用「", ch4, re.M)) == 2),
        ("第 9 章含「T+○○分钟」回退判据", bool(re.search(r"T\+\d+分钟", ch9))),
    ]
    record("C-02", "正例", "项目 B 完整渲染", checks, f"云侧身份状态声明字数={cjk(decl)}")


def c03() -> None:
    cfg = C.kit / "examples" / EXAMPLES["c-entraconnect"] / "project.yaml"
    build, r, lint, cal = pipeline(cfg, "C-03")
    text = (build / "01_提案書.md").read_text(encoding="utf-8") if (build / "01_提案書.md").is_file() else ""
    ch1 = section(text, "1 前提与制约")
    ch4 = section(text, "4 方式比较与选型")
    checks = _base_checks(build, r, lint, cal) + [
        ("第 1 章含出站端点清单表（域名/用途/是否经代理）", "| 域名 | 用途 | 是否经代理 |" in ch1),
        ("第 4 章含身份同步方式论证", "身份同步方式" in ch4 and "密码哈希同步" in ch4 and "直通认证" in ch4 and "联合认证" in ch4),
        ("第 4 章明文「暂存模式不是备份」", "暂存模式不是备份" in ch4),
    ]
    record("C-03", "正例", "项目 C 完整渲染", checks)


def c04() -> None:
    cfg = load(EXAMPLES["a-sccm"])
    del cfg["project"]["industry"]
    del cfg["project"]["employee_range"]
    del cfg["jp"]["budget_period"]
    del cfg["jp"]["decision_path"]
    path = dump(cfg, "C-04")
    build, r, lint, cal = pipeline(path, "C-04", render_args=["--assume"])
    text = (build / "01_提案書.md").read_text(encoding="utf-8") if (build / "01_提案書.md").is_file() else ""
    sec = section(text, "前提假设清单")
    items = re.findall(r"^- \[假设\] ", sec, re.M)
    no_assume = __import__("tlib").run("render.py", "--config", path, "--out", C.work / "C-04" / "noassume")
    # 删除假设清单章节后 L-14 应阻断
    stripped = re.sub(r"## 前提假设清单.*?(?=\n## )", "", text, flags=re.S)
    (build / "01_提案書.md").write_text(stripped, encoding="utf-8")
    l14 = lint_only(path, build, None, "--assume")
    checks = [
        ("未授权假设时 render 退出码 2（S0 停止）", no_assume[0] == 2),
        ("--assume 渲染成功", r[0] == 0),
        ("方案书含「前提假设清单」章节", bool(sec)),
        (f"缺失的 4 项（共 6 个键）均以 [假设] 列出（实测 {len(items)} 条）", len(items) >= 6),
        ("lint 校验该章节存在：章节完整时无 L-14", "L-14" not in lint[1]),
        ("删除该章节后 lint 报 L-14", l14[0] == 1 and "L-14" in l14[1]),
    ]
    record("C-04", "正例", "假设模式", checks, "\n".join(items[:3]) + "\n" + l14[1][:300])


def c05() -> None:
    build = C.work / "C-01" / "build"
    text = (build / "02_稟議用サマリ.md").read_text(encoding="utf-8")
    body = re.sub(r"<!--.*?-->", "", text)
    body = re.sub(r"信息核实时点：\S+", "", body)
    n = len(re.sub(r"[\s|#*>\-]", "", body))
    checks = [(f"正文字数 ≤1200（实测 {n}）", n <= 1200), ("不含代码块", "```" not in text),
              ("不含命令行", not re.search(r"\b(Get|Set|New|Invoke)-[A-Z]|python3? \S+\.py|^\s*\$ ", text, re.M))]
    record("C-05", "正例", "裁决摘要篇幅", checks, f"字数={n}")


def c06() -> None:
    build = C.work / "C-01" / "build"
    text = (build / "01_提案書.md").read_text(encoding="utf-8")
    lint = lint_only(C.kit / "examples" / EXAMPLES["a-sccm"] / "project.yaml", build)
    m = re.search(r"信息核实时点：(\d{4}-\d{2}-\d{2})", text)
    checks = [("L-13 通过（无 L-13 报告）", "L-13" not in lint[1]),
              ("页脚出现「信息核实时点：YYYY-MM-DD」", bool(m))]
    record("C-06", "正例", "锚点填写完整", checks, m.group(0) if m else "")


def c07() -> None:
    cfg = load(EXAMPLES["a-sccm"])
    cfg["rollout"][0]["start"] = "2028-08-14"
    cfg["schedule"]["override_freeze"] = {"task_id": "W-01", "reason": "试点拠点仅お盆期间停产可接受变更",
                                          "approved_by": "客户信息系统部 部长"}
    path = dump(cfg, "C-07")
    build, r, lint, cal = pipeline(path, "C-07")
    risk = (build / "05_リスク台帳.csv").read_text(encoding="utf-8") if r[0] == 0 else ""
    text = (build / "01_提案書.md").read_text(encoding="utf-8") if r[0] == 0 else ""
    checks = [
        ("render 退出码 0", r[0] == 0),
        ("calendar_check 退出码 0（R1 降级为提示）", cal[0] == 0),
        ("calendar_check 输出 R1 [提示]", has(cal[1], "R1 [提示]", "W-01", "お盆")),
        ("风险台账含「已获批准覆盖」条目", "已获批准覆盖" in risk),
        ("方案书风险章节标注「已获批准覆盖」", "已获批准覆盖" in section(text, "8 风险与对策")),
        ("lint 退出码 0", lint[0] == 0),
    ]
    record("C-07", "正例", "冻结窗口覆盖", checks, cal[1])


def run_all() -> None:
    for fn in (c01, c02, c03, c04, c05, c06, c07):
        fn()
