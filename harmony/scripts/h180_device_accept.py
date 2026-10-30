#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""H-180/H-181 真机验收（Qoder，2026-10-26）

装机后按这个脚本走，四件事都落截图/页树文字：
  A. 空格键文案是「三生」（H-181）
  B. 展开工具栏后打字 → 工具栏收起、候选行回来（H-180①「打字盖候选」）
  C. 空格左右滑移光标（H-180②）：先上屏「你好你好」，左滑 ≈2 格后一次退格应少 1 个字；
     右滑回末尾再一次退格再少 1 个字；全程页树文字**不许出现空格**
  D. 七枚图标（H-179）与网格页标识 6/6（H-174）：只拍，人工看图

坐标全部**运行时**算：
  - 候选行左 ▶ / 工具栏展开点：`h165_h168_device_accept.tri_point(panel_rect(), density())`
  - 字母键：沿用 h164 的 LETTERS（1280x2832 实测，面板 1849 起）
  - 空格中心：底栏第 5 键，取 (763, 2588)（h164 实测）；左右滑都在键内起止（900↔1000）
安全：每段注入前过 `assert_our_app()`；只在本应用试打框里打字/退格。

用法：
    python scripts/h180_device_accept.py selftest   # 先跑这个：量具在合成图上自证（不碰设备）
    python scripts/h180_device_accept.py all
    python scripts/h180_device_accept.py label|toolbar|cursor|clipboard|align|letters
