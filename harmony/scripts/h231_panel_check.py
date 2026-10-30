#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""H-231 文本编辑面板「选择」格取证（Qoder，2026-10-27 21:0x）

为什么写：主人 19:0x 报「图标成点了，里面没有选择按钮」。图标那条已修（退回系统符号
`arrow_left_arrow_right`，实机不再是个点）。面板那条**代码里一直有这格**，但主人实机看不见；
当晚手机一度锁屏且无口令可解 ⇒ **取不到面板逐格量**，只能按结构唯一异常改
（内联 Stack → @Builder 同构格）。本脚本把「量」这件事交给机器：启动三生自己的 App、
拉起键盘、展开 ⇆ 面板，**把面板的控件树与截图落盘**，并报告「选择」这一格在不在、在哪。

锁屏判定（2026-10-27 21:0x 实测校准，抄 h164_wait_unlock.py 的已验证解析）：
    hidumper -s WindowManagerService -a '-a'
      ⇒ **列式**输出：WindowName DisplayId Pid WinId Type Mode Flag ZOrd Orientation [x y w h]
         SCBScreenLock12   0   8474   15   2110  1   0    -1  0   [ 0 0 1280 2832 ]
         ↑ 名字      ↑pid ↑winId ↑type       ↑ZOrd（-1＝隐藏）
    hidumper -s WindowManagerService -a '-w <winId>'
      ⇒ IsVisible: true/false
  规则：锁窗存在且（ZOrd≠-1 或 IsVisible=true）⇒ locked；锁窗存在但 ZOrd=-1 且
  IsVisible=false ⇒ unlocked；连锁窗都查不到 ⇒ unknown（按「未解锁」处理，绝不猜）。

  ⚠ 上一版栽在哪：`-a` 输出里**根本没有 `WinId=` 这个字样**，用 `WinId=(\d+)` 去搜必然搜不到
  ⇒ 永远 unknown。后来又因为搜不到就退化成查了别的窗口 ⇒ 得到假的「unlocked」。
  这版按**列位置**解析（与 h164 已验证的 `_WIN_RE` 同源）。

安全闸（每次注入前重判，不靠一次判断走全程）：
  ① 必须已解锁（否则中止，不猜密码）；
  ② 只在**三生自己的 App**（com.sansheng.ime）里操作：`aa start` 把它拉到前台、点它自带的
     输入框，**不碰主人的记事本/聊天/邮件**；前台归属用 WMS 的 ZOrd 最高应用窗校验，
     不是自家就不点；
  ③ 面板只截图 + 读控件树；**默认不点「选择」格**（开/关扩选会动文本选区，没有必要），
     要点得显式加 --tap-select。

用法：
  python scripts/h231_panel_check.py probe                    # 探一次：locked / unlocked / unknown
  python scripts/h231_panel_check.py up                        # 拉起自家 App + 键盘，落截图/控件树
  python scripts/h231_panel_check.py flow                      # 全流程：量图标 → 展工具栏 → 点 ⇆ → 落面板证据
  python scripts/h231_panel_check.py panel --x 1150 --y 1950  # 点顶栏 ⇆ 图标（坐标在 up 的截图上量）
  python scripts/h231_panel_check.py tapsel --x 430 --y 2050   # 点「选择」格（需显式 --tap-select）
  python scripts/h231_panel_check.py selftest                  # 离线自测（不碰设备）

产出（docs/evidence/2026-10-27/h231-panel/）：
  wait-unlock.log   守候/执行时间线（每次判定依据）
  app-layout.json   自家 App 控件树（找输入框）
  panel-layout.json 面板态控件树（uitest dumpLayout -i，不合并窗口）
  keyboard-up.jpeg  键盘拉起后的截图
  toolbar.jpeg      工具栏展开后（7 枚图标）的截图
  cursor-icon-zoom.png  ⇆ 图标放大图（看它是不是「成点」）
  panel.jpeg        ⇆ 面板展开后的截图
  panel-select-zoom.png 面板「选择」格放大图
  panel-report.txt  结论：面板里有没有「选择」这一格、在哪个坐标、截图路径、装机包版本
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
EVID = os.path.join(ROOT, "docs", "evidence", "2026-10-27", "h231-panel")
LOG = os.path.join(EVID, "wait-unlock.log")
HDC = r"D:\DevTools\DevEco\DevEco Studio\sdk\default\openharmony\toolchains\hdc.exe"
BUNDLE = "com.sansheng.ime"
ABILITY = "EntryAbility"

sys.path.insert(0, HERE)
import h231_find_cursor_icon as finder        # noqa: E402  同目录模块：候选栏图标逐像素量法

try:
    from PIL import Image
