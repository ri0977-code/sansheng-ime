#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""H-165 候选栏高度预算闸门（Qoder，2026-10-25 14:5x）。

为什么需要这个闸门：H-165 形态 B 第一版在离线套件全绿的情况下装到 Mate80，真机实测把
候选行顶到主键区——候选字被 q 行键帽盖住、右侧「展开网格」的 ▼ 被键面遮住点不到，
H-164/H-168 的真机判据当场跑不了。根因是纯几何：

    CandidateBar 外层 Column 高度恒为 candBarHeight()（竖屏 44vp），
    而 44vp 已被 L1(commentRowHeight=16) + 候选行(candRowHeight=28) 占满；
    面板实测 983px = 候选栏 152 + 键区 665 + 底栏 160，整屏零余量
    （keyH() 定高，QwertyPanel 的 layoutWeight 只会把底栏顶出面板）。
    往那个 Column 里再加一行，无论多高都会溢出到主键区。

现有 18 项内容闸门 / 收口五件 / 图标几何都只查打包产物，看不见这条几何不变式，
所以把它落成静态闸门：解析 KeyboardIndex.ets 的 CandidateBar()，把「行级」.height()
连同各自的 if 守卫收集起来，枚举互斥守卫的所有同时可见组合，
断言每种组合下的高度之和 <= candBarHeight()。

用法：
    python scripts/h165_bar_height_check.py             # 跑源码；溢出即 exit 1
    python scripts/h165_bar_height_check.py --selftest   # 已知坏样本（H-165 第一版）必须变红
