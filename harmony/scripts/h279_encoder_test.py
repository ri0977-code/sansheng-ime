#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""H-279 判定性实验（Qoder，2026-10-30）：区分「encoder 规则造词」和「连句候选」。

为什么必须做这条实验：
  10-21 探针与今天的真机测试都拿「打 mqfd 出刚需」当自造词通了，但这句话证不了 ——
  librime 在 enable_sentence: true 时，只要输入能切成若干合法码，Poet 就会**当场连句**，
  连句结果和 encoder 存进用户词典的词条在候选条里长得一模一样。

判据（离线从 entry/src/main/resources/rawfile/rime/wubi86.dict.yaml 逐行量出）：
  鑫 = qqq / qqqf      （'qq' 这个码是「多」，不是鑫）
  淼 = iiiu            （'ii' 这个码是「水」，不是淼）
  ⇒ 打 qqqiiiu 出「鑫淼」：连句就能解释（qqq+iiiu 都是合法码），**不算证据**
  ⇒ 打 qqii 出「鑫淼」：连句只能拼「多水」，出现鑫淼只可能是 encoder 按二字规则
     AaAbBaBb（鑫 stem 首二 q q + 淼 stem 首二 i i）造出来并落进用户词典的词条 —— 这才是铁证。
  三字同理：行不行 的规则码 tgtf（AaBaCaCb），而 tf+gi+tf 的连串是 tgtftf。

用法：python scripts/h279_encoder_test.py [qqii|tgtf|all]
退出码 0=跑完（判词看打印 + 截图）。
"""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from h279_probe import KEYS, BACKSPACE, SPACE, field_text, need_device, shot, sh  # noqa: E402


def type_code(code: str) -> None:
    for ch in code:
        if ch not in KEYS:
            print("不认识：", ch)
            sys.exit(2)
        x, y = KEYS[ch]
        sh([os.environ.get("SS_HDC",
             r"D:/DevTools/DevEco/DevEco Studio/sdk/default/openharmony/toolchains/hdc.exe"),
             "shell", "uitest", "uiInput", "click", str(x), str(y)])
        time.sleep(0.18)


def clear_code(n: int) -> None:
    for _ in range(n):
        x, y = BACKSPACE
        sh([os.environ.get("SS_HDC",
             r"D:/DevTools/DevEco/DevEco Studio/sdk/default/openharmony/toolchains/hdc.exe"),
             "shell", "uitest", "uiInput", "click", str(x), str(y)])
        time.sleep(0.15)


def focus_field() -> None:
    # 「试一试」输入框（App 窗口内，y 1380..1900 带）；点它才起面板
    sh([os.environ.get("SS_HDC",
         r"D:/DevTools/DevEco/DevEco Studio/sdk/default/openharmony/toolchains/hdc.exe"),
         "shell", "uitest", "uiInput", "click", "400", "1600"])
    time.sleep(1.0)


def step(label: str, code: str, clear: int) -> None:
    if clear:
        clear_code(clear)
    type_code(code)
    time.sleep(0.5)
    shot(label)
    print(f"[{label}] 输入={code}  正文={field_text()!r}")


def main(argv):
    if not need_device():
        return 2
    which = argv[0] if argv else "all"
    focus_field()
    shot("21-focused")
    print("正文(聚焦后)=", repr(field_text()))
    if which in ("all", "qqii"):
        # 二字规则码：只有 encoder 能命中
        step("22-rulecode-qqii", "qqii", 0)
        # 连串码：连句也能命中，用来对照
        step("23-fullcode-qqqiiiu", "qqqiiiu", 4)
    if which in ("all", "tgtf"):
        step("24-rulecode-tgtf", "tgtf", 7)
    clear_code(6)
    shot("25-idle")
    print("收尾正文=", repr(field_text()))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
