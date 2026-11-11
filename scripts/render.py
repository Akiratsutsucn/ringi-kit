#!/usr/bin/env python3
"""render.py：project.yaml →（schema 校验）→ fact model → Jinja2 渲染 → 交付物。

本文件同时提供 lint.py / calendar_check.py / new_project.py 共用的基础函数
（配置读取、schema 校验、S0 必填检查、工作日计算、正文切分与计数）。
退出码：0 成功；1 渲染失败（模板变量缺失等阻断）；2 参数、文件、schema 或 S0 错误。
"""
from __future__ import annotations

import argparse
import calendar
import copy
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = SKILL_ROOT / "schema" / "project.schema.json"
TEMPLATE_DIR = SKILL_ROOT / "templates"
ASSET_DIR = SKILL_ROOT / "assets"
REFERENCE_DIR = SKILL_ROOT / "references"

PLACEHOLDER = "<待填写>"
EXIT_OK, EXIT_BLOCK, EXIT_ARG = 0, 1, 2
FIXED_MARK = "<!-- 固定版式字段：请勿改写 -->"
LINT_MARK = "<!-- LINT_STATUS -->"
LINT_PENDING = "未通过完备性校验（渲染后尚未执行 lint.py）"


class ConfigError(Exception):
    """参数、文件、schema 或 S0 错误（退出码 2）。"""

    def __init__(self, message: str, details: list[str] | None = None):
        super().__init__(message)
        self.details = details or []


# ---------------------------------------------------------------- 配置读取

