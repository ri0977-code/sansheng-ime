#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""H-231r2：在键盘截图里**逐像素量**顶栏那排图标的位置，用来点 ⇆。

为什么要有这个：`uitest dumpLayout` 取不到我们输入法窗口的子节点（h164 10:02 实测：
键盘面板窗里一个 text 节点都没有），所以图标坐标只能从**像素**量。

坐标基准（2026-10-27 21:1x 实测）：Mate 80 的 `snapshot_display` 输出 **1280×2832**，
与 `uitest uiInput click` 的触摸空间**同一尺寸（1:1）** ⇒ 截图上量到的像素可以直接当点击坐标。
（内存里那条「截图比触摸大 2.21×」对本机这条抓图路径不成立，别再除。）

量法（第一版栽在哪）：第一版用「亮度 ≥ 140 的像素算笔画」，而候选栏底色本身就是
亮色（242,243,245）⇒ 整行 1280 列全被算成笔画，量出「1 簇 x=0..1279」。
改成**逐行背景模型**：
  ① 每一行单独算自己的背景色（该行每通道的中位数）——图标只占少数像素，中位数稳；
  ② 该行像素与本行背景任一通道差 > 容差(默认 12) 就算「笔画」；
  ③ 整行笔画占比 > 50% 的行丢掉（那是边界过渡行 / 整条分隔线，不是图标）；
  ④ 剩下的行按列累计笔画数，≥2 列算「有笔画」；间隙 ≤16px 的相邻列并成一枚图标。

形态判读（用簇数分辨当前处于哪种形态，不靠猜）：
  · 空闲态候选栏只有两枚：左边「›」（点它展开工具栏）、右边「⌄」（展开候选网格）⇒ 2 簇；
  · 工具栏展开态是 7 枚：‹ 撤销 重做 ⇆(光标) 剪贴板 ··· ▼ ⇒ 7 簇，**第 4 簇是 ⇆**。
  真截图实测（h213_menu_closed_toolbar_back.jpeg，空闲态）：2 簇，中心 x=69 与 x=1209，
  与安卓实测的 5.4% / 94.4% 一致。

用法：
  python scripts/h231_find_cursor_icon.py docs/evidence/2026-10-27/h231-panel/keyboard-up.jpeg
  python scripts/h231_find_cursor_icon.py <jpg> --expect 7 --index 4
  python scripts/h231_find_cursor_icon.py <jpg> --band-top 1850 --band-bottom 2005
  python scripts/h231_find_cursor_icon.py --selftest
