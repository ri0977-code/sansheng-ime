#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""H-165 方案 D 示意图生成（Qoder，2026-10-25 00:5x）

只画示意图，不改 App 代码。输出：
  docs/evidence/2026-10-25/h165-android-toolbar/h165-mockup-D.png

坐标按 Mate 80 竖屏 1280px = 360vp（1vp≈3.56px）：
  L1 16vp≈57px、L2 28vp≈99px、新增功能行 44vp≈156px。
"""
import os
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "evidence", "2026-10-25", "h165-android-toolbar", "h165-mockup-D.png")
ANDROID = os.path.join(ROOT, "docs", "evidence", "2026-10-25", "h165-android-toolbar", "k1_toolbar.png")

W = 1280
VP = W / 360.0            # 3.555
L1 = int(16 * VP)         # 57
L2 = int(28 * VP)         # 99
FN = int(44 * VP)         # 156

BG_PAGE = (255, 255, 255)
BG_BAR = (244, 245, 247)
BG_KEY = (255, 255, 255)
FG = (26, 26, 26)
FG_HINT = (140, 140, 140)
GOLD = (184, 134, 11)
LINE = (220, 222, 226)

FONT = r"C:\Windows\Fonts\msyh.ttc"
FONT_B = r"C:\Windows\Fonts\msyhbd.ttc"


def f(size, bold=False):
    return ImageFont.truetype(FONT_B if bold else FONT, size)


def text(d, xy, s, size=34, color=FG, bold=False, anchor="la"):
    d.text(xy, s, font=f(size, bold), fill=color, anchor=anchor)


def rrect(d, box, r, fill, outline=None):
    d.rounded_rectangle(box, radius=r, fill=fill, outline=outline)


def draw_l1(d, y, label):
    rrect(d, (0, y, W, y + L1), 0, BG_BAR)
    text(d, (W // 2, y + L1 // 2), label, 26, FG_HINT, False, "mm")


def draw_candidate_row(d, y, items):
    rrect(d, (0, y, W, y + L2), 0, BG_BAR)
    x = 10
    for it in items:
        w = 40 + len(it) * 34
        rrect(d, (x, y + 10, x + w, y + L2 - 10), 12, BG_KEY, LINE)
        text(d, (x + w // 2, y + L2 // 2), it, 34, FG, False, "mm")
        x += w + 16
    text(d, (W - 28, y + L2 // 2), "▼", 34, FG_HINT, False, "rm")


def draw_function_row(d, y):
    rrect(d, (0, y, W, y + FN), 0, BG_BAR)
    chips = ["中英", "简繁", "半角", "增廣", "反查", "…"]
    cw = (W - 150) // len(chips)
    for i, c in enumerate(chips):
        bx = 16 + i * cw
        active = c in ("简繁", "反查")
        bg = (250, 246, 235) if active else BG_KEY
        rrect(d, (bx, y + 18, bx + cw - 18, y + FN - 18), 14, bg, GOLD if active else LINE)
        text(d, ((bx + bx + cw - 18) // 2, y + FN // 2), c, 36, GOLD if active else FG, active, "mm")
    rrect(d, (W - 136, y + 18, W - 20, y + FN - 18), 14, BG_KEY, LINE)
    text(d, (W - 78, y + FN // 2), "▼", 34, FG_HINT, False, "mm")


canvas = Image.new("RGB", (W, 1900), BG_PAGE)
DRAW = ImageDraw.Draw(canvas)

text(DRAW, (20, 24), "H-165 顶部功能栏 · 方案 D 示意", 52, FG, True)
text(DRAW, (20, 92), "示意图 · 未实现 · 等主人拍板（A/B/C/D 见 spec 第三、九节）", 30, GOLD, True)

y = 170
# --- 现在 ---
text(DRAW, (20, y), "现在：44vp 候选栏——空闲时最上面一行是空的", 40, FG, True)
y += 62
draw_l1(DRAW, y, "（空闲时这一行只有 12fp 灰字 → 主人说的「空白栏」）")
y += L1
draw_candidate_row(DRAW, y, ["你好", "拟好", "你号"])
y += L2
text(DRAW, (20, y + 14), "右上角 ▼ 现在只做「展开候选网格 / 收键盘」，主人说浪费", 30, FG_HINT)
y += 76

# --- 方案 D ---
text(DRAW, (20, y), "方案 D 展开态：多一行 44vp 功能行（照安卓），点 ▼ 收起", 40, FG, True)
y += 62
draw_l1(DRAW, y, "L1 预编辑 / 反查（原样保留）")
y += L1
draw_function_row(DRAW, y)
y += FN
draw_candidate_row(DRAW, y, ["你好", "拟好", "你号"])
y += L2
text(DRAW, (20, y + 14), "中英/简繁/半角/增廣/反查 直调 setOption；… 打开开关磁贴（Reload 暂缺）", 30, FG_HINT)
y += 76

# --- 安卓实物 ---
text(DRAW, (20, y), "安卓实物（展开态，截图 @ 模拟器）", 40, FG, True)
y += 60
if os.path.exists(ANDROID):
    im = Image.open(ANDROID).convert("RGB")
    ratio = (W - 40) / im.width
    im = im.resize((W - 40, int(im.height * ratio)), Image.LANCZOS)
    canvas.paste(im, (20, y))
    y += im.height + 12
    text(DRAW, (20, y), "‹ 收起 · 撤销 · 重做 · 光标 · 剪贴板 · …（开关磁贴） · ▼ 收起", 30, FG_HINT)
    y += 44
    text(DRAW, (20, y), "注意：撤销/重做/光标/剪贴板这 4 个 v1 都不做（spec §十 逐枚实测）——", 30, GOLD)
    y += 40
    text(DRAW, (20, y), "我们那条只在 ▼ 旁边放 5 个开关 + … + ▼，不放按不动的图标。", 30, GOLD)
    y += 50

y += 10
text(DRAW, (20, y), "推荐 D：最贴安卓实物，也不占候选宽度。", 36, GOLD, True)
y += 50
text(DRAW, (20, y), "拍板只需回一个字母（A/B/C/D），我再出变更包。", 36, GOLD, True)
y += 60
canvas = canvas.crop((0, 0, W, min(1900, y + 20)))
os.makedirs(os.path.dirname(OUT), exist_ok=True)
canvas.save(OUT, "PNG")
print("MOCKUP OK:", OUT, os.path.getsize(OUT), "B", canvas.size)
