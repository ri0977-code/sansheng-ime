#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""H-279 自造词「干净对照」真机判定（Qoder，2026-10-30）

为什么还要再写一套（`h279_zaozici_device_check.py` / `h279_ab_drive_qoder.py` 都能跑）：
前面两轮的设备复验都有**共同的漏洞**，也是我 09:5x 自己戳穿的：
  1. `tgtf`→「行不行」和 `ttyn`→「自造词」这两个码，离线查表都是**词典里本来就有词的槽位**
     （`ttyn` = 笔记，权重 1670 万；`qqqb` = 多terrible ☯），
     造出来的词只能挤在同一槽位里，「看到了 ☯ 词」无法证明是**这次**造的。
     上一轮我在 expanded 列表第 5 位看到「自造词 ☯」，很可能它是**装机前就在用户词典里**的存量词。
  2. 判据一直是「打完三个字再打合并码，看有没有那个词」，但没有**同码的前后基线**，
     等于没有阴性对照。

本脚本用一条**词典里根本不存在的码** `vxxk`（好 vb / 红 xa / 强 xk ⇒ AaBaCaCb = vxxk，
离线核对：`vxxk` 不是任何词条的码，「好红强」也不是任何词条）做严格前后对照：
  before(打 vxxk，逐页截图) → commit(逐字上屏 好/红/强，读输入框正文) →
  after(再打 vxxk，逐页截图) → diff(before/after 同名页逐像素) →
  restart(aa force-stop 后重开，再打 vxxk，看是否还记住)

关键纪律：
  * before/after 阶段打完码**只看图、按 ⌫ 清码，绝不按空格**——不空格就不上屏，
    不进 commit_history，不触发 Memorize，基线才不会被自己污染。
  * 唯一上屏动作集中在 commit 阶段，且逐字用**整段字根码 + 空格**（vb␠/xa␠/xk␠），
    与主人报的「打 行(tf) 不(gi) 行(tf)」口径一致。
  * 每一步都落 PNG，判定只看图（H-116：dumpLayout 取不到输入法窗口）。

用法：
    python scripts/h279_clean_control_qoder.py before
    python scripts/h279_clean_control_qoder.py commit
    python scripts/h279_clean_control_qoder.py after
    python scripts/h279_clean_control_qoder.py diff
    python scripts/h279_clean_control_qoder.py restart
    python scripts/h279_clean_control_qoder.py all      # before→commit→after→diff（不含 restart）
