#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""H-165 + H-168 装机后真机自验（Qoder，2026-10-25 15:2x 重写）

为什么重写（真机教训，同 `panel_keys.py` 的 M3 教训）：
  上一版把三角/磁贴/菜单项坐标**写死成像素值**，而键盘面板在 `uitest dumpLayout` 里
  一个节点都不暴露（实测 `kb.json` 里只有应用页的树）⇒ 布局一变（H-165 返工把三角从
  屏幕正中 x=668 挪回候选行最左）全部坐标作废，点在空白处就产不出日志，白跑一轮。
  本版**坐标一律运行时量出来**：
    · 面板矩形 ← `hidumper -s WindowManagerService -a '-a'` 的 `softKeyboard1` 行
    · 密度    ← `hidumper -s DisplayManagerService -a -a` 的 `Density:`
    · 磁贴中心 ← 截图白色键帽游程检测（复用 `panel_keys.measure`，磁贴底色就是 BG_KEY=白）
    · 三角中心 ← 面板顶 + (CAND_PAD_H + FUNC_TRI_LEFT_W/2, commentRow + candRow/2) × 密度（H-188）
  量不到就**报错退出**，不再拿占位坐标蒙。

判据（主人 2026-10-25 拍板「装，自验后回数字」）：
 H-165（形态 B 返工后）——
   a) 收起态：▶ 画在候选行**最左**（中心 x ≈ 面板左 + (8+18)vp×密度），不在屏幕正中（缺陷 A 的对照）；
      点 ▶ 展开成「▼＋6 枚磁贴」，再点 ▼ 收起。
   b) 点「中英」磁贴 → 磁贴大字与底栏简/英键**同时**翻转（缺陷 D：按值参数冻住的对照——
      上一版实测引擎 ascii_mode=1、底栏已「英」而磁贴仍「中」）。
   c) 切九键后磁贴只剩 4 枚白底（增廣/注释变 BG_BAR＝白色检测扫不到），点它无反应。
   f) **几何预算**：候选栏带高 = candBarHeight()×密度，且主键区第一行紧跟其下（缺陷 B 的对照：
      上一版磁贴溢出压到 q 行、候选字被键帽盖住 ⇒ H-168 的 ▼ 点不开）。
 H-168——
   d) ▼（候选行最右）展开网格；网格能出多屏。
   e) 上下滑整屏翻页有过渡、**末屏可达**：按 `H-168 gridFlip ... screen=k/N` 日志报数字。

注入铁律：只点本应用 `com.sansheng.ime` 自己的界面（试打框 + 键盘面板），
绝不碰第三方应用、绝不往别人的文档里注入输入、绝不用退格/清空循环。

用法：
  python scripts/h165_h168_device_accept.py probe      # 只量几何，不注入（装机前先跑通量法）
  python scripts/h165_h168_device_accept.py run        # 全流程自验
  python scripts/h165_h168_device_accept.py run --dry-run
  python scripts/h165_h168_device_accept.py clear      # 清 hilog 缓冲
  python scripts/h165_h168_device_accept.py tap X Y / shot NAME / dump NAME
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from panel_keys import measure  # noqa: E402  白色键帽游程检测（同一套量法，别再复制一份）

HDC = os.environ.get("SS_HDC",
                     r"D:/DevTools/DevEco/DevEco Studio/sdk/default/openharmony/toolchains/hdc.exe")
DEV = "7GL0226408083897"
BUNDLE = "com.sansheng.ime"
ABILITY = "EntryAbility"
TAG = "SSKeyboardIndex"
DRY = False
EVID = os.path.join(ROOT, "docs", "evidence", "2026-10-25", "h165-h168-device")

DEV_ERR_MARKERS = ("inaccessible or not found", "[Fail]", "error: ", "unknown option")

# ---- 与 ArkTS 同源的几个布局常量（改 KeyboardIndex.ets 时同步这里；闸门只测源码侧）----
CAND_PAD_H = 8          # KeyboardIndex.ets CAND_PAD_H
FUNC_TRI_WIDTH = 36     # KeyboardIndex.ets FUNC_TRI_WIDTH（展开网格 ▼ / 工具栏首末枚）
FUNC_TRI_LEFT_W = 24    # H-188 KeyboardIndex.ets FUNC_TRI_LEFT_W（收起态最左 ›；中心 = 8+12 = 20vp）
CAND_ROW_RIGHT_PAD = 2  # H-188 候选行右内边距（8→2，把 ▼ 中心对齐到屏宽 94.4%）
COMMENT_ROW_H = 16      # commentRowHeight() 竖屏定值
CAND_ROW_H = 28         # candRowHeight() @ candFs=18（Mate80 走 18 档）
BAR_H = COMMENT_ROW_H + CAND_ROW_H   # candBarHeight() 竖屏 = max(44, 16+28) = 44vp

