#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""H-279 自造词真机判定实验（Qoder，2026-10-30 04:5x，主人 04:47 报「打 tgtf 造不出词」）

要回答的问题只有一个：**连续上屏几个单字之后，再打它们的合并编码，引擎会不会给出这个新词**。
安卓侧这条是通的（`rime/wubi_pinyin.custom.yaml` 第 81-83 行：`enable_encoder: true` +
`encode_commit_history: true`，注释里写的例子就是「打『刚』『需』→ 下次 mqfd 出『刚需』」）。
鸿蒙侧配置看着一样（`rawfile/rime/wubi_pinyin.schema.yaml` 79-91 行，另加 `db_class: userdb`），
所以**不能靠读配置下结论**（硬规则 11：读到配置不等于读到实机行为），必须真机跑一遍。

为什么用「点键 + 空格选第一个候选」而不是去点候选格：
`uitest dumpLayout` 取不到输入法面板窗口的子节点（H-116 实测），候选格坐标只能从截图量；
而空格＝选当前高亮候选是引擎行为，不依赖坐标，判定更干净。

实验步骤（全部在**我们自己 App 的「试一试」输入框**里做，不碰主人任何文档）：
  ① 起 App、点输入框、确认三生键盘在屏上；
  ② 打 t g t f → 截图（基线：这时 tgtf 有没有一个四字词候选）；
  ③ 清空重来，逐字上屏：t+空格、g+空格、t+空格、f+空格（读输入框正文，确认真的上屏了 4 个字）；
  ④ 再打 t g t f → 截图（造出来了＝候选里出现刚才那 4 个字连成的词）；
  ⑤ `aa force-stop` 杀输入法进程，重开再打 t g t f → 截图（跨进程还在＝userdb 真的落盘）。

输出：每一步的截图落在 `docs/evidence/2026-10-30/h279-device/`，并在最后打一段 JSON 摘要
（每步输入框正文 + 键位坐标来源 + 有没有量到键）。**判词由人看图下**，脚本不猜候选文字。

用法：
    python scripts/h279_zaozici_device_check.py            # 跑全套
    python scripts/h279_zaozici_device_check.py --codes tg tf   # 换一组编码
退出码：0＝跑完（不代表功能通过）；2＝环境不对（没设备/键盘没弹起/量不到键）。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

try:
    from PIL import Image  # noqa: F401  (panel_keys 依赖)
except ImportError:
    sys.exit("需要 Pillow：python -m pip install pillow")

import panel_keys  # 复用已验证的白色键帽量法

HDC = os.environ.get(
    "SS_HDC",
    r"D:/DevTools/DevEco/DevEco Studio/sdk/default/openharmony/toolchains/hdc.exe",
)
BUNDLE = "com.sansheng.ime"
ABILITY = "EntryAbility"
DEV_TMP = "/data/local/tmp/h279.png"
LAY_DEV = "/data/local/tmp/h279_layout.json"
EVID = os.path.join(ROOT, "docs", "evidence", "2026-10-30", "h279-device")

QWERTY_ROWS = ["qwertyuiop", "asdfghjkl"]


def sh(*args, binary=False):
    env = dict(os.environ, MSYS_NO_PATHCONV="1")
    r = subprocess.run([HDC] + list(args), capture_output=True, env=env)
    out = r.stdout or b""
    return out if binary else out.decode("utf-8", "replace")


def tap(x, y, hold=0.25):
    sh("shell", "uitest", "uiInput", "click", str(int(x)), str(int(y)))
    time.sleep(hold)


def shot(name):
    path = os.path.join(EVID, name)
    sh("shell", "uitest", "screenCap", "-p", DEV_TMP)
    sh("file", "recv", DEV_TMP, path)
    return path


def dump_layout():
    sh("shell", "uitest", "dumpLayout", "-p", LAY_DEV)
    raw = sh("shell", "cat", LAY_DEV, binary=True)
    try:
        return json.loads(raw.decode("utf-8", "replace"))
    except Exception:
        return {}


def walk(node, out):
    a = node.get("attributes", {}) or {}
    out.append(a)
    for c in node.get("children", []) or []:
        walk(c, out)
    return out


