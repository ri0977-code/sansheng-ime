# -*- coding: utf-8 -*-
"""H-241 诊断（Qoder 2026-10-28 03:4x）：注入 longClick 到底有没有走到「出泡计时器」？

背景：契约 §3-6/§3-7 两项判据都盯 hilog `H-215 timer open bubble`，而**这条日志在历史上
从来没出现过一次**（grep 全 docs/evidence 只有判据文本自己）。三种可能：
  A. 注入的持按时长 < 阈值 ⇒ 计时器没到点；
  B. 到了点但守卫没过（`letterHeld` 已被 Up 置 false / `longPressLetter` 残留非空 /
     `getHiddenSymbols('q')` 为空 ⇒ 压根没起计时）；
  C. 判据盯的日志串与实际不一致。
反证口径：长按空格开设置卡走的是 `SETTINGS_HOLD_MS=600` 的 setTimeout，注入 longClick
**能**开卡 ⇒ 持按 ≥600ms 是实测事实，A 只对「阈值 >600」成立。本脚本把一次长按 q 前后
IME 进程的全部 JSAPP 行落盘，看 Down/振动/出泡哪几条在，再配一张像素图。

用法：PYTHONIOENCODING=utf-8 python scripts/h241_diag_bubble.py [字母]
"""
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import h231_panel_check as h231           # noqa: E402
import h241_settings_device_check as drv  # noqa: E402
import h241_settings_items as it          # noqa: E402


def main():
    ch = sys.argv[1] if len(sys.argv) > 1 else "q"
    if h231.bring_up() is None:
        drv.log("DIAG 拉起键盘失败")
        return 1
    it.refresh()
    b = it.key_box(ch)
    cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
    drv.log("DIAG 键 %s 框=%s 中心=(%d,%d)" % (ch, [int(v) for v in b], cx, cy))
    drv.hl(r"JSAPP", clear=True, wait=0.3)
    drv.long_press(cx, cy)
    time.sleep(1.2)
    lines = drv.hl(r"JSAPP", wait=0.2)
    p = it.uniq(it.item_dir("diag_bubble"), "longpress-all-%s" % ch, "txt")
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    drv.log("DIAG 长按后 JSAPP 行数=%d -> %s" % (len(lines), p))
    for pat, tag in [(r"timer open bubble", "出泡"),
                     (r"haptic|vibrat", "振动"),
                     (r"SettingsStore: set|settings synced", "设置"),
                     (r"bubble|H-215|H-216", "气泡相关")]:
        hit = [ln for ln in lines if re.search(pat, ln)]
        drv.log("DIAG[%s] %d 条" % (tag, len(hit)))
        for ln in hit[-6:]:
            drv.log("   | %s" % ln[-120:])
    shot = it.shot("diag_bubble", "after-longclick-%s" % ch)
    band = [b[0] - 60, b[1] - 175, b[2] + 300, b[1] - 18]
    m = it.ink_stats(shot, band)
    drv.log("DIAG 键 %s 上方带 %s 暗像素=%d（有泡应显著 >0）" % (ch, [int(v) for v in band], m["ink"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
