#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""信箱状态词闸门（Qoder，2026-10-26 H-185）

为什么要有它（真事故，不是假想）：
  M-214~M-218 五条派单，状态格我写成了「已发 CodeArts 收」而不是 `OPEN`。
  `scripts/mail_open.py` 的判据是**状态格精确等于 OPEN** ⇒ 巡检一直报「无 OPEN」，
  五条派单在信箱里躺了几小时没人认领。同批还有三条行被正文换行拆碎（行内段数不足），
  任何按行解析的脚本都读不到——两种错法一个后果：**待办对巡检隐形**。

规则（与 `docs/MAILBOX.md` 使用规则 4 一致）：
  · 收件人是 Qoder / CodeArts 的消息行，状态格只能是 `OPEN` / `ACK` / `DONE` / `BLOCKED`；
  · 一行必须是完整表格行（**6 格或 7 格**，状态格从行尾读）：正文不许换行，正文里的竖线
    必须转义成 `\|`（H-225：分段只吃**未被反斜杠转义**的竖线，所以 `\|` 合法、裸 `|`
    会把行顶坏）。6 格＝没写「文件」列，报 WARN 不阻断——列口径统一等主人点头（H-223）。
  历史区（M-190 以前）是混格式时代（6 格/8 格/`SENT（…）`/`CodeArts 未读`），
  迁移是另一件清理活，不在本闸门范围——那批行全部已闭环或被后续消息取代。

用法：
    python scripts/check_mailbox_states.py            # rc=0 通过 / 1 有违规 / 2 用法错
    python scripts/check_mailbox_states.py --selftest # 正负控自测（含「旧区不管」的对照）
