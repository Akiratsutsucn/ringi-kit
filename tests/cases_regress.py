"""回归用例 R-01..R-08：代码审查发现问题的修复验证（06 之外的补充用例）。"""
from __future__ import annotations

import re

from tlib import C, EXAMPLES, dump, load, pipeline, record, run

A = EXAMPLES["a-sccm"]


def r01():
    cfg = load(A)
    cfg["jp"]["freeze_windows"][0]["start"] = "2028-02-30"
    rc, out = run("render.py", "--config", dump(cfg, "R-01"), "--out", C.work / "R-01" / "build")
    cfg2 = load(A)
    cfg2["jp"]["freeze_windows"][0].update(start="2028-01-05", end="2027-12-29")
    rc2, out2 = run("calendar_check.py", "--config", dump(cfg2, "R-01b"))
    record("R-01", "回归", "非法或倒置的日期不被静默丢弃",
           [("不存在的日期：render 退出码 2 并指出字段", rc == 2 and "jp.freeze_windows[0].start" in out),
            ("start 晚于 end：calendar_check 退出码 2", rc2 == 2 and "晚于" in out2)], out + out2)


def r02():
    cfg = load(A)
    cfg["schedule"]["go_live"] = "<待填写>"
    rc, out = run("render.py", "--config", dump(cfg, "R-02"), "--out", C.work / "R-02" / "build")
    cfg2 = load(A)
    cfg2["comparison"]["options"][0]["scores"]["cost"] = "<待填写>"
    rc2, out2 = run("calendar_check.py", "--config", dump(cfg2, "R-02b"))
    record("R-02", "回归", "日程与评分字段为占位符时给出明确错误而不崩溃",
           [("go_live 占位符：退出码 2，无 Traceback", rc == 2 and "schedule.go_live" in out and "Traceback" not in out),
            ("评分占位符：退出码 2，无 Traceback", rc2 == 2 and "scores" in out2 and "Traceback" not in out2)], out + out2)


def r03():
    cfg = load(A)
    path = dump(cfg, "R-03")
    build, r, lint, cal = pipeline(path, "R-03")
    cfg["schedule"]["go_live"] = "2028-10-20"
    path.write_text(path.read_text(encoding="utf-8").replace("2028-10-15", "2028-10-20"), encoding="utf-8")
    lint2 = run("lint.py", "--build", build, "--config", path)
    cal2 = run("calendar_check.py", "--config", path, "--build", build)
    status = (build / "LINT_STATUS.txt").read_text(encoding="utf-8")
    record("R-03", "回归", "配置在渲染后被修改时拒绝陈旧产物",
           [("基线全绿", r[0] == 0 and lint[0] == 0 and cal[0] == 0),
            ("lint 报 BUILD 阻断", lint2[0] == 1 and "BUILD" in lint2[1] and "陈旧" in lint2[1]),
            ("calendar_check 报 BUILD 阻断", cal2[0] == 1 and "BUILD" in cal2[1]),
            ("LINT_STATUS.txt 回到 FAIL", status.startswith("FAIL"))], lint2[1][:300])


def r04():
    from tlib import copy_kit
    kit = copy_kit("R-04")
    ref = kit / "references" / "sccm-deployment.md"
    ref.write_text(ref.read_text(encoding="utf-8") +
                   '\n<!-- ANCHOR:AN-01 topic="x" source="learn.microsoft.com" --> 当前版本 10.0.1\n', encoding="utf-8")
    build, _r, lint, _c = pipeline(kit / "examples" / A / "project.yaml", "R-04", kit=kit)
    record("R-04", "回归", "锚点注释同一行的硬编码版本仍被扫描", [("S-01 命中 10.0.1", "S-01" in lint[1] and "10.0.1" in lint[1])],
           lint[1][-300:])


def r05():
    rc, out = run("render.py", "--config", C.kit / "examples" / A / "project.yaml", "--out", C.work / "R-05" / "build",
                  "--only", "meeting_minutes")
    cfg = load(A)
    cfg["deliverables"]["items"] = ["proposal"]
    rc2, out2 = run("render.py", "--config", dump(cfg, "R-05b"), "--out", C.work / "R-05b" / "build", "--only", "wbs")
    record("R-05", "回归", "--only 与 deliverables 没有交集时报错",
           [("单项 --only 正常", rc == 0), ("无交集：退出码 2", rc2 == 2 and "没有交集" in out2)], out2)


def r06():
    cfg = load(A)
    cfg["current_state"]["domains"].append({"name": "<待填写>", "forest": "x", "dc_count": 1, "functional_level": "y"})
    rc, out = run("render.py", "--config", dump(cfg, "R-06"), "--out", C.work / "R-06" / "build", "--assume")
    record("R-06", "回归", "假设模式不整体覆盖已部分填写的列表",
           [("退出码 2，要求逐条补全", rc == 2 and "current_state.domains" in out and "逐条补全" in out)], out)


def r07():
    cfg = load(A)
    cfg["rollout"][0].update(start="2028-08-14", end="2028-08-15")
    cfg["schedule"]["go_live"] = "2028-08-15"
    cfg["schedule"]["milestones"].append({"name": "盆期上线", "date": "2028-08-15", "approval": False, "kind": "go_live"})
    cfg["schedule"]["override_freeze"] = [
        {"task_id": "W-01", "reason": "停产期作业", "approved_by": "客户部长"},  # 里程碑按日期排序编号，8-15 的里程碑为 M-03
        {"task_id": "M-03", "reason": "停产期上线", "approved_by": "客户部长"}]
    path = dump(cfg, "R-07")
    rc, out = run("calendar_check.py", "--config", path)
    record("R-07", "回归", "同日上线去重，override_freeze 支持多个任务",
           [("calendar_check 退出码 0", rc == 0), ("无 M-GL 重复冲突", "M-GL" not in out),
            ("两项均为 R1 提示", len(re.findall(r"R1 \[提示\]", out)) == 2)], out)


def r08():
    lab = C.work / "R-08" / "lab"
    run("labgen.py", "--type", "sccm", "--out", lab, "--mgmt-cidr", "192.0.2.0/24")
    tf = (lab / "terraform" / "variables.tf").read_text(encoding="utf-8")
    record("R-08", "回归", "Terraform 变量校验拒绝非 CIDR 与 /0",
           [("使用 cidrhost 校验合法 CIDR", "can(cidrhost(var.mgmt_cidr, 0))" in tf),
            ("前缀长度须大于 0", "> 0" in tf)])


def run_all() -> None:
    for fn in (r01, r02, r03, r04, r05, r06, r07, r08):
        fn()