except Exception as _e:                       # pragma: no cover
    Image = None
    log_msg = "PIL 不可用（%s），像素量法不可用" % _e

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def log(msg):
    os.makedirs(EVID, exist_ok=True)
    line = "%s %s" % (time.strftime("%Y-%m-%d %H:%M:%S"), msg)
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def sh(*args):
    """跑 hdc；Git-Bash 会把 /data/... 改写成 Windows 路径 ⇒ 统一用 MSYS_NO_PATHCONV。"""
    env = dict(os.environ)
    env["MSYS_NO_PATHCONV"] = "1"
    cmd = [HDC] + list(args)
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", env=env, timeout=120)
    except subprocess.TimeoutExpired:
        return ""
    return (p.stdout or "") + (p.stderr or "")


# WMS `-a` 的列式输出（2026-10-27 21:0x 实拍，抄 h164_wait_unlock.py 的已验证正则）：
# SCBScreenLock12   0   8474   15   2110  1   0   -1   0   [ 0    0    1280 2832 ] ...
# 名字              pid   winId  type       ZOrd
_WIN_RE = re.compile(
    r"^(\S+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(-?\d+)\s+(\d+)\s+"
    r"\[\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*\]")


def windows(text=None):
    """把 WMS 全量 dump 解析成窗口列表（text 参数只为离线自测）。"""
    out = []
    for ln in (text if text is not None else
               sh("shell", "hidumper -s WindowManagerService -a '-a'")).splitlines():
        m = _WIN_RE.match(ln)
        if not m:
            continue
        name, disp, pid, wid, typ, mode, flag, zord, ori, x, y, w, h = m.groups()
        out.append({"name": name, "pid": int(pid), "winId": int(wid), "type": int(typ),
                    "zord": int(zord), "rect": [int(x), int(y), int(w), int(h)]})
    return out


def _is_visible(win_id):
    txt = sh("shell", "hidumper -s WindowManagerService -a '-w %d'" % win_id)
    for ln in txt.splitlines():
        if ln.startswith("IsVisible:"):
            return ln.split(":", 1)[1].strip().lower() == "true", ln.strip()
    return None, "no IsVisible line"


def locked_state():
    """返回 (state, 依据)：locked / unlocked / unknown。判不准就当未解锁，绝不猜。"""
    wins = windows()
    lock = [w for w in wins if w["name"].startswith("SCBScreenLock")]
    if not lock:
        return "unknown", "WMS 里没有 SCBScreenLock 窗口"
    w = lock[0]
    vis, raw = _is_visible(w["winId"])
    why = "SCBScreenLock winId=%d ZOrd=%d %s" % (w["winId"], w["zord"], raw)
    if w["zord"] != -1:
        return "locked", why + "（ZOrd≠-1＝锁窗在上层）"
    if vis is True:
        return "locked", why
    if vis is False:
        return "unlocked", why
    return "unknown", why


def own_pid():
    p = sh("shell", "pidof %s" % BUNDLE).strip()
    return int(p) if p.isdigit() else None


def foreground_app():
    """前台应用窗＝可见(Type=1,ZOrd≠-1)里 ZOrd 最大的那个。"""
    apps = [w for w in windows() if w["type"] == 1 and w["zord"] != -1]
    if not apps:
        return None
    return max(apps, key=lambda w: w["zord"])


def own_foreground():
    """前台是不是本应用；返回 (ok, 依据)。"""
    pid = own_pid()
    top = foreground_app()
    if top is None:
        return False, "没有可见的应用窗"
    if pid is None:
        return False, "本应用未运行（pidof 无输出），前台=%s pid=%d" % (top["name"], top["pid"])
    ok = top["pid"] == pid
    return ok, "前台 %s pid=%d zord=%d（本应用 pid=%d）" % (top["name"], top["pid"], top["zord"], pid)


def keyboard_panel_visible():
    """键盘面板窗是否可见（SCBKeyboardPanel，Type=2134）。"""
    panel = [w for w in windows() if w["name"].startswith("SCBKeyboardPanel")]
    if not panel:
        return None
    vis, _ = _is_visible(panel[0]["winId"])
    return vis


def dump_layout(name="panel-layout", extra=None):
    """落一份控件树。默认不合并窗口（-i），尽量把 IME 窗口也捞进来。"""
    local = os.path.join(EVID, name + ".json")
    remote = "/data/local/tmp/h231_%s.json" % name
    args = ["shell", "uitest", "dumpLayout", "-p", remote]
    if extra:
        args += extra
    sh(*args)
    sh("file", "recv", remote, local)
    return local if os.path.exists(local) else ""


def screenshot(name="panel"):
    remote = "/data/local/tmp/h231_%s.jpeg" % name
    local = os.path.join(EVID, name + ".jpeg")
    sh("shell", "snapshot_display", "-f", remote)
    sh("file", "recv", remote, local)
    return local if os.path.exists(local) else ""