def _stringify_dates(node):
    if isinstance(node, dict):
        return {k: _stringify_dates(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_stringify_dates(v) for v in node]
    if isinstance(node, (dt.date, dt.datetime)):
        return node.strftime("%Y-%m-%d")
    return node


def load_yaml(path: Path):
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - 环境问题
        raise ConfigError("缺少依赖 PyYAML，请先安装（仅允许 Jinja2 与 PyYAML 两个第三方库）") from exc
    if not path.is_file():
        raise ConfigError(f"配置文件不存在：{path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"YAML 解析失败：{path}：{exc}") from exc
    except UnicodeDecodeError as exc:
        raise ConfigError(f"配置文件不是 UTF-8 编码：{path}") from exc
    except OSError as exc:
        raise ConfigError(f"配置文件无法读取：{path}：{exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"配置文件顶层必须是映射：{path}")
    return _stringify_dates(data)


def load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- schema 校验（标准库实现）

_TYPES = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
}


def _resolve(root: dict, schema: dict) -> dict:
    while "$ref" in schema:
        node = root
        for part in schema["$ref"].lstrip("#/").split("/"):
            node = node[part]
        schema = node
    return schema


def _join(path: str, key) -> str:
    if isinstance(key, int):
        return f"{path}[{key}]"
    return f"{path}.{key}" if path else str(key)


def validate(inst, schema: dict, root: dict, path: str = "") -> list[str]:
    """返回错误列表；每条形如『路径：原因』。"""
    schema = _resolve(root, schema)
    where = path or "(根)"
    if "anyOf" in schema:
        if all(validate(inst, sub, root, path) for sub in schema["anyOf"]):
            return [f"{where}：值 {inst!r} 不符合允许的类型或取值"]
        return []
    errors: list[str] = []
    if "const" in schema and inst != schema["const"]:
        errors.append(f"{where}：必须为 {schema['const']!r}，实际为 {inst!r}")
    if "enum" in schema and inst not in schema["enum"]:
        hint = schema.get("x-message") or f"允许值：{' / '.join(map(str, schema['enum']))}"
        errors.append(f"{where}：取值 {inst!r} 不允许。{hint}")
    expected = schema.get("type")
    if expected and not _TYPES[expected](inst):
        return errors + [f"{where}：类型应为 {expected}，实际为 {type(inst).__name__}"]
    if isinstance(inst, dict):
        errors += _validate_object(inst, schema, root, path)
    elif isinstance(inst, list):
        if len(inst) < schema.get("minItems", 0):
            errors.append(f"{where}：至少需要 {schema['minItems']} 项，实际 {len(inst)} 项")
        if "items" in schema:
            for i, item in enumerate(inst):
                errors += validate(item, schema["items"], root, _join(path, i))
    elif isinstance(inst, str) and "pattern" in schema:
        if not re.search(schema["pattern"], inst):
            errors.append(f"{where}：格式不符（{schema['pattern']}），实际为 {inst!r}")
    elif _TYPES["number"](inst):
        if "minimum" in schema and inst < schema["minimum"]:
            errors.append(f"{where}：不得小于 {schema['minimum']}")
        if "maximum" in schema and inst > schema["maximum"]:
            errors.append(f"{where}：不得大于 {schema['maximum']}")
    for sub in schema.get("allOf", []):
        if "if" in sub and not validate(inst, sub["if"], root, path):
            errors += validate(inst, sub.get("then", {}), root, path)
    return errors


def _validate_object(inst: dict, schema: dict, root: dict, path: str) -> list[str]:
    errors = []
    props = schema.get("properties", {})
    for key in schema.get("required", []):
        if key not in inst:
            errors.append(f"{_join(path, key)}：缺少必填键")
    for key, value in inst.items():
        if key in props:
            errors += validate(value, props[key], root, _join(path, key))
        elif schema.get("additionalProperties") is False:
            errors.append(f"{_join(path, key)}：未定义的键（键名固定，不得改名或新增）")
        elif isinstance(schema.get("additionalProperties"), dict):
            errors += validate(value, schema["additionalProperties"], root, _join(path, key))
    return errors


# ---------------------------------------------------------------- S0：12 项必填字段

S0_FIELDS = [
    (1, "客户名（可脱敏代号）", ["project.client_name"]),
    (2, "行业", ["project.industry"]),
    (3, "员工规模区间", ["project.employee_range"]),
    (4, "拠点数与地理分布", ["project.sites_count", "project.sites_distribution"]),
    (5, "现有域数量与林结构", ["current_state.domains"]),
    (6, "现有云租户数量", ["current_state.cloud_tenants"]),
    (7, "财年与预算期", ["jp.fiscal_year_start_month", "jp.budget_period"]),
    (8, "决策路径（提案人/审批人/签字人）",
     ["jp.decision_path.proposer", "jp.decision_path.approver", "jp.decision_path.signer"]),
    (9, "既有供应商与作业边界", ["jp.vendors"]),
    (10, "安全审查要求", ["jp.security_review"]),
    (11, "作业冻结窗口", ["jp.freeze_windows"]),
    (12, "交付物语言与格式", ["deliverables.language", "deliverables.format"]),
]
# 不可假设的字段：没有它们无法计算日程或决定输出语言。
NOT_ASSUMABLE = {"jp.fiscal_year_start_month", "jp.freeze_windows", "deliverables.language"}
ASSUMED_TEXT = "[假设] 待客户确认"


def get_path(data, dotted: str, default=None):
    node = data
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return default
        node = node[part]
    return node


def set_path(data: dict, dotted: str, value) -> None:
    parts = dotted.split(".")
    node = data
    for part in parts[:-1]:
        if not isinstance(node.get(part), dict):
            node[part] = {}
        node = node[part]
    node[parts[-1]] = value


_MISSING = object()


def is_blank(value) -> bool:
    if value is _MISSING or value is None:
        return True
    if isinstance(value, str):
        return not value.strip() or PLACEHOLDER in value
    if isinstance(value, (list, dict)):
        return len(value) == 0 or has_placeholder(value)
    return False


def has_placeholder(value) -> bool:
    if isinstance(value, str):
        return PLACEHOLDER in value
    if isinstance(value, dict):
        return any(has_placeholder(v) for v in value.values())
    if isinstance(value, list):
        return any(has_placeholder(v) for v in value)
    return False


def s0_missing(config: dict) -> list[tuple[int, str, str]]:
    """返回 (序号, 字段名, 路径) 列表。cloud_tenants 允许空列表（表示 0 个租户），但键必须存在。"""
    missing = []
    for num, label, paths in S0_FIELDS:
        for p in paths:
            value = get_path(config, p, _MISSING)
            if p == "current_state.cloud_tenants" and value == []:
                continue
            if is_blank(value):
                missing.append((num, label, p))
    return missing


def _assumed_value(path: str):
    if path == "current_state.domains":
        return [{"name": ASSUMED_TEXT, "forest": ASSUMED_TEXT, "dc_count": ASSUMED_TEXT,
                 "functional_level": ASSUMED_TEXT}]
    if path == "current_state.cloud_tenants":
        return [{"name": ASSUMED_TEXT, "user_count": ASSUMED_TEXT, "sync_method": ASSUMED_TEXT}]
    if path == "jp.vendors":
        return [{"tier": 1, "name": ASSUMED_TEXT, "role": ASSUMED_TEXT, "scope": ASSUMED_TEXT,
                 "not_doing": ASSUMED_TEXT, "contact_role": ASSUMED_TEXT}]
    return f"{ASSUMED_TEXT}"


def apply_assumptions(config: dict, missing) -> tuple[dict, list[str], list[str]]:
    """假设模式：为可假设的缺失字段填入带 [假设] 标记的值。返回 (新配置, 已假设路径, 假设条目)。"""
    cfg = copy.deepcopy(config)
    assumed, notes = [], []
    for _num, label, path in missing:
        current = get_path(cfg, path, _MISSING)
        if path in NOT_ASSUMABLE or (isinstance(current, (list, dict)) and current):
            # 已部分填写的列表/对象不整体替换，避免丢失真实数据；由 S0 列出，须逐条填写
            continue
        set_path(cfg, path, _assumed_value(path))
        assumed.append(path)
        notes.append(f"[假设] {label}（{path}）：客户尚未提供，本稿暂按待确认处理，须在客户评审时逐条确认")
    return cfg, assumed, notes


def normalize_assumption(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^【假设】\s*", "[假设] ", text)
    return text if text.startswith("[假设]") else f"[假设] {text}"


def check_config(config: dict, assume: bool = False):
    """S0 门禁 + schema 校验。返回 (配置, 已假设路径, 假设条目)；失败抛 ConfigError。"""
    missing = s0_missing(config)
    assumed, notes = [], []
    if missing and assume:
        config, assumed, notes = apply_assumptions(config, missing)
        missing = [m for m in missing if m[2] not in assumed]
    if missing:
        details = [f"#{n} {label}：{path}" for n, label, path in missing]
        if assume:
            details.append("以上字段不可按假设值生成：日程与输出语言依赖其真实值，或该列表已部分填写，须逐条补全占位符")
        raise ConfigError("S0 停止：12 项必填字段缺失，不得用默认值填充", details)
    schema = load_schema()
    errors = validate(config, schema, schema)
    if assumed:
        errors = [e for e in errors if not any(e.startswith(p) for p in assumed)]
    if errors:
        raise ConfigError("schema 校验失败", errors)
    errors = schedule_errors(config)
    if errors:
        raise ConfigError("日程与评分字段校验失败（渲染前必须为真实值）", errors)
    return config, assumed, notes


def _date_or_error(value, where: str, errors: list[str]):
    if isinstance(value, str) and PLACEHOLDER in value:
        errors.append(f"{where}：仍为占位符 {PLACEHOLDER}")
        return None
    try:
        return to_date(value)
    except (TypeError, ValueError):
        errors.append(f"{where}：不是有效日期 {value!r}")
        return None


def _range_errors(items, prefix: str, start_key: str, end_key: str, errors: list[str]) -> None:
    for i, item in enumerate(items or []):
        s = _date_or_error(item.get(start_key), f"{prefix}[{i}].{start_key}", errors)
        e = _date_or_error(item.get(end_key), f"{prefix}[{i}].{end_key}", errors)
        if s and e and s > e:
            errors.append(f"{prefix}[{i}]：{start_key} {s} 晚于 {end_key} {e}")


def schedule_errors(config: dict) -> list[str]:
    """日程计算与方式评分依赖的字段必须是真实值：日期合法、区间不倒置、评分为整数。"""
    errors: list[str] = []
    _range_errors(get_path(config, "jp.freeze_windows", []), "jp.freeze_windows", "start", "end", errors)
    _range_errors(config.get("rollout", []), "rollout", "start", "end", errors)
    start = _date_or_error(get_path(config, "schedule.start"), "schedule.start", errors)
    go = _date_or_error(get_path(config, "schedule.go_live"), "schedule.go_live", errors)
    if start and go and start > go:
        errors.append(f"schedule：start {start} 晚于 go_live {go}")
    for i, m in enumerate(get_path(config, "schedule.milestones", []) or []):
        _date_or_error(m.get("date"), f"schedule.milestones[{i}].date", errors)
    comp = config.get("comparison") or {}
    if comp.get("client_profile") not in WEIGHTS:
        errors.append(f"comparison.client_profile：须为 conservative 或 balanced，实际 {comp.get('client_profile')!r}")
    for i, o in enumerate(comp.get("options") or []):
        bad = [k for k, v in (o.get("scores") or {}).items() if not isinstance(v, int)]
        if bad:
            errors.append(f"comparison.options[{i}].scores：{', '.join(bad)} 仍为占位符或非整数")
    return errors


# ---------------------------------------------------------------- 日期与工作日

def to_date(text: str) -> dt.date:
    return dt.date.fromisoformat(text)


def freeze_ranges(config: dict) -> list[tuple[str, dt.date, dt.date]]:
    """冻结窗口区间。日期合法性已由 schedule_errors 在 check_config 中保证，这里不吞异常。"""
    return [(w["name"], to_date(w["start"]), to_date(w["end"]))
            for w in get_path(config, "jp.freeze_windows", []) or []]


def in_freeze(day: dt.date, freezes) -> str | None:
    for name, start, end in freezes:
        if start <= day <= end:
            return name
    return None


def is_workday(day: dt.date, freezes) -> bool:
    return day.weekday() < 5 and in_freeze(day, freezes) is None


def workdays_strictly_between(a: dt.date, b: dt.date, freezes) -> int:
    """开区间 (a, b) 内的工作日数：两个承认节点之间可用于审批往返的缓冲日。"""
    if a > b:
        a, b = b, a
    return workdays_between(a, b - dt.timedelta(days=1), freezes) if b > a else 0


def workdays_between(a: dt.date, b: dt.date, freezes) -> int:
    """区间 (a, b] 内的工作日数（排除周末与冻结窗口）。a > b 时取绝对区间。"""
    if a > b:
        a, b = b, a
    count, day = 0, a + dt.timedelta(days=1)
    while day <= b:
        count += is_workday(day, freezes)
        day += dt.timedelta(days=1)
    return count


def shift_workdays(day: dt.date, n: int, freezes) -> dt.date:
    """从 day 起向前（n<0）或向后（n>0）移动 |n| 个工作日。"""
    step = 1 if n > 0 else -1
    remaining = abs(n)
    while remaining:
        day += dt.timedelta(days=step)
        remaining -= is_workday(day, freezes)
    return day


def wareki(day: dt.date) -> str:
    """公历日期对应的年号表记（令和/平成）。改元时须在此追加，见 IMPLEMENTATION_NOTES。"""
    if day >= dt.date(2019, 5, 1):
        year, era = day.year - 2018, "令和"
    else:
        year, era = day.year - 1988, "平成"
    return f"{era}{'元' if year == 1 else year}年{day.month}月{day.day}日"


def jp_date(day: dt.date) -> str:
    return f"{day.year}年{day.month}月{day.day}日（{wareki(day)}）"


def month_end(year: int, month: int) -> dt.date:
    return dt.date(year, month, calendar.monthrange(year, month)[1])


# ---------------------------------------------------------------- 正文切分与计数（lint 共用）

CJK_RE = re.compile(r"[一-鿿]")
KANA_RE = re.compile(r"[぀-ヿ]")
COMMENT_RE = re.compile(r"<!--.*?-->")


def prose_lines(text: str) -> list[tuple[int, str]]:
    """返回正文行 (行号, 去注释文本)：排除代码块、标题、表格、图片、固定版式字段行与空行。"""
    out, in_code, after_mark = [], False, False
    for no, raw in enumerate(text.splitlines(), 1):
        stripped = raw.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if FIXED_MARK in stripped:
            after_mark = True
            continue
        if after_mark and stripped:
            after_mark = False
            continue
        line = COMMENT_RE.sub("", raw).strip()
        if not line or line.startswith(("#", "|", "![")) or line == "---":
            continue
        out.append((no, line))
    return out


def count_chars(text: str, lang: str = "zh") -> int:
    total = 0
    for _no, line in prose_lines(text):
        total += len(CJK_RE.findall(line))
        if lang == "ja":
            total += len(KANA_RE.findall(line))
    return total


H2_RE = re.compile(r"^##\s+(.+?)\s*$")


def split_sections(text: str) -> list[tuple[str, int, str]]:
    """按二级标题切分。返回 (标题, 起始行号, 本节文本)。"""
    sections, title, start, buf = [], None, 0, []
    for no, line in enumerate(text.splitlines(), 1):
        m = H2_RE.match(line)
        if m:
            if title is not None:
                sections.append((title, start, "\n".join(buf)))
            title, start, buf = m.group(1), no, []
        elif title is not None:
            buf.append(line)
    if title is not None:
        sections.append((title, start, "\n".join(buf)))
    return sections


# ---------------------------------------------------------------- 术语（glossary.md）

def load_glossary() -> list[dict]:
    path = REFERENCE_DIR / "glossary.md"
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 4 or cells[0] in ("中文", "") or set(cells[0]) <= set("-: "):
            continue
        rows.append({"zh": cells[0], "ja": cells[1], "client": cells[2], "note": cells[3]})
    return rows


def term_regex(glossary: list[dict]):
    terms = sorted({g["zh"] for g in glossary}, key=len, reverse=True)
    if not terms:
        return None
    return re.compile("|".join(re.escape(t) for t in terms))


def first_term_hits(text: str, glossary: list[dict]) -> list[tuple[str, int, int, str]]:
    """每个术语在正文行中的首次出现：(术语, 行号, 行内结束位置, 行文本)。最长匹配优先。"""
    rx = term_regex(glossary)
    if rx is None:
        return []
    seen, hits = set(), []
    for no, line in prose_lines(text):
        for m in rx.finditer(line):
            if m.group(0) not in seen:
                seen.add(m.group(0))
                hits.append((m.group(0), no, m.end(), line))
    return hits


# ---------------------------------------------------------------- 固定常量（规格给定，非版本事实）

TYPE_META = {
    "sccm": {"letter": "A", "label": "终端管理平台部署与客户端铺装", "reference": "sccm-deployment.md"},
    "admerge": {"letter": "B", "label": "多企业 Active Directory 域合并", "reference": "ad-consolidation.md"},
    "entraconnect": {"letter": "C", "label": "云端 Entra Connect 同步服务器搭建", "reference": "entra-connect-cloud.md"},
}
WEIGHTS = {
    "conservative": {"cost": 0.15, "risk": 0.35, "duration": 0.20, "impact": 0.25, "scalability": 0.05},
    "balanced": {"cost": 0.25, "risk": 0.25, "duration": 0.20, "impact": 0.20, "scalability": 0.10},
}
PROFILE_LABEL = {"conservative": "保守型", "balanced": "平衡型"}
DIMENSIONS = [("cost", "成本（初期+三年运维）"), ("risk", "风险（技术+组织）"), ("duration", "工期（含审批往返）"),
              ("impact", "业务影响（中断面）"), ("scalability", "可扩展性（未来三年）")]
NINE_FIELDS = [("id", "step_id"), ("preconditions", "前置条件"), ("action", "操作"), ("expected", "预期结果"),
               ("verify", "验证方法"), ("on_fail", "失败处置"), ("rollback", "回退动作"), ("minutes", "预计耗时"),
               ("owner_role", "责任人角色")]
CHANGE_KINDS = {"cutover", "go_live", "mass_change"}
GATE_CHECKS = {  # 02 第 6 节：三类项目 Gate 检查项（固定，判定方法见对应 references）
    "sccm": ("G-A-01", "客户端铺装前检查", [
        "管理共享可访问", "目录服务所需 RPC 与共享通道已放通", "边界组覆盖目标全部网段", "站点系统已在 DNS 正确发布",
        "推送账号在目标机具备本地管理员权限", "集合成员规则已复核（含排除项）", "试点拠点验证报告已出具"]),
    "admerge": ("G-B-01", "域合并切换前检查", [
        "账户映射表逐条可追溯", "历史 SID 存活期限与回收日已书面确定", "依赖旧 SID 的应用清单及改造计划已确认",
        "跨林权限重写完成", "回退时间点精确到分钟", "云侧租户数量与合并后状态已向客户书面说明", "移行工具官方支持状态已核实"]),
    "entraconnect": ("G-C-01", "同步服务器上云前检查", [
        "云主机到域控的目录服务连通正常", "出站 443 目标域名清单已出具（域名+用途+是否经代理）", "未与域控同机",
        "防病毒/EDR 排除项已配置", "时间同步正常", "暂存模式切换已演练", "财年期末与长连休已避开", "安全审查应答材料已准备"]),
}
MIN_ANCHORS = [  # 02 第 9 节最小集；附录 A 将「出站端点」与「受支持服务器 OS」合并为 AN-06
    ("AN-01", "配置管理器 current branch 版本与生命周期", "learn.microsoft.com/mem/configmgr"),
    ("AN-02", "客户端支持的操作系统版本矩阵", "learn.microsoft.com/mem/configmgr"),
    ("AN-03", "目录服务功能级别支持矩阵", "learn.microsoft.com"),
    ("AN-04", "移行工具官方支持状态与版本要求", "learn.microsoft.com"),
    ("AN-05", "历史 SID 默认存活期限与配置项", "learn.microsoft.com"),
    ("AN-06", "同步服务出站端点清单与支持的服务器操作系统", "learn.microsoft.com"),
]
TIER_LABEL = {1: "第1层 总承包（元請）", 2: "第2层 一次承包（一次請け）", 3: "第3层 作业方（作業者）", 4: "第4层 再承包（二次請け）"}
SYNC_LABEL = {"none": "未同步", "password_hash": "密码哈希同步", "pass_through": "直通认证", "federation": "联合认证",
              ASSUMED_TEXT: ASSUMED_TEXT}
ANCHOR_RE = re.compile(r"<!--\s*ANCHOR:(AN-\d{2})\b")
ANCHOR_MAX_AGE_DAYS = 90
UNVERIFIED_MARKERS = ("待核实填写", PLACEHOLDER)

CHAPTERS = {
    "zh": ["前提与制约", "现状评估", "目标架构", "方式比较与选型", "实施方针与阶段划分", "详细计划",
           "影响与中断评估", "风险与对策", "回退计划", "体制与责任分界", "验收与移交"],
    "ja": ["前提と制約", "現状評価", "目標アーキテクチャ", "方式比較と選定", "実施方針とフェーズ分割", "詳細計画",
           "影響と中断評価", "リスクと対策", "切り戻し計画", "体制と責任分界", "受入と引継ぎ"],
}
FRONT = {
    "zh": {"revision": "修订履历", "precomm": "事前沟通记录", "summary": "本书结论摘要", "glossary": "术语集",
           "assumptions": "前提假设清单", "anchors": "核查锚点与信息核实时点"},
    "ja": {"revision": "改訂履歴", "precomm": "事前説明記録", "summary": "本書の結論", "glossary": "用語集",
           "assumptions": "前提仮定一覧", "anchors": "確認アンカーと情報確認時点"},
}
CHAPTER_MIN = {  # 03 第 3 节篇幅下限
    "sccm": [400, 500, 500, 600, 500, 300, 600, 500, 400, 300, 300],
    "admerge": [700, 700, 600, 900, 600, 400, 700, 600, 700, 350, 350],
    "entraconnect": [600, 400, 500, 700, 400, 300, 350, 500, 500, 300, 300],
}
OUTPUT_NAMES = {
    "proposal": ("01_提案書.md", "proposal.md.j2"),
    "approval_summary": ("02_稟議用サマリ.md", "approval-summary.md.j2"),
    "runbook": ("03_実施手順書.md", "runbook.md.j2"),
    "wbs": ("04_WBS.csv", "wbs.csv.j2"),
    "risk": ("05_リスク台帳.csv", "risk-register.csv.j2"),
    "test_matrix": ("06_受入試験項目表.csv", "test-matrix.csv.j2"),
    "qa": ("07_想定質問集.md", "anticipated-qa.md.j2"),
    "meeting_minutes": ("08_週次議事録雛形.md", "meeting-minutes.md.j2"),
}
FIGURES = {  # (资产模板, 编号, 图题, 所在章)
    "sccm": [("boundary-collection", "图3-1", "目标架构与边界组、集合设计", 3),
             ("rollout-phases", "图5-1", "分阶段铺装推进与冻结窗口", 5),
             ("org-structure", "图10-1", "承包体制与联络路径", 10)],
    "admerge": [("ad-topology", "图3-1", "现状与目标林结构差异（对象归属）", 3),
                ("rollout-phases", "图5-1", "分批迁移推进与冻结窗口", 5),
                ("org-structure", "图10-1", "承包体制与联络路径", 10)],
    "entraconnect": [("ad-topology", "图2-1", "现状与目标对象归属差异", 2),
                     ("sync-flow", "图3-1", "目标架构与同步链路（端口与出站目标）", 3),
                     ("rollout-phases", "图5-1", "分阶段推进与冻结窗口", 5),
                     ("org-structure", "图10-1", "承包体制与联络路径", 10)],
}


# ---------------------------------------------------------------- fact model 构建

def fiscal_year_of(day: dt.date, start_month: int = 4) -> int:
    return day.year if day.month >= start_month else day.year - 1


def half_label(day: dt.date) -> str:
    return "上半期" if 4 <= day.month <= 9 else "下半期"


def _safe_date(text):
    try:
        return to_date(text)
    except (TypeError, ValueError):
        return None


def build_project(cfg: dict) -> dict:
    p = dict(cfg["project"])
    meta = TYPE_META[p["project_type"]]
    start, go = _safe_date(cfg["schedule"]["start"]), _safe_date(cfg["schedule"]["go_live"])
    if start and go:
        fy_a, fy_b = fiscal_year_of(start), fiscal_year_of(go)
        p["fiscal_year"] = f"{fy_a}年度" if fy_a == fy_b else f"{fy_a}年度至{fy_b}年度"
        la, lb = f"{fy_a}年度{half_label(start)}", f"{fy_b}年度{half_label(go)}"
        p["phase_label"] = la if la == lb else f"{la}至{lb}"
    else:
        p["fiscal_year"] = p["phase_label"] = "【待确认】日程未定"
    p.update(type_letter=meta["letter"], type_label=meta["label"], reference=meta["reference"])
    return p


def number_milestones(cfg: dict) -> list[dict]:
    ms = sorted(cfg["schedule"]["milestones"], key=lambda m: m["date"])
    out = []
    for i, m in enumerate(ms, 1):
        item = dict(m)
        item.setdefault("id", f"M-{i:02d}")
        item.setdefault("kind", "normal")
        out.append(item)
    return out


def change_tasks(cfg: dict, milestones: list[dict]) -> list[dict]:
    """上线、切换、大范围变更类任务（R1/R3 的检查对象）。"""
    tasks = [{"id": m["id"], "name": m["name"], "start": m["date"], "end": m["date"]}
             for m in milestones if m["kind"] in CHANGE_KINDS]
    tasks += [{"id": w["id"], "name": w["name"], "start": w["start"], "end": w["end"]} for w in cfg["rollout"]]
    gl = cfg["schedule"]["go_live"]
    if not any(m["kind"] == "go_live" and m["date"] == gl for m in milestones):
        tasks.append({"id": "M-GL", "name": "上线（本番稼働）", "start": gl, "end": gl})
    return tasks


def overrides_of(schedule: dict) -> dict[str, dict]:
    """override_freeze 支持单个对象（02 第 7 节）或对象列表；按 task_id 索引。"""
    raw = schedule.get("override_freeze")
    items = raw if isinstance(raw, list) else ([raw] if raw else [])
    return {o["task_id"]: o for o in items}


def approval_gaps(milestones, buffer_days: int, freezes) -> list[dict]:
    """相邻承认节点之间的缓冲工作日：只计开区间 (前节点, 后节点) 内的工作日，与 WBS 承认缓冲行一致。"""
    nodes = [m for m in milestones if m["approval"]]
    gaps = []
    for a, b in zip(nodes, nodes[1:]):
        wd = workdays_strictly_between(to_date(a["date"]), to_date(b["date"]), freezes)
        gaps.append({"from": a["name"], "from_id": a["id"], "to": b["name"], "to_id": b["id"], "workdays": wd,
                     "required": buffer_days, "shortfall": max(0, buffer_days - wd), "ok": wd >= buffer_days})
    return gaps


def freeze_conflicts(tasks, freezes, overrides: dict[str, dict]) -> list[dict]:
    out = []
    for t in tasks:
        s, e = to_date(t["start"]), to_date(t["end"])
        for name, fs, fe in freezes:
            if s <= fe and fs <= e:
                ov = overrides.get(t["id"])
                out.append({"task_id": t["id"], "task_name": t["name"], "task_start": t["start"],
                            "task_end": t["end"], "window": name, "window_start": fs.isoformat(),
                            "window_end": fe.isoformat(), "overridden": ov is not None, "override": ov})
    return out


def fiscal_boundary_risks(tasks, months, freezes) -> list[dict]:
    out = []
    for t in tasks:
        s, e = _safe_date(t["start"]), _safe_date(t["end"])
        if not s or not e:
            continue
        for year in range(s.year - 1, e.year + 2):
            for m in months:
                boundary = month_end(year, m)
                lo, hi = shift_workdays(boundary, -10, freezes), shift_workdays(boundary, 10, freezes)
                if s <= hi and lo <= e:
                    out.append({"task_id": t["id"], "task_name": t["name"], "start": t["start"], "end": t["end"],
                                "boundary": f"{year}年{m}月末", "window": f"{lo.isoformat()}～{hi.isoformat()}"})
    return out


WBS_SHORT = "工期不足，须调整"


def _wd_len(start: dt.date, end: dt.date, freezes) -> str:
    return f"{workdays_between(start - dt.timedelta(days=1), end, freezes)}工作日"


def _milestone_rows(cfg: dict, m: dict, prev_end: dt.date, prev_id: str, seq: int, freezes, owner: str):
    buffer_days = cfg["jp"]["approval_buffer_days"]
    nodes = "、".join(cfg["jp"]["approval_nodes"])
    mdate = to_date(m["date"])
    rows, buffer_row, work_end = [], None, mdate - dt.timedelta(days=1)
    if m["approval"] and buffer_days > 0:
        b_start, b_end = shift_workdays(mdate, -buffer_days, freezes), shift_workdays(mdate, -1, freezes)
        buffer_row = {"phase": "承认", "name": f"承认缓冲（{m['name']}）", "start": b_start.isoformat(),
                      "end": b_end.isoformat(), "duration": _wd_len(b_start, b_end, freezes), "owner": owner,
                      "approval": "", "note": f"承认待ち缓冲 {buffer_days} 工作日（{nodes}）"}
        work_end = b_start - dt.timedelta(days=1)
    w_start = max(prev_end + dt.timedelta(days=1), to_date(cfg["schedule"]["start"]))
    w_end = max(work_end, w_start)
    seq += 1
    work = {"id": f"WBS-{seq:02d}", "phase": m["name"], "name": f"{m['name']}相关作业", "depends": prev_id,
            "start": w_start.isoformat(), "end": w_end.isoformat(), "duration": _wd_len(w_start, w_end, freezes),
            "owner": owner, "approval": "", "note": WBS_SHORT if work_end < w_start else ""}
    rows.append(work)
    last = work["id"]
    if buffer_row:
        seq += 1
        buffer_row.update(id=f"WBS-{seq:02d}", depends=last)
        rows.append(buffer_row)
        last = buffer_row["id"]
    rows.append({"id": m["id"], "phase": "里程碑", "name": m["name"], "depends": last, "start": m["date"],
                 "end": m["date"], "duration": "0工作日", "owner": owner,
                 "approval": nodes if m["approval"] else "", "note": "承认节点" if m["approval"] else ""})
    return rows, seq


def build_wbs(cfg: dict, milestones, freezes, owner: str) -> list[dict]:
    """由里程碑、承认缓冲、铺装/迁移波次与上线日派生 WBS 行。"""
    rows, seq = [], 0
    prev_end, prev_id = to_date(cfg["schedule"]["start"]) - dt.timedelta(days=1), ""
    for m in milestones:
        new_rows, seq = _milestone_rows(cfg, m, prev_end, prev_id, seq, freezes, owner)
        rows += new_rows
        prev_end, prev_id = to_date(m["date"]), m["id"]
    prev = ""
    for w in cfg["rollout"]:
        s, e = _safe_date(w["start"]), _safe_date(w["end"])
        rows.append({"id": w["id"], "phase": "铺装/迁移波次", "name": w["name"], "depends": prev, "start": w["start"],
                     "end": w["end"], "duration": _wd_len(s, e, freezes) if s and e else PLACEHOLDER, "owner": owner,
                     "approval": "", "note": f"对象：{w['scope']}；退出条件：{w['exit_criteria']}"})
        prev = w["id"]
    gl = cfg["schedule"]["go_live"]
    rows.append({"id": "M-GL", "phase": "里程碑", "name": "上线（本番稼働）", "depends": prev, "start": gl, "end": gl,
                 "duration": "0工作日", "owner": owner, "approval": "", "note": "上线类任务，受 R1/R3 校验"})
    return sorted(rows, key=lambda r: (r["start"], r["id"]))


def build_schedule(cfg: dict) -> dict:
    freezes = freeze_ranges(cfg)
    ms = number_milestones(cfg)
    tasks = change_tasks(cfg, ms)
    overrides = overrides_of(cfg["schedule"])
    sched = dict(cfg["schedule"])
    gaps = approval_gaps(ms, cfg["jp"]["approval_buffer_days"], freezes)
    wbs = build_wbs(cfg, ms, freezes, cfg["cutover"]["decision_role"])
    sched.update(
        milestones=ms, approval_gaps=gaps, approval_buffer_ok=all(g["ok"] for g in gaps),
        freeze_conflicts=freeze_conflicts(tasks, freezes, overrides),
        fiscal_boundary_risks=fiscal_boundary_risks(tasks, cfg["jp"]["fiscal_boundary_months"], freezes),
        change_tasks=tasks, override_freeze=list(overrides.values()), wbs=wbs,
        wbs_short=[r["id"] for r in wbs if r["note"] == WBS_SHORT],
        go_live_jp=jp_date(to_date(cfg["schedule"]["go_live"])),
    )
    return sched


def build_comparison(cfg: dict) -> dict:
    c = dict(cfg["comparison"])
    weights = WEIGHTS[c["client_profile"]]
    rows = [{"name": o["name"], "scores": o["scores"],
             "weighted": round(sum(o["scores"][k] * w for k, w in weights.items()), 2)} for o in c["options"]]
    ranked = sorted(rows, key=lambda r: r["weighted"], reverse=True)
    for i, r in enumerate(ranked, 1):
        r["rank"] = i
    top = ranked[0] if ranked else None
    chosen = next((r for r in rows if r["name"] == c["chosen"]), None)
    c.update(weights=weights, profile_label=PROFILE_LABEL[c["client_profile"]], rows=rows, top=top,
             chosen_row=chosen, chosen_is_top=bool(top and chosen and top["name"] == chosen["name"]),
             rejected=[{"name": r["name"], "reason": c["rejected_reasons"].get(r["name"], ""),
                        "weighted": r["weighted"]} for r in rows if r["name"] != c["chosen"]],
             dimensions=[{"key": k, "label": lbl, "weight": weights[k]} for k, lbl in DIMENSIONS])
    return c


def derived_risks(sched: dict, owner: str) -> list[dict]:
    out = []
    for i, fb in enumerate(sched["fiscal_boundary_risks"], 1):
        out.append({"id": f"R-FB-{i:02d}", "category": "日程",
                    "description": f"{fb['task_name']}（{fb['task_id']}）落在 {fb['boundary']} 前后 10 个工作日内",
                    "trigger": f"任务日期与期末窗口 {fb['window']} 重叠",
                    "impact": "与客户决算及期末业务高峰重叠，变更审批与现场支援人员受限", "likelihood": "中",
                    "mitigation": "提前与客户财务及业务部门确认期末日程；该任务前后各 5 个工作日内冻结非必要变更；准备改期候选日",
                    "owner": owner, "related_task": fb["task_id"], "status": "未处理（calendar_check R3 派生）"})
    overridden = [fc for fc in sched["freeze_conflicts"] if fc["overridden"]]
    for j, fc in enumerate(overridden, 1):
        ov = fc["override"]
        out.append({"id": f"R-FZ-{j:02d}", "category": "日程",
                    "description": f"{fc['task_name']}（{fc['task_id']}）与冻结窗口「{fc['window']}」重叠，已获批准覆盖",
                    "trigger": f"冻结窗口 {fc['window_start']}～{fc['window_end']} 内执行变更",
                    "impact": "冻结期内客户侧支援人员与升级路径受限，故障响应时间延长", "likelihood": "中",
                    "mitigation": f"已获批准覆盖：批准人 {ov['approved_by']}；理由：{ov['reason']}。须事先确认冻结期内的值班与升级联系人",
                    "owner": owner, "related_task": fc["task_id"], "status": "已获批准覆盖"})
    return out


def build_risks(cfg: dict, sched: dict) -> dict:
    items = [dict(r) for r in cfg["risks"]] + derived_risks(sched, cfg["cutover"]["decision_role"])
    order = {"高": 0, "中": 1, "低": 2}
    top5 = sorted(cfg["risks"], key=lambda r: order.get(r.get("likelihood"), 3))[:5]
    return {"list": items, "top5": top5,
            "missing_mitigation": [r["id"] for r in cfg["risks"] if is_blank(r.get("mitigation"))]}


def step_missing_fields(step: dict) -> list[str]:
    lacks = []
    for key, label in NINE_FIELDS:
        value = step.get(key, _MISSING)
        if key == "minutes":
            if not (isinstance(value, int) and not isinstance(value, bool) and value > 0):
                lacks.append(label)
        elif is_blank(value):
            lacks.append(label)
    return lacks


def build_steps(cfg: dict) -> dict:
    items = cfg["steps"]
    missing = [{"id": s.get("id", "?"), "fields": f} for s in items if (f := step_missing_fields(s))]
    phases, by_phase = [], {}
    for s in items:
        if s["phase"] not in by_phase:
            by_phase[s["phase"]] = []
            phases.append(s["phase"])
        by_phase[s["phase"]].append(s)
    return {"list": items, "missing_fields": missing,
            "by_phase": [{"phase": p, "steps": by_phase[p]} for p in phases],
            "total_minutes": sum(s["minutes"] for s in items if isinstance(s["minutes"], int))}


def reference_anchor_ids(ref_dir: Path = REFERENCE_DIR) -> list[str]:
    ids = []
    for path in sorted(ref_dir.glob("*.md")):
        ids += ANCHOR_RE.findall(path.read_text(encoding="utf-8"))
    return sorted(set(ids))


def anchor_problems(anchor: dict, as_of: dt.date) -> list[str]:
    probs = []
    value = anchor.get("value", "")
    if is_blank(value) or any(m in value for m in UNVERIFIED_MARKERS):
        probs.append("value 未填写")
    verified = _safe_date(anchor.get("verified_on") or "")
    if verified is None:
        probs.append("verified_on 未填写")
    else:
        age = (as_of - verified).days
        if age > ANCHOR_MAX_AGE_DAYS:
            probs.append(f"verified_on 距今 {age} 天，超过 {ANCHOR_MAX_AGE_DAYS} 天")
        elif age < 0:
            probs.append("verified_on 晚于信息核实时点")
    return probs


def build_anchors(cfg: dict, as_of: dt.date) -> dict:
    items = cfg["anchors"]
    unverified = [{"id": a["id"], "problems": p} for a in items if (p := anchor_problems(a, as_of))]
    known = {a["id"] for a in items}
    unverified += [{"id": rid, "problems": ["references 中存在该锚点，但 project.yaml 未登记"]}
                   for rid in reference_anchor_ids() if rid not in known]
    return {"list": items, "by_id": {a["id"]: a for a in items}, "unverified": unverified}


def build_tiers(cfg: dict) -> list[dict]:
    n = cfg["jp"]["vendor_tiers"] if isinstance(cfg["jp"]["vendor_tiers"], int) else 3
    return [{"tier": t, "label": TIER_LABEL[t], "vendors": [v for v in cfg["jp"]["vendors"] if v["tier"] == t]}
            for t in range(1, n + 1)]


def _int_sum(values) -> int:
    return sum(v for v in values if isinstance(v, int) and not isinstance(v, bool))


def build_current_state(cfg: dict) -> dict:
    cs = dict(cfg["current_state"])
    cs.update(
        domain_count=len(cs["domains"]), forest_count=len({d["forest"] for d in cs["domains"]}),
        dc_total=_int_sum(d["dc_count"] for d in cs["domains"]), tenant_count=len(cs["cloud_tenants"]),
        tenant_users=_int_sum(t["user_count"] for t in cs["cloud_tenants"]),
        tenants=[{**t, "sync_label": SYNC_LABEL.get(t["sync_method"], t["sync_method"])} for t in cs["cloud_tenants"]],
        sites=[{"name": k, "count": v} for k, v in cs["endpoints"]["by_site"].items()],
    )
    return cs


def build_figures(ptype: str, selected: set) -> list[dict]:
    if "diagrams" not in selected:
        return []
    return [{"asset": a, "number": n, "title": t, "chapter": c, "file": f"figures/{a}.svg",
             "source": f"figures/{a}.mmd"} for a, n, t, c in FIGURES[ptype]]


def build_fact_model(cfg: dict, as_of: dt.date, assumed=(), assume_notes=(), selected=None,
                     assume_mode: bool = False) -> dict:
    lang = cfg["deliverables"]["language"]
    selected = set(selected or cfg["deliverables"]["items"])
    sched = build_schedule(cfg)
    figures = build_figures(cfg["project"]["project_type"], selected)
    fm = {k: copy.deepcopy(v) for k, v in cfg.items() if k not in ("risks", "steps", "anchors", "deliverables")}
    fm.update(
        project=build_project(cfg), current_state=build_current_state(cfg), schedule=sched,
        comparison=build_comparison(cfg), risks=build_risks(cfg, sched), steps=build_steps(cfg),
        anchors=build_anchors(cfg, as_of), tiers=build_tiers(cfg),
        deliverables={"selected": sorted(selected), "language": lang, "format": cfg["deliverables"]["format"]},
        assumptions={"mode": bool(assume_mode or cfg.get("assumptions_mode") or assumed),
                     "list": [normalize_assumption(a) for a in cfg.get("assumptions", [])] + list(assume_notes),
                     "assumed_fields": list(assumed)},
        doc={"info_as_of": as_of.isoformat(), "issue_date": jp_date(as_of), "language": lang,
             "lint_status": f"{LINT_MARK}完备性校验：{LINT_PENDING}", "figures": figures,
             "figure": {f["asset"]: f for f in figures}, "template_override": bool(cfg.get("template_override"))},
        L={"ch": CHAPTERS[lang], "front": FRONT[lang]},
        glossary_overrides=cfg.get("glossary_overrides", {}),
        network=cfg.get("network"), review=cfg.get("review"),
    )
    return fm


# ---------------------------------------------------------------- 渲染

class RenderError(Exception):
    """渲染阻断（退出码 1）。"""


def csv_cell(value) -> str:
    text = "" if value is None else str(value)
    if any(ch in text for ch in ',"\n\r'):
        return '"' + text.replace('"', '""') + '"'
    return text


MERMAID_UNSAFE = str.maketrans({'"': "'", "|": "／", ":": "：", ";": "；", "#": "＃", "\n": " ", "\r": " "})


def mermaid_text(value) -> str:
    """转义 mermaid 标签中的保留字符。"""
    return str(value).translate(MERMAID_UNSAFE)


def make_env():
    """沙箱化的 Jinja2 环境：客户自有模板（template_override）也在沙箱内执行。"""
    try:
        import jinja2
        from jinja2.sandbox import SandboxedEnvironment
    except ImportError as exc:  # pragma: no cover
        raise ConfigError("缺少依赖 Jinja2") from exc
    env = SandboxedEnvironment(
        loader=jinja2.FileSystemLoader([str(TEMPLATE_DIR), str(ASSET_DIR)]),
        undefined=jinja2.StrictUndefined, trim_blocks=True, lstrip_blocks=True, keep_trailing_newline=True,
        autoescape=False,
    )
    env.filters["csv"] = csv_cell
    env.filters["mm"] = mermaid_text
    env.filters["pct"] = lambda v: f"{round(v * 100)}%"
    env.filters["jpdate"] = lambda s: jp_date(to_date(s)) if _safe_date(s) else s
    return env


def annotate_terms(text: str, glossary: list[dict], overrides: dict) -> str:
    """术语首次出现处附日文原文：中文（日文原文）。仅作用于正文行；中日同形的术语不注。"""
    by_zh = {g["zh"]: g for g in glossary}
    lines = text.splitlines()
    for term, no, end, _line in reversed(first_term_hits(text, glossary)):
        raw = lines[no - 1]
        g = by_zh[term]
        if "<!--" in raw or g["ja"] == term:
            continue
        pos = end + len(raw) - len(raw.lstrip())
        if raw[pos:].startswith(("（", "(")):
            continue
        note = f"{g['ja']}；贵司称「{overrides[term]}」" if term in overrides else g["ja"]
        lines[no - 1] = f"{raw[:pos]}（{note}）{raw[pos:]}"
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


GLOSSARY_MARK = "<!-- GLOSSARY_TABLE -->"


def glossary_table(text: str, glossary: list[dict], overrides: dict) -> str:
    """术语集：列出正文中出现的全部术语（中文 / 日文原文 / 客户用语 / 说明）。"""
    by_zh = {g["zh"]: g for g in glossary}
    rows = ["| 中文 | 日文原文 | 客户用语 | 说明 |", "|---|---|---|---|"]
    for term, *_ in first_term_hits(text, glossary):
        g = by_zh[term]
        rows.append(f"| {term} | {g['ja']} | {overrides.get(term, g['client'])} | {g['note']} |")
    if len(rows) == 2:
        rows.append("| （正文未使用术语集中的术语） | | | |")
    return "\n".join(rows)


def _override_source(cfg: dict, config_path: Path) -> str | None:
    """读取客户自有方案书模板（只加载这一个文件，不把其目录加入搜索路径，避免遮蔽内置模板）。"""
    if not cfg.get("template_override"):
        return None
    tp = (config_path.parent / cfg["template_override"]).resolve()
    if not tp.is_file():
        raise ConfigError(f"template_override 指向的模板不存在：{tp}")
    try:
        return tp.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ConfigError(f"template_override 无法以 UTF-8 读取：{tp}") from exc


def render_all(cfg: dict, fm: dict, config_path: Path, selected: set) -> dict[str, str]:
    """返回 {相对路径: 内容}。任何模板错误抛出异常，不写半成品。"""
    import jinja2
    override_src = _override_source(cfg, config_path)
    env = make_env()
    glossary = load_glossary()
    outputs = {}
    try:
        for key, (out_name, tpl) in OUTPUT_NAMES.items():
            if key not in selected:
                continue
            template = env.from_string(override_src) if (key == "proposal" and override_src) else env.get_template(tpl)
            text = template.render(**fm, fm=fm)
            if key == "proposal":
                if fm["deliverables"]["language"] == "zh":
                    text = annotate_terms(text, glossary, fm["glossary_overrides"])
                text = text.replace(GLOSSARY_MARK, glossary_table(text, glossary, fm["glossary_overrides"]))
            outputs[out_name] = text
        for f in fm["doc"]["figures"]:
            outputs[f["source"]] = env.get_template(f"{f['asset']}.mmd.j2").render(**fm, fm=fm)
    except jinja2.UndefinedError as exc:
        raise RenderError(f"模板变量缺失：{exc}") from exc
    except jinja2.TemplateError as exc:
        raise RenderError(f"模板错误：{exc}") from exc
    outputs["evidence/README.md"] = evidence_index(fm)
    return {k: (tidy_markdown(v) if k.endswith(".md") else v) for k, v in outputs.items()}


def tidy_markdown(text: str) -> str:
    """标题前补空行、压缩连续空行，保证 Markdown 结构稳定（不改动文字内容）。"""
    out: list[str] = []
    for line in text.splitlines():
        if line.startswith("#") and out and out[-1].strip():
            out.append("")
        if not line.strip() and out and not out[-1].strip():
            continue
        out.append(line)
    return "\n".join(out).strip("\n") + "\n"


EVIDENCE_SCRIPTS = {
    "sccm": "powershell/sccm/Get-ClientPushReadiness.ps1、Export-CollectionMembers.ps1、Export-BoundaryCoverage.ps1",
    "admerge": "powershell/ad/Get-ForestInventory.ps1、Export-AccountMapping.ps1、Get-SIDHistoryAudit.ps1",
    "entraconnect": "powershell/entraconnect/Test-DcConnectivity.ps1、Test-OutboundEndpoints.ps1、Get-SyncStatus.ps1",
}


def evidence_index(fm: dict) -> str:
    lines = ["# 证据目录说明", "",
             f"本目录存放 Gate 证据 CSV（PowerShell 层输出）。对应脚本：{EVIDENCE_SCRIPTS[fm['project']['project_type']]}。",
             "CSV 列名与验收矩阵列定义一致，可直接作为方案书附录证据。", "",
             "| Gate | 检查项 | 证据文件（建议名） |", "|---|---|---|"]
    for g in fm["gates"]:
        lines += [f"| {g['id']} | {c} | {g['id']}-{i:02d}.csv |" for i, c in enumerate(g["checks"], 1)]
    lines += ["", f"信息核实时点：{fm['doc']['info_as_of']}", ""]
    return "\n".join(lines)


def config_digest(path: Path) -> str:
    """配置文件的 sha256：写入 fact_model.json，lint / calendar_check 据此拒绝陈旧产物。"""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_outputs(out_dir: Path, outputs: dict[str, str], fm: dict) -> list[str]:
    """先把状态置为 FAIL，再写到临时目录，全部成功后逐个原子替换。中途失败时状态保持 FAIL。

    输出目录中的其他文件（例如 evidence/ 下 PowerShell 导出的证据 CSV）不删除。
    """
    root = out_dir.resolve()
    status = (
        "FAIL\n原因：渲染后尚未执行 lint.py 与 calendar_check.py，产物不得标记为可交付。\n"
        f"渲染时点：{fm['doc']['info_as_of']}\n")
    files = dict(outputs)
    files["fact_model.json"] = json.dumps(fm, ensure_ascii=False, indent=2)
    for rel in files:
        target = (root / rel).resolve()
        if root not in target.parents:
            raise ConfigError(f"输出路径越界：{target}")
    root.mkdir(parents=True, exist_ok=True)
    (root / "LINT_STATUS.txt").write_text(status, encoding="utf-8")
    staging = Path(tempfile.mkdtemp(prefix=".render-", dir=root))
    try:
        for rel, text in files.items():
            tmp = staging / rel
            tmp.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(text, encoding="utf-8", newline="\n")
        for sub in ("figures", "evidence"):
            (root / sub).mkdir(exist_ok=True)
        for rel in files:
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            os.replace(staging / rel, root / rel)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return list(files) + ["LINT_STATUS.txt"]


def parse_as_of(text: str | None) -> dt.date:
    if not text:
        return dt.date.today()
    try:
        return to_date(text)
    except ValueError as exc:
        raise ConfigError(f"--as-of 日期格式错误：{text}（应为 YYYY-MM-DD）") from exc


def utf8_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


def emit(tool: str, result: dict, as_json: bool) -> None:
    utf8_stdout()
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print(f"[{tool}] {result['status']}：{result['message']}")
    for d in result.get("details", []):
        print(f"  - {d}")
    for f in result.get("files", []):
        print(f"  + {f}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="ringi-kit 渲染：project.yaml → 全部交付物")
    ap.add_argument("--config", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", default="", help="逗号分隔，如 proposal,runbook；默认全部")
    ap.add_argument("--assume", action="store_true", help="用户已授权按假设值生成（缺失字段标注 [假设]）")
    ap.add_argument("--as-of", default=None, help="信息核实时点（默认今天，YYYY-MM-DD）")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    try:
        config_path = Path(args.config).resolve()
        raw = load_yaml(config_path)
        assume = args.assume or bool(raw.get("assumptions_mode"))
        cfg, assumed, notes = check_config(raw, assume=assume)
        as_of = parse_as_of(args.as_of)
        only = {x.strip() for x in args.only.split(",") if x.strip()}
        unknown = only - set(OUTPUT_NAMES) - {"diagrams"}
        if unknown:
            raise ConfigError(f"--only 含未知交付物：{', '.join(sorted(unknown))}")
        selected = set(cfg["deliverables"]["items"])
        if only:
            selected &= only | ({"diagrams"} if "proposal" in only else set())
            if not selected:
                raise ConfigError(f"--only {args.only} 与 deliverables.items 没有交集，没有可渲染的交付物")
        fm = build_fact_model(cfg, as_of, assumed, notes, selected, assume_mode=assume)
        fm["doc"]["config_sha256"] = config_digest(config_path)
        outputs = render_all(cfg, fm, config_path, selected)
        files = write_outputs(Path(args.out), outputs, fm)
    except OSError as exc:
        emit("render", {"status": "error", "exit_code": EXIT_ARG, "message": f"写出失败：{exc}",
                        "details": ["LINT_STATUS.txt 已置为 FAIL；修正后重新渲染"]}, args.json)
        return EXIT_ARG
    except ConfigError as exc:
        emit("render", {"status": "error", "exit_code": EXIT_ARG, "message": str(exc), "details": exc.details}, args.json)
        return EXIT_ARG
    except RenderError as exc:
        emit("render", {"status": "error", "exit_code": EXIT_BLOCK, "message": str(exc), "details": []}, args.json)
        return EXIT_BLOCK
    emit("render", {"status": "ok", "exit_code": EXIT_OK,
                    "message": f"已渲染到 {args.out}；下一步执行 lint.py 与 calendar_check.py",
                    "files": files, "assumed_fields": assumed}, args.json)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
