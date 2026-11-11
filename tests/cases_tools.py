"""工具链用例 X-01..X-03：真实 mermaid-cli 渲染、terraform validate、PowerShell 替身模块测试。

外部工具通过环境变量定位：RINGI_MMDC / RINGI_PUPPETEER_CONFIG（mermaid-cli 与本机浏览器配置）、
RINGI_TERRAFORM（terraform 可执行文件）；未设置时在 PATH 中查找，找不到则记为「跳过」，不计为通过。
"""
from __future__ import annotations

import os
import shutil
import subprocess

from tlib import C, ENV, EXAMPLES, ROOT, ps_exe, record, run


def _tool(env_key: str, name: str) -> str | None:
    path = os.environ.get(env_key) or shutil.which(name)
    return path if path and (os.path.isfile(path) or shutil.which(path)) else None


def x01() -> None:
    mmdc = _tool("RINGI_MMDC", "mmdc")
    if not mmdc:
        record("X-01", "工具链", "mermaid-cli 实际渲染全部图表", [], skipped="未找到 mermaid-cli")
        return
    checks, evid = [], []
    for case in ("C-01", "C-02", "C-03"):
        figs = C.work / case / "build" / "figures"
        args = ["--src", figs, "--out", figs, "--mmdc", mmdc]
        if os.environ.get("RINGI_PUPPETEER_CONFIG"):
            args += ["--puppeteer-config", os.environ["RINGI_PUPPETEER_CONFIG"]]
        rc, out = run("diagram.py", *args)
        mmds = sorted(figs.glob("*.mmd"))
        svgs = [figs / f"{m.stem}.svg" for m in mmds]
        bad = [s.name for s in svgs if not s.is_file() or b"Syntax error" in s.read_bytes()]
        checks.append((f"{case}：{len(mmds)} 张图全部生成 svg 且无语法错误（失败：{bad or '无'}）", rc == 0 and not bad))
        evid.append(out.strip())
    record("X-01", "工具链", "mermaid-cli 实际渲染全部图表", checks, "\n".join(evid))


def x02() -> None:
    tf = _tool("RINGI_TERRAFORM", "terraform")
    if not tf:
        record("X-02", "工具链", "labgen 产物通过 terraform validate", [], skipped="未找到 terraform")
        return
    env = {**ENV}
    cache = os.environ.get("TF_PLUGIN_CACHE_DIR")
    if cache:
        env["TF_PLUGIN_CACHE_DIR"] = cache
    checks, evid = [], []
    for ptype in ("sccm", "admerge", "entraconnect"):
        lab = C.work / "X-02" / ptype
        rc, _o = run("labgen.py", "--type", ptype, "--out", lab, "--mgmt-cidr", "192.0.2.0/24")
        tdir = lab / "terraform"
        init = subprocess.run([tf, "init", "-backend=false", "-input=false", "-no-color"], cwd=tdir, env=env,
                              capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
        val = subprocess.run([tf, "validate", "-no-color"], cwd=tdir, env=env, capture_output=True, text=True,
                             encoding="utf-8", errors="replace", check=False)
        fmt = subprocess.run([tf, "fmt", "-check", "-no-color"], cwd=tdir, env=env, capture_output=True, text=True,
                             encoding="utf-8", errors="replace", check=False)
        checks.append((f"{ptype}：init/validate/fmt 均成功", rc == 0 and init.returncode == 0 and val.returncode == 0
                       and fmt.returncode == 0))
        evid.append(f"{ptype}: {val.stdout.strip() or val.stderr.strip()[:200]}")
    tdir = C.work / "X-02" / "sccm" / "terraform"
    base = ["-var", "location=x", "-var", "prefix=x", "-var", "vnet_cidr=10.0.0.0/16", "-var", "vm_size=x",
            "-var", "admin_username=x", "-var", 'windows_image={publisher="a",offer="b",sku="c",version="d"}']
    for cidr, expect_ok in (("192.0.2.0/24", True), ("0.0.0.0/0", False), ("*", False), ("Internet", False)):
        p = subprocess.run([tf, "console", "-no-color", "-var", f"mgmt_cidr={cidr}", *base], cwd=tdir, env=env,
                           input="var.mgmt_cidr\n", capture_output=True, text=True, encoding="utf-8", errors="replace",
                           check=False)
        rejected = "Invalid value for variable" in (p.stdout + p.stderr)
        checks.append((f"mgmt_cidr={cidr} {'被接受' if expect_ok else '被拒绝'}", rejected != expect_ok))
    record("X-02", "工具链", "labgen 产物通过 terraform validate，变量校验拒绝全网来源", checks, "\n".join(evid))


def _ps_mock(exe: str) -> tuple[int | None, str]:
    path = ps_exe(exe)
    if not path:
        return None, "未安装"
    p = subprocess.run([path, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ROOT / "tests" / "ps_mock_run.ps1"),
                        "-Kit", str(C.kit / "powershell"), "-Out", str(C.work / "X-03" / exe)],
                       capture_output=True, check=False)
    raw = p.stdout + p.stderr
    for enc in ("utf-8", "gbk"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    lines = [ln for ln in text.splitlines() if ln.startswith(("OK", "FAIL", "MOCK"))]
    return p.returncode, "\n".join(lines)


def x03() -> None:
    res = {exe: _ps_mock(exe) for exe in ("powershell", "pwsh")}
    if all(rc is None for rc, _ in res.values()):
        record("X-03", "工具链", "PowerShell 依赖模块脚本（替身模块）", [], skipped="未安装 PowerShell")
        return
    checks = [(f"{exe}：7 个脚本在替身模块下判定与 CSV 列名正确", rc == 0) for exe, (rc, _o) in res.items() if rc is not None]
    record("X-03", "工具链", "PowerShell 依赖模块脚本（替身模块，非真实环境）", checks,
           "\n".join(f"[{exe}]\n{o}" for exe, (_rc, o) in res.items()))


def run_all() -> None:
    x01()
    x02()
    x03()