def tap(x, y):
    sh("shell", "uitest", "uiInput", "click", str(int(x)), str(int(y)))


def walk(node, out):
    """控件树节点收集。**三种形态都要吃得下**（22:25 实测踩到过）：

    - 根是 dict（`dumpLayout` 不带 `-i`）：`{"attributes": {...}, "children": [...]}`；
    - 根是 **list**（`dumpLayout -i`＝按窗口分组的数组，22:25 崩在这）；
    - `attributes` 本身是 list（`-i` 版可能是 `[{"name":..,"value":..}, ...]`）。

    崩过一次就补成都能走，别再让「取证脚本自己先崩」。
    """
    if isinstance(node, list):
        for c in node:
            walk(c, out)
        return
    if not isinstance(node, dict):
        return
    at = node.get("attributes", {}) or {}
    if isinstance(at, dict):
        out.append(at)
    elif isinstance(at, list):
        flat = {}
        for it in at:
            if isinstance(it, dict):
                k = it.get("name") or it.get("key") or it.get("attr")
                if k is not None:
                    flat[str(k)] = it.get("value")
        out.append(flat)
    for c in node.get("children", []) or []:
        walk(c, out)


def collect_nodes(path):
    if not path:
        return []
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            d = json.load(f)
    except Exception as e:
        log("dump 解析失败 %s: %s" % (path, e))
        return []
    nodes = []
    walk(d, nodes)
    return nodes


def find_by_text(nodes, needle):
    for at in nodes:
        if needle in (at.get("text") or ""):
            return at
    return None


def find_textbox(nodes):
    """自家页面上的输入框：先认 TextInput/TextArea，再退到「试打」占位文字
    （h164 同一套口径：Index 页的试打框是 TextArea，placeholder 是「点这里试打一行」）。"""
    for at in nodes:
        if (at.get("type") or "") in ("TextInput", "TextArea"):
            return at
    for at in nodes:
        if "试打" in (at.get("text") or ""):
            return at
    return None