# 试打框：按控件类型（TextArea/TextInput）在 dumpLayout 里现找，找不到的兜底默认位
# ＝ 实测 bounds [70,1466][1210,1849] 的中心（kb.json，2026-10-25 14:2x）。
# 长按弹「26键/九键」方案的入口键与菜单项：一律**运行时现量**，不写死。
# 写死过一次的教训：15:36 那轮用 14:3x 的旧坐标（globe (440,2638)、九键 (100,2400)），
# 菜单没弹着，点击落到第三方应用里去；此后两步全废，还差点继续往别人家应用注入。
# 现在由 bottom_bar_keys()/menu_rows() 现量，量不到就 SystemExit。


def sh(*args, check=False, cwd=None):
    a = [str(x) for x in args]
    if a and a[0] == "shell":
        a = ["shell", " ".join(a[1:])]
    if DRY:
        print("DRY hdc -t %s %s" % (DEV, " ".join(a)))
        return ""
    env = dict(os.environ)
    env["MSYS_NO_PATHCONV"] = "1"
    r = subprocess.run([HDC, "-t", DEV] + a, capture_output=True, env=env, cwd=cwd)
    txt = ((r.stdout or b"") + (r.stderr or b"")).decode("utf-8", "replace")
    if check and (r.returncode != 0 or any(m in txt for m in DEV_ERR_MARKERS)):
        raise SystemExit("hdc 失败: %s\n%s" % (" ".join(a), txt))
    return txt


def tap(x, y):
    print("TAP (%d,%d)" % (int(x), int(y)))
    sh("shell", "uitest uiInput click", str(int(x)), str(int(y)), check=True)
    time.sleep(0.35)


def press(x, y):
    print("LONGPRESS (%d,%d)" % (int(x), int(y)))
    sh("shell", "uitest uiInput longClick", str(int(x)), str(int(y)), check=True)
    time.sleep(0.5)


def swipe(x1, y1, x2, y2, v=2000):
    sh("shell", "uitest uiInput swipe %d %d %d %d %d" %
       (int(x1), int(y1), int(x2), int(y2), int(v)), check=True)
    time.sleep(0.45)


def shot(name):
    os.makedirs(EVID, exist_ok=True)
    remote = "/data/local/tmp/%s.jpeg" % name
    sh("shell", "snapshot_display -f", remote, check=True)
    sh("file", "recv", remote, (name + ".jpeg"), check=True, cwd=EVID)
    p = os.path.join(EVID, name + ".jpeg")
    print("SHOT %s%s" % (p, "" if DRY else " (%d B)" % os.path.getsize(p)))
    return p


def dump(name="h165_lay"):
    remote = "/data/local/tmp/%s.json" % name
    sh("shell", "uitest dumpLayout -p", remote, check=True)
    sh("file", "recv", remote, (name + ".json"), check=True, cwd=EVID)
    return os.path.join(EVID, name + ".json")


def launch():
    print(sh("shell", "aa start -a", ABILITY, "-b", BUNDLE))


# ---------------- 运行时几何 ----------------

RECT_RE = re.compile(r"\[\s*(-?\d+)\s+(-?\d+)\s+(\d+)\s+(\d+)\s*\]")


def panel_rect():
    """键盘面板矩形：hidumper WMS 全量窗口表里第一条名字含 KeyboardPanel / softKeyboard 的行。
    实测 Mate80 出键盘时两条都在：
      `SCBKeyboardPanel  ... [ 0 1849 1280 983 ]`   ← 用这条（983px 与像素量到的
        「候选栏 152 + 键区 665 + 底栏 160」一致，H-165 缺陷 B 就是按它算的零余量）
      `softKeyboard1     ... [ 0 1849 1280 826 ]`   ← IME 窗口本体，比视觉面板矮（不含系统让出的那条）
    `SCBKeyboardDialog*` 是整屏 [0 0 1280 2832]，按 h<1500 排除。
    量不到直接 SystemExit —— 上一版占位坐标就是这么把一轮装机跑废的。"""
    if DRY:
        print("DRY: 面板矩形用实测值 [0 1849 1280 983]")
        return (0, 1849, 1280, 983)
    txt = sh("shell", "hidumper -s WindowManagerService -a '-a'")
    for line in txt.splitlines():
        if "softKeyboard" in line or "KeyboardPanel" in line:
            m = RECT_RE.search(line)
            if m:
                x, y, w, h = (int(g) for g in m.groups())
                if w > 0 and h > 0 and h < 1500:      # 整屏那条（2832）不是面板
                    print("PANEL %-18s rect=[%d %d %d %d]" % (line.split()[0], x, y, w, h))
                    return (x, y, w, h)
    raise SystemExit("没在 hidumper WMS 表里找到键盘面板矩形——键盘没弹起？先跑 run 的第 1 步出键盘")


