#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""H-280 符号面板「中文引号」一键直出真机判定（Qoder，2026-10-30）

为什么要跑这个（闸门冲突，见 docs/ISSUES.md H-280）：
发布闸门 `check_app_content.py` 第 4 项断言 `default.yaml` 的
`punctuator.half_shape["'"]` 里含中文引号（H-093 的口径：1.0.0 必须能打中文引号）。
但 CodeArts 的 h275（M-368）把 `'` 等 9 个符号从**多候选数组压成单值**，理由是
「librime 只要值是 list，长度 1 也会弹候选菜单」（`fanxing_napi.cpp` 的 M-368 验收口径注释），
压成单值才能一键直出——主人已经真机验过这条（M-369：9 个键全部 `menu=0 num=0`，正文原样落字）。
于是第 4 项变红。

**不能靠读配置下结论**（硬规则 11），所以要判的是**用户可见属性**：
1.0.0 到底能不能一键打出中文引号？承载物是符号面板「常用」页的 “ ” ‘ ’ 「 」 『 』 格子
（多字节 UTF-8 ⇒ 走 `fanxing_napi.cpp:763` 那条「直接上屏、不进引擎」分支），
与 `punctuator.half_shape["'"]` 是两条独立路径。

本脚本用「点格子 + 读自家 App「试一试」输入框正文增量」证明这条路径真的通：
每一步只看正文多出来的是不是那一个字，不看候选、不猜坐标含义。
只做**追加**，绝不注入退格/清空（硬规则：不许在主人活文档里做破坏性输入；
这块输入框里的现存文字会在跑之前原样打印并留档）。

用法：
    python scripts/h279_symbol_quote_probe.py open                 # 起 App＋点输入框＋截面板
    python scripts/h279_symbol_quote_probe.py nav <x> <y>          # 点任意键并截图（用来找符号页）
    python scripts/h279_symbol_quote_probe.py cells <x1> <y1> ...  # 依次点这些坐标，逐个读正文增量
证据落在 docs/evidence/2026-10-30/h280-quote/。
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import h279_zaozici_device_check as D  # 复用已验证的 sh/tap/shot/find_field/量键法

EVID = os.path.join(D.ROOT, "docs", "evidence", "2026-10-30", "h280-quote")
BUNDLE = D.BUNDLE
ABILITY = D.ABILITY
D.EVID = EVID  # 截图落到本工单目录（复用函数内部读的是模块级 EVID）


def text() -> str:
    f = D.find_field()
    return f["text"] if f else "<找不到输入框>"


def main() -> int:
    os.makedirs(EVID, exist_ok=True)
    cmd = sys.argv[1] if len(sys.argv) > 1 else "open"
    D.sh("shell", "aa", "start", "-a", ABILITY, "-b", BUNDLE)
    import time
    time.sleep(2.5)
    f = D.find_field()
    if not f:
        print("没找到自家 App 的输入框（页面没起来？）⇒ 不跑")
        return 2
    if cmd == "open":
        print("输入框 bounds=%r 现有正文=%r" % (f["box"], f["text"]))
        D.tap(f["cx"], f["cy"], hold=1.2)
        p = D.shot("h280-00-panel.png")
        print("面板截图 ->", p)
        return 0
    if cmd == "nav":
        x, y = int(sys.argv[2]), int(sys.argv[3])
        print("点之前正文=%r" % text())
        D.tap(x, y, hold=1.0)
        p = D.shot("h280-01-after-tap-%d-%d.png" % (x, y))
        print("点之后正文=%r 截图 -> %s" % (text(), p))
        return 0
    if cmd == "cells":
        coords = [(int(a), int(b)) for a, b in zip(sys.argv[2::2], sys.argv[3::2])]
        before = text()
        print("基线正文=%r" % before)
        out = []
        for i, (x, y) in enumerate(coords):
            b = text()
            D.tap(x, y, hold=0.8)
            a = text()
            added = a[len(b):] if a.startswith(b) else ("<非追加>" if a != b else "")
            out.append({"i": i, "xy": [x, y], "before": b, "after": a, "added": added})
            print("[%02d] 点 (%d,%d) ⇒ 正文 %r → %r  新增=%r" % (i, x, y, b, a, added))
            D.shot("h280-10-%02d-%d-%d.png" % (i, x, y))
        path = os.path.join(EVID, "h280-cells.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"baseline": before, "steps": out}, fh, ensure_ascii=False, indent=2)
        print("摘要 ->", path)
        return 0
    print("未知命令", cmd)
    return 2


if __name__ == "__main__":
    sys.exit(main())
