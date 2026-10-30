#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""H-232（Qoder 2026-10-27 22:4x 真机实测）：⤶ 面板右列「粘贴」格的**像素级**判据。

背景（为什么需要这条）:
  ⤶ 面板右列 5 格里，只有「粘贴」这一枚用系统 PasteButton，而它**不支持 layoutWeight**
  （ArkTS 实测：Property 'layoutWeight' does not exist on type 'PasteButtonAttribute'），
  所以它的尺寸只能由外层容器给。修复前它按 cellW/cellH 拿到 26.7×35.2vp：
  真机截图量到徽章 **95×123px 的椭圆**，而且比兄弟格行高（113px）还高出 10px，溢出行格。
  修复后改成「外层格子照兄弟格均分 + 内层徽章取右列行高见方」⇒ 实测 **115×115px 正圆**，不越界。
  静态口径由 scripts/h220_keymap_check.py 的 H-232 判据守住；本脚本守**画面**这一层：
  任何一次改动又把徽章拉扁或让它溢出，本脚本立刻红。

用法:
  python scripts/h232_paste_check.py                     # 量最近一次 panel.jpeg
  python scripts/h232_paste_check.py 路径/panel.jpeg     # 量指定截图
  python scripts/h232_paste_check.py --selftest          # 用合成正圆/椭圆样本验判据本身

判据（全部以像素为单位，取自 1280×2832 真机截图，vp 比 3.5556 px/vp）:
  ① 徽章是「蓝底」连通块（右列唯一是蓝色的东西），量它的外接框 w×h；
  ② 正圆：|w−h| ≤ 8px（实测修复后 115×115，修复前 95×123 ⇒ 差 28px，必红）；
  ③ 不溢出：徽章高度 ≤ 同列白卡（复制/⌫ 等）的中位高度 + 8px
     （修复前徽章 123px vs 兄弟 113px ⇒ 高出 10px，必红）。