"""
import io
import os
import re
import sys
import tempfile

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIL = os.path.join(ROOT, "docs", "MAILBOX.md")

EPOCH = 190                       # 只查 M-190 起（含）的现行消息行
STATUS_OK = {"OPEN", "ACK", "DONE", "BLOCKED"}
# (Qoder H-225) 箭头两种写法都认：现行区实测 11 行（M-244～M-255）把收件格写成 ASCII
# `->`，老判据的子串 `→ CodeArts` 匹配不到 ⇒ 这些行连闸门都看不见。箭头字形不是契约。
ARROW_RE = re.compile(u"(?:→|->)")
NAMES = ("Qoder", "CodeArts")
ID_RE = re.compile(r"^M-(\d+)")


def addressed(cell):
    """第 3 格是不是「<名字> 箭头 <含 Qoder/CodeArts>」——只看箭头右侧。"""
    parts = ARROW_RE.split(cell)
    return len(parts) >= 2 and any(n in parts[-1] for n in NAMES)


def cells_of(ln):
    r"""一行表格 → 格子列表（H-225，Qoder 2026-10-27 16:1x）。

    三件必须记住的事：
      1. **分段只吃未被反斜杠转义的竖线**。信箱里 M-254/M-257/M-264 的正文写了
         符号气泡数据（`z=['|', Z]` 这类），naive `ln.split("|")` 把一行读成 10~11 段
         ⇒ 巡检读不到它们的状态格，正是 H-185 记的「待办对巡检隐形」同一类事故。
         正文里的竖线现在必须写 `\|`。
      2. **状态格从行尾数，不按列号数**。现行 7 格（多一个「文件」列），M-254/M-257/M-264
         修行后实测就是 6 格（没写「文件」列）；列口径统一是 H-223 记的待主人点头的活。
         在统一之前按固定列号解析＝6 格行的状态被判成正文，同样隐形。从行尾取 ⇒
         6 格/7 格都能读到状态，谁也不用改别人的行（缺「文件」列只 WARN，不阻断）。
      3. **首尾空段都要丢**，但只在各自行尾真的带 `|` 时丢——行尾没有 `|` 就是
         「正文里有换行、行被拆成两截」，那本身要报，不能悄悄当 6 格行。
    """
    p = re.split(r"(?<!\\)\|", ln)
    if p and p[0].strip() == "":
        p = p[1:]
    if p and p[-1].strip() == "":
        p = p[:-1]
    return p


def scan_text(text):
    """返回 [(行号, ID, 问题)]；问题串以 `WARN ` 开头的不影响退出码。纯函数，自测喂字符串。"""
    lines = text.split("\n")
    start = 0
    for i, ln in enumerate(lines):
        if ln.strip() == "## 消息表":
            start = i
            break
    out = []
    for i in range(start, len(lines)):
        ln = lines[i].rstrip("\r")
        if not ln.startswith("| M-"):
            continue
        c = cells_of(ln)
        mid = c[0].strip() if c else ""
        m = ID_RE.match(mid)
        if not m or int(m.group(1)) < EPOCH:
            continue                      # 历史区/模板行不在本闸门范围
        if len(c) < 4 or not any(addressed(x) for x in c[:3]):
            continue                      # 不是发给两个 agent 的行（如看门狗「全员」通知）
        if not ln.rstrip().endswith("|"):
            out.append((i + 1, mid, "行尾没有 `|`——正文里有换行，这一行被拆成两截，"
                                    "巡检读不到状态格（要写成一行）"))
            continue
        if len(c) not in (6, 7):
            out.append((i + 1, mid, "行不完整（%d 格，6/7 格行才合法）——正文夹了没转义的裸竖线"
                                   "（要写 \\|）" % len(c)))
            continue
        if len(c) == 6:
            out.append((i + 1, mid, "WARN 只有 6 格（缺「文件」列）；列口径等主人点头（H-223），不阻断"))
        st = c[-1].strip()
        if st not in STATUS_OK:
            out.append((i + 1, mid, "状态格里是 %r；待办必须写 OPEN，处理完写 DONE" % st))
    return out


def blocking(bad):
    """真违规（影响退出码）：串首不是 WARN 的那些。"""
    return [b for b in bad if not b[2].startswith("WARN ")]


def selftest():
    good = "| M-200 | t | Qoder → CodeArts | s | body | f | OPEN |"
    six = r"| M-205 | t | Qoder → CodeArts | s | body | OPEN |"
    legacy = "| M-100 | t | Qoder → CodeArts | s | body | f | SENT（等他交付） |"
    wrong = "| M-201 | t | Qoder → CodeArts | s | body | f | 已发 CodeArts 收 |"
    broken = "| M-202 | t | Qoder → CodeArts | s | body | f |"
    split_row = "| M-207 | t | Qoder → CodeArts | s | body | f"
    # H-225：正文里的竖线必须转义成 \|。正控＝转义行判合规；负控＝同一行写成裸竖线必须报。
    esc = r"| M-203 | t | Qoder → CodeArts | s | 气泡数据 z=['\|', Z] 混输 | f | OPEN |"
    bare = "| M-206 | t | Qoder → CodeArts | s | 气泡数据 z=['|', Z] 混输 | f | OPEN |"
    # H-225：收件格写 ASCII -> 的行必须在闸门眼里（现行区实测 11 行这么写，修前连闸门都看不见）
    ascii_bad = "| M-208 | t | Qoder -> CodeArts | s | body | f | 已发 CodeArts 收 |"
    cases = [
        ("正控：规范 OPEN 行", "## 消息表\n" + good + "\n", 0),
        ("负控①：已发 CodeArts 收（本次事故原样）", "## 消息表\n" + wrong + "\n", 1),
        ("负控②：少一格（正文换行被拆/漏状态）", "## 消息表\n" + broken + "\n", 1),
        ("负控②b：行尾连 `|` 都没有（就是被换行拆半截）", "## 消息表\n" + split_row + "\n", 1),
        ("对照③：历史区 M-100 用旧词不报", "## 消息表\n" + legacy + "\n", 0),
        ("负控④：正确行后面多一格也算坏", "## 消息表\n" + good + " |\n", 1),
        # H-225 两条新控：转义竖线必须被当成合法正文；6 格行必须能读到状态（只 WARN 缺列）
        ("正控⑤：正文里 \\| 转义竖线不顶坏行", "## 消息表\n" + esc + "\n", 0),
        ("负控⑥：同一行把 \\| 写成裸 | ⇒ 行被顶坏必须报", "## 消息表\n" + bare + "\n", 1),
        ("正控⑦：6 格行状态从行尾读得到（只 WARN 缺列，不阻断）", "## 消息表\n" + six + "\n", 0),
        ("负控⑧：6 格行状态词写错照样拦", "## 消息表\n" + six.replace("OPEN", "已发 CodeArts 收") + "\n", 1),
        ("负控⑨：收件格写 ASCII -> 的行也必须被闸门看见（修前整行隐形）",
         "## 消息表\n" + ascii_bad + "\n", 1),
    ]
    bad = 0
    for name, text, want in cases:
        got = len(blocking(scan_text(text)))
        ok = got == want
        print("%s %s（期望 %d 条违规，实得 %d）" % ("SELFTEST OK " if ok else "SELFTEST FAIL",
                                                name, want, got))
        if not ok:
            bad += 1
    print("SELFTEST %s" % ("PASS" if bad == 0 else "FAIL"))
    return 0 if bad == 0 else 1


def main():
    if "--selftest" in sys.argv:
        return selftest()
    if not os.path.exists(MAIL):
        sys.stderr.write("MAILBOX not found: %s\n" % MAIL)
        return 2
    text = io.open(MAIL, encoding="utf-8", newline="").read()
    bad = scan_text(text)
    hard = blocking(bad)
    warn = [b for b in bad if b not in hard]
    if warn:
        print("信箱格式提醒 %d 条（WARN，不计退出码）：" % len(warn))
        for line, mid, why in warn:
            print("  行 %-5d %-12s %s" % (line, mid, why[5:]))
    if not hard:
        print("信箱状态词 OK（M-%d 起的现行消息行状态格全部合规）" % EPOCH)
        return 0
    print("信箱状态词违规 %d 条：" % len(hard))
    for line, mid, why in hard:
        print("  行 %-5d %-12s %s" % (line, mid, why))
    return 1


if __name__ == "__main__":
    sys.exit(main())