"""
import argparse
import os
import sys

try:
    from PIL import Image
except Exception as e:  # pragma: no cover
    print("PIL 不可用：%s" % e)
    sys.exit(2)

BAND_ABOVE_KEYS = 180          # 键区顶沿之上扫多少像素（44vp 候选栏按 ~3.5px/vp ≈ 156px）
BAND_GAP = 8
DEFAULT_TOL = 12
DEFAULT_MIN_COUNT = 2
DEFAULT_MAX_GAP = 16
MAX_ICON_W = 110
MAX_ICON_H = 110
CORE_TOL = 60                # 「笔画核心」阈值：浅色高亮底（与行底色差 ≈23）不算笔画，
                             # 只有深色字形（差 ≈200）才算——见 find_clusters 里的说明。
KEYCAP_MIN = 250               # 键帽＝近纯白
KEYCAP_MIN_W = 30
DOT_MAX_W = 14                 # 主人报的 H-231 症状：图标「成点」
DOT_MAX_H = 14
DOT_MAX_INK = 60


def _median(vals):
    s = sorted(vals)
    n = len(s)
    if n == 0:
        return 0
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) // 2


def _clusters(cols, max_gap):
    """把有笔画的列并成簇：间隙 ≤ max_gap 的两段算同一枚图标。"""
    out = []
    if not cols:
        return out
    start = prev = cols[0]
    for c in cols[1:]:
        if c - prev <= max_gap:
            prev = c
            continue
        out.append((start, prev))
        start = prev = c
    out.append((start, prev))
    return out


def keycap_row(im, start_y=200, limit=None):
    """从 start_y 往下找第一行「有 ≥3 段宽白键帽」的行（键区顶沿）。找不到返回 None。"""
    px = im.load()
    w, h = im.size
    limit = limit if limit is not None else h
    for y in range(max(0, start_y), min(h, limit)):
        run = 0
        segs = 0
        for x in range(w):
            r, g, b = px[x, y]
            if r >= KEYCAP_MIN and g >= KEYCAP_MIN and b >= KEYCAP_MIN:
                run += 1
            else:
                if run >= KEYCAP_MIN_W:
                    segs += 1
                run = 0
        if run >= KEYCAP_MIN_W:
            segs += 1
        if segs >= 3:
            return y
    return None


def band_from_panel(im, panel_top):
    """候选栏扫描带：以面板顶沿为上沿，到键区第一行键帽为止。"""
    kc = keycap_row(im, start_y=panel_top, limit=panel_top + 420)
    if kc is None:
        return (panel_top, min(im.size[1], panel_top + 220))
    return (panel_top, max(panel_top + 20, kc - BAND_GAP))


def find_clusters(im, band=None, tol=DEFAULT_TOL, min_count=DEFAULT_MIN_COUNT,
                  max_gap=DEFAULT_MAX_GAP):
    """返回候选栏里的图标簇：[{x1,x2,cy,cx,w,h,ink}]。"""
    px = im.load()
    w, h = im.size
    if band is None:
        band = band_from_panel(im, 0)
    top, bot = band
    top = max(0, min(top, h - 1))
    bot = max(top + 1, min(bot, h))

    keep_rows = []
    ink_by_row = {}
    bg_by_row = {}
    for y in range(top, bot):
        row = [px[x, y] for x in range(w)]
        bg = (_median([c[0] for c in row]),
              _median([c[1] for c in row]),
              _median([c[2] for c in row]))
        bg_by_row[y] = bg
        ink = set()
        for x in range(w):
            c = row[x]
            if (abs(c[0] - bg[0]) > tol or abs(c[1] - bg[1]) > tol
                    or abs(c[2] - bg[2]) > tol):
                ink.add(x)
        if not ink or len(ink) * 2 > w:
            continue          # 空行 / 整行过渡线：不是图标
        keep_rows.append(y)
        ink_by_row[y] = ink

    counts = {}
    for y in keep_rows:
        for x in ink_by_row[y]:
            counts[x] = counts.get(x, 0) + 1
    cols = sorted(x for x, n in counts.items() if n >= min_count)

    out = []
    for (x1, x2) in _clusters(cols, max_gap):
        ys = []
        ink = 0
        for y in keep_rows:
            hit = False
            for x in range(x1, x2 + 1):
                if x in ink_by_row[y]:
                    hit = True
            if hit:
                ys.append(y)
                ink += sum(1 for x in range(x1, x2 + 1) if x in ink_by_row[y])
        if not ys:
            continue
        # **笔画核心**（2026-10-27 22:2x 真机踩到）：
        # 顶栏那枚 ⇆ 是「被按下/选中态」的浅蓝灰圆角方块托着一枚深色字形。
        # 浅色高亮底与行底色只差 ≈23（> 容差 12）⇒ 整簇宽度 ≈124px ⇒ 撞上
        # MAX_ICON_W(110) 被**整簇丢掉**，那枚 ⇆ 就这么量不到（22:26 实测：
        # 量到 8 簇，唯独 4 枚的位置是空的）。
        # 所以：簇仍按「与行底色的差」圈（要能框住高亮底），但**尺寸/中心/成点
        # 判据一律按深色字形核心算**（CORE_TOL=60）——高亮底是背景，不是图标。
        core_x = []
        core_y = []
        core_ink = 0
        for y in keep_rows:
            bg = bg_by_row[y]
            for x in range(x1, x2 + 1):
                if x not in ink_by_row[y]:
                    continue
                c = px[x, y]
                if (abs(c[0] - bg[0]) > CORE_TOL or abs(c[1] - bg[1]) > CORE_TOL
                        or abs(c[2] - bg[2]) > CORE_TOL):
                    core_x.append(x)
                    core_y.append(y)
                    core_ink += 1
        if core_x:
            bx1, bx2 = min(core_x), max(core_x)
            by1, by2 = min(core_y), max(core_y)
        else:
            # 没有深色核心（浅色图标）⇒ 退回整簇
            bx1, bx2 = x1, x2
            by1, by2 = min(ys), max(ys)
            core_ink = ink
        cw = bx2 - bx1 + 1
        ch = by2 - by1 + 1
        if cw > MAX_ICON_W or ch > MAX_ICON_H:
            continue
        out.append({"x1": bx1, "x2": bx2, "cx": (bx1 + bx2) // 2,
                    "cy": (by1 + by2) // 2, "w": cw, "h": ch, "ink": core_ink,
                    "box_x1": x1, "box_x2": x2,
                    "box_w": x2 - x1 + 1, "box_h": max(ys) - min(ys) + 1})
    return out, band


def looks_like_dot(c):
    """H-231 症状判据：图标「成点」＝笔画盒很小、笔画数很少。"""
    return c["w"] <= DOT_MAX_W and c["h"] <= DOT_MAX_H and c["ink"] <= DOT_MAX_INK


def analyze_image(path, band=None, **kw):
    im = Image.open(path).convert("RGB")
    out, used = find_clusters(im, band=band, **kw)
    return im.size, used, out


def _synth(bg=(242, 243, 245), ink=(138, 143, 153), centers=(), glyph=7, size=(1280, 120)):
    """合成一张「候选栏里有 n 枚图标」的图，供离线自测用。"""
    im = Image.new("RGB", size, bg)
    px = im.load()
    for cx in centers:
        for dy in range(-glyph, glyph + 1):
            for dx in range(-glyph, glyph + 1):
                if abs(dx) + abs(dy) > glyph + 1:
                    continue
                if abs(dy) == glyph and dx == 0:
                    continue
                x, y = cx + dx, 60 + dy
                if 0 <= x < size[0] and 0 <= y < size[1]:
                    px[x, y] = ink
    return im


def selftest():
    """离线自测：合成图 + 真截图都要量对。"""
    # ① 7 枚图标（工具栏展开态）
    centers = [70, 240, 440, 640, 840, 1040, 1210]
    im = _synth(centers=centers)
    out, _ = find_clusters(im, band=(0, 120))
    assert len(out) == 7, out
    assert abs(out[3]["cx"] - 640) <= 3, out[3]
    assert all(abs(out[i]["cx"] - centers[i]) <= 3 for i in range(7)), out

    # ② 2 枚（空闲态：左 › 右 ⌄）
    im = _synth(centers=[70, 1210])
    out, _ = find_clusters(im, band=(0, 120))
    assert len(out) == 2, out
    assert out[0]["cx"] <= 100 and out[1]["cx"] >= 1100, out

    # ③ 一整行文字：不能被当成 1 枚大图标
    im = Image.new("RGB", (1280, 120), (242, 243, 245))
    px = im.load()
    for x in range(60, 700):
        for dy in (-6, 0, 6):
            px[x, 60 + dy] = (90, 95, 105)
    out, _ = find_clusters(im, band=(0, 120))
    assert not (len(out) == 1 and out[0]["w"] > MAX_ICON_W), out

    # ④ 「成点」判据：一小团像素 ⇒ looks_like_dot=True；正常箭头 ⇒ False
    im = _synth(centers=[640], glyph=2)
    out, _ = find_clusters(im, band=(0, 120))
    assert len(out) == 1, out
    assert looks_like_dot(out[0]), out[0]
    im = _synth(centers=[640], glyph=7)
    out, _ = find_clusters(im, band=(0, 120))
    assert not looks_like_dot(out[0]), out[0]

    # ⑤ 高亮底托着的图标（22:26 真机踩到）：浅蓝灰圆角方块 124px 宽 + 深色字形
    #     ⇒ 老算法整簇超 MAX_ICON_W 被丢掉；新算法按深色字形核心定位，必须能量到。
    im = Image.new("RGB", (1280, 120), (242, 243, 245))
    px = im.load()
    for y in range(30, 90):                       # 124×60 的高亮底
        for x in range(578, 702):
            px[x, y] = (219, 226, 236)
    for dy in range(-10, 11):                     # 深色字形（两撇一捺，够粗）
        for dx in range(-14, 15):
            if abs(dx) + abs(dy) > 16:
                continue
            px[640 + dx, 60 + dy] = (30, 38, 56)
    out, _ = find_clusters(im, band=(0, 120))
    assert len(out) == 1, out
    assert abs(out[0]["cx"] - 640) <= 4, out[0]
    assert out[0]["w"] <= 40, out[0]              # 量到的是字形核心，不是 124px 的高亮底
    assert not looks_like_dot(out[0]), out[0]

    # ⑥ 真截图（空闲候选栏）：左「›」x≈69、右「⌄」x≈1209 ⇒ 2 簇
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    real = os.path.join(root, "docs", "evidence", "2026-10-27",
                        "h213_menu_closed_toolbar_back.jpeg")
    if os.path.exists(real):
        _, band, out = analyze_image(real, band=(1890, 2000))
        print("真截图扫描带 y=%d..%d ⇒ %d 簇：%s"
              % (band[0], band[1], len(out), " ".join("x=%d" % c["cx"] for c in out)))
        assert len(out) == 2, out
        assert 50 <= out[0]["cx"] <= 95, out[0]
        assert out[1]["cx"] >= 1150, out[1]
    else:
        print("（真截图不在，跳过第 ⑤ 项）")
    print("SELFTEST OK：合成 7 簇/2 簇/文字行/成点判据都对；真截图空闲态量到 2 簇（› 与 ⌄）")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image", nargs="?")
    ap.add_argument("--band-top", type=int, default=None)
    ap.add_argument("--band-bottom", type=int, default=None)
    ap.add_argument("--panel-top", type=int, default=None, help="面板顶沿（px），据此自动定扫描带")
    ap.add_argument("--index", type=int, default=4, help="第几簇算 ⇆（1-based，默认 4）")
    ap.add_argument("--expect", type=int, default=None, help="期望的簇数，不符则退出码 2")
    ap.add_argument("--tol", type=int, default=DEFAULT_TOL)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        return selftest()
    if not a.image:
        ap.print_help()
        return 1
    if not os.path.exists(a.image):
        print("图片不存在：%s" % a.image)
        return 1
    band = None
    if a.band_top is not None and a.band_bottom is not None:
        band = (a.band_top, a.band_bottom)
    elif a.panel_top is not None:
        im = Image.open(a.image).convert("RGB")
        band = band_from_panel(im, a.panel_top)
    (w, h), used, out = analyze_image(a.image, band=band, tol=a.tol)
    print("图片 %dx%d，扫描带 y=%d..%d，容差 %d" % (w, h, used[0], used[1], a.tol))
    print("量到 %d 簇：" % len(out))
    for i, c in enumerate(out, 1):
        mark = "  ★=第%d簇" % a.index if i == a.index else ""
        dot = "  ←成点?" if looks_like_dot(c) else ""
        print("  %2d) x=%d..%d 中心=(%d,%d) 宽=%d 高=%d 笔画=%d%s%s"
              % (i, c["x1"], c["x2"], c["cx"], c["cy"], c["w"], c["h"], c["ink"], mark, dot))
    if a.expect is not None and len(out) != a.expect:
        print("簇数 %d ≠ 期望 %d（形态不符，不猜坐标）" % (len(out), a.expect))
        return 2
    if len(out) >= a.index:
        c = out[a.index - 1]
        print("ANSWER cursor=(%d,%d)" % (c["cx"], c["cy"]))
        return 0
    print("簇数不足 %d 簇（量到 %d），不能猜坐标" % (a.index, len(out)))
    return 2


if __name__ == "__main__":
    sys.exit(main())