def bounds_center(b):
    m = re.match(r"\[(-?\d+),(-?\d+)\]\[(-?\d+),(-?\d+)\]", b or "")
    if not m:
        return None
    x1, y1, x2, y2 = (int(v) for v in m.groups())
    return ((x1 + x2) // 2, (y1 + y2) // 2)


def carrier():
    """装机包版本锚点：报告要绑定到「哪一版」，不能靠事后回忆。"""
    out = sh("shell", "bm dump -n %s" % BUNDLE)
    ut = [ln.strip() for ln in out.splitlines() if '"updateTime"' in ln]
    return ut[0] if ut else "updateTime 未取到"


def guard(tag):
    """注入前的双闸：必须已解锁 + 前台是自家 App。"""
    st, why = locked_state()
    if st != "unlocked":
        log("GUARD-ABORT[%s] 设备不是已解锁状态：%s" % (tag, why))
        return False
    ok, why2 = own_foreground()
    if not ok:
        log("GUARD-ABORT[%s] 前台不是本应用（绝不在别人窗口里注入）：%s" % (tag, why2))
        return False
    log("GUARD-OK[%s] %s / %s" % (tag, why, why2))
    return True


def bring_up():
    """启动自家 App → 点自家输入框 → 键盘起来。返回输入框中心坐标（失败 None）。"""
    log("启动自家 App: %s/%s" % (BUNDLE, ABILITY))
    sh("shell", "aa", "start", "-a", ABILITY, "-b", BUNDLE)
    time.sleep(4)
    ok, why = own_foreground()
    log("FOREGROUND %s：%s" % ("本应用" if ok else "不是本应用", why))
    if not ok:
        return None

    lay = dump_layout("app-layout")
    nodes = collect_nodes(lay)
    log("自家 App 控件树节点数: %d（%s）" % (len(nodes), lay))
    tb = find_textbox(nodes)
    if tb is None:
        log("没找到自家页面的输入框（不乱点）")
        return None
    c = bounds_center(tb.get("bounds", ""))
    log("输入框 type=%s bounds=%s center=%s" % (tb.get("type"), tb.get("bounds"), c))
    if not c:
        return None
    if not guard("focus-input"):
        return None
    tap(c[0], c[1])
    for _ in range(8):
        time.sleep(0.8)
        if keyboard_panel_visible() is True:
            log("KEYBOARD UP（WMS SCBKeyboardPanel IsVisible=true）")
            break
    else:
        log("键盘面板窗未报可见（可能窗口名不同），以截图为准")
    time.sleep(1.0)
    shot = screenshot("keyboard-up")
    log("键盘态截图: %s" % shot)
    return c


def open_panel(x, y):
    """点顶栏 ⇆ 图标 → 面板展开 → 落盘。"""
    if not guard("open-panel"):
        return 1
    log("点 ⇆ 图标 (%s,%s)" % (x, y))
    tap(x, y)
    time.sleep(1.5)
    shot = screenshot("panel")
    log("面板截图: %s" % shot)
    lay = dump_layout("panel-layout", extra=["-i"])
    nodes = collect_nodes(lay)
    texts = sorted({(n.get("text") or "").strip() for n in nodes if (n.get("text") or "").strip()})
    log("面板态控件树节点数: %d（%s）" % (len(nodes), lay))
    log("面板态控件树文本项: %s" % " | ".join(texts[:60]))
    sel = find_by_text(nodes, "选择")
    if sel is not None:
        log("★ 控件树里有「选择」：type=%s bounds=%s text=%r"
            % (sel.get("type"), sel.get("bounds"), sel.get("text")))
    else:
        log("△ 控件树里没有「选择」二字（IME 窗口可能不进控件树——以截图为准）")
    return 0


def tap_select(x, y, report):
    """点「选择」格：只在本应用里动扩选开关，不碰主人文档。"""
    if not guard("tap-select"):
        return 1
    sh("shell", "hilog", "-r")
    time.sleep(0.5)
    tap(x, y)
    time.sleep(1.5)
    shot = screenshot("panel-select-on")
    log("点「选择」后截图: %s" % shot)
    lay = dump_layout("panel-layout-after", extra=["-i"])
    nodes = collect_nodes(lay)
    texts = sorted({(n.get("text") or "").strip() for n in nodes if (n.get("text") or "").strip()})
    log("点选后控件树文本项: %s" % " | ".join(texts[:60]))
    cancel = find_by_text(nodes, "取消选择")
    log("控件树里有「取消选择」: %s" % ("是" if cancel is not None else "否"))
    hl = sh("shell", "hilog", "-x")
    hit = [ln for ln in hl.splitlines() if "H-231 gridSelect tapped" in ln]
    log("hilog 命中 H-231 gridSelect tapped: %d 行" % len(hit))
    for ln in hit[-3:]:
        log("  %s" % ln.strip())
    report.append("「选择」点击结果: 截图=%s 取消选择格=%s hilog 命中=%d" %
                   (shot, cancel is not None, len(hit)))
    return 0


def panel_rect():
    """键盘面板窗矩形（WMS）：[x, y, w, h]；面板顶沿＝候选栏顶沿。"""
    for w in windows():
        if w["name"].startswith("SCBKeyboardPanel"):
            return w["rect"]
    return None


def white_segments(im, y, thr=250, min_w=30):
    """一行里的近白连续段（键帽/格子）。"""
    px = im.load()
    w = im.size[0]
    out = []
    run = None
    for x in range(w):
        r, g, b = px[x, y]
        if r >= thr and g >= thr and b >= thr:
            if run is None:
                run = [x, x]
            else:
                run[1] = x
        else:
            if run and run[1] - run[0] + 1 >= min_w:
                out.append((run[0], run[1]))
            run = None
    if run and run[1] - run[0] + 1 >= min_w:
        out.append((run[0], run[1]))
    return out


def find_panel_cells(path, panel_top):
    """在面板区域找白色格子，返回 (左列三行的行带, 每带里的格子段)。

    面板结构照 ToolPanels.ets：左边一列 3×3（行首/上页/选择/下页/行尾…），
    「选择」＝**左列中间那一行的中间那格**。左列三行等高 ⇒ 找左列的 3 条行带，
    取第 2 条，再在带顶（文字上方）取一行探针，横向第 2 段就是「选择」格。
    """
    im = Image.open(path).convert("RGB")
    w, h = im.size
    px = im.load()
    # ① 找左列最左格子的 x 起点：面板区内所有行的最小白段起点
    left_x0 = None
    for y in range(panel_top + 40, h):
        segs = white_segments(im, y)
        if len(segs) >= 3:
            left_x0 = segs[0][0]
            break
    if left_x0 is None:
        return {"ok": False, "why": "面板区里没找到成排的白格"}
    col_x1 = left_x0 + 40

    # ② 左列的行带：左列第一格所在 x 区间出现白像素的连续 y
    bands = []
    cur = None
    for y in range(panel_top + 40, h):
        hit = False
        for x in range(left_x0, min(col_x1, w)):
            r, g, b = px[x, y]
            if r >= 250 and g >= 250 and b >= 250:
                hit = True
                break
        if hit:
            if cur is None:
                cur = [y, y]
            else:
                cur[1] = y
        else:
            if cur and cur[1] - cur[0] >= 10:
                bands.append(tuple(cur))
            cur = None
    if cur and cur[1] - cur[0] >= 10:
        bands.append(tuple(cur))
    if len(bands) < 3:
        return {"ok": False, "why": "左列只量到 %d 条行带（要 3 条）" % len(bands)}

    mid = bands[1]
    probe = min(mid[1], mid[0] + 6)          # 带顶下方一点＝格子里、文字上方
    segs = white_segments(im, probe)
    if len(segs) < 2:
        return {"ok": False, "why": "中间行带探针行只量到 %d 段白" % len(segs)}
    cell = segs[1]                            # 第 2 段＝中间那格＝「选择」
    return {"ok": True, "bands": bands, "left_x0": left_x0, "probe_y": probe,
            "segments": segs,
            "cell": {"x1": cell[0], "x2": cell[1],
                     "cx": (cell[0] + cell[1]) // 2, "cy": (mid[0] + mid[1]) // 2,
                     "row_y0": mid[0], "row_y1": mid[1]}}


def zoom_crop(path, box, scale, out):
    """裁一块放大存盘（看图标是不是「成点」、看格子里有没有「选择」两个字）。"""
    im = Image.open(path).convert("RGB")
    x1, y1, x2, y2 = box
    x1 = max(0, min(x1, im.size[0] - 1))
    x2 = max(x1 + 1, min(x2, im.size[0]))
    y1 = max(0, min(y1, im.size[1] - 1))
    y2 = max(y1 + 1, min(y2, im.size[1]))
    c = im.crop((x1, y1, x2, y2)).resize(((x2 - x1) * scale, (y2 - y1) * scale),
                                         Image.LANCZOS)
    c.save(out)
    return out


def measure_bar(path, panel_top):
    """量候选栏里的图标簇（扫描带由面板顶沿推出）。"""
    im = Image.open(path).convert("RGB")
    band = finder.band_from_panel(im, panel_top)
    clusters, band = finder.find_clusters(im, band=band)
    return clusters, band


def pick_cursor_icon(clusters):
    """在「工具栏展开态」的簇里挑出 ⇆（那排的第 4 枚）。

    展开态的实测构成（2026-10-27 22:2x 真机，keyboard-up.jpeg）：
    ‹(69) 撤销(260) 重做(448) **⇆(639)** 剪贴板(829) ···(994/1019/1043 三个点分开算) ⌄(1209)
    ⇒ 一共 **9 簇**（不是 7：那三个点各自成簇），但 **第 4 簇仍然是 ⇆**。

    判据：① 至少 6 簇（展开态的规模）；② 最左一枚落在 x∈[30,140]（「‹」的位置）；
    ③ 第 4 簇不是「成点」（w≤14 且 ink≤60 ⇒ 那就是 H-231 那个症状，认出来但不算图标）。
    不满足任何一条 ⇒ 返回 None（不猜坐标）。
    """
    if len(clusters) < 6:
        return None
    if not (30 <= clusters[0]["cx"] <= 140):
        return None
    if len(clusters) < 4:
        return None
    c = clusters[3]
    if finder.looks_like_dot(c):
        return None
    if c["w"] < 18:
        return None
    return c


def expand_func_bar(path, panel_top):
    """把顶栏工具栏弄成展开态，并挑出 ⇆ 那枚。返回 (截图路径, ⇆簇, 扫描带)。

    2026-10-27 22:2x 改：原来只认「2 簇＝空闲 / 7 簇＝展开」，可真机展开态是 **9 簇**
    （··· 三个点分开算）+ ⇆ 带浅色高亮底；老判据会把「已经是展开态」误判成
    「形态不认识」直接放弃（22:27 实测：量到 8 簇 ⇒ 不猜不点，白白错过一次解锁窗口）。
    现在改成「先看能不能直接挑出 ⇆；挑不出再看是不是空闲态（2 簇）→ 点「›」展开」。
    """
    clusters, band = measure_bar(path, panel_top)
    log("候选栏量到 %d 簇：%s" % (len(clusters),
                                " ".join("x=%d@%d" % (c["cx"], c["cy"]) for c in clusters)))
    cur = pick_cursor_icon(clusters)
    if cur is not None:
        log("工具栏已是展开态，直接挑出 ⇆：(%d,%d) 宽=%d 高=%d 笔画=%d"
            % (cur["cx"], cur["cy"], cur["w"], cur["h"], cur["ink"]))
        return path, cur, band
    if len(clusters) != 2:
        log("簇数 %d 且挑不出 ⇆ ⇒ 不猜，不点" % len(clusters))
        return "", None, band
    opener = clusters[0]          # 最左那枚＝「›」（点它展开工具栏）
    log("点空闲态左「›」(%d,%d) 展开工具栏" % (opener["cx"], opener["cy"]))
    if not guard("expand-func-bar"):
        return "", None, band
    tap(opener["cx"], opener["cy"])
    time.sleep(1.5)
    shot = screenshot("toolbar")
    log("工具栏展开截图: %s" % shot)
    p2 = panel_rect()
    top2 = p2[1] if p2 else panel_top
    clusters2, band2 = measure_bar(shot, top2)
    log("展开后量到 %d 簇：%s" % (len(clusters2),
                                " ".join("x=%d@%d" % (c["cx"], c["cy"]) for c in clusters2)))
    cur2 = pick_cursor_icon(clusters2)
    if cur2 is None:
        log("展开后仍挑不出 ⇆ ⇒ 不点")
        return shot, None, band2
    return shot, cur2, band2


def flow(report, tap_select=True):
    """全流程：拉键盘 → 展工具栏 → 量 ⇆ → 点 ⇆ → 落面板证据。"""
    # 只要求「已解锁」；**不去劫持别人的页面**——下面第一步是把自家 App 拉到前台，
    # 之后的每一次点都发生在自家 App 里（bring_up/expand_func_bar/flow 自己再核一次前台）。
    st, why = locked_state()
    if st != "unlocked":
        log("设备不是已解锁状态：%s" % why)
        return 1
    log("已解锁（%s）⇒ 起自家 App 做取证" % why)
    c = bring_up()
    if not c:
        log("键盘没拉起来，流程中止")
        return 1
    pr = panel_rect()
    if not pr:
        log("WMS 里没有键盘面板窗，流程中止")
        return 1
    panel_top = pr[1]
    log("键盘面板矩形 %s（候选栏顶沿 y=%d）" % (pr, panel_top))

    shot, cursor, band = expand_func_bar(os.path.join(EVID, "keyboard-up.jpeg"), panel_top)
    if cursor is None:
        report.append("未量到 ⇆ 图标：候选栏形态不是 2 簇(空闲)/7 簇(展开)，流程中止")
        return 2
    log("⇆ 图标中心 (%d,%d) 笔画=%d 宽=%d 高=%d 成点=%s"
        % (cursor["cx"], cursor["cy"], cursor["ink"], cursor["w"], cursor["h"],
           finder.looks_like_dot(cursor)))
    zoom = zoom_crop(shot, (cursor["x1"] - 14, cursor["cy"] - 14,
                             cursor["x2"] + 14, cursor["cy"] + 14), 8,
                     os.path.join(EVID, "cursor-icon-zoom.png"))
    log("⇆ 图标放大图: %s" % zoom)

    if not guard("open-panel"):
        return 1
    log("点 ⇆ (%d,%d)" % (cursor["cx"], cursor["cy"]))
    tap(cursor["cx"], cursor["cy"])
    time.sleep(2.0)
    pshot = screenshot("panel")
    log("面板截图: %s" % pshot)
    lay = dump_layout("panel-layout", extra=["-i"])
    nodes = collect_nodes(lay)
    texts = sorted({(n.get("text") or "").strip() for n in nodes if (n.get("text") or "").strip()})
    log("面板态控件树节点数: %d（%s）" % (len(nodes), lay))
    log("面板态控件树文本项: %s" % " | ".join(texts[:60]))
    sel = find_by_text(nodes, "选择")
    log("控件树里有「选择」: %s" % ("是" if sel is not None else "否"))

    pr2 = panel_rect()
    top2 = pr2[1] if pr2 else panel_top
    cells = find_panel_cells(pshot, top2)
    if cells.get("ok"):
        cc = cells["cell"]
        log("「选择」格：中心 (%d,%d) 盒 x=%d..%d 所在行 y=%d..%d 左列行带=%s"
            % (cc["cx"], cc["cy"], cc["x1"], cc["x2"], cc["row_y0"], cc["row_y1"],
               cells["bands"]))
        z2 = zoom_crop(pshot, (cc["x1"] - 8, cc["row_y0"] - 6,
                                cc["x2"] + 8, cc["row_y1"] + 6), 4,
                       os.path.join(EVID, "panel-select-zoom.png"))
        log("「选择」格放大图: %s" % z2)
    else:
        cc = None
        log("△ 没量到面板格子：%s" % cells.get("why"))

    report.append("⇆ 图标中心=(%d,%d) 笔画=%d 宽×高=%dx%d 成点=%s"
                  % (cursor["cx"], cursor["cy"], cursor["ink"], cursor["w"],
                     cursor["h"], finder.looks_like_dot(cursor)))
    report.append("工具栏 7 簇扫描带 y=%d..%d；截图 %s" % (band[0], band[1], shot))
    report.append("面板截图 %s；控件树「选择」=%s"
                  % (pshot, "有" if sel is not None else "无（IME 窗口不进控件树，看放大图）"))
    if cc:
        report.append("「选择」格中心=(%d,%d) 放大图 panel-select-zoom.png" % (cc["cx"], cc["cy"]))

    # 点「选择」两次：证明这格真在、真能点（hilog 有 `H-231 gridSelect tapped`），
    # 第二次点回去把选择模式还原成关。**只在自家 App 的试打框里点，不碰主人的文档。**
    if cc and tap_select:
        if not guard("tap-select"):
            return 1
        sh("shell", "hilog", "-r")
        time.sleep(0.5)
        tap(cc["cx"], cc["cy"])
        time.sleep(1.2)
        shot2 = screenshot("panel-select-on")
        tap(cc["cx"], cc["cy"])          # 再点一次：模式回关
        time.sleep(1.2)
        hl = sh("shell", "hilog", "-x")
        hits = [ln for ln in hl.splitlines() if "H-231 gridSelect tapped" in ln]
        log("点「选择」两次：hilog 命中 %d 行；截图 %s" % (len(hits), shot2))
        for ln in hits[-4:]:
            log("  %s" % ln.strip())
        report.append("「选择」格点击验证：hilog 命中 %d 行（点得动=这格存在且已接上）；截图 %s"
                      % (len(hits), shot2))
    report.append("装机包 %s" % carrier())
    return 0


def wait(minutes, do_run):
    """守候解锁。解锁即把自家 App + 键盘拉起来，落 keyboard-up 截图与控件树。

    **H-232 轮（Qoder 2026-10-27 21:4x）修正本注释**：原文写「不在无人值守时点「选择」格」，
    与 flow() 实际行为不符——flow() 会点「选择」**两次**（开→关，把选择模式还原回去），
    目的只是让 hilog 出现 `H-231 gridSelect tapped` 这一行，证明这一格真在、真能点。

    安全边界不变也不放宽：**解锁后的每一次注入都发生在自家 App 的试打框里**
    （flow()/bring_up()/expand_func_bar() 每次点之前都重核「已解锁 ＋ 前台是本应用」，
    核不过就中止）；主人的文档、第三方应用（钱包页等）一律不碰、不截屏。
    """
    deadline = time.time() + minutes * 60
    log("守候开始（%d 分钟，每 45 秒一探；解锁前不注入任何东西）" % minutes)
    while time.time() < deadline:
        st, why = locked_state()
        log("WAIT %s（%s）" % (st, why))
        if st == "unlocked":
            if not do_run:
                log("已解锁 ⇒ 停止守候（未加 --run，不注入）")
                return 0
            log("已解锁 ⇒ 拉起自家 App 与键盘")
            c = bring_up()
            if not c:
                log("键盘没拉起来，继续守候")
            else:
                # 控件树再落一份（不合并窗口），供找 ⇆ 图标/「选择」格用
                lay = dump_layout("panel-layout", extra=["-i"])
                nodes = collect_nodes(lay)
                texts = sorted({(n.get("text") or "").strip()
                                for n in nodes if (n.get("text") or "").strip()})
                log("面板态控件树节点数: %d；文本项: %s" % (len(nodes), " | ".join(texts[:60])))
                log("READY 键盘已起，截图 %s" % os.path.join(EVID, "keyboard-up.jpeg"))
                report = []
                rc = flow(report)
                log("FLOW rc=%d" % rc)
                if report:
                    rep = os.path.join(EVID, "panel-report.txt")
                    with open(rep, "a", encoding="utf-8") as f:
                        f.write("\n".join(report) + "\n")
                return 0
        time.sleep(45)
    log("守候超时（%d 分钟），未解锁，未做任何注入。" % minutes)
    return 1


def selftest():
    """离线自测：列式解析 + 锁屏判定 + 文本查找（不碰设备）。"""
    fx = (
        "SCBScenePanel12      0         8474    4     2109 1    0    100  0           [ 0    0    1280 2832 ] [ 0       0       ] [ 1       1       0.5     0.5     ]\n"
        "SCBKeyboardPanel     0         8474    37    2134 1    0    -1   0           [ 0    1849 1280 983  ] [ 0       0       ] [ 1       1       0.5     0.5     ]\n"
        "notepad0             0         8964    35    1    1    0    102  0           [ 0    0    1280 2832 ] [ 0       0       ] [ 1       1       0.5     0.5     ]\n"
        "SCBScreenLock12      0         8474    15    2110 1    0    -1   0           [ 0    0    1280 2832 ] [ 0       0       ] [ 1       1       0.5     0.5     ]\n")
    ws = windows(fx)
    assert len(ws) == 4, ws
    lock = [w for w in ws if w["name"].startswith("SCBScreenLock")][0]
    assert lock["winId"] == 15, lock
    assert lock["type"] == 2110 and lock["zord"] == -1, lock
    kp = [w for w in ws if w["name"].startswith("SCBKeyboardPanel")][0]
    assert kp["winId"] == 37 and kp["type"] == 2134, kp
    nd = [w for w in ws if w["name"] == "notepad0"][0]
    assert nd["pid"] == 8964 and nd["zord"] == 102, nd

    # ZOrd 最高的应用窗是前台
    apps = [w for w in ws if w["type"] == 1 and w["zord"] != -1]
    assert max(apps, key=lambda w: w["zord"])["name"] == "notepad0"

    # 控件树文本查找
    lay = {"attributes": {"type": "Column", "text": "", "bounds": "[0,0][1280,2832]"},
           "children": [{"attributes": {"type": "Text", "text": "取消选择",
                                        "bounds": "[300,2000][600,2080]"}, "children": []}]}
    nodes = []
    walk(lay, nodes)
    assert find_by_text(nodes, "选择") is not None
    assert find_by_text(nodes, "取消选择") is not None
    assert find_by_text(nodes, "剪贴板") is None

    # 面板格子量法（合成一张 3×3 左列 + 右列的假面板）
    tmp = os.path.join(EVID, "selftest-panel.jpeg")
    im = Image.new("RGB", (1280, 2832), (228, 231, 237))
    px = im.load()
    # 左列 3 行 × 3 格；格宽 240、格高 120、行间距 10；右列 1 格
    for r in range(3):
        for c in range(3):
            x0, y0 = 10 + c * 250, 1900 + r * 130
            for x in range(x0, x0 + 240):
                for y in range(y0, y0 + 120):
                    px[x, y] = (255, 255, 255)
    for r in range(4):
        x0, y0 = 800, 1900 + r * 100
        for x in range(x0, x0 + 200):
            for y in range(y0, y0 + 90):
                px[x, y] = (255, 255, 255)
    im.save(tmp)
    cells = find_panel_cells(tmp, 1849)
    assert cells.get("ok"), cells
    cc = cells["cell"]
    # 「选择」＝左列中间行的中间那格：x 应在第二格内，y 在中间行
    assert 250 <= cc["cx"] <= 510, cc
    assert 1900 + 130 <= cc["cy"] <= 1900 + 250, cc
    assert len(cells["bands"]) == 3, cells["bands"]
    os.remove(tmp)

    print("SELFTEST OK：4 行列式解析、锁窗 winId=15/type=2110、键盘面板 winId=37、"
          "前台取 ZOrd 最高的 notepad0、控件树「选择/取消选择」可查、"
          "面板格子量法在合成面板上定位到左列中间行的中间格")
    return 0


def main():
    ap = argparse.ArgumentParser(description="H-231 面板「选择」格取证")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("probe")
    sub.add_parser("up")
    fl = sub.add_parser("flow")
    fl.add_argument("--no-tap-select", action="store_true",
                    help="不点「选择」格（默认点两次做客观验证，点了会还原）")
    w = sub.add_parser("wait")
    w.add_argument("--minutes", type=int, default=240)
    w.add_argument("--run", action="store_true")
    p = sub.add_parser("panel")
    p.add_argument("--x", type=int, required=True)
    p.add_argument("--y", type=int, required=True)
    ts = sub.add_parser("tapsel")
    ts.add_argument("--x", type=int, required=True)
    ts.add_argument("--y", type=int, required=True)
    ts.add_argument("--tap-select", action="store_true")
    sub.add_parser("selftest")
    a = ap.parse_args()

    os.makedirs(EVID, exist_ok=True)
    if a.cmd == "selftest":
        return selftest()
    if a.cmd == "probe":
        st, why = locked_state()
        log("PROBE %s（%s）" % (st, why))
        top = foreground_app()
        log("PROBE 前台: %s" % (top["name"] if top else "无"))
        print(st)
        return 0
    if a.cmd == "up":
        c = bring_up()
        print("input-center=%s" % (c,))
        return 0 if c else 2
    if a.cmd == "flow":
        report = []
        rc = flow(report, tap_select=not a.no_tap_select)
        rep = os.path.join(EVID, "panel-report.txt")
        with open(rep, "a", encoding="utf-8") as f:
            f.write("\n".join(report) + "\n")
        print("flow rc=%d" % rc)
        return rc
    if a.cmd == "wait":
        return wait(a.minutes, a.run)
    if a.cmd == "panel":
        rc = open_panel(a.x, a.y)
        return rc
    if a.cmd == "tapsel":
        if not a.tap_select:
            log("默认不点「选择」格（会动文本选区）；要点请加 --tap-select")
            return 3
        report = []
        rc = tap_select(a.x, a.y, report)
        rep = os.path.join(EVID, "panel-report.txt")
        with open(rep, "a", encoding="utf-8") as f:
            f.write("\n".join(report) + "\n")
        return rc
    return 0


if __name__ == "__main__":
    sys.exit(main())
