#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""三生输入法 · AGC 商店/包内图标母版（黑底金，Qoder 归属，M6 ⑤）

为什么重写（H-147，2026-10-23 12:5x）
--------------------------------------
12:14 CodeArts 说「AppScope 分层图标换黑底金（前景=nova6金图形）」，我拿真源
（`F:/dshdesktopwork/sansheng-ime-android/_backup_ascii_rename_20261021/发布-安卓-1.10.1-20261021/1-三生输入法-1.10.1-android.apk`
里 `res/mipmap-xxxhdpi/ic_launcher.png`，192×192）逐像素量了一遍：

  nova6 真源（192 画布）          包里现在那张（1024 画布）
  ─────────────────────────       ─────────────────────────
  背景 纯黑 (0,0,0)                背景 纯黑 (0,0,0)          ✓ 一致
  外圈金环 r≈75、环宽≈4            没有外环                   ✗ 丢了
  三条金杠 x=56..137（宽 81）      三条金杠                    ✓ 有
  杠色 (255,231,118)               杠色 (255,224,114) 附近     ≈ 一致

⇒ 包内那张**不是从 nova6 提取的**，是把 10-22 那套「蓝底三条白杠」的几何重新上色的
产物（三条杠的 x 区间 56..137 与旧蓝图 188..836/1024 归一化后同形）。主人认识的
「黑底金」是**带外圈金环**的那个（nova6 桌面上就是它），少了环＝商店与安卓端不一致，
老用户认不出来。

口径（D-022，2026-10-23 12:5x 定案）：品牌＝**nova6 黑底金（含外环）**，
按「能过审怎么来」定案，不再问主人。本脚本按实测几何重画，产物归本项目所有。

用法：
  python scripts/make_store_icon.py             # dry run，只打印
  python scripts/make_store_icon.py --write     # 落盘
"""
import argparse
import hashlib
import io
import os
import sys

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── 从 nova6 `res/mipmap-xxxhdpi/ic_launcher.png`（192×192）逐像素量出来的几何 ──
SRC_W = 192
BLACK = (0, 0, 0)
RING_HI = (255, 224, 114)     # 环顶部（y=23 处实测）
RING_LO = (252, 217, 111)     # 环底部（y=169 处实测）
BAR_TOP = (255, 231, 118)     # 杠顶（y=64 处实测）
BAR_BOT = (250, 215, 110)     # 杠底（y=100 处实测）
RING_R = 75.0                 # 环半径（y=20..24 与 y=167..171 ⇒ 96-75=21）
RING_W = 5.0                  # 环宽（y=20..24 = 5px）
BAR_X0, BAR_X1 = 56, 137      # 三条杠水平区间（宽 81，中心列实测）
BAR_H = 17.0                  # 杠高（y=48..65 = 18px，取中 17）
BAR_GAP = 20.0                # 杠间距（y=65..86 = 21px，取中 20）

TARGETS = [
    # (相对仓库的路径, 尺寸)
    ("docs/release/store/icon/layered/preview-216.png", 216),
    ("docs/release/store/icon/layered/preview-launcher-1024.png", 1024),
    ("docs/release/store/icon/layered/preview-square-1024.png", 1024),
    ("docs/release/store/icon/layered/background-1024.png", 1024),
    ("docs/release/store/icon/layered/foreground-1024.png", 1024),
    ("docs/release/store/icon/gen-appicon-512.png", 512),
    ("docs/release/store/icon/gen-appicon-1024.png", 1024),
    ("docs/release/store/icon/gen-appicon-216.png", 216),
]


def draw(size):
    """按 nova6 实测几何画一张 size×size 的方图（黑底 + 金环 + 三杠）。"""
    k = size / float(SRC_W)
    im = Image.new("RGB", (size, size), BLACK)
    d = ImageDraw.Draw(im)
    cx = cy = size / 2.0
    r = RING_R * k
    wd = max(2, int(round(RING_W * k)))
    # 外环：nova6 实测环色上 (255,224,114) 下 (252,217,111) 几乎同色 ⇒ 用主体色
    # 单色画整圈。曾试过逐行插值画左右两段弧，在 216/432 上出现断点和接缝，废掉。
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=RING_LO, width=wd)
    # 三条杠（nova6 实测为直角、无圆角；金色带轻微垂直渐变）
    bh = BAR_H * k
    gap = BAR_GAP * k
    x0, x1 = BAR_X0 * k, BAR_X1 * k
    total = 3 * bh + 2 * gap
    y = cy - total / 2.0
    for i in range(3):
        seg = max(2, int(round(bh)))
        for j in range(seg):
            t = j / float(seg - 1)
            col = tuple(round(a + (b - a) * t) for a, b in zip(BAR_TOP, BAR_BOT))
            yy = y + j * bh / seg
            d.line([(x0, yy), (x1, yy)], fill=col)
        y += bh + gap
    return im


def md5b(b):
    return hashlib.md5(b).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()

    for rel, size in TARGETS:
        dst = os.path.join(ROOT, rel.replace("/", os.sep))
        img = draw(size)
        buf = io.BytesIO()
        img.save(buf, "PNG", optimize=True)
        data = buf.getvalue()
        old = ""
        if os.path.exists(dst):
            old = md5b(io.open(dst, "rb").read())
        print("  %-52s %4dx%-4d %6d B  md5 %s%s"
              % (rel, size, size, len(data), md5b(data),
                 ("  ← 覆盖（旧 %s）" % old) if old else "  ← 新文件"))
        if a.write:
            io.open(dst, "wb").write(data)
    if not a.write:
        print("dry run：加 --write 才落盘")
    return 0


if __name__ == "__main__":
    sys.exit(main())
