"""负例 N-01..N-25：每个负例同时断言退出码、规则 ID 与对象名。"""
from __future__ import annotations

import datetime as dt
import re
import shutil

from tlib import C, EXAMPLES, TODAY, copy_kit, dump, has, lint_only, load, pipeline, record, run

A, B = EXAMPLES["a-sccm"], EXAMPLES["b-admerge"]


def _cfg_case(cid, title, mutate, example=A, expect_render=0, rule=None, needles=(), tool="lint"):
    cfg = load(example)
    mutate(cfg)
    path = dump(cfg, cid)
    build, r, lint, cal = pipeline(path, cid)
    out = lint if tool == "lint" else cal
    checks = []
    if expect_render is not None:
        checks.append((f"render 退出码 {'≠0' if expect_render else '0'}（实测 {r[0]}）",
                       (r[0] != 0) if expect_render else (r[0] == 0)))
    checks.append((f"{tool} 退出码 1（实测 {out[0]}）", out[0] == 1))
    if rule:
        checks.append((f"报告含规则 ID {rule}", rule in out[1]))
    for n in needles:
        checks.append((f"报告含对象「{n}」", n in out[1]))
    record(cid, "负例", title, checks, _excerpt(out[1], rule))


def _excerpt(text: str, rule: str | None) -> str:
    if not rule:
        return text[:500]
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        if ln.startswith(rule):
            return "\n".join(lines[i:i + 4])
    return text[:500]


def _build_case(cid, title, example, edit, rule, needles=(), filename="01_提案書.md"):
    """先完整渲染，再修改构建产物，验证 lint 能拒绝。"""
    cfg = C.kit / "examples" / example / "project.yaml"
    build, r, _l, _c = pipeline(cfg, cid)
    target = build / filename
    target.write_text(edit(target.read_text(encoding="utf-8")), encoding="utf-8")
    out = lint_only(cfg, build)
    checks = [("基线渲染成功", r[0] == 0), (f"lint 退出码 1（实测 {out[0]}）", out[0] == 1),
              (f"报告含规则 ID {rule}", rule in out[1])] + [(f"报告含「{n}」", n in out[1]) for n in needles]
    record(cid, "负例", title, checks, _excerpt(out[1], rule))


def n01():
    cfg = load(A)
    del cfg["project"]["client_name"]
    path = dump(cfg, "N-01")
    rc, out = run("render.py", "--config", path, "--out", C.work / "N-01" / "build")
    record("N-01", "负例", "缺必填字段", [("render 退出码 2", rc == 2), ("S0 停止", "S0 停止" in out),
                                       ("列出缺失字段名 project.client_name", "project.client_name" in out),
                                       ("未输出交付物", not (C.work / "N-01" / "build" / "01_提案書.md").exists())], out)


def n02():
    _cfg_case("N-02", "占位符未替换", lambda c: c["targets"].__setitem__("scope", "<待填写>"), rule="L-01",
              needles=("targets.scope", "01_提案書.md:第"))


def n03():
    kit = copy_kit("N-03")
    tpl = kit / "templates" / "proposal.md.j2"
    text = tpl.read_text(encoding="utf-8")
    text = re.sub(r"## 9 \{\{ L\.ch\[8\] \}\}.*?(?=## 10 \{\{ L\.ch\[9\] \}\})", "", text, flags=re.S)
    tpl.write_text(text, encoding="utf-8")
    cfg = kit / "examples" / A / "project.yaml"
    build, r, lint, _c = pipeline(cfg, "N-03", kit=kit)
    record("N-03", "负例", "缺方案书章节", [("模板已删除第 9 章且渲染成功", r[0] == 0), ("lint 退出码 1", lint[0] == 1),
                                         ("报告含 L-02", "L-02" in lint[1]), ("报「缺章：9 回退计划」", "缺章：9 回退计划" in lint[1])],
           _excerpt(lint[1], "L-02"))


def n04():
    def edit(text):
        body = "本章内容" + "测" * 196
        return re.sub(r"(## 4 方式比较与选型\n).*?(?=\n## 5 )", lambda m: m.group(1) + "\n" + body + "\n", text, flags=re.S)
    _build_case("N-04", "章节篇幅不足（项目 B 第 4 章）", B, edit, "L-03", ("第4章 200/900",))


def n05():
    _cfg_case("N-05", "步骤缺字段", lambda c: c["steps"][1].pop("rollback"), expect_render=1, rule="L-04",
              needles=("A-03-01", "rollback"))


def n06():
    _cfg_case("N-06", "前置条件含糊", lambda c: c["steps"][0]["preconditions"].__setitem__(0, "环境已就绪"),
              rule="L-05", needles=("环境已就绪",))


def n07():
    _cfg_case("N-07", "风险缺缓解措施", lambda c: c["risks"][0].__setitem__("mitigation", ""), rule="L-06", needles=("R-01",))


def n08():
    _cfg_case("N-08", "验收缺证据形式", lambda c: c["acceptance"][0].__setitem__("evidence", ""), rule="L-07", needles=("T-01",))


def n09():
    _cfg_case("N-09", "方式比较不足三种", lambda c: c["comparison"]["options"].pop(2), expect_render=1, rule="L-09",
              needles=("comparison.options",))


def n10():
    _cfg_case("N-10", "缺否决理由", lambda c: c["comparison"]["rejected_reasons"].pop("一次性全量推送"), rule="L-09",
              needles=("缺否决理由：一次性全量推送",))


def n11():
    _build_case("N-11", "日文版式字段被翻译", A, lambda t: t.replace("A社 御中", "A社 敬启", 1), "L-10", ("第", "敬启"))