def density():
    """px/vp：`hidumper -s DisplayManagerService -a -a` 的 `Density:`（Mate80 实测 3.5）。
    旧笔记里那个 3.4545 是拿「候选栏 152px ÷ 44vp」反推的，误差来自带高本身是目测的，不作准。"""
    if DRY:
        print("DRY: Density 用实测值 3.5")
        return 3.5
    txt = sh("shell", "hidumper -s DisplayManagerService -a -a")
    m = re.search(r"Density:\s*([\d.]+)", txt)
    if not m:
        raise SystemExit("读不到 Density——换用 --density 显式给")
    return float(m.group(1))


def tri_point(rect, d, expanded=False):
    """折叠三角中心：收起态在候选行（L1 之下）最左；展开态在磁贴行整栏居中高。"""
    x = rect[0] + (CAND_PAD_H + FUNC_TRI_LEFT_W / 2.0) * d
    if expanded:
        y = rect[1] + BAR_H / 2.0 * d
    else:
        y = rect[1] + (COMMENT_ROW_H + CAND_ROW_H / 2.0) * d
    return (int(round(x)), int(round(y)))


def grid_tri_point(rect, d):
    """候选行最右的「展开网格」三角（H-188 后）：Stack 定宽 36vp，Row 右内边距 2vp ⇒
    中心 x = 面板右 − (2+18)vp = 94.4% 屏宽，与展开后工具栏最后一枚 ▼ 同一条竖线。"""
    x = rect[0] + rect[2] - (CAND_ROW_RIGHT_PAD + FUNC_TRI_WIDTH / 2.0) * d
    y = rect[1] + (COMMENT_ROW_H + CAND_ROW_H / 2.0) * d
    return (int(round(x)), int(round(y)))


def grid_swipe_band(rect, d):
    """展开态网格的滑动带：`build()` 里 expanded 时 ExpandedPanel **替换掉键区**
    （Column = CandidateBar + ExpandedPanel），所以安全区＝候选栏以下到面板底。
    绝不把滑动算进键区——H-165/166 之后键面带上下滑手势，滑到键上会打出符号（污染证据）。
    **下边界必须再往上收 200px**：面板底 2832 是**系统导航条**（Home 指示条），
    2026-10-25 15:36 上一版把起点放在 y=2802，滑动被系统当成上滑返回 ⇒ 直接退回桌面，
    后面几步的点击全落在第三方应用页上（购物 App 的列表）——这是真事故，不是「坐标小偏差」。
    现在滑动带上限＝面板底 −200px，且**注入前必须过 `assert_our_app()` 这道闸**。"""
    lo = int(rect[1] + (BAR_H + 6) * d)          # 靠上（下一屏从此划走）
    hi = int(rect[1] + rect[3] - 200)            # 靠下，但离系统导航条远远的
    if hi - lo < 200:
        hi = lo + 200
    return (lo, hi)


def assert_our_app(tag=""):
    """注入前的安全闸：确认当前前台是**本应用**（dumpLayout 里有「三生输入法」）。
    为什么要这道闸：2026-10-25 15:36 那轮，滑动越界触发系统返回手势，跑到桌面后
    后续点击落进了第三方购物应用——违反「注入工具/第三方应用铁律」。任何一步发现
    前台不是本应用就**立刻停下**，不再注入。"""
    p = dump("zz_guard")
    try:
        tree = json.load(open(p, encoding="utf-8"))
    except Exception as e:
        raise SystemExit("GUARD 失败：dump 读不出来（%s），拒绝继续注入" % e)
    found = []

    def walk(n):
        if isinstance(n, dict):
            a = n.get("attributes", n)
            if "三生输入法" in str(a.get("text", "")):
                found.append(1)
            for v in n.values():
                walk(v)
        elif isinstance(n, list):
            for v in n:
                walk(v)

    walk(tree)
    if not found:
        raise SystemExit("GUARD 失败：前台不是本应用（dump 里没有「三生输入法」），"
                         "拒绝注入——可能已被系统手势带去了别的 App")
    print("GUARD ok%s：前台＝本应用" % (("（%s）" % tag) if tag else ""))
    return True


# 字母行 → 该行白帽序列里的下标偏移（第三行首尾是 shift / 退格，字母从 1 起）
LETTER_ROWS = (("qwertyuiop", 0), ("asdfghjkl", 0), ("zxcvbnm", 1))


def key_band_rows(png, rect, d):
    """键区白帽行：只取**起点在候选栏带之下**的带（候选栏底色是 BG_BAR 灰、不出白帽，
    面板以上的应用页白区也不该被当键）。返回顺序＝从上到下＝q 行、a 行、z 行、底栏。"""
    if not os.path.exists(png):          # DRY 或截图没落盘：没有可量的图，返回空行
        rows = []
    else:
        rows = measure(png)[0]
    out = [r for r in rows if r and r[0]["y0"] >= rect[1] + BAR_H * d - 6]
    print("  键区行数=%d %s" % (len(out), [(r[0]["y0"], r[0]["y1"], len(r)) for r in out]))
    return out