退出码 0＝动作做完（不代表功能通过）。
"""
from __future__ import annotations

import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import h279_zaozici_device_check as H          # 已验证的 sh/shot/tap/dump_layout
import h279_ab_drive_qoder as D                 # 已实测的键位缓存 + 输入框定位

MERGED = os.environ.get("CC_CODE", "vxxk")       # 合并码；默认 好(vb) 红(xa) 强(xk) ⇒ AaBaCaCb = vxxk
CHUNKS = os.environ.get("CC_CHUNKS", "vb,xa,xk").split(",")
EXPECT = os.environ.get("CC_EXPECT", "好红强")     # 逐字上屏后输入框应有的正文
TAG = os.environ.get("CC_TAG", "cc")              # 证据文件名前缀，换用例时另起前缀，别覆盖上一轮

EXPAND = (1200, 1950)          # 候选条右侧 ⌄（实测：展开候选面板）
NEXT = (665, 2610)             # 展开面板底部「下一页」
COLLAPSE = (1105, 2610)        # 展开面板底部「收起」
BACKSPACE = (1188, 2420)       # 第三行 ⌫

PAGES = int(os.environ.get("CC_PAGES", "6"))      # 逐页截图上界（候选多的码要调大）
EVID = H.EVID


def snap(tag):
    p = H.shot("%s-%s.png" % (TAG, tag))
    print("  shot -> %s" % os.path.basename(p))
    return p


def tap_xy(x, y, note=""):
    H.tap(x, y)
    if note:
        print("  tap %s @ (%d,%d)" % (note, x, y))


def clear_preedit(n):
    """按 ⌫ 清掉当前编码段——不空格，所以上屏历史不变、不产生学习。"""
    for _ in range(n):
        tap_xy(*BACKSPACE, note="⌫")


def capture_pages(prefix, code):
    """打 code → 截收起态 → 展开 → 逐页截 → 收起 → 清码。

    停止条件：screenCap 出来的图和上一页**逐字节相同**＝翻页到底了（面板没变），
    不靠猜页数（硬规则 4）。
    """
    import hashlib
    letters, space = D.load_keymap()
    if not letters:
        print("[FAIL] 没有键位缓存，先跑 h279_ab_drive_qoder.py panel")
        return 2
    for ch in code:
        H.tap(*letters[ch])
    snap("%s-00-%s" % (prefix, code))
    tap_xy(*EXPAND, note="⌄展开")
    prev = None
    done = 0
    for i in range(1, PAGES + 1):
        p = snap("%s-page%d" % (prefix, i))
        digest = hashlib.md5(open(p, "rb").read()).hexdigest()
        done = i
        if digest == prev:
            print("  page%d 与上一页完全相同 ⇒ 判定已到底，多余页删除" % i)
            os.remove(p)
            done = i - 1
            break
        prev = digest
        tap_xy(*NEXT, note="下一页")
    tap_xy(*COLLAPSE, note="收起")
    clear_preedit(len(code))
    f = D.field() or {"text": "?"}
    print("  清码后输入框正文=%r（应为空） 共截 %d 页" % (f.get("text"), done))
    return 0


def cmd_before():
    print("== BEFORE：打 %s，只看不上屏 ==" % MERGED)
    return capture_pages("before", MERGED)


def cmd_commit():
    print("== COMMIT：逐字上屏 %s ==" % EXPECT)
    letters, space = D.load_keymap()
    f0 = D.field() or {"text": ""}
    if (f0.get("text") or "") != "":
        print("[FAIL] 输入框不干净，先手工清空：%r" % f0.get("text"))
        return 2
    for c in CHUNKS:
        for ch in c:
            H.tap(*letters[ch])
        snap("commit-in-%s" % c)
        tap_xy(*space, note="空格上屏")
        snap("commit-out-%s" % c)
    f = D.field() or {"text": "?"}
    txt = (f.get("text") or "")
    print("  输入框正文=%r 期望=%r 命中=%s" % (txt, EXPECT, EXPECT in txt))
    return 0


def cmd_after():
    print("== AFTER：再打 %s ==" % MERGED)
    return capture_pages("after", MERGED)


def cmd_restart():
    print("== RESTART：杀进程重开，看是否仍记得 ==")
    print("  " + (H.sh("shell", "aa", "force-stop", H.BUNDLE) or "(空)").strip())
    print("  残留进程:", (H.sh("shell", "pidof", H.BUNDLE) or "(无)").strip())
    print("  " + H.sh("shell", "aa", "start", "-a", H.ABILITY, "-b", H.BUNDLE).strip())
    time.sleep(3)
    f = D.field()
    if not f:
        print("[FAIL] 找不到「试一试」输入框，页面可能没起来（先跑 pages 看状态）")
        return 2
    tap_xy(f["cx"], f["cy"], "点「试一试」输入框")
    time.sleep(1)
    snap("restart-focus")
    return capture_pages("restart", MERGED)


def cmd_diff():
    """before/after 同名页逐像素比对：不同像素数 > 0 即「候选列表变了」。"""
    from PIL import Image, ImageChops
    print("== DIFF：before-pageN vs after-pageN ==")
    any_diff = False
    for i in range(0, PAGES + 1):
        name = "%s-00-%s" % ("before", MERGED) if i == 0 else "before-page%d" % i
        a = os.path.join(EVID, "%s-%s.png" % (TAG, name))
        b = os.path.join(EVID, "%s-%s.png" % (TAG, name.replace("before", "after")))
        if not (os.path.isfile(a) and os.path.isfile(b)):
            print("  page%-2d 缺图，跳过" % i)
            continue
        ia, ib = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
        d = ImageChops.difference(ia, ib)
        bbox = d.getbbox()
        # 只数候选面板列表区（实测 y 1860..2560）：状态栏时钟、网速、光标闪烁不参与判定
        crop = d.crop((0, 1860, ia.size[0], 2560)) if bbox else None
        n = sum(1 for p in crop.getdata() if p != (0, 0, 0)) if crop else 0
        print("  page%-2d 全图diff_bbox=%s 候选区(y1860-2560)不同像素=%d" % (i, bbox, n))
        if n:
            any_diff = True
    print("结论：候选区%s" % ("有变化" if any_diff else "无变化"))
    return 0


def cmd_all():
    for fn in (cmd_before, cmd_commit, cmd_after, cmd_diff):
        rc = fn()
        if rc:
            return rc
    return 0


CMDS = {"before": cmd_before, "commit": cmd_commit, "after": cmd_after,
        "restart": cmd_restart, "diff": cmd_diff, "all": cmd_all}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in CMDS:
        print(__doc__)
        return 2
    return CMDS[sys.argv[1]]()


if __name__ == "__main__":
    sys.exit(main())
