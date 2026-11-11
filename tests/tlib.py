"""ringi-kit 自测公共工具：子进程调用、配置复制、结果记录。"""
from __future__ import annotations

import argparse
import copy
import csv
import datetime as dt
import io
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
RESULTS: list[dict] = []
ENV = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8"}
TODAY = dt.date.today()


class Ctx:
    kit: Path
    work: Path


C = Ctx()


# ---------------------------------------------------------------- 工具

def run(script: str, *args, kit: Path | None = None, env=None) -> tuple[int, str]:
    kit = kit or C.kit
    proc = subprocess.run([sys.executable, str(kit / "scripts" / script), *map(str, args)], capture_output=True,
                          text=True, encoding="utf-8", env=env or ENV, check=False)
    return proc.returncode, proc.stdout + proc.stderr


def load(example: str) -> dict:
    return yaml.safe_load((C.kit / "examples" / example / "project.yaml").read_text(encoding="utf-8"))


def dump(cfg: dict, case: str) -> Path:
    d = C.work / case
    d.mkdir(parents=True, exist_ok=True)
    p = d / "project.yaml"
    p.write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return p


def pipeline(cfg_path: Path, case: str, kit: Path | None = None, render_args=(), env=None):
    build = C.work / case / "build"
    if build.exists():
        shutil.rmtree(build)
    r = run("render.py", "--config", cfg_path, "--out", build, *render_args, kit=kit, env=env)
    lint = run("lint.py", "--build", build, "--config", cfg_path, kit=kit, env=env)
    cal = run("calendar_check.py", "--config", cfg_path, "--build", build, kit=kit, env=env)
    return build, r, lint, cal


def lint_only(cfg_path: Path, build: Path, kit: Path | None = None, *extra) -> tuple[int, str]:
    return run("lint.py", "--build", build, "--config", cfg_path, *extra, kit=kit)


def record(cid: str, group: str, title: str, checks: list[tuple[str, bool]], evidence: str = "",
           skipped: str | None = None) -> None:
    """skipped 为跳过原因（外部工具不存在时）；跳过不计为通过。"""
    ok = (not skipped) and all(c[1] for c in checks)
    RESULTS.append({"id": cid, "group": group, "title": title, "passed": ok, "skipped": skipped,
                    "checks": [{"desc": d, "ok": bool(v)} for d, v in checks], "evidence": evidence.strip()[:900]})
    print(f"{'SKIP' if skipped else ('PASS' if ok else 'FAIL')} {cid} {title}" + (f"（{skipped}）" if skipped else ""))
    for d, v in checks:
        if not v:
            print(f"     ✗ {d}")


def section(text: str, heading_prefix: str) -> str:
    """取以 heading_prefix 开头的标题到下一个同级或更高级标题之间的内容。"""
    lines = text.splitlines()
    level = None
    out = []
    for ln in lines:
        m = re.match(r"^(#+)\s+(.*)$", ln)
        if level is None:
            if m and m.group(2).startswith(heading_prefix):
                level = len(m.group(1))
            continue
        if m and len(m.group(1)) <= level:
            break
        out.append(ln)
    return "\n".join(out)


def cjk(text: str) -> int:
    sys.path.insert(0, str(C.kit / "scripts"))
    import render  # noqa: WPS433
    return render.count_chars(text)


def copy_kit(case: str) -> Path:
    dst = C.work / case / "kit"
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(C.kit, dst, ignore=shutil.ignore_patterns("__pycache__", ".work", ".git", "tests", "docs"))
    return dst


def has(out: str, *needles: str) -> bool:
    return all(n in out for n in needles)


EXAMPLES = {"a-sccm": "project-a-sccm", "b-admerge": "project-b-admerge", "c-entraconnect": "project-c-entraconnect"}
DELIVERABLES = ["01_提案書.md", "02_稟議用サマリ.md", "03_実施手順書.md", "04_WBS.csv", "05_リスク台帳.csv",
                "06_受入試験項目表.csv", "07_想定質問集.md", "08_週次議事録雛形.md"]


def ps_exe(name: str) -> str | None:
    """powershell → 系统自带 Windows PowerShell 5.1（不用 PATH，PATH 里可能有转发到 7 的同名 .BAT）；pwsh → PowerShell 7。"""
    import shutil
    if name == "powershell":
        exe = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
        return str(exe) if exe.is_file() else None
    return shutil.which(name)