def letter_point(rows, ch):
    """按字母表位置在实测白帽行里取中心——不写死像素（上一版写死 q 行 y=2090，
    H-165 返工后键区上移，整套作废）。"""
    for ri, (spec, off) in enumerate(LETTER_ROWS):
        if ch in spec:
            if not rows and DRY:
                # 只为打印计划用旧实测行（q 行 y=2090、行距 163px），真跑时 rows 一定来自现量
                return (63 + 128 * spec.index(ch), 2090 + 163 * ri)
            if len(rows) <= ri:
                raise SystemExit("键区没量够 3 行（只 %d 行），取不到字母 %s——拒用占位坐标" % (len(rows), ch))
            i = spec.index(ch) + off
            row = rows[ri]
            if i >= len(row):
                raise SystemExit("字母 %s 应在第 %d 行第 %d 个，但该行只有 %d 个白帽" % (ch, ri, i, len(row)))
            return (row[i]["cx"], row[i]["cy"])
    raise SystemExit("不是字母: %s" % ch)


def bar_band_rows(png, rect, d):
    """把截图里**落在候选栏带内**的白色键帽行取出来（磁贴行/键区都会出现）。
    注意：磁贴行往往过不了 `measure` 的白色密度阈值，真正的磁贴数看 `measure_tiles`。"""
    rows = measure(png)[0] if os.path.exists(png) else []
    bar_lo, bar_hi = rect[1], rect[1] + BAR_H * d
    in_bar = [r for r in rows if r and abs(r[0]["cy"] - (bar_lo + bar_hi) / 2) < BAR_H * d * 0.6]
    return rows, in_bar


def white_runs_px(px, w, y, min_run=18, gap=24):
    """一条扫描线上的白帽游程（磁贴/键帽底色都是 BG_KEY=白，面板底 BG_BAR=灰）。
    为什么不用 `panel_keys.measure` 找磁贴：它按「全图白色密度峰值的 60%」筛行带，
    磁贴一行只有 6 个小块（实测约 600px 白）远低于键区一行（约 1100px），会被阈值整行丢掉
    ——拿旧证据 `c2_func.jpeg` 复现过：`measure()` 在候选栏带内一条带都没报（in_bar=0）。"""
    def is_white(x):
        r, g, b = px[x, y][:3]
        return abs(r - 255) <= 6 and abs(g - 255) <= 6 and abs(b - 255) <= 6

    runs = []
    x = 0
    while x < w:
        if is_white(x):
            x0 = x
            while x < w and is_white(x):
                x += 1
            if x - x0 >= min_run:
                runs.append([x0, x - 1])
            x += 1
        else:
            x += 1
    merged = []
    for (a, b) in runs:
        if merged and a - merged[-1][1] <= gap:
            merged[-1][1] = b
        else:
            merged.append([a, b])
    return [(a, b) for (a, b) in merged if b - a + 1 >= 40]


def scan_white_runs(png, y, min_run=18, gap=24):
    """同 white_runs_px，但按路径开图（单次探查用；批量扫描自己 load 一次）。"""
    from PIL import Image
    if not os.path.exists(png):
        return []
    im = Image.open(png).convert("RGB")
    w, _ = im.size
    return white_runs_px(im.load(), w, y, min_run, gap)