def box_center(a):
    m = re.match(r"\[(-?\d+),(-?\d+)\]\[(-?\d+),(-?\d+)\]", a.get("bounds", "") or "")
    if not m:
        return None
    x1, y1, x2, y2 = map(int, m.groups())
    return ((x1 + x2) // 2, (y1 + y2) // 2, x1, y1, x2, y2)


def find_field():
    """定位自家 App「试一试」下面那块输入区，返回 {cx, cy, box, text}。

    为什么不用 class 判（第一版踩的坑）：Mate 80 上 `uitest dumpLayout` 回来的节点
    **class 字段是空的**（04:56 实测 88 个节点全是 class=''），只有 text/bounds ⇒
    按 class 找 TextInput 必然找不到，脚本会误报「页面没起来」。
    改用几何判据：先找文字等于「试一试」的那条标签，再取它**正下方**最高的一块，
    那块就是输入区（实测 bounds [70,1466][1210,1849]，正文＝主人刚打的字）。
    """
    nodes = walk(dump_layout(), [])
    label = None
    for a in nodes:
        if (a.get("text") or "").strip() == "试一试":
            label = box_center(a)
            break
    if not label:
        return None
    _, _, lx1, ly1, lx2, ly2 = label
    best = None
    for a in nodes:
        c = box_center(a)
        if not c:
            continue
        cx, cy, x1, y1, x2, y2 = c
        if y1 < ly2 - 10:          # 只要标签下方的
            continue
        if x2 - x1 < 600:          # 输入区是整宽的
            continue
        h = y2 - y1
        if best is None or h > best[0]:
            best = (h, c, (a.get("text") or ""))
    if not best:
        return None
    (cx, cy, x1, y1, x2, y2), text = best[1], best[2]
    return {"cx": cx, "cy": cy, "box": [x1, y1, x2, y2], "text": text}


def key_map(png):
    """量键帽 → {字母: (cx,cy)} + 空格坐标。行按键数对位，认不出就返回 None。"""
    rows, (w, h) = panel_keys.measure(png)
    letters = {}
    for ri, pattern in enumerate(QWERTY_ROWS):
        want = len(pattern)
        row = None
        for r in rows:
            if len(r) == want:
                row = r
                break
        if row is None:
            continue
        for ch, k in zip(pattern, row):
            letters[ch] = (k["cx"], k["cy"])
        # 用过就从 rows 里摘掉，避免第二行误配
        rows.remove(row)
    space = None
    if rows:
        last = max(rows, key=lambda r: max((k["w"] for k in r), default=0))
        space = max(last, key=lambda k: k["w"])
        space = (space["cx"], space["cy"])
    return letters, space, len(rows)


def type_seq(letters, seq):
    for ch in seq:
        xy = letters.get(ch)
        if not xy:
            print("  [warn] 量不到键 '%s'，跳过" % ch)
            continue
        tap(*xy)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--codes", nargs="+", default=["t", "g", "t", "f"],
                    help="逐字上屏的编码序列（默认 t g t f）")
    args = ap.parse_args()
    codes = args.codes
    merged = "".join(codes)

    os.makedirs(EVID, exist_ok=True)
    targets = [ln.strip() for ln in sh("list", "targets").splitlines()
               if ln.strip() and "[Empty]" not in ln]
    if not targets:
        print("没有设备在线 ⇒ 不跑")
        return 2

    sh("shell", "aa", "start", "-a", ABILITY, "-b", BUNDLE)
    time.sleep(2.5)

    field = find_field()
    if not field:
        print("没找到自家 App 的输入框（页面没起来？）⇒ 不跑")
        return 2
    tap(field["cx"], field["cy"], hold=1.2)

    letters, space, nrows = key_map(shot("h279-00-panel.png"))
    missing = [c for c in set(codes) if c not in letters]
    if not letters or missing or not space:
        print("键位量不全：认到 %d 个字母键 / 缺 %s / 空格 %s（行数 %d）"
              % (len(letters), missing or "无", space, nrows))
        print("⇒ 面板可能停在符号页或单手模式没退，先人工看 h279-00-panel.png")
        return 2

    report = {"codes": codes, "merged": merged, "steps": []}

    def step(tag, action):
        png = shot("h279-%s.png" % tag)
        f = find_field() or {"text": "?"}
        report["steps"].append({"tag": tag, "action": action,
                                "field_text": f["text"], "png": os.path.basename(png)})
        print("[%s] %s ⇒ 输入框正文=%r" % (tag, action, f["text"]))

    # ① 基线：直接打合并编码，看有没有现成词
    step("01-before", "清空前现状")
    type_seq(letters, merged)
    step("02-baseline", "打 %s（未造词基线）" % merged)
    tap(*space)
    step("03-baseline-commit", "空格上屏基线候选")

    # ② 逐字上屏（每段编码 + 空格）
    for i, c in enumerate(codes):
        type_seq(letters, c)
        tap(*space)
        print("  逐字 %d/%d：%s+空格" % (i + 1, len(codes), c))
    step("04-learned", "逐字上屏完 %s" % "+".join(codes))

    # ③ 再打合并编码，看新词有没有出现
    type_seq(letters, merged)
    step("05-retype", "再打 %s（造出来就该有新词候选）" % merged)
    tap(*space)
    step("06-retype-commit", "空格上屏第二次")

    # ④ 杀进程，验跨会话还在（userdb 落盘判据）
    sh("shell", "aa", "force-stop", "-b", BUNDLE)
    time.sleep(1.5)
    sh("shell", "aa", "start", "-a", ABILITY, "-b", BUNDLE)
    time.sleep(3.0)
    f2 = find_field()
    if f2:
        tap(f2["cx"], f2["cy"], hold=1.2)
        letters2, space2, _ = key_map(shot("h279-07-restart-panel.png"))
        if letters2 and space2:
            type_seq(letters2, merged)
            step("08-after-kill", "杀进程重开后再打 %s" % merged)
        else:
            report["steps"].append({"tag": "07-restart", "action": "重开后量不到键位", "field_text": "?"})
    with open(os.path.join(EVID, "h279-report.json"), "w", encoding="utf-8") as fp:
        json.dump(report, fp, ensure_ascii=False, indent=2)
    print("\n摘要写到 docs/evidence/2026-10-30/h279-device/h279-report.json")
    print("看图定判：02（基线候选）vs 05（造词后候选）vs 08（杀进程后还在不在）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