"""
import argparse
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h164_device_accept as acc      # noqa: E402  image_cands/input_text/LETTERS/dump
import h165_h168_device_accept as base  # noqa: E402  tap/shot/launch/assert_our_app/panel_rect/density

EVID = os.path.join(os.path.dirname(HERE), "docs", "evidence", "2026-10-26", "h180-device")
os.makedirs(EVID, exist_ok=True)
acc.EVID = EVID       # 让 input_text/dump 落到本目录
base.EVID = EVID      # 让 shot/dump 落到本目录

SPACE = (763, 2588)
BK = (1175, 2420)
TRIAL = (640, 1600)
BAR_H = base.BAR_H   # 2026-10-26 11:3x：此前 measure_toolbar_icons 里直接写 BAR_H，
                     # 但本文件从未定义它（只在 h165 里）⇒ 运行时 NameError，
                     # 也就是说「量七枚图标」那一步**从没在真机上真正跑过**。显式取过来。


def keys(word):
    for ch in word:
        x, y = acc.LETTERS[ch]
        base.tap(x, y)
        time.sleep(0.12)


def text_now(tag):
    p = base.dump("h180_%s" % tag)
    t = acc.input_text(p)
    print("TEXT[%s] = %r" % (tag, t))
    return t


def clear_trial(max_taps=20):
    """只在**本应用试打框**里清空：每 5 次退格前重新确认前台。"""
    for i in range(max_taps):
        if i % 5 == 0:
            base.assert_our_app("clear")
            if (text_now("clear%d" % i) or "") == "":
                return True
        base.tap(*BK)
        time.sleep(0.15)
    return (text_now("clear_end") or "") == ""


def tap_first_candidate(shot_name):
    """拍候选行 → 按像素量出第 1 条候选中心 → 点它（键盘面板不在页树里，只能量图）。"""
    jpeg = base.shot(shot_name)
    cands = acc.image_cands(jpeg)
    if not cands:
        raise SystemExit("候选行没量到任何条目（%s）——先看图，别瞎点" % jpeg)
    c = cands[0]
    base.tap(c["x"], c["y"])
    print("tap first candidate: %r at (%d,%d)" % (c.get("text"), c["x"], c["y"]))
    time.sleep(0.6)


def commit_nihao_twice():
    for n in range(2):
        keys("nihao")
        time.sleep(0.9)
        tap_first_candidate("d%d_cands" % (n + 1))


def swipe_space(x_start, x_end):
    base.swipe(x_start, SPACE[1], x_end, SPACE[1], v=800)
    time.sleep(0.6)


def measure_toolbar_icons(shot_name, rect, d):
    """H-183：量展开态工具栏七枚图标的中心（图标是深灰 SymbolGlyph，画在白色候选栏带上）。
    键盘面板不在页树里，只能从像素量：在面板顶 ~ +44vp 的带内按列统计暗像素，
    相邻列段间隙 <40px 的并成一颗。量不到 7 颗就报错，不猜坐标。"""
    from PIL import Image
    jpeg = base.shot(shot_name)
    im = Image.open(jpeg).convert("RGB")
    w, _ = im.size
    px = im.load()
    y0 = int(rect[1] + 6)
    y1 = int(rect[1] + BAR_H * d - 6)
    cols = []
    for x in range(w):
        n = 0
        for y in range(y0, y1, 2):
            c = px[x, y]
            if max(c) < 200:
                n += 1
        cols.append(n)
    segs, s = [], None
    last = None
    for x, n in enumerate(cols):
        if n > 0:
            if s is None:
                s = x
            last = x
        elif s is not None and x - last > 40:
            segs.append((s, last))
            s = None
    if s is not None:
        segs.append((s, last))
    cy = (y0 + y1) // 2
    out = [((a + b) // 2, cy, b - a + 1) for (a, b) in segs]
    print("H-183 工具栏图标 %d 颗（应为 7）：%s" % (len(out), out))
    if len(out) < 7:
        raise SystemExit("工具栏没量到 7 颗图标——先看 %s，别按写死坐标点" % jpeg)
    return out


def step_label():
    base.shot("a_bar_and_space")      # 一图同时看七枚图标 + 空格文案


def bar_upper_ink(jpeg, rect):
    """候选栏带最上面 ~34px 的墨量。L1 预编辑行（12fp 灰字）只在**收起态**出现在这里；
    展开态七枚图标是整带垂直居中（y≈带顶+77px），顶部这段是空白。
    ⇒ 判 H-180①「打字后工具栏收起、候选行回来」用这一个数，不依赖认字。"""
    from PIL import Image
    im = Image.open(jpeg).convert("RGB")
    px = im.load()
    y0, y1 = int(rect[1] + 2), int(rect[1] + 36)
    n = sum(1 for y in range(y0, y1, 2) for x in range(0, im.size[0], 2) if max(px[x, y]) < 210)
    print("BAR-UPPER ink=%d（展开态≈0；收起态有 L1 预编辑行则明显>0）" % n)
    return n


def step_toolbar():
    rect = base.panel_rect()
    d = base.density()
    tri = base.tri_point(rect, d)
    base.tap(*tri)                    # 展开工具栏
    time.sleep(0.7)
    ink_open = bar_upper_ink(base.shot("b1_toolbar_open"), rect)
    if ink_open > 50:
        print("!! 展开态顶部仍有 L1 墨迹 ⇒ 这一次没展开成功（b1 与后续判据只作对照）")
    base.tap(*acc.LETTERS["q"])       # 打字 ⇒ H-180 应自动收起
    time.sleep(0.9)
    jpeg = base.shot("b2_after_typing")
    text_now("b2")
    ink_after = bar_upper_ink(jpeg, rect)
    cands = acc.image_cands(jpeg)
    print("H-180① 打字后：顶部墨量 %d、候选 %d 条 ⇒ %s" % (
        ink_after, len(cands),
        "PASS（工具栏收起、候选回来）" if (ink_after > 50 and len(cands) >= 1) else "CHECK（看 b1/b2）"))


def step_cursor():
    base.assert_our_app("cursor")
    if not clear_trial():
        raise SystemExit("试打框清不干净，停——别在带内容的状态下做光标判据")
    commit_nihao_twice()
    base_text = text_now("c1_base")
    if not base_text:
        raise SystemExit("没能上屏「你好你好」（页树为空）——先看 d1/d2 候选截图")
    if " " in base_text:
        print("!! 基础上屏就带空格，后续判据会被污染：%r" % base_text)

    swipe_space(1000, 900)            # 左滑 100px ≈ 28.6vp ≈ 2 格
    base.shot("c2_swipe_left")
    mid = text_now("c2")
    if mid != base_text:
        print("!! 左滑后文字变了（不该上屏任何字符）：%r -> %r" % (base_text, mid))

    base.tap(*BK)
    time.sleep(0.5)
    after_left = text_now("c3_bs_after_left")
    ok1 = (base_text and after_left is not None and len(base_text) - len(after_left) == 1)
    print("左滑后一次退格：%r -> %r（只该少 1 个字）" % (base_text, after_left))

    swipe_space(900, 1040)            # 右滑 140px ≈ 40vp ≈ 4 格（回末尾足够）
    base.shot("c4_swipe_right")
    mid2 = text_now("c4")
    if mid2 != after_left:
        print("!! 右滑后文字变了：%r -> %r" % (after_left, mid2))
    base.tap(*BK)
    time.sleep(0.5)
    after_right = text_now("c5_bs_after_right")
    ok2 = (after_left and after_right is not None and len(after_left) - len(after_right) == 1)
    print("右滑回末尾再一次退格：%r -> %r" % (after_left, after_right))

    print("判定：c2==c1（滑移不上屏）、c3 少 1 字（左滑真的动了光标）、c5 再少 1 字（右滑回到末尾）。")
    print("结论：%s" % ("PASS" if (ok1 and ok2 and mid == base_text and mid2 == after_left)
                      else "CHECK（看截图与日志）"))


def step_clipboard():
    """H-183：工具栏第 5 枚（剪贴板）必须真把剪贴板内容粘进试打框。

    判据用**唯一串**「你好世界」而不是「你好」——万一 PASTE 没生效、框里留着旧剪贴板
    内容（这台机上之前有过英文/别的词），单看「你好」会假过。全流程只在本应用试打框里
    选全/复制/清空，绝不碰第三方应用（铁律）。"""
    base.assert_our_app("clipboard")
    if not clear_trial():
        raise SystemExit("试打框清不干净，停——剪贴板判据需要空框")
    for word in ("nihao", "shijie"):
        keys(word)
        time.sleep(0.9)
        tap_first_candidate("e_%s_cands" % word)
    copied = text_now("e1_copied")
    print("H-183 待复制内容 = %r（应为「你好世界」）" % copied)
    if not copied or "你好世界" not in copied:
        raise SystemExit("没能上屏「你好世界」，后续判据不成立——先看 e_*_cands 截图")
    base.press(*acc.LETTERS["a"])      # 全选
    time.sleep(0.6)
    base.press(*acc.LETTERS["c"])      # 复制
    time.sleep(0.6)
    if not clear_trial():
        raise SystemExit("复制后试打框清不干净，停")
    rect = base.panel_rect()
    d = base.density()
    base.tap(*base.tri_point(rect, d))  # 展开工具栏
    time.sleep(0.8)
    icons = measure_toolbar_icons("e2_toolbar", rect, d)
    base.tap(*icons[4][:2])             # 第 5 枚＝剪贴板（PASTE）
    time.sleep(1.0)
    pasted = text_now("e3_pasted")
    ok = (pasted is not None and "你好世界" in pasted)
    print("H-183 粘贴后 = %r ⇒ %s" % (pasted, "PASS" if ok else "FAIL（第 5 枚没粘上）"))
    return ok


# ---------------------------------------------------------------------------
# H-188 / H-190 / H-192 / H-187 真机判据（2026-10-26 11:3x 新增）
# 共同前提：键盘面板不在页树里，一切几何都从**截图像素**量，量不到就报错，不猜坐标。
# ---------------------------------------------------------------------------
def bar_segments_img(jpeg, rect, y_lo, y_hi, gap=40):
    """按列统计暗像素 → 连续墨段（段中心, 段宽）。与拍图分开，便于离线自测。"""
    from PIL import Image
    im = Image.open(jpeg).convert("RGB")
    w, _ = im.size
    px = im.load()
    y0 = int(rect[1] + y_lo)
    y1 = min(im.size[1], int(rect[1] + y_hi))
    cols = []
    for x in range(w):
        n = sum(1 for y in range(y0, y1, 2) if max(px[x, y]) < 200)
        cols.append(n)
    segs, s, last = [], None, None
    for x, n in enumerate(cols):
        if n > 0:
            if s is None:
                s = x
            last = x
        elif s is not None and x - last > gap:
            segs.append(((s + last) // 2, last - s + 1))
            s = None
    if s is not None:
        segs.append(((s + last) // 2, last - s + 1))
    return segs


# ---------------------------------------------------------------------------
# 量具（可离线自测，见 `--selftest`）
# 为什么不用「墨段条数」判展开/收起：收起态 L2 里是**候选词**，一条 40px 间隙的
# 分段器会把它们切成 6+ 段 ⇒ 「收起」判据 `len(segs)<=4` 必然假红，白烧一轮真机
# （装机要主人输密码）。改成按**结构**量：七枚图标的位置是固定的（20…340vp 等距），
# 只在图标那一小段竖直带里看这七个位置有没有墨迹 —— 展开 7 中 7，收起只剩两侧。
# ---------------------------------------------------------------------------
def icon_centers(d=None, expect=7):
    """展开态七枚图标的期望中心 x（px）。几何来自 spec §十一：首末 20vp/340vp、等距。"""
    first, last = 20.0, 340.0
    dd = 1.0 if d is None else d
    return [int(round((first + (last - first) * i / (expect - 1)) * dd))
            for i in range(expect)]


def _ink_in_box(im, x0, x1, y0, y1, thr=200):
    px = im.load()
    w, h = im.size
    x0, x1 = max(0, int(x0)), min(w, int(x1))
    y0, y1 = max(0, int(y0)), min(h, int(y1))
    n = 0
    for x in range(x0, x1):
        for y in range(y0, y1):
            if max(px[x, y]) < thr:
                n += 1
    return n


def icons_hit_count(jpeg, rect, d, tol_vp=8.0, y_lo_vp=8.0, y_hi_vp=13.0):
    """七个期望位置里，有几个在「图标上半」那条窄带里有墨迹。
    为什么取 8…13vp：图标垂直居中于 44vp 栏 ⇒ 本体约 12…32vp；候选行从 16vp 起、
    候选字中心约 30vp ⇒ 取 8…13vp 只碰图标上沿，不碰候选字（收起态 L1 的 preedit
    只在最左，恰好落在首枚窗口里，所以收起时测得 1，展开时 7 —— 判据仍分得清）。"""
    from PIL import Image
    im = Image.open(jpeg).convert("RGB")
    hit = []
    for cx in icon_centers(d):
        ink = _ink_in_box(im, cx - tol_vp * d, cx + tol_vp * d,
                          rect[1] + y_lo_vp * d, rect[1] + y_hi_vp * d)
        hit.append(ink > 6)
    return sum(hit), hit


def ink_centroid_x(jpeg, rect, x_lo, x_hi, y_lo, y_hi, thr=200):
    """窗口内暗像素的加权重心 x（多行取和）。窗口里没墨返回 None —— 不猜坐标。"""
    from PIL import Image
    im = Image.open(jpeg).convert("RGB")
    px = im.load()
    w, h = im.size
    x0, x1 = max(0, int(x_lo)), min(w, int(x_hi))
    y0, y1 = max(0, int(rect[1] + y_lo)), min(h, int(rect[1] + y_hi))
    tot = sw = 0
    for x in range(x0, x1):
        n = sum(1 for y in range(y0, y1, 2) if max(px[x, y]) < thr)
        if n:
            tot += n
            sw += x * n
    return None if tot == 0 else int(round(float(sw) / tot))


def letters_right_edge(jpeg, rect, d):
    """L1 带上墨迹的**最右端**（px）。step_letters 与离线自测共用这一个量具。

    为什么取「段的右端」而不是「段中心」：注释是紧跟在 4 个字母后面的（间隙 ≈4vp <40px），
    分段器会把字母和注释并成**一段**；这时段中心会被拉回中间（≈139px）⇒ 用中心判 180
    会把「gavc 开始」误判成干净（假 PASS）。右端则是 250px+，一眼就分得开——
    正好对应主人那句「gavc 后面是『开始』的注释，混乱」。"""
    segs = bar_segments_img(jpeg, rect, 2, int(16 * d))
    # bar_segments 给的是（段中心, 段宽）：右端 = 中心 + (宽-1)/2（不是 +宽-1，那会多算半段宽）
    return max((c + (w - 1) // 2 for c, w in segs), default=0), segs


def step_letters():
    """H-190：字母行只许有 preedit。判据=打字后拍 L1 带，右端墨迹必须落在很左边。

    主人原话：「gavc 后面是『开始』的注释，混乱」。4 个 ASCII 字母 12fp 大约占 30vp≈105px，
    L1 左内边距 8vp≈28px ⇒ 右端应 < ~140px；一旦把候选注释并回字母行，右端会推到 200px+。
    阈值取 **180px**（约 51vp）：既容下 4 字母＋光标，又拦得住任何中文注释。
    另存原图供人工复看（注释/字形这类观感最终仍以肉眼为准）。"""
    base.assert_our_app("letters")
    clear_trial()
    keys("gavc")
    time.sleep(0.9)
    rect = base.panel_rect()
    d = base.density()
    jpeg = base.shot("f1_letters")
    right, segs = letters_right_edge(jpeg, rect, d)
    ok = 0 < right < 180
    print("H-190 字母行墨段 %s ⇒ 右端 %dpx（阈值 180）" % (segs, right))
    print("判定：%s（看图 %s 复核『gavc 后面有没有中文注释』）" % ("PASS" if ok else "CHECK", jpeg))
    return ok


def step_align():
    """H-188+H-192+H-187 一条链跑完：

    1) 收起态量两枚三角的 x 中心（L2 带，避开 L1 的 preedit 墨迹）；
    2) 展开量七枚图标中心 —— ›/‹ 与首枚、▼ 与末枚必须同一条竖线（容差 8px≈2vp）；
    3) H-192：点「撤销」后工具栏**不许**收起（七枚仍在）；
    4) H-192：点 ‹ 才收起（候选行回来）；
    5) H-187：再展开 → 打字（自动收起）→ 点首条候选 commit → 回 Idle 时工具栏**自动回来**。

    为什么不按「墨段条数」判展开/收起：收起态 L2 是候选词，40px 间隙的分段器会切出 6+ 段
    ⇒ 旧判据 `len(segs)<=4` 必然假红（白烧一轮装机）。改按结构量 `icons_hit_count()`。
    三角中心也改成**窗口内重心**：候选字紧跟三角（间隙 <40px 会被并成一段），
    用「第一段中心」同样会假偏。窗口由常量算出，窗口里没墨就报错不猜。
    """
    base.assert_our_app("align")
    clear_trial()
    keys("ni")                        # 有 preedit ⇒ 收起态：L1「ni」+ L2 候选
    time.sleep(0.9)
    rect = base.panel_rect()
    d = base.density()
    l2_lo, l2_hi = int(18 * d), int(BAR_H * d) - 2      # 只扫 L2，避开 L1 的字母墨迹
    jpeg = base.shot("f2_collapsed")
    tri_left_x = ink_centroid_x(
        jpeg, rect,
        base.CAND_PAD_H * d,
        (base.CAND_PAD_H + base.FUNC_TRI_LEFT_W) * d - 2,
        l2_lo, l2_hi)
    tri_right_x = ink_centroid_x(
        jpeg, rect,
        rect[2] - (base.CAND_ROW_RIGHT_PAD + base.FUNC_TRI_WIDTH) * d + 2,
        rect[2] - base.CAND_ROW_RIGHT_PAD * d,
        l2_lo, l2_hi)
    if tri_left_x is None or tri_right_x is None:
        raise SystemExit("收起态三角的窗口里没量到墨（左=%s 右=%s）——先看 %s，别猜坐标"
                         % (tri_left_x, tri_right_x, jpeg))
    hits0, _ = icons_hit_count(jpeg, rect, d)
    if hits0 > 2:
        print("!! 收起态却量到 %d 个图标位有墨（应为 ≤2）——这一轮的前置状态不对，后续只作对照" % hits0)

    base.tap(*base.tri_point(rect, d))          # 展开
    time.sleep(0.8)
    icons = measure_toolbar_icons("f3_open", rect, d)
    dl = abs(tri_left_x - icons[0][0])
    dr = abs(tri_right_x - icons[-1][0])
    ok_align = dl <= 8 and dr <= 8
    print("H-188 收起 › x=%d / 展开 ‹ x=%d（差 %dpx）；收起 ▼ x=%d / 展开末枚 x=%d（差 %dpx）⇒ %s"
          % (tri_left_x, icons[0][0], dl, tri_right_x, icons[-1][0], dr,
             "PASS" if ok_align else "FAIL（容差 8px≈2vp）"))

    base.tap(*icons[1][:2])                     # 撤销
    time.sleep(0.7)
    hits_undo, _ = icons_hit_count(base.shot("f4_after_undo"), rect, d)
    still_open = hits_undo >= 6
    print("H-192 点撤销后图标位命中 %d/7 ⇒ %s" % (
        hits_undo, "仍展开 PASS" if still_open else "被收起 FAIL"))

    base.tap(*icons[0][:2])                     # ‹ 收起
    time.sleep(0.8)
    hits_back, _ = icons_hit_count(base.shot("f5_after_back"), rect, d)
    closed = hits_back <= 2
    print("H-192 点 ‹ 后图标位命中 %d/7 ⇒ %s" % (hits_back, "已收起 PASS" if closed else "没收起 FAIL"))

    base.tap(*base.tri_point(rect, d))          # 再展开（pinned）
    time.sleep(0.8)
    keys("n")
    time.sleep(1.0)                             # H-180① 打字即收起
    tap_first_candidate("f6_commit")
    time.sleep(1.0)                             # commit → Idle ⇒ H-187 应自动回来
    hits_auto, _ = icons_hit_count(base.shot("f7_auto_back"), rect, d)
    auto_back = hits_auto >= 6
    print("H-187 commit 回 Idle 后图标位命中 %d/7 ⇒ %s" % (
        hits_auto, "工具栏自动回来 PASS" if auto_back else "没回来 FAIL"))

    print("汇总：对齐=%s 撤销不收起=%s ‹ 收起=%s 自动回来=%s"
          % (ok_align, still_open, closed, auto_back))
    print("H-189（展开过渡）无法用静帧判——由 scripts/h190_bar_ux_check.py 静态锁 + 主人肉眼确认。")
    return ok_align and still_open and closed and auto_back


def selftest():
    """量具离线自测（不碰设备）：在合成图上量，证明判据会随画面变、不是永远真/永远假。

    合成图是**按 spec §十一 的几何画的**：rect=(0,0,1280,200)、d=3.5、图标 20vp 方块、
    候选字画在 L2（16…44vp）里。正控 + 负控：
      ① 展开态（7 枚）⇒ icons_hit_count 应 =7；
      ② 收起态（› + 一串候选 + ▼）⇒ 应 ≤2（旧「墨段条数」判据在这里会数出 6+ 段）；
      ③ 收起态两枚三角的窗口重心应落在 20vp/340vp（±5px）；
      ④ ⑥/⑦ 字母行：干净（只有 gavc）右端 <180px；紧贴中文注释时必须 ≥180px
         —— 后者用「段中心」会假 PASS，所以量具取段右端；
      ⑤ 两条负控：「展开只画 5 枚」必须 =5（不是恒 7）；「左三角右移 10px」重心必须跟着移。
    """
    from PIL import Image, ImageDraw
    import tempfile
    fails = []
    d = 3.5
    rect = (0, 0, 1280, 200)
    tmp = tempfile.mkdtemp(prefix="h180_selftest_")

    def canvas(name):
        im = Image.new("RGB", (1280, 200), (255, 255, 255))
        p = os.path.join(tmp, name + ".png")
        os.makedirs(tmp, exist_ok=True)
        return im, ImageDraw.Draw(im), p

    def draw_icons(dr, centers):
        for cx in centers:
            dr.rectangle([cx - 35, 42, cx + 35, 112], fill=(40, 40, 40))   # 20vp 见方，居中于 77

    # ① 展开态
    im, dr, p = canvas("open7")
    draw_icons(dr, icon_centers(d))
    im.save(p)
    n, hits = icons_hit_count(p, rect, d)
    if n != 7:
        fails.append("展开态应命中 7，实测 %d（%s）" % (n, hits))

    # ② 收起态
    def draw_collapsed(dr, shift=0):
        dr.rectangle([28, 20, 90, 40], fill=(120, 120, 120))              # L1 preedit「ni」
        dr.rectangle([42 + shift, 77, 98 + shift, 133], fill=(150, 150, 150))  # ›
        x = 130
        for _ in range(12):                                             # 候选字
            dr.rectangle([x, 84, x + 40, 147], fill=(60, 60, 60))
            x += 54
        dr.rectangle([1155, 77, 1225, 133], fill=(150, 150, 150))        # ▼
    im, dr, p = canvas("closed")
    draw_collapsed(dr)
    im.save(p)
    n2, hits2 = icons_hit_count(p, rect, d)
    if n2 > 2:
        fails.append("收起态应 ≤2，实测 %d（%s）——判据会把收起误判成展开" % (n2, hits2))
    lx = ink_centroid_x(p, rect, base.CAND_PAD_H * d,
                        (base.CAND_PAD_H + base.FUNC_TRI_LEFT_W) * d - 2, 18 * d, BAR_H * d - 2)
    rx = ink_centroid_x(p, rect, 1280 - (base.CAND_ROW_RIGHT_PAD + base.FUNC_TRI_WIDTH) * d + 2,
                        1280 - base.CAND_ROW_RIGHT_PAD * d, 18 * d, BAR_H * d - 2)
    if lx is None or abs(lx - 70) > 5:
        fails.append("左三角重心应≈70，实测 %s" % lx)
    if rx is None or abs(rx - 1190) > 5:
        fails.append("右三角重心应≈1190，实测 %s" % rx)

    # ④ 负控：只画 5 枚
    im, dr, p = canvas("open5")
    draw_icons(dr, icon_centers(d)[:5])
    im.save(p)
    n4, _ = icons_hit_count(p, rect, d)
    if n4 != 5:
        fails.append("负控「只画 5 枚」应 =5，实测 %d = 量具不管画了几枚" % n4)

    # ⑤ 负控：左三角右移 10px（≈2.9vp，在窗口可测范围内）⇒ 重心必须跟着移。
    #    为什么不是移 20px：窗口右界 32vp 就是首条候选的起点，真机三角再偏也偏不出这个
    #    范围（偏出去就和候选字重叠了）；用 20px 会让窗口裁掉一角、量出的偏差变小——
    #    那是**假 PASS** 的偏置，正好是这条负控该抓的，所以把负控放在物理可测范围内。
    im, dr, p = canvas("closed_shift")
    draw_collapsed(dr, shift=10)
    im.save(p)
    lx2 = ink_centroid_x(p, rect, base.CAND_PAD_H * d,
                         (base.CAND_PAD_H + base.FUNC_TRI_LEFT_W) * d - 2, 18 * d, BAR_H * d - 2)
    if lx2 is None or abs(lx2 - (lx + 10)) > 3:
        fails.append("负控「三角右移 10px」重心应跟着移 10px，实测 %s（原 %s）" % (lx2, lx))

    # ⑥/⑦ 字母行判据（H-190）：干净 ⇒ <180；混进中文注释 ⇒ 必须 ≥180。
    #    脏样本把注释紧贴字母画（间隙 8px <40px ⇒ 并成一段），正是真机的形态：
    #    用「段中心」判会把这一段拉回 ≈139px 假 PASS，只有「段右端」分得开。
    def draw_letters(dr, comment_end=None):
        x = 28
        for _ in range(4):                                              # gavc
            dr.rectangle([x, 12, x + 18, 44], fill=(90, 90, 90))
            x += 24
        if comment_end:
            dr.rectangle([x + 8, 12, comment_end, 44], fill=(150, 150, 150))

    im, dr, p = canvas("letters_clean")
    draw_letters(dr)
    im.save(p)
    r1, s1 = letters_right_edge(p, rect, d)
    if not (0 < r1 < 180):
        fails.append("字母行「干净」样本应 <180，实测 %d（%s）" % (r1, s1))

    im, dr, p = canvas("letters_dirty")
    draw_letters(dr, comment_end=300)
    im.save(p)
    r2, s2 = letters_right_edge(p, rect, d)
    if not (r2 >= 180):
        fails.append("字母行「混注释」样本应 ≥180，实测 %d（%s）" % (r2, s2))

    for f in fails:
        print("  [红] " + f)
    if fails:
        print("SELFTEST FAIL：%d 项（量具会假真/假红，先修再上真机）" % len(fails))
        return 1
    print("SELFTEST OK：展开 7/7、收起 %d/7、三角 70/1190、字母行干净 %dpx/混注释 %dpx、三条负控都跟着变"
          % (n2, r1, r2))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["label", "toolbar", "cursor", "clipboard",
                                     "align", "letters", "all", "launch", "selftest"])
    args = ap.parse_args()
    if args.step == "selftest":
        return selftest()
    if args.step in ("launch", "all"):
        base.launch()
        time.sleep(3.5)
    if args.step == "launch":
        base.tap(*TRIAL)
        time.sleep(1.2)
        base.shot("a0_kb")
        return 0
    base.assert_our_app(args.step)
    if args.step in ("label", "all"):
        step_label()
    if args.step in ("toolbar", "all"):
        step_toolbar()
    if args.step in ("cursor", "all"):
        step_cursor()
    if args.step in ("clipboard", "all"):
        step_clipboard()
    if args.step in ("letters",):
        step_letters()
    if args.step in ("align",):
        step_align()
    return 0


if __name__ == "__main__":
    sys.exit(main())