def measure_tiles(png, rect, d):
    """候选栏带内的白底磁贴：**在带内多条扫描线里挑白块数最多的一条**，那条的白色游程就是磁贴。
    为什么不是按列投票：按列投票在旧证据 `c2_func.jpeg` 上给出 5 段、中心还整体偏 +76px
    （那版磁贴只占半条带，投票把缝隙也投成了段）——同一份旧图上单线法 y=1932 给出的
    6 段中心（82/218/354/490/639/788）与人工量的磁贴中心完全一致，所以以单线法为准。
    多扫几条线是为了不怕 JPEG 振铃（某条线恰好压在字缝上会少一两块）。"""
    if DRY:
        # 只为打印计划，**不作判据**：值取自 14:3x 旧装机实测（缺陷 B 那版，磁贴行整体偏低 ~6px）
        print("DRY: 磁贴用 14:3x 实测占位（真跑时按候选栏带内多线现量）")
        return [(82, 1932, 94), (218, 1932, 94), (354, 1932, 94),
                (490, 1932, 94), (639, 1932, 120), (788, 1932, 94)]
    from PIL import Image
    if not os.path.exists(png):
        return []
    im = Image.open(png).convert("RGB")
    w, _ = im.size
    px = im.load()
    y0 = int(rect[1] + 8)
    y1 = int(rect[1] + BAR_H * d - 8)
    best = []
    best_y = None
    for y in range(y0, y1, 4):
        rs = white_runs_px(px, w, y, min_run=18, gap=24)
        if len(rs) > len(best):
            best, best_y = rs, y
    if not best:
        return []
    return [((a + b) // 2, best_y, b - a + 1) for (a, b) in best]


def report_bands(png, rect, d, label):
    """判据 f 的数字：候选栏带里白底磁贴有几枚、键区第一行从哪开始（溢出对照）。"""
    rows, in_bar = bar_band_rows(png, rect, d)
    print("  [%s] 白色行带 %d 条；候选栏带(±%dpx)内 %d 条" % (
        label, len(rows), int(BAR_H * d), len(in_bar)))
    for i, r in enumerate(rows):
        print("     band%-2d y=%d..%d n=%d  %s" % (
            i, r[0]["y0"], r[0]["y1"], len(r),
            " ".join("%d,%d" % (k["cx"], k["cy"]) for k in r[:9])))
    return rows, in_bar


def find_testbox_center():
    """试打框中心：应用页节点在 dumpLayout 里可见（实测 `kb.json` 有一条
    `TextArea bounds=[70,1466][1210,1849]`），按控件类型找、取面积最大那条。
    不按文案找——输入框的 text 是**已输入内容**（实测「笔帝之之军田g bvhj」），没有「试打」二字。"""
    p = dump("zz_testbox")
    try:
        tree = json.load(open(p, encoding="utf-8"))
    except Exception as e:
        print("WARN dump 解析失败(%s)，试打框用默认位" % e)
        return (640, 1657)
    hits = []

    def walk(n):
        if isinstance(n, dict):
            attrs = n.get("attributes", n)
            if str(attrs.get("type", "")) in ("TextArea", "TextInput"):
                m = re.findall(r"-?\d+", str(attrs.get("bounds", "")))
                if len(m) == 4:
                    hits.append(tuple(int(v) for v in m))
            for v in n.values():
                walk(v)
        elif isinstance(n, list):
            for v in n:
                walk(v)

    walk(tree)
    if not hits:
        print("WARN dump 里没有 TextArea/TextInput 节点，试打框用默认位")
        return (640, 1657)
    x0, y0, x1, y1 = max(hits, key=lambda r: (r[2] - r[0]) * (r[3] - r[1]))
    c = ((x0 + x1) // 2, (y0 + y1) // 2)
    print("TESTBOX bounds=[%d %d %d %d] center=%s" % (x0, y0, x1, y1, c))
    return c


# ---------------- 日志（面板无 dump 节点，翻屏计数只能按日志）----------------

DEV_SNIP = "/data/local/tmp/h165_hilog.txt"


def log_flush():
    sh("shell", "%s -x | grep %s >> %s" % ("hilog", TAG, DEV_SNIP))


def log_clear():
    sh("shell", "hilog", "-r")
    print("hilog 缓冲已清")


def log_pull(name="h165_hilog"):
    log_flush()
    sh("file", "recv", DEV_SNIP, (name + ".txt"), check=True, cwd=EVID)
    sh("shell", "rm", "-f", DEV_SNIP)
    p = os.path.join(EVID, name + ".txt")
    if not os.path.exists(p):
        print("LOG %s 不在（DRY？）" % p)
        return "", []
    txt = open(p, encoding="utf-8", errors="replace").read()
    flips = re.findall(r"H-168 gridFlip dir=(-?\d+) step=(\d+) len=(\d+) maxOff=(\d+) "
                       r"off=(\d+)->(\d+) screen=(\d+)/(\d+)", txt)
    print("LOG %s：gridFlip 命中 %d 行" % (p, len(flips)))
    for f in flips:
        print("   dir=%s step=%s len=%s maxOff=%s off=%s->%s screen=%s/%s" % f)
    return txt, flips


# ---------------- 主流程 ----------------

def crop(png, name, box):
    """按区域裁小图存证——磁贴大字/底栏简英键这种「字是哪个」的判断只能看图，
    像素游程只能数块数、认不出字形。box=(x0,y0,x1,y1)。"""
    from PIL import Image
    out = os.path.join(EVID, name + ".png")
    if not os.path.exists(png):
        print("CROP skip（DRY/图不在）%s %s" % (out, box))
        return out
    Image.open(png).convert("RGB").crop(box).save(out)
    print("CROP %s %s (%d B)" % (out, box, os.path.getsize(out)))
    return out


def steps_probe():
    d = density()
    rect = panel_rect()
    p = shot("g0_probe")
    report_bands(p, rect, d, "probe")
    print("TRI 收起态中心 %s / 展开态 %s / 网格三角 %s / 磁贴扫描线 y=%d" % (
        tri_point(rect, d), tri_point(rect, d, True), grid_tri_point(rect, d),
        int(rect[1] + BAR_H * d / 2)))
    return rect, d


def bottom_bar_keys(png, rect, d):
    """底栏按键中心（从左到右）：底栏是面板最下面一条（实测 y≈2518..2656，即面板底 −314..−182px）。
    上一版把 globe 写死成 (440,2638)（旧几何，H-165 返工后键区上移，整套失效）——
    那轮长按点空、菜单没弹出来，后面的点击全落到第三方应用里。这版**现量**：
    按列统计「键帽色或白色」的像素占比，连续高占比的列段＝一个键。
    实测（`a0_kb_up.jpeg`，Mate80）出 4 个非白键：globe 15..140(cx=77)、?123 175..215、
    emoji 232..272、英 371..403；白色键（空格/回车）另算，不影响取左数第一个。"""
    from PIL import Image
    if not os.path.exists(png):
        return []
    im = Image.open(png).convert("RGB")
    w, _ = im.size
    px = im.load()
    y0 = int(rect[1] + rect[3] - 320)
    y1 = int(rect[1] + rect[3] - 180)
    step = 2
    n_rows = max(1, len(range(y0, y1, step)))
    frac = []
    for x in range(w):
        n = 0
        for y in range(y0, y1, step):
            c = px[x, y]
            is_cap = (abs(c[0] - 202) <= 10 and abs(c[1] - 206) <= 10 and abs(c[2] - 218) <= 10)
            is_white = min(c) >= 246
            if is_cap or is_white:
                n += 1
        frac.append(n / float(n_rows))
    segs = []
    x = 0
    while x < w:
        if frac[x] > 0.6:
            a = x
            while x < w and frac[x] > 0.6:
                x += 1
            if x - 1 - a + 1 >= 30:
                segs.append((a, x - 1))
        else:
            x += 1
    return [((a + b) // 2, (y0 + y1) // 2, b - a + 1) for (a, b) in segs]


def steps_t9(rect, d, png_kb=None):
    """判据 c：切九键 → 白底磁贴应只剩 4 枚（增廣/注释置灰＝底色变 BG_BAR，白色扫描扫不到）。
    全部现量：globe 键从底栏扫描结果里取（不写死 440,2638——那是旧几何）；
    菜单项从**长按后现截的图**里量（不写死 100,2400），量不到就报错停下，不猜。
    上一版（15:36 那轮）没现量，菜单点击落到了别处，连带把滑动也带出了应用。"""
    assert_our_app("切九键前")
    keys = bottom_bar_keys(png_kb, rect, d)
    print("  底栏按键现量：%s" % (keys[:6],))
    if not keys:
        raise SystemExit("底栏一颗键都没量到——拒用写死坐标长按（那会点到别处）")
    globe = keys[0]                     # 左数第一个＝语言/方案键
    press(*globe[:2])
    time.sleep(0.8)
    p = shot("d0_menu")
    assert_our_app("长按出菜单后")
    # 菜单行现量：菜单是盖在键区上的浮层，取带内白色行段，从上往下第二条＝九键
    menu = menu_rows(p, rect)
    print("  菜单行现量：%s" % (menu,))
    if len(menu) < 2:
        raise SystemExit("菜单没量到两行（26键/九键）——拒用写死坐标点（那会点到别处）")
    tap(*menu[-1][:2])                  # 最后一行＝九键（实测 26键 在上、九键 在下）
    time.sleep(1.0)
    p = shot("d1_t9_kb")
    assert_our_app("切九键后")
    rect = panel_rect()                 # 九键面板几何会变，重新量
    tap(*tri_point(rect, d))
    time.sleep(0.8)
    p = shot("d2_t9_func")
    assert_our_app("九键展开磁贴后")
    pts = measure_tiles(p, rect, d)
    print("H165-c 九键白底磁贴 %d 枚（应为 4：简繁/中英/半全/标点；增廣/注释置灰）：%s" % (len(pts), pts))
    crop(p, "d2_t9_tiles", (0, int(rect[1]), rect[2], int(rect[1] + BAR_H * d)))
    tap(*tri_point(rect, d, True))
    time.sleep(0.5)
    return rect, pts


def menu_rows(png, rect):
    """方案切换菜单的两行（26键/九键）中心。菜单是白底浮层盖在变暗的键区上：
    实测整块白区 x=28..587、y≈2178..2474，两行文字各在一段里（26键 ≈2226–2266、
    九键 ≈2378–2426）⇒ 在白色浮层的 y 区间内，按**行内暗像素（文字）数量**聚成两簇，
    每簇的中心 y 就是该行点击点；x 取浮块左中（实测 cx≈300）。量不到就返回空，调用方报错停下。"""
    from PIL import Image
    if not os.path.exists(png):
        return []
    im = Image.open(png).convert("RGB")
    w, _ = im.size
    px = im.load()
    # 1) 找白色浮块的 y 范围：取一行白色游程最宽的几行聚成块
    ys = []
    for y in range(int(rect[1] + 200), int(rect[1] + rect[3]), 3):
        rs = white_runs_px(px, w, y, min_run=120, gap=20)
        if rs:
            a, b = rs[0]
            ys.append((y, a, b))
    if not ys:
        return []
    top = min(y for y, _, _ in ys)
    bot = max(y for y, _, _ in ys)
    # 2) 块内逐行统计**非白**像素数，找出两个文字行。
    #    实测色值：纯白底 (255,255,255)、选中行蓝字 (45,95,192)、未选中行深字 (73,73,73)，
    #    JPEG 噪点会给到 250+ ⇒ 判据取 min(c) < 240（纯白放行，蓝/深字命中）。
    #    选中那行是**蓝色**不是深色，所以不能用「暗像素」判，否则只测得出一行。
    ink_rows = []
    for y in range(top, bot + 1):
        n = 0
        for x in range(ys[0][1], ys[0][2] + 1, 2):
            if min(px[x, y]) < 240:
                n += 1
        ink_rows.append((y, n))
    peak = max(n for _, n in ink_rows) or 1
    # thr=14 实测能同时拿到两行（26键 2229–2272、九键 2384–2426）；
    # 取 25 以上就只剩一行（九键墨量本就比选中的蓝字少）——阈值不能按峰值比例放大。
    thr = max(14, peak * 0.05)
    clusters = []
    cur = []
    for (y, n) in ink_rows:
        if n >= thr:
            cur.append(y)
        elif cur:
            clusters.append(cur)
            cur = []
    if cur:
        clusters.append(cur)
    # 相邻文字簇间距 <40px 的并成一个（一个字里笔画之间也有空隙，不能算两行）
    merged = []
    for c in clusters:
        if merged and c[0] - merged[-1][-1] <= 40:
            merged[-1].extend(c)
        else:
            merged.append(list(c))
    # 分隔线滤掉：两行菜单之间有一条**整行**的灰色分隔线（实测 y=2332、非白采样点 280 个），
    # 它高 1–3px，而文字行高 40px 上下 ⇒ 按高度区分，不按墨量区分（分隔线墨量比文字大）。
    merged = [c for c in merged if len(c) >= 8]
    cx = (ys[0][1] + ys[0][2]) // 2
    return [(cx, (c[0] + c[-1]) // 2, c[-1] - c[0] + 1) for c in merged]


def steps_run():
    d = density()
    os.makedirs(EVID, exist_ok=True)
    log_flush()          # 先把上一轮残留冲掉
    log_clear()
    sh("shell", "rm", "-f", DEV_SNIP)
    launch()
    time.sleep(1.5)
    cx, cy = find_testbox_center()
    tap(cx, cy)          # 出键盘
    time.sleep(1.2)
    assert_our_app("出键盘后")     # 铁律：注入前确认前台是本应用
    rect = panel_rect()
    p0 = shot("a0_kb_up")
    # —— 判据 f：候选栏带高与键区起始（缺陷 B 的对照）——
    bar_bot = rect[1] + BAR_H * d
    rows_kb = key_band_rows(p0, rect, d)
    if rows_kb:
        q = rows_kb[0]
        print("H165-f 候选栏预算 %.1fvp=%.0fpx（面板顶 %d → 带底 %.0f）；"
              "实测键区第一行 y=%d..%d（高 %dpx，顶边与带底差 %+.0fpx）" % (
                  BAR_H, BAR_H * d, rect[1], bar_bot, q[0]["y0"], q[0]["y1"], q[0]["h"],
                  q[0]["y0"] - bar_bot))
        print("     对照：上一版装机实测候选行被压进键区，q 行白色带被截成 26px 高（正牌应为 ~90px）")
    # —— 判据 a：三角在**最左**，不是屏幕正中 ——
    tp = tri_point(rect, d)
    crop(p0, "a0_bar", (0, rect[1], rect[2], int(bar_bot)))
    print("H165-a ▶ 预测中心=%s（面板左=%d／中轴=%d；缺陷 A 实测画在 x=668≈中轴）" % (
        tp, rect[0], rect[0] + rect[2] // 2))
    log_flush()
    tap(*tp)
    time.sleep(0.7)
    p1 = shot("b1_func_open")
    tile_pts = measure_tiles(p1, rect, d)
    print("H165-a 展开态白底磁贴 %d 枚（五笔应为 6） centre=%s" % (len(tile_pts), tile_pts))
    crop(p1, "b1_tiles", (0, rect[1], rect[2], int(bar_bot)))
    if len(tile_pts) < 3:
        raise SystemExit("展开态没量到磁贴——三角点空了或几何又变了；停下，别再往下烧这一轮")
    # —— 判据 b：点第 2 枚（中英）看磁贴与底栏**同时**翻转 ——
    tap(*tile_pts[1][:2])
    time.sleep(0.7)
    p2 = shot("b2_after_ascii")
    crop(p2, "b2_tiles", (0, rect[1], rect[2], int(bar_bot)))
    crop(p2, "b2_bottom", (0, 2540, 700, 2700))     # 底栏简/英键
    log_flush()
    tap(*tri_point(rect, d, True))                  # 收起（▼ 在磁贴行最左）
    time.sleep(0.6)
    p3 = shot("b3_collapsed")
    rows_kb = key_band_rows(p3, rect, d)
    # —— 判据 b 的对照组：磁贴**再点一次切回来**（不切回就带着英文态往下跑，
    #     后面 `ghos` 会出字母而不是候选词，网格三角在「无候选」态一点就收键盘，整轮判据作废）——
    tap(*tri_point(rect, d))                        # 再展开
    time.sleep(0.6)
    p4 = shot("b4_func_reopen")
    pts2 = measure_tiles(p4, rect, d)
    if len(pts2) >= 2:
        tap(*pts2[1][:2])
    else:
        print("WARN b4 没量到磁贴，跳过切回（后面候选判据可能失真）")
    time.sleep(0.6)
    crop(shot("b5_back"), "b5_tiles", (0, rect[1], rect[2], int(rect[1] + BAR_H * d)))
    tap(*tri_point(rect, d, True))                  # 收起
    time.sleep(0.6)
    p6 = shot("b6_collapsed2")
    rows_kb = key_band_rows(p6, rect, d)
    # —— 判据 d/e：展开网格 + 上下滑多屏 ——
    # 先打字出候选：三角单击的语义是「有候选=展开网格，无候选=折叠键盘」
    # （`Stack().onClick` 读 candidates/preedit），空状态点它会把键盘收掉。
    for ch in "ghos":
        tap(*letter_point(rows_kb, ch))
    time.sleep(0.6)
    shot("c0_typed")
    assert_our_app("打字出候选后")
    gt = grid_tri_point(rect, d)
    tap(*gt)
    time.sleep(0.8)
    shot("c1_grid_open")
    lo_y, hi_y = grid_swipe_band(rect, d)
    gx = rect[0] + rect[2] // 2
    print("H168-d 网格滑动带 y=%d..%d（候选栏底 %d 以下，绝不进键区）" % (lo_y, hi_y, rect[1] + BAR_H * d))
    for i in range(6):
        swipe(gx, hi_y, gx, lo_y)       # 上滑 → 下一屏
        log_flush()
    shot("c2_grid_last")
    for i in range(3):
        swipe(gx, lo_y, gx, hi_y)       # 下滑 → 上一屏
        log_flush()
    shot("c3_grid_back")
    tap(*gt)
    time.sleep(0.4)
    shot("c4_grid_close")
    # —— 判据 c：切九键看置灰 ——
    steps_t9(rect, d, png_kb=p6)
    _, flips = log_pull()
    if flips:
        last = max(flips, key=lambda f: int(f[6]))
        print("H168-e 最远到达 screen=%s/%s（maxOff=%s，len=%s）" % (last[6], last[7], last[3], last[2]))
    else:
        print("H168-e 没抓到 gridFlip 日志——展开网格没翻页（判据 e 没过，别当成手势问题绕过）")
    print("DONE：坐标/带高/磁贴数/翻屏日志都已落到 %s" % EVID)


def main():
    global DRY
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("probe"); p.add_argument("--dry-run", action="store_true")
    p = sub.add_parser("run"); p.add_argument("--dry-run", action="store_true")
    p = sub.add_parser("t9"); p.add_argument("--dry-run", action="store_true")
    p = sub.add_parser("clear")
    p = sub.add_parser("logs"); p.add_argument("--name", default="h165_hilog")
    p = sub.add_parser("shot"); p.add_argument("name")
    p = sub.add_parser("tap"); p.add_argument("x"); p.add_argument("y")
    p = sub.add_parser("dump"); p.add_argument("name")
    p = sub.add_parser("geo")
    a = ap.parse_args()
    if getattr(a, "dry_run", False):
        DRY = True
    if a.cmd == "probe":
        steps_probe()
    elif a.cmd == "run":
        steps_run()
    elif a.cmd == "t9":
        steps_t9(panel_rect(), density())
    elif a.cmd == "clear":
        log_clear()
    elif a.cmd == "logs":
        log_pull(a.name)
    elif a.cmd == "shot":
        shot(a.name)
    elif a.cmd == "tap":
        tap(int(a.x), int(a.y))
    elif a.cmd == "dump":
        dump(a.name)
    elif a.cmd == "geo":
        d = density()
        rect = panel_rect()
        print(json.dumps({"density": d, "panel": rect,
                          "tri": tri_point(rect, d), "tri_expanded": tri_point(rect, d, True),
                          "grid_tri": grid_tri_point(rect, d)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
