#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
三生输入法 · 键盘面板键位测量器（Qoder 归属）

为什么要有这个脚本（M3 的真机教训，`docs/evidence/2026-10-21/m3-close-run13-15-panel.md` B2 节）：
  `uitest dumpLayout` **看不到输入法面板窗口**，键位坐标只能从截图量；
  而面板存在「首帧窄布局 → relayout 铺满 2832px」的变化，期间键位整体平移，
  上一轮的坐标下一轮就全部失效 → 之前每轮注入前都要手抠一次坐标，
  这是 M3 真机回归最耗时的环节。本脚本把量法固化下来，一条命令出坐标。

量法（已在 Mate 80 上验证）：键帽是纯白 `#FFFFFF`，面板底 `#E5E7ED`，面板外 `#E3E4E6`。
逐行扫描找白色游程（run），长度在阈值以上的算「键帽的一段」，再按 y 聚成行、
按 x 聚成键，输出每键中心点（设备像素，可直接喂 `uitest uiInput click`）。

用法：
  python scripts/panel_keys.py --shot                 # 截屏 + 收回来 + 量键位
  python scripts/panel_keys.py --png path.png         # 量已有截图
  python scripts/panel_keys.py --png path.png --rows  # 只打每行的概览
  python scripts/panel_keys.py --png path.png --key 5  # 只打第 5 行第 ... 见 --pick

依赖：Pillow（`python -m pip install pillow`）。
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile

try:
    from PIL import Image
except ImportError:
    sys.exit("需要 Pillow：python -m pip install pillow")

HDC = os.environ.get(
    "SS_HDC",
    r"D:/DevTools/DevEco/DevEco Studio/sdk/default/openharmony/toolchains/hdc.exe",
)
DEVICE_TMP = "/data/local/tmp/ss_panel.png"

# 颜色判据（BGR 无所谓，这里用 RGB 元组）
KEY_CAP = (255, 255, 255)
TOL = 6              # 与纯白的容差
MIN_RUN = 18         # 白色游程短于这个像素数不算键帽（间隙/字缝）
MIN_HEIGHT = 20      # 键帽最小高度（vp→px 后 Mate 80 上远大于此）
# 键帽里的字母/图标会把一条白色游程切成几段，段间空隙 <= MERGE_GAP 的合并成同一个键。
# 24px 是 Mate 80（1280px 宽布局）上实测值：字母间隙 ~10–20px，键间隙 ~28–40px。
MERGE_GAP = 24
MIN_KEY_W = 40       # 合并后仍窄于此的段不算键（残留的字缝/图标）


def shot(dst):
    env = dict(os.environ, MSYS_NO_PATHCONV="1")
    subprocess.run([HDC, "shell", "uitest", "screenCap", "-p", DEVICE_TMP],
                   check=True, env=env, capture_output=True)
    subprocess.run([HDC, "file", "recv", DEVICE_TMP, dst], check=True,
                   env=env, capture_output=True)
    return dst


def is_cap(px, x, y):
    r, g, b = px[x, y][:3]
    return abs(r - KEY_CAP[0]) <= TOL and abs(g - KEY_CAP[1]) <= TOL and abs(b - KEY_CAP[2]) <= TOL


def measure(path, gap=MERGE_GAP):
    """返回按行分组的键帽矩形列表：[row][ {x0,x1,y0,y1,cx,cy,w,h} ]"""
    img = Image.open(path).convert("RGB")
    w, h = img.size
    px = img.load()
    # 1) 每行的白色总像素数 —— 键盘区是画面里白色最密的带
    row_white = []
    for y in range(h):
        n = 0
        x = 0
        while x < w:
            if is_cap(px, x, y):
                x0 = x
                while x < w and is_cap(px, x, y):
                    x += 1
                if x - x0 >= MIN_RUN:
                    n += x - x0
            else:
                x += 1
        row_white.append(n)
    # 2) 取白色密度 > 60% 峰值的连续行带（就是键帽所在的高度区间）
    peak = max(row_white) if row_white else 0
    if peak < 100:
        return [], (w, h)
    thr = peak * 0.6
    bands = []
    y = 0
    while y < h:
        if row_white[y] > thr:
            y0 = y
            while y < h and row_white[y] > thr:
                y += 1
            bands.append((y0, y))
        else:
            y += 1
    rows = []
    for (y0, y1) in bands:
        if y1 - y0 < MIN_HEIGHT:
            continue
        # 3) 在该行带中间取一条扫描线，收集白色游程 = 一排键
        my = (y0 + y1) // 2
        runs = []
        x = 0
        while x < w:
            if is_cap(px, x, my):
                x0 = x
                while x < w and is_cap(px, x, my):
                    x += 1
                if x - x0 >= MIN_RUN:
                    runs.append((x0, x - 1))
            else:
                x += 1
        # 4) 相邻游程合并成键（同一个键帽上被字/图标打断的段要并起来）
        keys = []
        for (x0, x1) in runs:
            if keys and x0 - keys[-1][1] <= gap:
                keys[-1] = (keys[-1][0], x1)
            else:
                keys.append((x0, x1))
        keys = [(a, b) for (a, b) in keys if b - a + 1 >= MIN_KEY_W]
        rows.append([{
            "x0": a, "x1": b, "y0": y0, "y1": y1,
            "cx": (a + b) // 2, "cy": (y0 + y1) // 2,
            "w": b - a + 1, "h": y1 - y0 + 1,
        } for (a, b) in keys])
    return rows, (w, h)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--png", help="要量的截图路径")
    ap.add_argument("--shot", action="store_true", help="先截屏再量")
    ap.add_argument("--out", help="截图保存路径（配合 --shot）")
    ap.add_argument("--row", type=int, help="只输出第 N 行（从 0 起）")
    ap.add_argument("--gap", type=int, default=MERGE_GAP, help="游程合并阈值（像素，默认 %d）" % MERGE_GAP)
    ap.add_argument("--keys-only", action="store_true", help="只打 'cx,cy' 列表，便于脚本消费")
    args = ap.parse_args()

    path = args.png
    if args.shot:
        path = args.out or os.path.join(tempfile.gettempdir(), "ss_panel.png")
        shot(path)
    if not path or not os.path.isfile(path):
        sys.exit("给 --png 路径或 --shot")

    rows, (w, h) = measure(path, gap=args.gap)
    if not rows:
        print(json.dumps({"image": [w, h], "rows": [], "note": "没找到白色键帽带：面板可能没弹起"},
                         ensure_ascii=False))
        return
    if args.row is not None:
        rows = [rows[args.row]] if args.row < len(rows) else []
    if args.keys_only:
        for i, r in enumerate(rows):
            print("row%d: " % i + " ".join("%d,%d" % (k["cx"], k["cy"]) for k in r))
        return
    print("image %dx%d，识别到 %d 行键帽" % (w, h, len(rows)))
    for i, r in enumerate(rows):
        print(" row%-2d n=%-2d band=%d..%d  %s" % (
            i, len(r), r[0]["y0"], r[0]["y1"],
            " ".join("(%d,%d)w%d" % (k["cx"], k["cy"], k["w"]) for k in r)))
    print(json.dumps({"image": [w, h],
                      "rows": [[{"cx": k["cx"], "cy": k["cy"], "w": k["w"]} for k in r] for r in rows]},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