def n12():
    _build_case("N-12", "孤图", A, lambda t: t.replace("如图5-1所示，", "", 1), "L-11", ("rollout-phases",))


def n13():
    _cfg_case("N-13", "事前沟通记录为空", lambda c: c.__setitem__("pre_communication", []), rule="L-12",
              needles=("事前沟通记录",))


def n14():
    _cfg_case("N-14", "锚点未填", lambda c: c["anchors"][0].__setitem__("value", ""), rule="L-13", needles=("AN-01", "value 未填写"))


def n15():
    old = (TODAY - dt.timedelta(days=200)).isoformat()
    _cfg_case("N-15", "锚点过期（200 天前）", lambda c: c["anchors"][0].__setitem__("verified_on", old), rule="L-13",
              needles=("AN-01", "距今 200 天"))


def n16():
    _build_case("N-16", "缺页脚时点", A, lambda t: re.sub(r"信息核实时点：\d{4}-\d{2}-\d{2}", "", t), "L-15", ("01_提案書.md",))


def n17():
    cfg = C.kit / "examples" / A / "project.yaml"
    build, r, _l, _c = pipeline(cfg, "N-17")
    (build / "figures" / "org-structure.mmd").unlink()
    text = (build / "01_提案書.md").read_text(encoding="utf-8")
    (build / "01_提案書.md").write_text(re.sub(r"!\[图10-1[^\n]*\n", "", text), encoding="utf-8")
    out = lint_only(cfg, build)
    record("N-17", "负例", "缺体制图（multi_tier_vendors: true）",
           [("lint 退出码 1", out[0] == 1), ("报告含 L-16", "L-16" in out[1]), ("指出缺少体制图", "缺少体制图" in out[1])],
           _excerpt(out[1], "L-16"))


def n18():
    def edit(text):
        return text.replace("## 5 请批事项", "## 5 请批事项\n\n" + "补充说明" * 375, 1)
    cfg = C.kit / "examples" / A / "project.yaml"
    build, r, _l, _c = pipeline(cfg, "N-18")
    p = build / "02_稟議用サマリ.md"
    p.write_text(edit(p.read_text(encoding="utf-8")), encoding="utf-8")
    out = lint_only(cfg, build)
    m = re.search(r"审批摘要超长：(\d+)/1200", out[1])
    record("N-18", "负例", "摘要超长（≥1500 字）",
           [("lint 退出码 1", out[0] == 1), ("报告含 L-18", "L-18" in out[1]),
            (f"报字数（实测 {m.group(1) if m else '无'}，≥1500）", bool(m) and int(m.group(1)) >= 1500)], _excerpt(out[1], "L-18"))


def n19():
    _cfg_case("N-19", "回退含糊", lambda c: c["steps"][2].__setitem__("rollback", "视情况回退"), rule="L-19", needles=("A-04-01",))


def n20():
    _cfg_case("N-20", "WBS 无缓冲（approval_buffer_days: 0）", lambda c: c["jp"].__setitem__("approval_buffer_days", 0),
              rule="L-20", needles=("M-01", "要件定義完了"))


def n21():
    _cfg_case("N-21", "失败模式引用失效", lambda c: c["steps"][0].__setitem__("on_fail", "F-999"), rule="L-21",
              needles=("F-999", "A-02-01"))


def _n22(c):
    c["jp"]["freeze_windows"].append({"name": "年末年始", "start": "2028-12-29", "end": "2029-01-03"})
    c["schedule"]["go_live"] = "2028-12-30"


def n22():
    _cfg_case("N-22", "冻结窗口冲突（上线日在年末年始）", _n22, rule="R1", needles=("M-GL", "年末年始"), tool="cal")


def n23():
    def mutate(c):
        # 2028-05-15（周一）与 2028-05-19（周五）之间严格相隔 16/17/18 三个工作日
        c["schedule"]["milestones"][1]["date"] = "2028-05-19"
    _cfg_case("N-23", "审批缓冲不足（相邻承认节点间隔 3 工作日）", mutate, rule="R2", needles=("缺 7 天", "间隔 3 个工作日"), tool="cal")


def n24():
    kit = copy_kit("N-24")
    ref = kit / "references" / "sccm-deployment.md"
    ref.write_text(ref.read_text(encoding="utf-8") + "\n本手册基于 Windows Server 2022 验证。\n", encoding="utf-8")
    cfg = kit / "examples" / A / "project.yaml"
    build, r, lint, _c = pipeline(cfg, "N-24", kit=kit)
    record("N-24", "负例", "references 中出现硬编码版本号",
           [("lint 退出码 1", lint[0] == 1), ("静态扫描规则 S-01 告警并阻断", "S-01 [阻断]" in lint[1]),
            ("指出文件与行", "references/sccm-deployment.md:第" in lint[1]), ("指出命中值 2022", "2022" in lint[1])],
           _excerpt(lint[1], "S-01"))


def n25():
    cfg = load(A)
    cfg["project"]["project_type"] = "network"
    path = dump(cfg, "N-25")
    rc, out = run("render.py", "--config", path, "--out", C.work / "N-25" / "build")
    record("N-25", "负例", "schema 不符（project_type: network）",
           [("render 退出码 2", rc == 2), ("schema 校验失败", "schema 校验失败" in out), ("提示仅支持三类", "仅支持三类" in out)], out)


def run_all() -> None:
    for fn in (n01, n02, n03, n04, n05, n06, n07, n08, n09, n10, n11, n12, n13, n14, n15, n16, n17, n18, n19, n20,
               n21, n22, n23, n24, n25):
        fn()
