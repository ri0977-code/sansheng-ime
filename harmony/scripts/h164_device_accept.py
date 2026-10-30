#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""H-164 真机验收小工具（Qoder）——锁屏一解，按下面的子命令逐步取证。

为什么单独写：`uitest uiInput swipe/drag` 实测只产生 Down/Up（2026-10-24 17:0x
`docs/evidence/2026-10-24/gesture-injection-recipe-1650.md`），滑不动 List；
本工具改用 `uinput -T -m` 的**真实触点平滑移动**（多点/带 smooth time），
并统一收截图与 hilog，避免每一步手打长命令。

用法（Mate 80，hdc 已在 PATH 之外，用绝对路径）：
    python scripts/h164_device_accept.py plan                  # 看九条判据的取证步骤
    python scripts/h164_device_accept.py launch                # 拉起本应用（带试打框）
    python scripts/h164_device_accept.py dump                  # 拉布局 + 自动列出候选行每条的字与中心点
    python scripts/h164_device_accept.py cands                 # 重新解析上一份布局（不碰设备）
    python scripts/h164_device_accept.py tapcand 3             # 点当轮布局里的第 3 条候选（判据④）
    python scripts/h164_device_accept.py tap 640 1600          # 点屏幕
    python scripts/h164_device_accept.py keys nihao            # 按坐标敲字母（qwerty）
    python scripts/h164_device_accept.py smooth 1000 1922 300 1922   # 候选行上平滑左滑
    python scripts/h164_device_accept.py shot before           # 截图到 evidence 目录
    python scripts/h164_device_accept.py logs                  # 打印 H-164 相关日志
    python scripts/h164_device_accept.py clear                 # 清 hilog 缓冲（验收前先清）
    python scripts/h164_device_accept.py <任意子命令> --dry-run   # 只打印将执行的 hdc 命令，不碰设备

坐标来源：1280x2832 Mate 80 实机截图。字母三行与 `scripts/type.sh` 实测值一致（2026-10-25 00:4x
用 11:32 实拍按像素连通域复核，x 值逐个相同）；底栏按同一张 11:32 实拍重校为 7 键
（`?123｜九键｜😊｜🌐｜空格｜.｜↵`，旧 09:47 六键表作废）；候选行中心 y≈1922。
**布局一变先 `dump`（uitest dumpLayout）拿精确矩形再改本表**，别拿旧截图硬点。
**键盘布局一改就要重量**：先用 `shot` 看一张再动手，别信记忆。

解锁后一条龙（判据编号见 ISSUES H-164「验收」列；每步都把证据落在 EVID）：
    1) shot lock            —— 先确认真解锁了（锁屏也能拍，别在锁屏上白点）
    2) clear → launch       —— 清日志、拉起应用（页面带试打框）
    3) shot a0 → tap 640 1600 → shot a1   —— 点试打框出键盘；a1 里核对底栏/候选行位置
    4) dump                 —— 自动列候选行每条的字与中心点（存 h164_cands.json）
    5) keys nihao → shot b1 → smooth 1000 1922 300 1922 → shot b2
                            —— 判据①：跟手、无整页闪变；b1/b2 对比看是否连续左移
    6) smooth 再两次 → shot b3/b4     —— 判据①后半：到尾部自动续下一页（只续一次）
    7) tapcand 1 → shot c1 → dump    —— 判据②④：上屏第 1 条正确、且滚动位/候选回第一条
    8) keys ni → tap 退格×2 → shot c2 —— 判据②：退到空，滚动位回第一条
    9) keys nihaoma → shot d1        —— 判据⑤：长词不截断（「你好吗」完整可见）
   10) tap ▼（cand）→ shot e1 → tap ▼ → shot e2 —— 判据⑧：网格展开/收起不破
   11) logs                 —— 判据③⑦：续页只发生一次、绝对下标可判定、setPageSize 不中途触发
   12) 横屏三条另跑（`docs/evidence/2026-10-24/landscape-h096-1150/ltap-measure.py`），竖屏九条先走完。
