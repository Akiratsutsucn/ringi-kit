#!/usr/bin/env python3
"""diagram.py：mermaid 源码 → svg/png。

优先调用本机 mermaid-cli（mmdc）；不可用时降级为输出 .mmd 源码，并在报告中明确提示「需手工渲染」（WARN），
不静默失败。--src 为含 .mmd 的目录（通常是 render.py 输出的 figures/）；
若 --src 为 assets/（.mmd.j2 模板），须同时给出 --config，由 fact model 先渲染出 .mmd。
退出码：0 成功（含降级）；1 mermaid-cli 存在但转换失败；2 参数或文件错误。
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render as R  # noqa: E402


def render_sources(src: Path, out: Path, config: str | None) -> list[Path]:
    """收集 .mmd；若只有 .mmd.j2 模板，则经 fact model 渲染到 out。"""
    mmds = sorted(src.glob("*.mmd"))
    if mmds:
        return mmds
    if not sorted(src.glob("*.mmd.j2")):
        raise R.ConfigError(f"源目录中没有 .mmd 或 .mmd.j2：{src}")
    if not config:
        raise R.ConfigError("源目录为图表模板（.mmd.j2），请同时给出 --config，或改用 render.py 输出的 figures/")
    import jinja2
    raw = R.load_yaml(Path(config).resolve())
    cfg, assumed, notes = R.check_config(raw, assume=bool(raw.get("assumptions_mode")))
    fm = R.build_fact_model(cfg, R.parse_as_of(None), assumed, notes, assume_mode=bool(raw.get("assumptions_mode")))
    if not fm["doc"]["figures"]:
        raise R.ConfigError("deliverables.items 不含 diagrams，没有可生成的图表")
    env = R.make_env()
    try:  # 先全部渲染到内存，成功后再写盘，不留半成品
        texts = {f"{f['asset']}.mmd": env.get_template(f"{f['asset']}.mmd.j2").render(**fm, fm=fm)
                 for f in fm["doc"]["figures"]}
    except jinja2.TemplateError as exc:
        raise R.ConfigError(f"图表模板渲染失败：{exc}") from exc
    out.mkdir(parents=True, exist_ok=True)
    result = []
    for name, text in texts.items():
        (out / name).write_text(text, encoding="utf-8")
        result.append(out / name)
    return result


def convert(mmdc: str, mmd: Path, out: Path, fmt: str, puppeteer: str | None = None) -> tuple[bool, str]:
    target = out / f"{mmd.stem}.{fmt}"
    cmd = [mmdc, "-i", str(mmd), "-o", str(target), "-b", "white"]
    if puppeteer:
        cmd += ["-p", puppeteer]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                              timeout=180, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"{mmd.name}：调用 mermaid-cli 失败：{exc}"
    if proc.returncode != 0 or not target.is_file():
        return False, f"{mmd.name}：转换失败：{(proc.stderr or proc.stdout).strip()[:300]}"
    return True, f"{mmd.name} → {target.name}"


def main(argv=None) -> int:
    R.utf8_stdout()
    ap = argparse.ArgumentParser(description="mermaid → svg/png（mermaid-cli 缺失时降级输出 .mmd 并 WARN）")
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--format", choices=["svg", "png"], default="svg")
    ap.add_argument("--config", default=None, help="--src 为 assets/ 模板目录时必填")
    ap.add_argument("--mmdc", default=os.environ.get("RINGI_MMDC"),
                    help="mermaid-cli 可执行文件路径（默认取环境变量 RINGI_MMDC，否则在 PATH 中查找 mmdc）")
    ap.add_argument("--puppeteer-config", default=os.environ.get("RINGI_PUPPETEER_CONFIG"),
                    help="puppeteer 配置文件（用本机 Edge/Chrome 渲染时指定；默认取环境变量 RINGI_PUPPETEER_CONFIG）")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    src, out = Path(args.src), Path(args.out)
    report = {"status": "ok", "exit_code": 0, "converted": [], "warnings": [], "errors": []}
    try:
        if not src.is_dir():
            raise R.ConfigError(f"源目录不存在：{src}")
        mmds = render_sources(src, out, args.config)
        if not mmds:
            raise R.ConfigError(f"没有找到任何图表源码：{src}")
    except (R.ConfigError, OSError) as exc:
        report.update(status="error", exit_code=R.EXIT_ARG, errors=[str(exc)])
        return finish(report, args.json)
    out.mkdir(parents=True, exist_ok=True)
    mmdc = args.mmdc or shutil.which("mmdc")
    if mmdc and not (Path(mmdc).is_file() or shutil.which(mmdc)):
        mmdc = None
    if not mmdc:
        for m in mmds:
            if m.resolve().parent != out.resolve():
                shutil.copyfile(m, out / m.name)
        report["status"] = "warn"
        report["warnings"].append(
            f"WARN：未找到 mermaid-cli（mmdc），已输出 {len(mmds)} 个 .mmd 源码到 {out}，需手工渲染为 {args.format} "
            "后放回同一目录（文件名不变，仅扩展名改为 ." + args.format + "）。")
        return finish(report, args.json)
    for m in mmds:
        ok, msg = convert(mmdc, m, out, args.format, args.puppeteer_config)
        (report["converted"] if ok else report["errors"]).append(msg)
    if report["errors"]:
        report.update(status="error", exit_code=R.EXIT_BLOCK)
    return finish(report, args.json)


def finish(report: dict, as_json: bool) -> int:
    if as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"[diagram] {report['status']}")
        for key in ("converted", "warnings", "errors"):
            for line in report[key]:
                print(f"  {line}")
    return report["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
