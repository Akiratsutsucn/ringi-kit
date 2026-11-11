#!/usr/bin/env python3
"""calendar_check.py：财年 / 期末 / 冻结窗口校验（02 第 7 节三条规则）。

R1 冻结窗口冲突（阻断；显式覆盖时降级为提示）
R2 审批缓冲不足（阻断）
R3 财年边界风险（提示，不阻断；但风险台账必须出现对应条目，缺失则阻断）
工作日 = 排除周末与 jp.freeze_windows 的日期。地方假日一律追加到 freeze_windows，不写死在代码里。
退出码：0 通过；1 存在阻断项；2 参数、文件或 schema 错误。
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render as R  # noqa: E402
from lint import load_fact_model, stale_build, update_status  # noqa: E402

RISK_FILE = "05_リスク台帳.csv"


def check_r1(sched: dict) -> list[dict]:
    out = []
    for fc in sched["freeze_conflicts"]:
        target = f"{fc['task_id']}「{fc['task_name']}」（{fc['task_start']}～{fc['task_end']}）× {fc['window']}（{fc['window_start']}～{fc['window_end']}）"
        if fc["overridden"]:
            ov = fc["override"]
            out.append({"rule": "R1", "severity": "info", "target": target,
                        "message": f"冻结窗口冲突已获批准覆盖（批准人：{ov['approved_by']}；理由：{ov['reason']}），降级为提示",
                        "fix": "方案书第 6 章与风险台账已标注「已获批准覆盖」，确认冻结期值班与升级联系人"})
        else:
            out.append({"rule": "R1", "severity": "error", "target": target, "message": "上线/切换/大范围变更类任务与冻结窗口重叠",
                        "fix": "改期；或在 schedule.override_freeze 中填写 {task_id, reason, approved_by} 显式覆盖"})
    return out


def check_r2(sched: dict) -> list[dict]:
    return [{"rule": "R2", "severity": "error",
             "target": f"{g['from_id']}「{g['from']}」→ {g['to_id']}「{g['to']}」",
             "message": f"相邻承认节点间隔 {g['workdays']} 个工作日，要求 {g['required']} 个，缺 {g['shortfall']} 天",
             "fix": "后移后一个承认节点，或合并承认节点；不得降低 approval_buffer_days"}
            for g in sched["approval_gaps"] if not g["ok"]]


def check_r3(sched: dict, build: Path | None) -> list[dict]:
    risk_tasks = None
    if build and (build / RISK_FILE).is_file():
        rows = csv.DictReader(io.StringIO((build / RISK_FILE).read_text(encoding="utf-8")))
        risk_tasks = {(r.get("关联任务"), r.get("风险ID", "")[:4]) for r in rows}
    out = []
    for fb in sched["fiscal_boundary_risks"]:
        target = f"{fb['task_id']}「{fb['task_name']}」× {fb['boundary']}（{fb['window']}）"
        out.append({"rule": "R3", "severity": "info", "target": target,
                    "message": "上线/切换落在期末前后 10 个工作日内（提示，不阻断）",
                    "fix": "确认无法改期；风险台账已派生 R-FB 条目"})
        if risk_tasks is not None and (fb["task_id"], "R-FB") not in risk_tasks:
            out.append({"rule": "R3", "severity": "error", "target": target,
                        "message": "风险台账中没有对应的期末风险条目", "fix": "重新执行 render.py，不得手工删除派生风险"})
    return out


def report(findings: list[dict]) -> str:
    label = {"error": "阻断", "warning": "警告", "info": "提示"}
    errors = sum(f["severity"] == "error" for f in findings)
    lines = [f"[calendar_check] 阻断 {errors} / 提示 {sum(f['severity'] == 'info' for f in findings)}"]
    for f in findings:
        lines += [f"{f['rule']} [{label[f['severity']]}]", f"  违规对象：{f['target']}", f"  问题：{f['message']}",
                  f"  修复建议：{f['fix']}"]
    if not findings:
        lines.append("未发现日程冲突。")
    return "\n".join(lines)


def main(argv=None) -> int:
    R.utf8_stdout()
    ap = argparse.ArgumentParser(description="ringi-kit 日程校验（冻结窗口 / 审批缓冲 / 财年边界）")
    ap.add_argument("--config", required=True)
    ap.add_argument("--build", default=None)
    ap.add_argument("--assume", action="store_true")
    ap.add_argument("--as-of", default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    build = Path(args.build) if args.build else None
    try:
        config_path = Path(args.config).resolve()
        as_of = R.parse_as_of(args.as_of)
        raw = R.load_yaml(config_path)
        cfg, _assumed, _notes = R.check_config(raw, assume=args.assume or bool(raw.get("assumptions_mode")))
        sched = R.build_schedule(cfg)
        stale = None
        if build and build.is_dir():
            fm = load_fact_model(build)
            stale = stale_build(config_path, fm.get("doc", {}).get("config_sha256") if fm else None)
    except R.ConfigError as exc:
        msg = {"status": "error", "exit_code": R.EXIT_ARG, "message": str(exc), "details": exc.details}
        print(json.dumps(msg, ensure_ascii=False, indent=2) if args.json else
              "\n".join([f"[calendar_check] error：{exc}"] + [f"  - {d}" for d in exc.details]))
        return R.EXIT_ARG
    findings = check_r1(sched) + check_r2(sched) + check_r3(sched, build)
    if stale:
        findings.append({"rule": "BUILD", "severity": "error", "target": str(build), "message": stale,
                         "fix": "重新执行 render.py 后再校验"})
    blocked = any(f["severity"] == "error" for f in findings)
    code = R.EXIT_BLOCK if blocked else R.EXIT_OK
    if build and build.is_dir():
        update_status(build, "calendar_check.py", not blocked, as_of.isoformat())
    if args.json:
        print(json.dumps({"status": "fail" if blocked else "pass", "exit_code": code, "findings": findings},
                         ensure_ascii=False, indent=2))
    else:
        print(report(findings))
    return code


if __name__ == "__main__":
    sys.exit(main())