"""
import argparse
import os
import subprocess
import sys
import time

try:  # Git Bash 控制台默认 GBK，脚本输出按 UTF-8
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HDC = r"D:\DevTools\DevEco\DevEco Studio\sdk\default\openharmony\toolchains\hdc.exe"
DEV = "7GL0226408083897"
BUNDLE = "com.sansheng.ime"
DRY = False   # --dry-run：只打印将要执行的 hdc 命令，不碰设备（布局没确认前先拿它走一遍）
ABILITY = "EntryAbility"
EVID = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "docs", "evidence", "2026-10-25", "h164-candidate-scroll")

# 字母三行（与 scripts/type.sh 同源，2026-10-22 实测，2026-10-24 截图复核未变）
LETTERS = {
    "q": (63, 2090), "w": (191, 2090), "e": (319, 2090), "r": (447, 2090), "t": (575, 2090),
    "y": (703, 2090), "u": (831, 2090), "i": (959, 2090), "o": (1087, 2090), "p": (1215, 2090),
    "a": (114, 2253), "s": (245, 2253), "d": (377, 2253), "f": (508, 2253), "g": (639, 2253),
    "h": (771, 2253), "j": (902, 2253), "k": (1033, 2253), "l": (1165, 2253),
    "z": (248, 2420), "x": (378, 2420), "c": (509, 2420), "v": (640, 2420), "b": (770, 2420),
    "n": (901, 2420), "m": (1032, 2420),
}
# 底栏 7 键 + 候选行右侧 ▼（2026-10-25 00:4x 按 11:32 实拍 `docs/evidence/2026-10-23/q-1115-screen.jpeg` 重量：
# 10:35 底栏重排后是 ?123｜九键｜😊｜🌐｜空格｜.｜↵，旧的 09:47 六键表（😊/简/三生）已作废）
# 字母三行的 x 与本文件 LETTERS 逐个对上；简/繁＝长按 🌐（globe），不再有独立「简」键。
SPECIAL = {
    "q123": (82, 2588),   # 符号页（10:44 实拍量：底栏 y 2524–2652，?123 键 x 0–110）
    "emoji": (190, 2588), # 本装机包底栏第 2 键是 😊，**没有九键键**——九键只能走长按菜单（H-078）
    "globe": (440, 2638), # 语言键；简/繁 = 长按
    "space": (763, 2588),
    "dot": (1050, 2588),
    "enter": (1165, 2588),
    "bk": (1175, 2420),   # z 行最右退格
    "cand": (1188, 1950), # 候选行最右 ▼（单击展开/折叠）；y 按 10-25 10:03 实拍 1946–1960 量
    # 长按 ?123/ABC 弹出的布局菜单（10:44 实拍：浮层 y 2160–2480、x 28–587，中间 Divider 在 y2332）
    "lay_26": (200, 2246),
    "lay_9": (200, 2408),
}


def sh(*args, check=False, cwd=None):
    """hdc 封装。**shell 子命令一律先拼成一整条**再发。

    坑（2026-10-25 09:54 实测）：hdc 会把「含空格的单个参数」原样加引号送到设备，
    于是 `sh("shell", "uitest uiInput click", 640, 1600)` 在设备上变成
    `"uitest uiInput click" 640 1600` ⇒ `/bin/sh: uitest uiInput click: inaccessible or not found`，
    而 hdc 的退出码**仍是 0**——tap() 之前一直静默失败、shot() 拿到空文件才炸。
    所以：① shell 参数 join 成一条；② check=True 时把设备侧报错也算失败。
    """
    args = list(args)
    if args and args[0] == "shell":
        args = ["shell", " ".join(str(a) for a in args[1:])]
    if DRY:
        print("DRY  hdc -t %s %s%s" % (DEV, " ".join(args), ("   (cwd=%s)" % cwd) if cwd else ""))
        return ""
    env = dict(os.environ)
    env["MSYS_NO_PATHCONV"] = "1"
    r = subprocess.run([HDC, "-t", DEV] + args, capture_output=True, env=env, cwd=cwd)
    out = (r.stdout or b"") + (r.stderr or b"")
    txt = out.decode("utf-8", "replace")
    if check and (r.returncode != 0 or any(m in txt for m in DEV_ERR_MARKERS)):
        raise SystemExit("hdc 失败: %s\n%s" % (" ".join(args), txt))
    return txt


# 设备侧失败标志（hdc 经常回 0）：2026-10-25 09:54 三条实测样本
DEV_ERR_MARKERS = ("inaccessible or not found", "[Fail]", "error: ", "unknown option")


def recv(remote, local):
    """`hdc file recv` 的本地路径必须是**相对**的：Windows 绝对路径会被 hdc/MSYS 二次改写
    （2026-10-25 00:50 实测：切到目标目录 + 只传真名才稳）。"""
    d = os.path.dirname(os.path.abspath(local)) or "."
    os.makedirs(d, exist_ok=True)
    sh("file", "recv", remote, os.path.basename(local), check=True, cwd=d)
    return local


def tap(x, y):
    # check=True：以前这里静默失败（命令没发对也返回 0），12 步全打在空气里都不知道
    sh("shell", "uitest uiInput click", str(int(x)), str(int(y)), check=True)
    time.sleep(0.25)


def press(x, y):
    """长按（H-078：长按 ?123/ABC 弹 26键/九键 菜单）。uitest longClick 无时长参数，用系统默认。"""
    sh("shell", "uitest uiInput longClick", str(int(x)), str(int(y)), check=True)
    time.sleep(0.25)


def smooth(x1, y1, x2, y2, velocity=2000):
    """候选栏横滑。用 uitest swipe（快），不用 uinput -T -m。

    2026-10-25 10:24 实测：`uinput -T -m` 默认 smoothTime=1000ms ⇒ 手指按住整 1 秒，
    候选条目把它当年**长按**处理，试打框里多冒出「—=」两个字（b9.jpeg 可见）——注入方式
    污染了证据。改成 700–850px @2000px/s（≈0.4 秒）后，列表照样连续滚动（t5→t6 实拍），
    且试打框文字不变（runbook 里有 NO-COMMIT 前后比对）。
    """
    sh("shell", "uitest uiInput swipe %d %d %d %d %d" %
       (int(x1), int(y1), int(x2), int(y2), int(velocity)), check=True)


def shot(name):
    # 用 snapshot_display（2026-10-25 09:03 实测可用，后缀必须 .jpeg；锁屏也能拍，因此可当「解锁了没」的探针）
    os.makedirs(EVID, exist_ok=True)
    remote = "/data/local/tmp/%s.jpeg" % name
    sh("shell", "snapshot_display -f", remote, check=True)
    local = os.path.join(EVID, "%s.jpeg" % name)
    recv(remote, local)
    if DRY:
        return
    print("SHOT %s (%d B)" % (local, os.path.getsize(local)))


def dump(name="h164_lay"):
    remote = "/data/local/tmp/%s.json" % name
    local = os.path.join(EVID, name + ".json")
    sh("shell", "uitest dumpLayout -p", remote, check=True)
    os.makedirs(EVID, exist_ok=True)
    recv(remote, local)
    print("DUMP %s（应用页树：找试打框用；键盘面板不在其中，候选坐标见 cands）" % local)
    return local


def input_text(layout_path):
    """读应用页试打框里的**已上屏**文字（preedit 不在里面）。

    用途：判据① 的「注入不污染输入」——滑之前/之后各 dump 一次，文字必须一模一样；
    也对判据④ 有用（点候选后这里的尾巴就是上屏结果）。
    """
    import json
    try:
        with open(layout_path, encoding="utf-8", errors="replace") as f:
            root = json.load(f)
    except Exception:
        return None
    found = []

    def walk(n):
        if not isinstance(n, dict):
            return
        a = n.get("attributes") or {}
        typ = a.get("type") or ""
        if ("TextArea" in typ or "TextInput" in typ) and not found:
            found.append(a.get("text") or "")
        for c in n.get("children") or []:
            walk(c)

    walk(root)
    return found[0] if found else None


# 候选行竖向范围（1280x2832 竖屏；键盘布局一改先看 shot 再改这两个数）
CAND_BAND = (1855, 1995)          # 含上方浅灰编码串，只用于文档对照
CAND_ROWS = (1918, 1985)          # 截图里**候选黑字**的实拍行范围（2026-10-25 10:03 b1.jpeg 逐行量）
CAND_MIN_W = 12
CAND_MAX_X = 1140                 # ▼ 在 x 1174–1203，别当成候选


def image_cands(jpeg, rows=CAND_ROWS):
    """从截图里量候选：切候选行 → 逐列统计暗像素 → 按 ≥24px 空白切段 → 取每段中心。

    为什么不再用 dumpLayout：2026-10-25 10:02 实测，`uitest dumpLayout -i` 返回三个窗口树，
    键盘面板窗（hostWindowId=28，bundle=com.ohos.sceneboard）里**一个 text 节点都没有**——
    输入法面板不对无障碍暴露（防止读键），候选坐标只能从像素里量。
    """
    from PIL import Image
    import numpy as np
    a = np.asarray(Image.open(jpeg).convert("L"))
    band = a[rows[0]:rows[1], :]
    cols = (band < 160).sum(axis=0)
    runs, s, gap = [], None, 0
    for x, v in enumerate(cols):
        if v > 0:
            if s is None:
                s = x
            gap = 0
        elif s is not None:
            gap += 1
            if gap >= 24:
                runs.append((s, x - gap))
                s, gap = None, 0
    if s is not None:
        runs.append((s, len(cols) - 1))
    out = []
    for x1, x2 in runs:
        if x2 - x1 + 1 < CAND_MIN_W or x2 > CAND_MAX_X:
            continue
        out.append({"text": "", "x": (x1 + x2) // 2, "y": (rows[0] + rows[1]) // 2,
                    "bounds": [x1, rows[0], x2, rows[1]],
                    "src": os.path.basename(jpeg)})
    return out


def band_hash(jpeg, rows=CAND_ROWS):
    """候选行的像素指纹：判据①「注入了移动、列表真滚了」的机器判据（不用认字）。"""
    from PIL import Image
    import hashlib
    a = Image.open(jpeg).convert("L").crop((0, rows[0], 1280, rows[1]))
    return hashlib.md5(a.tobytes()).hexdigest()[:12]


def cands_from_shot(name):
    """把 shot 出来的截图量成 h164_cands.json，返回条数。"""
    import json
    jpeg = os.path.join(EVID, name + ".jpeg")
    cands = image_cands(jpeg)
    side = os.path.join(EVID, "h164_cands.json")
    with open(side, "w", encoding="utf-8") as f:
        json.dump(cands, f, ensure_ascii=False, indent=1)
    print("CANDS %d 条（图 %s，行 %d–%d）：%s" %
          (len(cands), name, CAND_ROWS[0], CAND_ROWS[1],
           ", ".join("x=%d[%d-%d]" % (c["x"], c["bounds"][0], c["bounds"][2]) for c in cands)))
    return len(cands)


def parse_cands(path, band=CAND_BAND):
    """从应用页 dumpLayout 的 JSON 里取 Text 节点（含 bounds 与中心点）。

    ⚠ 键盘面板不在这个树里（2026-10-25 10:02 实测），所以**候选坐标不能靠它**——
    候选走 image_cands()。这里仅保留给「试打框/页面控件」类查询。
    """
    import json
    import re
    with open(path, encoding="utf-8", errors="replace") as f:
        root = json.load(f)
    out = []

    def walk(node):
        if not isinstance(node, dict):
            return
        a = node.get("attributes") or {}
        text = (a.get("text") or "").strip()
        b = a.get("bounds") or ""
        m = re.match(r"\[(-?\d+),(-?\d+)\]\[(-?\d+),(-?\d+)\]", b)
        if text and m:
            x1, y1, x2, y2 = (int(v) for v in m.groups())
            cy = (y1 + y2) // 2
            if band[0] <= cy <= band[1] and x2 > x1 and text not in ("▼", "▲"):
                out.append({"text": text, "x": (x1 + x2) // 2, "y": cy,
                            "bounds": [x1, y1, x2, y2]})
        for c in node.get("children") or []:
            walk(c)

    walk(root)
    out.sort(key=lambda d: d["x"])
    return out


def show_cands(path):
    """路径是截图 ⇒ 从像素量；是布局 JSON ⇒ 只在应用页树里找（键盘面板取不到）。"""
    if path.lower().endswith((".jpeg", ".jpg")):
        return cands_from_shot(os.path.splitext(os.path.basename(path))[0])
    import json
    try:
        cands = parse_cands(path)
    except Exception as e:  # 布局 JSON 结构变了就只报错，不猜
        print("CANDS 解析失败（%s）；先看 %s" % (e, path))
        return 0
    side = os.path.join(EVID, "h164_cands.json")
    with open(side, "w", encoding="utf-8") as f:
        json.dump(cands, f, ensure_ascii=False, indent=1)
    print("CANDS %d 条（应用页树）：" % len(cands))
    for i, c in enumerate(cands, 1):
        print("  %d. %s  x=%d y=%d" % (i, c["text"], c["x"], c["y"]))
    print("  侧车 %s（tapcand N 用它）" % side)
    return len(cands)


def tapcand(idx):
    import json
    side = os.path.join(EVID, "h164_cands.json")
    if not os.path.exists(side):
        raise SystemExit("还没有候选坐标：先 cands <截图名>")
    with open(side, encoding="utf-8") as f:
        cands = json.load(f)
    n = int(idx)
    if not 1 <= n <= len(cands):
        raise SystemExit("只有 %d 条候选，取不到第 %d 条" % (len(cands), n))
    c = cands[n - 1]
    tap(c["x"], c["y"])
    print("tapcand %d = %s (%d,%d) 来自 %s" % (n, c.get("text") or "图测", c["x"], c["y"], c.get("src", "?")))


DEV_SNIP = "/data/local/tmp/h164_ie.txt"


def snip(reset=False):
    """把当前 hilog 里本键盘的 SSKeyboardIndex 行追加到设备侧小文件。

    为什么边跑边抓：hilog 环形缓冲只留了本应用约 15 秒的日志（2026-10-25 10:13 实测：
    10:11:51 打字、8 次拖拽期间的 H-164 scroll 行到 10:13 全被冲掉，只剩最后 4 行），
    所以滚动行必须在拖拽当时抓下来，否则判据③⑦ 无从核对。
    """
    if reset:
        sh("shell", "rm -f " + DEV_SNIP)
    sh("shell", "hilog -x | grep SSKeyboardIndex >> " + DEV_SNIP)


def logs(name="h164-hilog"):
    """把设备侧累积的 SSKeyboardIndex 行取回，按整行去重（多轮 snip 会重复追加）。"""
    os.makedirs(EVID, exist_ok=True)
    snip()
    local = os.path.join(EVID, name + ".txt")
    recv(DEV_SNIP, local)
    if DRY:
        return
    seen, out = set(), []
    with open(local, encoding="utf-8", errors="replace") as f:
        for line in f:
            if line in seen:
                continue
            seen.add(line)
            out.append(line)
    with open(local, "w", encoding="utf-8") as f:
        f.writelines(out)
    hits = [ln.rstrip() for ln in out if "H-164" in ln or "state: cand" in ln]
    print("LOG %s （%d 行，命中 %d 行）" % (local, len(out), len(hits)))
    for line in hits[-40:]:
        print(line)


def plan():
    print(__doc__)


def main():
    global DRY
    argv = [x for x in sys.argv[1:] if x != "--dry-run"]
    DRY = "--dry-run" in sys.argv[1:]
    ap = argparse.ArgumentParser(add_help=True)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("plan")
    sub.add_parser("launch")
    sub.add_parser("dump")
    p = sub.add_parser("cands"); p.add_argument("shot", nargs="?")
    sub.add_parser("logs")
    sub.add_parser("clear")
    p = sub.add_parser("tap"); p.add_argument("x"); p.add_argument("y")
    p = sub.add_parser("press"); p.add_argument("x"); p.add_argument("y")
    p = sub.add_parser("tapcand"); p.add_argument("n")
    p = sub.add_parser("keys"); p.add_argument("text")
    p = sub.add_parser("smooth"); p.add_argument("x1"); p.add_argument("y1"); p.add_argument("x2"); p.add_argument("y2")
    p = sub.add_parser("shot"); p.add_argument("name")
    a = ap.parse_args(argv)

    if a.cmd == "plan":
        plan()
    elif a.cmd == "launch":
        print(sh("shell", "aa", "start", "-a", ABILITY, "-b", BUNDLE))
    elif a.cmd == "dump":
        dump()
    elif a.cmd == "cands":
        show_cands(os.path.join(EVID, (a.shot + ".jpeg") if a.shot else "h164_lay.json"))
    elif a.cmd == "tapcand":
        tapcand(a.n)
    elif a.cmd == "logs":
        logs()
    elif a.cmd == "clear":
        sh("shell", "hilog", "-r")
        print("hilog 缓冲已清")
    elif a.cmd == "tap":
        tap(a.x, a.y)
        print("tap %s %s" % (a.x, a.y))
    elif a.cmd == "press":
        press(a.x, a.y)
        print("press %s %s" % (a.x, a.y))
    elif a.cmd == "keys":
        unknown = []
        for ch in a.text:
            if ch in LETTERS:
                tap(*LETTERS[ch])
            else:
                unknown.append(ch)
        if unknown:
            print("未映射字符（需先看 shot 重量坐标）: %s" % "".join(unknown))
        print("typed %s" % a.text)
    elif a.cmd == "smooth":
        smooth(a.x1, a.y1, a.x2, a.y2)
        print("smooth %s,%s -> %s,%s" % (a.x1, a.y1, a.x2, a.y2))
    elif a.cmd == "shot":
        shot(a.name)
    else:
        ap.print_help(sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
