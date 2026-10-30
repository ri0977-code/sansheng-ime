#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""H-279 自造词真机探针（Qoder，2026-10-30）—— 交互式，一条命令做一件事，判词由人看图下。

为什么不复用 h279_zaozici_device_check.py 的「自动量键位」：
  panel_keys.measure 只认**白色键帽**，而三生键盘 26 键页里只有第一行 + z/b + 空格是白的，
  第二三行是灰的（真机截图 h279-00-panel.png 实测），按颜色分带必然量不全 ⇒ 直接放弃颜色法，
  改成从这张截图里**逐行量出来的固定坐标**（量法见下方 KEYS 注释里的扫描结果）。

坐标系：Mate 80 1280x2832，截图与触摸 1:1（H-116 口径）。

用法：
    python scripts/h279_probe.py keys t g t f      # 依次点字母键
    python scripts/h279_probe.py space             # 点空格（=选当前候选，走引擎提交链）
    python scripts/h279_probe.py bk 4              # 点退格 4 次（只删编码，别乱加）
    python scripts/h279_probe.py shot 03-after     # 截图 + 裁出「输入框+候选条」小图
    python scripts/h279_probe.py raw 576 2086      # 裸点
退出码 0=动作完成；2=环境不对。
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import time

HDC = os.environ.get(
    "SS_HDC",
    r"D:/DevTools/DevEco/DevEco Studio/sdk/default/openharmony/toolchains/hdc.exe",
)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVID = os.path.join(ROOT, "docs", "evidence", "2026-10-30", "h279-device")
DEV_TMP = "/data/local/tmp/h279p.jpeg"  # 这台 Mate 80 的 snapshot_display 只收 .jpeg（实测报错）

# 键位：从 h279-00-panel.png 逐行扫描量出（背景色 229,231,237，游程 >40px 即一个键）。
# row1 y=2086: q w e r t y u i o p   （10 个，中心 64/192/.../1216，间距 128）
# row2 y=2253: a s d f g h j k l     （9 个，中心 114/246/377/508/640/771/902/1034/1165）
# row3 y=2420: z x c v b n m         （9 个游程里第 2..8 个；首尾是 shift/删除）
# row4 y=2587: 空格 = 432..992 的宽带（中间被「三生」两个字切开），中心 712
ROW1 = dict(zip("qwertyuiop", [64, 192, 320, 448, 576, 704, 832, 960, 1088, 1216]))
ROW2 = dict(zip("asdfghjkl", [114, 246, 377, 508, 640, 771, 902, 1034, 1165]))
ROW3 = dict(zip("zxcvbnm", [248, 378, 509, 640, 770, 901, 1032]))
KEYS = {}
for d, y in ((ROW1, 2086), (ROW2, 2253), (ROW3, 2420)):
    for k, x in d.items():
        KEYS[k] = (x, y)
SPACE = (712, 2587)
BACKSPACE = (1188, 2420)          # row3 最右 = 删除
CAND1 = (100, 1940)               # 候选第 1 格（称王称霸 实测占 x 20..210）


def sh(args, cwd=None):
    env = dict(os.environ, MSYS_NO_PATHCONV="1")
    return subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", cwd=cwd, env=env)


def need_device() -> bool:
    out = sh([HDC, "list", "targets"]).stdout
    if "7GL0226408083897" not in out and len(out.strip().splitlines()) < 1:
        print("没连上设备：", out.strip())
        return False
    return True


def tap(x: int, y: int, label: str = "") -> None:
    r = sh([HDC, "shell", "uitest", "uiInput", "click", str(x), str(y)])
    ok = "No Error" in (r.stdout + r.stderr)
    print(f"tap {label or (x, y)} -> {'ok' if ok else r.stdout.strip()[:60]}")
    if not ok:
        sys.exit(2)


def field_text() -> str:
    """读「试一试」输入框正文。

    输入法面板窗口 dumpLayout 取不到（H-116），但**被测 App 的窗口取得到**，
    所以正文能直接读——每一步到底上屏了什么，不用靠截图猜。
    """
    import json
    r = sh([HDC, "shell", "uitest", "dumpLayout"])
    m = re.search(r"(?:file saved at|saved to):\s*(\S+)", r.stdout)
    path = m.group(1) if m else None
    if not path:
        # dumpLayout 没报路径时，退而取 /data/local/tmp 下最新的 json
        ls = sh([HDC, "shell", "ls -t /data/local/tmp/*.json 2>/dev/null | head -1"])
        first = ls.stdout.split("\n")[0].strip()
        path = first or None
    if not path:
        return "<dumpLayout 失败>"
    js = sh([HDC, "shell", f"cat {path}"])
    try:
        tree = json.loads(js.stdout)
    except Exception:
        return "<解析失败>"
    best = ""
    stack = [tree]
    while stack:
        n = stack.pop()
        if isinstance(n, dict):
            t = n.get("text") or ""
            b = n.get("bounds") or ""
            mm = re.match(r"\[\d+,(\d+)\]\[\d+,\d+\]", b)
            in_field_band = bool(mm) and 1380 <= int(mm.group(1)) <= 1900
            if t and in_field_band and len(t) > len(best):
                best = t
            stack.extend(n.values())
        elif isinstance(n, list):
            stack.extend(n)
    return best


def shot(name: str) -> None:
    os.makedirs(EVID, exist_ok=True)
    sh([HDC, "shell", "snapshot_display", "-f", DEV_TMP])
    time.sleep(0.6)
    jpeg = os.path.join(EVID, f"h279p-{name}.jpeg")
    if os.path.exists(jpeg):
        os.remove(jpeg)
    sh([HDC, "file", "recv", DEV_TMP, f"./h279p-{name}.jpeg"], cwd=EVID)
    if not os.path.exists(jpeg):
        print("截图没落盘：", jpeg)
        sys.exit(2)
    from PIL import Image
    im = Image.open(jpeg).convert("RGB")
    full = os.path.join(EVID, f"h279p-{name}.png")
    im.save(full)
    im.crop((0, 1400, im.size[0], 2020)).save(os.path.join(EVID, f"h279p-{name}-crop.png"))
    print("full :", full)
    print("crop :", os.path.join(EVID, f"h279p-{name}-crop.png"))


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if not need_device():
        return 2
    cmd, rest = argv[0], argv[1:]
    if cmd == "keys":
        for ch in "".join(rest):
            if ch not in KEYS:
                print("不认识：", ch)
                return 2
            tap(*KEYS[ch], label=ch)
            time.sleep(0.18)
    elif cmd == "space":
        tap(*SPACE, label="space")
    elif cmd == "bk":
        n = int(rest[0]) if rest else 1
        for _ in range(n):
            tap(*BACKSPACE, label="bk")
            time.sleep(0.15)
    elif cmd == "cand":
        tap(*CAND1, label="cand1")
    elif cmd == "raw":
        tap(int(rest[0]), int(rest[1]))
    elif cmd == "shot":
        shot(rest[0] if rest else "now")
    elif cmd == "text":
        print("FIELD:", field_text())
    else:
        print("未知命令：", cmd)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
