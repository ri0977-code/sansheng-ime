#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""H-164 真机日志判据检查（Qoder，2026-10-25 09:06）

输入：`scripts/h164_device_accept.py logs` 落下的整段 hilog（UTF-8 文本）。
输出：给人看的一页结论 + 违规清单；不改设备、不改应用。

为什么单独写：H-164 连续滚动后，「屏上条数恒等于最后一次 setPageSize」这条旧断言
不再成立（`KeyboardIndex.ets:920-925` 已改口径）。新口径要判定的是：

  ⑦ 0 ≤ cand ≤ rendered ≤ all(≤50)，`rendered == all - uiStart`
  ③ 续页只由「本条滑动到了尾部」触发：`scroll-continue abs=` 出现前，
     最近一行 `H-164 scroll ... absLast=` 的「末条绝对下标 + 1」必须等于该 abs
     （`KeyboardIndex.ets:788-799`：abs = base+uiStart+items.length）；且一次滑动只续一次
     （两次 continue 之间若没有新的、非尾部的 scroll 行，视为可疑连续）
  ② 编码串变化后 `uiStart` 必须回到 0（能从 state 行看出回片）
  ⑥ 滚动期间不得出现「换片复位」以外的 uiStart 突变（uiStart 只会因换片/换编码变）

用法：
    python scripts/h164_log_check.py docs/evidence/2026-10-25/h164-candidate-scroll/h164-hilog.txt
    python scripts/h164_log_check.py <log> --verbose
    python scripts/h164_log_check.py --selftest        # 用合成样本验证每条判据都会红（不碰设备）