"""
import argparse
import math
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "entry", "src", "main", "ets", "pages", "KeyboardIndex.ets")

BAR_HEIGHT_PORTRAIT = 44    # @State barHeight 默认值（宿主竖屏设的同值）
BAR_HEIGHT_LANDSCAPE = 30   # 横屏示例值：barHeight<40 即走 H-096 压缩分支
CAND_FS_TIERS = (18, 20)    # H-077 ③：recomputePageSize 的字号档位
BASE_DEPTH = 1              # CandidateBar 体内第一行是 `Column() {` ⇒ 直接子节点在深度 1

CONST_RE = re.compile(r"^const\s+([A-Z_][A-Z0-9_]*)\s*:\s*number\s*=\s*([0-9.]+)\s*;", re.M)
IF_OPEN_RE = re.compile(r"^if\s*\((.*)\)\s*\{$")
# 一行一条链式属性，`.height(` 后到行尾最后一个 `)` 即参数（里面有 this.xxx() 的嵌套括号）
HEIGHT_RE = re.compile(r"\.height\((.*)\)\s*$")
# `.visibility(this.X ? Visibility.None : Visibility.Visible)` 语义上等价于该行的守卫 `!this.X`
VIS_RE = re.compile(r"\.visibility\(\s*this\.([A-Za-z_][A-Za-z0-9_]*)\s*\?\s*"
                    r"Visibility\.(None|Visible)\s*:\s*Visibility\.(None|Visible)\s*\)\s*$")


def comment_row_height():
    return 16


def cand_row_height(fs):
    return max(28, int(math.ceil(fs * 1.2 + 6)))


def cand_bar_height(world):
    """与 ArkTS candBarHeight() 同构（H-165 返工后；H-203 加空闲态分支）。

    横屏原样返回压缩值（H-096 的 24 vs 行高 28 差 4vp 是遗留，只 WARN 不阻断）；
    竖屏空闲态（无 preedit、无候选）返回单行候选行高（安卓窄条，H-203）；
    其余取 max(barHeight, L1 + 候选行)。
    这里刻意照抄 ArkTS 的推导式，而不是「理想预算」——谁往 CandidateBar 里新加一行、
    却没把高度加进这条推导式，本闸门就会红（--selftest 用 H-165 第一版的真实溢出布局证明有牙）。
    """
    if world["barHeight"] < 40:
        return max(24, world["barHeight"] - 6)
    if (not world["showFuncBar"]) and world["preeditLen"] == 0 and world["candLen"] == 0:
        return cand_row_height(world["candFs"])
    return max(world["barHeight"], comment_row_height() + cand_row_height(world["candFs"]))


def extract_body(text, marker):
    """取 `marker {` 到配平右括号之间的函数体。"""
    i = text.index(marker)
    j = text.index("{", i)
    depth = 0
    for k in range(j, len(text)):
        if text[k] == "{":
            depth += 1
        elif text[k] == "}":
            depth -= 1
            if depth == 0:
                return text[j + 1:k]
    raise SystemExit("括号不配平：%s" % marker)


def strip_comment(line):
    i = line.find("//")
    return line[:i] if i >= 0 else line


def scan_heights(body):
    """返回 (rows, container)。

    rows       = [([守卫...], height 表达式, 行号)] —— 候选栏里的「一行」。
    container  = [(height 表达式, 行号)]        —— 外层 Column 自己的高度（＝预算本身，不参与求和）。

    body 是 `CandidateBar() { ... }` 的函数体，第一行就是 `Column() {`，
    所以候选栏的直接子节点在 depth = BASE_DEPTH(=1)；每个 `if (...) {` 再多占一层。
    守卫 = 生效的 `if (...)` 条件链 + 由同行属性链上 `.visibility(this.X ? None : Visible)`
    推出的 `!this.X`（Visibility.None 不占布局高度，语义上就是这一行的隐藏守卫）。
    分级必须在扫描时就定：派生守卫是事后追加的，不能拿它反推层级。
    """
    rows = []
    container = []
    guards = []      # [(cond, open_depth)]
    depth = 0
    open_item = None
    open_depth = -1
    for lineno, raw in enumerate(body.splitlines(), start=1):
        line = strip_comment(raw)
        s = line.strip()
        row_level = depth == BASE_DEPTH + len(guards)
        if open_item is not None and depth != open_depth:
            open_item = None
        if open_item is not None and s.startswith("."):
            mv = VIS_RE.search(s)
            if mv:
                first, second = mv.group(2), mv.group(3)
                if (first, second) == ("None", "Visible"):
                    open_item[0].append("!this." + mv.group(1))
                elif (first, second) == ("Visible", "None"):
                    open_item[0].append("this." + mv.group(1))
        mi = IF_OPEN_RE.match(s)
        if mi and row_level:
            guards.append((mi.group(1), depth))
            depth += line.count("{") - line.count("}")
            while guards and depth <= guards[-1][1]:
                guards.pop()
            continue
        mh = HEIGHT_RE.search(s)
        if mh and row_level:
            item = ([c for c, _ in guards], mh.group(1).strip(), lineno)
            rows.append(item)
            open_item = item
            open_depth = depth
        elif mh and depth == 0:
            container.append((mh.group(1).strip(), lineno))
        depth += line.count("{") - line.count("}")
        if depth < 0:
            depth = 0
        while guards and depth <= guards[-1][1]:
            guards.pop()
    return rows, container


def guard_holds(cond, world):
    """守卫求值：只认 world 里有的布尔量（showFuncBar）与 barHeight 阈值；
    认不出的原子式一律按「可能为真」保守计入（宁可多算一行，不许漏算）。"""
    for atom in re.split(r"&&", cond):
        a = atom.strip().replace(" ", "")
        if not a:
            continue
        m = re.match(r"^(!?)this\.([A-Za-z_][A-Za-z0-9_]*)$", a)
        if m:
            neg, var = m.group(1) == "!", m.group(2)
            if var in world:
                if bool(world[var]) == neg:
                    return False
                continue
            continue          # 不认识的布尔量：保守按真
        m = re.match(r"^this\.barHeight(>=|<=|>|<|==)(\d+)$", a)
        if m:
            v = int(m.group(2))
            bh = world["barHeight"]
            ok = {">": bh > v, ">=": bh >= v, "<": bh < v, "<=": bh <= v, "==": bh == v}[m.group(1)]
            if not ok:
                return False
            continue
        # H-203：L1 的「有 preedit 才渲染」守卫——按世界里的 preeditLen 求值，
        # 否则空闲态会把空 L1 也计入，闸门对 H-203 的新预算假红。
        m = re.match(r"^this\.preedit\.length(>=|<=|>|<|===|==)(\d+)$", a)
        if m:
            v = int(m.group(2))
            ln = world["preeditLen"]
            eq = world["preeditLen"] == v
            ok = {">": ln > v, ">=": ln >= v, "<": ln < v, "<=": ln <= v,
                  "===": eq, "==": eq}[m.group(1)]
            if not ok:
                return False
            continue
        m = re.match(r"^this\.candidates\.length(>=|<=|>|<|===|==)(\d+)$", a)
        if m:
            v = int(m.group(2))
            ln = world["candLen"]
            eq = world["candLen"] == v
            ok = {">": ln > v, ">=": ln >= v, "<": ln < v, "<=": ln <= v,
                  "===": eq, "==": eq}[m.group(1)]
            if not ok:
                return False
            continue
        # 其余（this.showFuncBar 以外不认识的布尔量）保守按真
    return True


def resolve(expr, consts, world):
    e = expr.strip()
    if e.startswith("this.candBarHeight()"):
        return cand_bar_height(world)
    if e.startswith("this.commentRowHeight()"):
        return comment_row_height()
    if e.startswith("this.candRowHeight()"):
        return cand_row_height(world["candFs"])
    if e.startswith("this.rowHeight"):
        return 48
    m = re.match(r"^([A-Z_][A-Z0-9_]*)$", e)
    if m and m.group(1) in consts:
        return int(consts[m.group(1)])
    if re.match(r"^-?[0-9.]+$", e):
        return int(float(e))
    return None


def child_box_fail(text):
    """H-179：FuncIcon 的图标盒高度**必须跟着 candBarHeight() 收缩**，不能写死常量。

    为什么单独查这一处：行级 `.height()` 只扫 CandidateBar 的直接子节点，图标盒是行内**子节点**，
    写死 36vp 时竖屏 44vp 栏装得下、横屏 24vp 栏就溢出 12vp 压到键面（H-170 ① 同类）。
    2026-10-26 就是这么写死过一次，行级闸门全绿——因为它在行里面。
    """
    try:
        body = extract_body(text, "FuncIcon(action: string) {")
    except ValueError:
        return ["FuncIcon(action: string) { 找不到——闸门没法确认图标盒高度（绝不许静默通过）"]
    bad = []
    for m in re.finditer(r"\.height\(([^()]*(?:\([^()]*\)[^()]*)*)\)", body):
        expr = m.group(1).strip()
        line = body[:m.start()].count("\n") + 1
        ok = "candBarHeight" in expr
        # 允许经由一层自定义方法间接取：`.height(this.funcIconBox())` 只要该方法体里含 candBarHeight
        for fn in re.findall(r"this\.(\w+)\(\)", expr):
            try:
                impl = extract_body(text, "private %s(" % fn)
            except ValueError:
                impl = ""
            if "candBarHeight" in impl:
                ok = True
        if not ok:
            bad.append("FuncIcon 内第 %d 行 .height(%s) 写死高度，横屏栏只有 24vp 会溢出压键" % (line, expr))
    return bad


def check(text):
    consts = {k: float(v) for k, v in CONST_RE.findall(text)}
    body = extract_body(text, "CandidateBar() {")
    heights = scan_heights(body)
    rows, container = heights
    worlds = []
    for show in (False, True):
        for bh in (BAR_HEIGHT_PORTRAIT, BAR_HEIGHT_LANDSCAPE):
            for fs in CAND_FS_TIERS:
                # H-203：空闲态（0/0）与打字态（3/5）都要枚举——空闲预算只有一行，
                # 少了这一维闸门就看不见「空闲态被 L1 撑高」这类回退。
                for preedit_len, cand_len in ((0, 0), (3, 5)):
                    worlds.append({"showFuncBar": show, "barHeight": bh, "candFs": fs,
                                   "preeditLen": preedit_len, "candLen": cand_len})
    out = []
    for world in worlds:
        budget = cand_bar_height(world)
        total = 0
        parts = []
        whole_bar_rows = 0
        other_rows = 0
        for guards, expr, lineno in rows:
            if not all(guard_holds(g, world) for g in guards):
                continue
            h = resolve(expr, consts, world)
            if h is None:
                parts.append("L%d %s=?" % (lineno, expr))
                continue
            if "candBarHeight" in expr:
                # 按整栏高自撑的行：自己不超预算，但与其它行同时可见就是双算
                whole_bar_rows += 1
                parts.append("L%d 整栏行=%d" % (lineno, h))
                total = max(total, h)
                continue
            other_rows += 1
            parts.append("L%d %s=%d" % (lineno, expr, h))
            total += h
        reason = ""
        if whole_bar_rows and other_rows:
            reason = "整栏行与 L1/候选行同时可见 = 双算，必然溢出"
            total = max(total, budget + 1)
        out.append((world, budget, total, " + ".join(parts) or "(无固定高的行)", reason))
    return out, rows, container


# 已知坏样本 = H-165 第一版：独立 20vp 三角行 + 34vp 磁贴行，与 L1/候选行同挤在 44vp 容器里。
# 锚点取「展开工具栏那个 if 的 if 行」，**不绑定 space 数字、注释文字或紧随其后的分支**——
# 2026-10-25 16:2x 我把 `space: 6` 改成 `space: 4` 并加了注释，旧锚点就失配；
# 2026-10-26 H-194 又在 if 后面插了 cursor/clipboard 子面板分支，锚到「第一行 Row」再次失配。
# 现在只认 `if (this.showFuncBar) {` 这一行本身，在 CandidateBar 体内找第一处。
BAD_OLD_RE = re.compile(r"( +)if \(this\.showFuncBar\) \{\n")
BAD_NEW_TPL = (
    "{ind}if (this.showFuncBar) {{\n"
    "{ind}  Row() {{\n{ind}    Text('>')\n{ind}  }}\n"
    "{ind}  .height(FUNC_TRI_HEIGHT)\n"
    "{ind}  Row({{ space: 6 }}) {{\n{ind}    Text('x')\n{ind}  }}\n"
    "{ind}  .height(FUNC_TILE_ROW_HEIGHT)\n"
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true", help="已知坏样本必须变红")
    args = ap.parse_args()
    text = open(SRC, encoding="utf-8").read()

    if args.selftest:
        # 只在 CandidateBar 体内找锚点：文件里别处也可能有 `if (this.showFuncBar)`。
        try:
            cb_start = text.index("CandidateBar() {")
        except ValueError:
            cb_start = 0
        m = BAD_OLD_RE.search(text, cb_start)
        if not m:
            print("SELFTEST FAIL: CandidateBar 里找不到「if (this.showFuncBar) {」锚点，"
                  "坏样本造不出来（绝不许静默通过）")
            return 1
        patched = text[:m.start()] + BAD_NEW_TPL.format(ind=m.group(1)) + text[m.end():]
        if patched == text:
            print("SELFTEST FAIL: 替换没生效，坏样本根本没造出来（绝不许静默通过）")
            return 1
        patched = patched.replace("const FUNC_TRI_WIDTH: number = 36;",
                                  "const FUNC_TRI_WIDTH: number = 36;\nconst FUNC_TRI_HEIGHT: number = 20;\n"
                                  "const FUNC_TILE_ROW_HEIGHT: number = 34;", 1)
        res, _, _ = check(patched)
        bad = [r for r in res if r[2] > r[1] and r[0]["barHeight"] >= 40]
        if not bad:
            print("SELFTEST FAIL: 已知坏样本（H-165 第一版溢出布局）被判绿 = 闸门无效")
            return 1
        # 负控②：图标盒写死高度的坏样本也必须被抓住（H-179 真踩过的那个）
        hard = text.replace(".height(this.funcIconBox())", ".height(FUNC_ICON_SIZE + 16)", 1)
        if hard == text or not child_box_fail(hard):
            print("SELFTEST FAIL: 「FuncIcon 盒高写死」的坏样本没被抓住（负控②失效）")
            return 1
        worst = max(bad, key=lambda r: r[2] - r[1])
        print("SELFTEST OK: 已知坏样本变红（竖屏 %d 种世界溢出，最狠 预算 %dvp 实占 %dvp；"
              "负控②「图标盒写死」也变红）"
              % (len(bad), worst[1], worst[2]))
        return 0

    res, rows, container = check(text)
    print("H-165 候选栏高度预算：CandidateBar 行级固定高度之和 <= candBarHeight()")
    print("  容器自身 .height()：%s" %
          ("、".join("L%d %s" % (c[1], c[0]) for c in container) or "没扫到（异常）"))
    print("  行级 .height()：%d 处 —— %s" % (len(rows), "、".join("L%d %s" % (r[2], r[1]) for r in rows)))
    nbad = 0
    nwarn = 0
    for world, budget, total, parts, reason in res:
        portrait = world["barHeight"] >= 40
        ok = total <= budget
        if not ok:
            if portrait:
                nbad += 1
            else:
                nwarn += 1
        print("  [%-4s] showFuncBar=%-5s barHeight=%-3d candFs=%-3d 预算 %2dvp 实占 %2dvp  %s%s" %
              ("绿" if ok else ("红" if portrait else "WARN"),
               world["showFuncBar"], world["barHeight"], world["candFs"], budget, total, parts,
               "" if ok else "  => 溢出 %dvp%s" % (total - budget, ("：" + reason) if reason else "")))
    if nbad:
        print("\nFAIL: 竖屏 %d 种组合同时可见的行高之和超出候选栏预算 => 溢出压到主键区"
              "（H-165 真机缺陷 ① 的同类：候选行/展开键会被键帽盖住、吃掉点击）" % nbad)
        return 1
    box_bad = child_box_fail(text)
    for b in box_bad:
        print("  [红   ] %s" % b)
    if box_bad:
        print("\nFAIL: 工具栏图标盒高度没跟着栏高收缩（H-179 同类，横屏会压键）")
        return 1
    print("\nPASS: 竖屏 %d 种组合全部不溢出"
          "（收起态三角内联 = 0 额外高度；展开态 L1/候选行让位 = 磁贴行独占整栏预算）"
          % len([r for r in res if r[0]["barHeight"] >= 40]))
    if nwarn:
        gap = max(total - budget for world, budget, total, _, _ in res
                  if world["barHeight"] < 40 and total > budget)
        print("  WARN（不阻断）：横屏 %d 种组合差 %dvp —— H-096 遗留（横屏 L1 本就隐藏、"
              "预算 max(24, bar-6) 比候选行 28vp 少 4vp）。横屏判据 H-164 ⑨ 还挂在主人那儿没验过，"
              "不在没验过的屏幕上动几何；已记 docs/ISSUES.md。" % (nwarn, gap))
    return 0


if __name__ == "__main__":
    sys.exit(main())