"""
import os
import sys

try:
    from PIL import Image
except ImportError:
    print('需要 Pillow：pip install pillow')
    sys.exit(2)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_IMG = os.path.join(ROOT, 'docs', 'evidence', '2026-10-27', 'h231-panel', 'panel.jpeg')

# 右列在 1280 宽截图里的横向范围（22:39 实测：x 1012..1126）
X0, X1 = 985, 1185
Y0, Y1 = 1990, 2680

SQUARE_TOL = 8      # 正圆容差（px）
OVERFLOW_TOL = 4    # 允许比兄弟格高出的余量（px）


def is_blue(c):
    return c[2] > 170 and c[2] - c[0] > 60 and c[2] - c[1] > 40


def is_white(c):
    return c[0] >= 250 and c[1] >= 250 and c[2] >= 250


def components(px):
    """白卡 + 蓝徽章的连通块（4 邻域），返回 [(x1,x2,w,y1,y2,h,n,blue_n)]。"""
    seen = set()
    comps = []
    for y in range(Y0, Y1):
        for x in range(X0, X1):
            if (x, y) in seen:
                continue
            c = px[x, y]
            if not (is_blue(c) or is_white(c)):
                continue
            stack = [(x, y)]
            seen.add((x, y))
            pts = []
            while stack:
                a, b = stack.pop()
                pts.append((a, b))
                for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    na, nb = a + da, b + db
                    if na < X0 or na >= X1 or nb < Y0 or nb >= Y1 or (na, nb) in seen:
                        continue
                    cc = px[na, nb]
                    if is_blue(cc) or is_white(cc):
                        seen.add((na, nb))
                        stack.append((na, nb))
            if len(pts) < 200:
                continue
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            blue_n = sum(1 for p in pts if is_blue(px[p[0], p[1]]))
            comps.append((min(xs), max(xs), max(xs) - min(xs) + 1,
                          min(ys), max(ys), max(ys) - min(ys) + 1, len(pts), blue_n))
    return comps


def median(vals):
    vals = sorted(vals)
    n = len(vals)
    if n == 0:
        return 0
    return vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2.0


def judge(img):
    """返回 (ok, 说明行列表, 徽章盒子, 兄弟格中位高)。"""
    px = img.convert('RGB').load()
    comps = components(px)
    badge = None
    for c in comps:
        if c[7] > 500:          # 蓝色像素占多数 ⇒ 这是粘贴徽章
            badge = c
            break
    if badge is None:
        return False, ['[FAIL] 右列没找到蓝色粘贴徽章（截图不是 ⤶ 面板态？）'], None, 0
    x1, x2, w, y1, y2, h, _, _ = badge
    # 兄弟格＝右列里的白卡（不含徽章本体）
    sib_h = [c[5] for c in comps if c[7] == 0 and c[2] >= 60 and c[5] >= 60]
    sib_med = median(sib_h)
    lines = ['徽章外接框 x=%d..%d w=%d  y=%d..%d h=%d（正圆应 w≈h）' % (x1, x2, w, y1, y2, h),
             '同列白卡高度中位数 = %.0f px（%d 张卡）' % (sib_med, len(sib_h))]
    ok = True
    if abs(w - h) > SQUARE_TOL:
        ok = False
        lines.append('[FAIL] 徽章被拉扁：宽 %d 高 %d，差 %dpx > %dpx ⇒ 系统徽章画成椭圆'
                     % (w, h, abs(w - h), SQUARE_TOL))
    else:
        lines.append('[PASS] 徽章是正圆（宽高差 %dpx ≤ %dpx）' % (abs(w - h), SQUARE_TOL))
    if sib_med and h > sib_med + OVERFLOW_TOL:
        ok = False
        lines.append('[FAIL] 徽章溢出行格：高 %dpx > 兄弟格 %.0fpx + %dpx'
                     % (h, sib_med, OVERFLOW_TOL))
    else:
        lines.append('[PASS] 徽章不溢出行格（高 %dpx ≤ 兄弟格 %.0fpx + %dpx）'
                     % (h, sib_med, OVERFLOW_TOL))
    return ok, lines, (x1, x2, w, y1, y2, h), sib_med


def synth(badge_w, badge_h, row_h=115):
    """合成右列：一张白卡 + 一枚蓝徽章（只用来验判据本身）。"""
    img = Image.new('RGB', (1280, 2832), (242, 243, 245))
    px = img.load()
    cx = 1069
    for i in range(4):          # 兄弟白卡
        top = 2024 + i * 129
        for y in range(top, top + row_h):
            for x in range(cx - 40, cx + 40):
                px[x, y] = (255, 255, 255)
    bx1 = cx - badge_w // 2
    by1 = 2024 + 3 * 129
    for y in range(by1, by1 + badge_h):
        for x in range(bx1, bx1 + badge_w):
            px[x, y] = (0, 110, 255)
    return img


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if '--selftest' in sys.argv:
        ok1, l1, _, _ = judge(synth(115, 115))
        # 坏样本按真机「修复前」的实测量复刻：兄弟白卡 113px 高、徽章 95×123px
        ok2, l2, _, _ = judge(synth(95, 123, row_h=113))
        print('--- 样本A 正圆 115×115 ---')
        for l in l1:
            print(l)
        print('--- 样本B 椭圆 95×123（修复前的实测量）---')
        for l in l2:
            print(l)
        if (not ok1) or ok2:
            print('SELFTEST FAIL：正圆样本应过、椭圆样本应红，实际 A=%s B=%s' % (ok1, ok2))
            return 1
        print('SELFTEST OK：正圆样本判过、椭圆样本判红（判据本身有效）')
        return 0

    path = args[0] if args else DEFAULT_IMG
    if not os.path.exists(path):
        print('找不到截图：%s' % path)
        return 2
    ok, lines, box, sib = judge(Image.open(path))
    print('量图：%s' % path)
    for l in lines:
        print(l)
    print('结论：%s' % ('PASS（粘贴格是正圆且不溢出）' if ok else 'FAIL（粘贴格被拉扁或溢出）'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