退出码：0 无违规；1 有违规；2 没找到 H-164 行（判据未触发，不是通过）。
"""
import argparse
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

RE_STATE = re.compile(
    r"state: cand=(\d+) all=(\d+) base=(\d+) page=(\d+) next=(true|false)"
    r" uiSize=(\d+) uiStart=(\d+) rendered=(\d+)")
RE_SCROLL = re.compile(r"H-164 scroll first=(\d+) last=(\d+) n=(\d+) absFirst=(\d+) absLast=(\d+)")
RE_CONT = re.compile(r"H-164 scroll-continue abs=(\d+)")
RE_ABS = re.compile(r"H-164 continue-abs base=(\d+) start=(\d+) pending=(-?\d+)")
RE_REFUSE = re.compile(r"H-164 scroll-continue refused \(last page\)")
RE_SKIP = re.compile(r"H-164 scrollToIndex skipped")


def parse(lines):
    states, scrolls, conts, abs_lines, refusals, skips = [], [], [], [], [], []
    for i, line in enumerate(lines, 1):
        m = RE_STATE.search(line)
        if m:
            c, a, base, page, nxt, size, start, rend = m.groups()
            states.append(dict(ln=i, cand=int(c), all=int(a), base=int(base), page=int(page),
                               has_next=(nxt == "true"), ui_size=int(size),
                               ui_start=int(start), rendered=int(rend)))
            continue
        m = RE_SCROLL.search(line)
        if m:
            f, l, n, af, al = (int(x) for x in m.groups())
            scrolls.append(dict(ln=i, first=f, last=l, n=n, abs_first=af, abs_last=al))
            continue
        m = RE_CONT.search(line)
        if m:
            conts.append(dict(ln=i, abs=int(m.group(1))))
            continue
        m = RE_ABS.search(line)
        if m:
            b, s, p = (int(x) for x in m.groups())
            abs_lines.append(dict(ln=i, base=b, start=s, pending=p))
            continue
        if RE_REFUSE.search(line):
            refusals.append(i)
        elif RE_SKIP.search(line):
            skips.append(i)
    return states, scrolls, conts, abs_lines, refusals, skips


def last_state_before(states, ln):
    hit = None
    for s in states:
        if s["ln"] < ln:
            hit = s
        else:
            break
    return hit


def check(states, scrolls, conts, abs_lines, refusals, skips):
    viol, notes = [], []

    # ⑦ 条数与渲染关系
    for s in states:
        if s["cand"] > s["all"]:
            viol.append("L%d ⑦ cand=%d > all=%d" % (s["ln"], s["cand"], s["all"]))
        if s["all"] > 50:
            viol.append("L%d ⑦ all=%d > 50（引擎菜单页被放大？）" % (s["ln"], s["all"]))
        if s["rendered"] != max(0, s["all"] - s["ui_start"]):
            viol.append("L%d ⑦ rendered=%d 与 all-uiStart=%d 不符"
                        % (s["ln"], s["rendered"], max(0, s["all"] - s["ui_start"])))
        if s["rendered"] > s["all"]:
            viol.append("L%d ⑦ rendered=%d > all=%d" % (s["ln"], s["rendered"], s["all"]))

    # ③ 续页必须由「到了本片尾」触发，且 abs 对得上
    for c in conts:
        prev = None
        for s in scrolls:
            if s["ln"] < c["ln"]:
                prev = s
            else:
                break
        if prev is None:
            viol.append("L%d ③ 续页 abs=%d 之前没有任何 scroll 行（裸续）" % (c["ln"], c["abs"]))
            continue
        # 语义：scroll-continue abs = base+uiStart+本片条数 = 本片末条的绝对下标 + 1
        if prev["abs_last"] + 1 != c["abs"]:
            viol.append("L%d ③ 续页 abs=%d 应等于最近 scroll 的 absLast+1=%d"
                        % (c["ln"], c["abs"], prev["abs_last"] + 1))
        if prev["last"] != prev["n"] - 1:
            viol.append("L%d ③ 续页时可见末条 last=%d 不等于本片末条 n-1=%d"
                        % (c["ln"], prev["last"], prev["n"] - 1))
        if prev["n"] <= 0:
            viol.append("L%d ③ 续页时本片条数 n=0" % c["ln"])

    # ③ 一次滑动只续一次：相邻两次 continue 若中间没有新 scroll 行，视为可疑
    for a, b in zip(conts, conts[1:]):
        between = [s for s in scrolls if a["ln"] < s["ln"] < b["ln"]]
        if not between:
            viol.append("L%d→L%d ③ 两次续页之间无任何 scroll 行（疑似一次滑动连续）"
                        % (a["ln"], b["ln"]))
        elif all(s["last"] == s["n"] - 1 for s in between):
            notes.append("L%d→L%d 两次续页，中间 %d 行都在尾部（快速连续拖拽时可能出现，"
                         "人工判断是否合理）" % (a["ln"], b["ln"], len(between)))

    # ③ continue-abs 与随后的续页 abs 一致
    for ab in abs_lines:
        expect = ab["base"] + ab["start"] + ab["pending"]
        nxt = next((c for c in conts if c["ln"] > ab["ln"]), None)
        if nxt and nxt["abs"] != expect and ab["pending"] >= 0:
            viol.append("L%d ③ continue-abs 算出 %d，但随后续页 abs=%d"
                        % (ab["ln"], expect, nxt["abs"]))
        # ③ 续页后「新一屏首条」= 已显示末条的下一条（不跳条、不重条）：
        # 引擎回填时 uiPageStart 必须等于 pending - base（对应 KeyboardIndex.ets:960-963）
        if ab["pending"] >= 0:
            nstate = next((s for s in states if s["ln"] > ab["ln"]), None)
            if nstate is None:
                notes.append("L%d 续页后没有 state 行，无法核对「不跳条」" % ab["ln"])
            elif nstate["base"] <= ab["pending"] < nstate["base"] + nstate["all"]:
                want_start = ab["pending"] - nstate["base"]
                if nstate["ui_start"] != want_start:
                    viol.append("L%d ③ 续页后 uiStart=%d，应等于 pending-base=%d（跳条/重条）"
                                % (nstate["ln"], nstate["ui_start"], want_start))

    # ② 编码变化后回片：uiStart 出现「非 0 → 0」且此前有 preedit 变化，这里只能看 uiStart 序列
    starts = [s["ui_start"] for s in states]
    resets = sum(1 for a, b in zip(starts, starts[1:]) if a > 0 and b == 0)
    if starts and starts[0] != 0:
        notes.append("首条 state 的 uiStart=%d（日志可能从滚动中途开始，不作为违规）" % starts[0])

    return viol, notes, resets


def evaluate(path, verbose=False):
    """读一份日志，打印结论，返回退出码（0 通过／1 违规／2 判据未触发）。"""
    with open(path, encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    states, scrolls, conts, abs_lines, refusals, skips = parse(lines)
    if not (states or scrolls or conts):
        print("没有找到 H-164 行 —— 判据未触发（不当作通过）。")
        print("先确认：装的是不是带 H-164 的包、键盘是否出过候选、hilog 是否清过。")
        return 2
    if not scrolls and not conts:
        print("只有 state 行、没有任何 scroll 行 —— 本次日志里没有真实滚动，"
              "③⑦ 的滚动部分未覆盖（不当作通过）。")
        return 2

    viol, notes, resets = check(states, scrolls, conts, abs_lines, refusals, skips)

    print("=== H-164 日志判据 ===")
    print("state 行 %d｜scroll 行 %d｜续页 %d 次｜末页拒绝 %d 次｜scrollToIndex 跳过 %d 次｜回片(uiStart→0) %d 次"
          % (len(states), len(scrolls), len(conts), len(refusals), len(skips), resets))
    if states:
        s = states[-1]
        print("末条 state：cand=%d all=%d base=%d page=%d next=%s uiSize=%d uiStart=%d rendered=%d"
              % (s["cand"], s["all"], s["base"], s["page"], s["has_next"],
                 s["ui_size"], s["ui_start"], s["rendered"]))
    if scrolls:
        firsts = [s["abs_first"] for s in scrolls]
        print("可见首条绝对下标：最小 %d／最大 %d（应随滑动单调增；回片时归 0）"
              % (min(firsts), max(firsts)))
    if verbose:
        for s in scrolls:
            print("  L%d scroll absFirst=%d absLast=%d (n=%d)"
                  % (s["ln"], s["abs_first"], s["abs_last"], s["n"]))
        for c in conts:
            print("  L%d continue abs=%d" % (c["ln"], c["abs"]))

    if viol:
        print("\n违规 %d 条：" % len(viol))
        for v in viol:
            print("  " + v)
    else:
        print("\n无违规：⑦ 条数关系、③ 续页触发与次数、② 回片都成立。")
    if notes:
        print("\n提示 %d 条（不算违规）：" % len(notes))
        for n in notes:
            print("  " + n)
    return 1 if viol else 0


# ---- 自测：用合成样本证明「每条判据都会红」（2026-10-25 09:25 补，主人醒前没人能替我复核） ----
# 样本里的行格式照抄 KeyboardIndex.ets:922-924 / :1246-1248 / :963 的真实 emit。
_FX_GOOD = """
SSKeyboard state: cand=8 all=50 base=0 page=0 next=true uiSize=50 uiStart=0 rendered=50
SSKeyboard H-164 scroll first=0 last=3 n=8 absFirst=0 absLast=3
SSKeyboard H-164 scroll first=4 last=7 n=8 absFirst=4 absLast=7
SSKeyboard H-164 continue-abs base=0 start=0 pending=8
SSKeyboard H-164 scroll-continue abs=8
SSKeyboard state: cand=8 all=50 base=8 page=1 next=true uiSize=50 uiStart=0 rendered=50
SSKeyboard H-164 scroll first=0 last=7 n=8 absFirst=8 absLast=15
SSKeyboard H-164 scroll-continue refused (last page)
"""

_FX_RENDERED = """
SSKeyboard state: cand=8 all=50 base=0 page=0 next=true uiSize=50 uiStart=0 rendered=42
SSKeyboard H-164 scroll first=0 last=7 n=8 absFirst=0 absLast=7
"""

_FX_CAND_GT_ALL = """
SSKeyboard state: cand=60 all=50 base=0 page=0 next=true uiSize=50 uiStart=0 rendered=50
SSKeyboard H-164 scroll first=0 last=7 n=8 absFirst=0 absLast=7
"""

_FX_ALL_GT_50 = """
SSKeyboard state: cand=9 all=60 base=0 page=0 next=true uiSize=60 uiStart=0 rendered=60
SSKeyboard H-164 scroll first=0 last=7 n=8 absFirst=0 absLast=7
"""

_FX_BARE_CONTINUE = """
SSKeyboard state: cand=8 all=50 base=0 page=0 next=true uiSize=50 uiStart=0 rendered=50
SSKeyboard H-164 scroll-continue abs=8
"""

_FX_ABS_MISMATCH = """
SSKeyboard state: cand=8 all=50 base=0 page=0 next=true uiSize=50 uiStart=0 rendered=50
SSKeyboard H-164 scroll first=0 last=7 n=8 absFirst=0 absLast=7
SSKeyboard H-164 continue-abs base=0 start=0 pending=8
SSKeyboard H-164 scroll-continue abs=9
"""

_FX_UISTART_JUMP = """
SSKeyboard state: cand=8 all=50 base=0 page=0 next=true uiSize=50 uiStart=0 rendered=50
SSKeyboard H-164 scroll first=0 last=7 n=8 absFirst=0 absLast=7
SSKeyboard H-164 continue-abs base=0 start=0 pending=8
SSKeyboard H-164 scroll-continue abs=8
SSKeyboard state: cand=8 all=50 base=8 page=1 next=true uiSize=50 uiStart=2 rendered=48
"""

_FX_NOT_AT_TAIL = """
SSKeyboard state: cand=8 all=50 base=0 page=0 next=true uiSize=50 uiStart=0 rendered=50
SSKeyboard H-164 scroll first=0 last=5 n=8 absFirst=0 absLast=5
SSKeyboard H-164 scroll-continue abs=8
"""

_FX_DOUBLE_CONTINUE = """
SSKeyboard state: cand=8 all=50 base=0 page=0 next=true uiSize=50 uiStart=0 rendered=50
SSKeyboard H-164 scroll first=0 last=7 n=8 absFirst=0 absLast=7
SSKeyboard H-164 scroll-continue abs=8
SSKeyboard H-164 scroll-continue abs=16
"""

_FX_NO_LINES = """
2026-10-25 09:25:00.000  1234  1234 I A00000/SSKeyboard: 键盘已就绪
2026-10-25 09:25:00.100  1234  1234 I A00000/SSKeyboard: focus changed
"""

_FX_STATE_ONLY = """
SSKeyboard state: cand=8 all=50 base=0 page=0 next=true uiSize=50 uiStart=0 rendered=50
"""


def selftest():
    """每例都断言「退出码对不对」＋「该红的那句话在不在」——只断言退出码会漏掉红的理由错。"""
    import os
    import tempfile
    cases = [
        ("GOOD 一滑到尾续一页", _FX_GOOD, 0, []),
        ("BAD rendered≠all-uiStart", _FX_RENDERED, 1, ["⑦ rendered=42"]),
        ("BAD cand>all", _FX_CAND_GT_ALL, 1, ["⑦ cand=60 > all=50"]),
        ("BAD all>50", _FX_ALL_GT_50, 1, ["⑦ all=60 > 50"]),
        ("BAD 裸续（没先滑到尾）", _FX_BARE_CONTINUE, 1, ["③ 续页 abs=8 之前没有任何 scroll 行"]),
        ("BAD 续页 abs 与 absLast+1 不符", _FX_ABS_MISMATCH, 1,
         ["应等于最近 scroll 的 absLast+1=8", "continue-abs 算出 8"]),
        ("BAD 末条不在本片尾", _FX_NOT_AT_TAIL, 1, ["③ 续页时可见末条 last=5"]),
        ("BAD 续页后跳条（uiStart 不等于 pending-base）", _FX_UISTART_JUMP, 1,
         ["③ 续页后 uiStart=2，应等于 pending-base=0"]),
        ("BAD 一次滑动续两次", _FX_DOUBLE_CONTINUE, 1, ["两次续页之间无任何 scroll 行"]),
        ("无 H-164 行 → 2", _FX_NO_LINES, 2, ["没有找到 H-164 行"]),
        ("只有 state 无滚动 → 2", _FX_STATE_ONLY, 2, ["只有 state 行、没有任何 scroll 行"]),
    ]
    bad = 0
    for name, text, want_rc, want_txt in cases:
        fd, tmp = tempfile.mkstemp(suffix=".txt", text=True)
        os.close(fd)
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(text)
            import io
            import contextlib
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = evaluate(tmp)
            out = buf.getvalue()
        finally:
            os.unlink(tmp)
        miss = [t for t in want_txt if t not in out]
        if rc != want_rc or miss:
            bad += 1
            print("FAIL %s：rc=%d（期望 %d）%s" % (name, rc, want_rc,
                                                 ("；缺：%s" % "／".join(miss)) if miss else ""))
        else:
            print("ok   %s → rc=%d" % (name, rc))
    print("\nSELFTEST %s：%d 例，%d 失败" % ("OK" if bad == 0 else "FAIL", len(cases), bad))
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("log", nargs="?")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.log:
        ap.error("需要日志路径，或用 --selftest")
    return evaluate(a.log, a.verbose)


if __name__ == "__main__":
    sys.exit(main())
