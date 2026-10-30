#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""H-096 收口五件 · 一条命令全查（Qoder 归属，2026-10-23 14:2x）

为什么有它：CodeArts 的收口清单有五件（`docs/evidence/2026-10-23/h096-closure-checklist.md`），
其中只有两件有自动判据（反斜杠在 `check_rime_yaml.py`、图标在 `check_icon_ring.py`），
另外三件以前靠人 grep。本脚本把五件合成一条命令，**每件都只读、都给出明确结论**。

五件（M-134／M-140 派单）：
  F 探针页：`main_pages.json` 不得注册 M3Probe / LandscapeProbe（H-098，`.app` 闸门第 ⑩ 项）
  G 图标：包内两层 gold 覆盖率/内容占比/环厚对齐主人「顶四边贴满」口径（W-209 修订，
        覆盖 nova6 原版 fill≈0.77 几何；主人真机确认「好了」）
  H metadata：`module.json5` 的 `ohos.entry.mainability` 退掉或加注释说明理由
  I 注释：`KeyboardIndex.ets:1005` 注释与代码一致（代码已是条件分支）
  J 反斜杠：`default.yaml` 半角反斜杠出半角（D-023）

用法：
  python scripts/check_closure_items.py          # 查当前工作区
  python scripts/check_closure_items.py --strict # 任一件未过就 exit 1
"""
import argparse
import io
import os
import re
import sys

# Windows 控制台默认 GBK，含 ⇒/’/、 等非 GBK 字符会 UnicodeEncodeError 崩。
# 强制 stdout/stderr 走 UTF-8，让闸门在主人机器上也能打出完整报告。
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8", "utf_8"):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def rd(rel):
    p = os.path.join(ROOT, rel.replace("/", os.sep))
    if not os.path.exists(p):
        return None
    return io.open(p, encoding="utf-8", errors="replace").read()


def gold_ratio(path):
    from PIL import Image
    im = Image.open(path).convert("RGB")
    w, h = im.size
    data = im.getdata()
    c = sum(1 for px in data if px[0] > 150 and px[1] > 120 and px[2] < 140)
    return c / float(w * h)


def fill_and_ring(path):
    from PIL import Image
    im = Image.open(path).convert("RGB")
    w, h = im.size
    thick = 0
    y = h // 2
    for x in range(w):
        r, g, b = im.getpixel((x, y))
        if r > 140 and g > 100 and b < 140:
            thick += 1
        elif thick:
            break
    xs, ys = [], []
    for yy in range(0, h, 2):
        for xx in range(0, w, 2):
            r, g, b = im.getpixel((xx, yy))
            if r > 140 and g > 100 and b < 140:
                xs.append(xx); ys.append(yy)
    fill = ((max(xs) - min(xs)) / float(w)) if xs else 0.0
    return fill, thick / float(w)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args(argv)
    print(u"== H-096 收口五件检查（只读） ==")
    fails = []

    # F 探针页
    mp = rd("entry/src/main/resources/base/profile/main_pages.json")
    if mp is None:
        fails.append(u"F 探针页：main_pages.json 读不到")
    else:
        bad = [n for n in ("M3Probe", "LandscapeProbe") if n in mp]
        if bad:
            fails.append(u"F 探针页：仍注册 %s（删这两行 ⇒ `.app` 闸门第 ⑩ 项由红转绿，H-098）" % u"、".join(bad))
        else:
            print(u"  [OK  ] F 探针页：已摘（`.app` 可达 18/18，D-033 起）")

    # G 图标 —— 口径：主人「顶四边贴满」(W-209, 2026-10-23 真机确认"好了")，
    # 覆盖 nova6 原版 fill≈0.77 几何。判据：内容顶到四边(fill>=0.97)、gold 环占满画布。
    for rel in ("entry/src/main/resources/base/media/app_icon.png",
                "AppScope/resources/base/media/foreground.png"):
        p = os.path.join(ROOT, rel.replace("/", os.sep))
        if not os.path.exists(p):
            fails.append(u"G 图标：%s 不存在" % rel)
            continue
        gr, fill, ring = gold_ratio(p), fill_and_ring(p)[0], fill_and_ring(p)[1]
        # 顶四边：fill 接近 1.0（边到边），gold 环覆盖率放宽到 0.20~0.40（大金环顶满）
        ok = 0.20 <= gr <= 0.40 and fill >= 0.97 and ring >= 0.018
        if ok:
            print(u"  [OK  ] G 图标 %s：gold=%.3f fill=%.3f ring=%.4f（顶四边贴满口径，W-209）"
                  % (os.path.basename(rel), gr, fill, ring))
        else:
            fails.append(u"G 图标 %s：gold=%.3f fill=%.3f ring=%.4f 未达顶四边贴满（gold 0.20~0.40 / fill>=0.97 / ring>=0.018，W-209）"
                         % (os.path.basename(rel), gr, fill, ring))

    # H metadata
    mj = rd("entry/src/main/module.json5")
    if mj is None:
        fails.append(u"H metadata：module.json5 读不到")
    elif "ohos.entry.mainability" in mj:
        # 有注释说明理由也放行
        line_no = next((i + 1 for i, l in enumerate(mj.split("\n"))
                        if "ohos.entry.mainability" in l), 0)
        ctx = "\n".join(mj.split("\n")[max(0, line_no - 6):line_no])
        has_reason = bool(re.search(r"保留|理由|为什么|需要", ctx))
        if has_reason:
            print(u"  [OK  ] H metadata：仍在（第 %d 行）但附近有保留理由注释" % line_no)
        else:
            fails.append(u"H metadata：module.json5:%d 仍有 `ohos.entry.mainability` 且无保留理由注释（改 actions 前加的，现入口条件已满足 ⇒ 退掉或加注释）" % line_no)
    else:
        print(u"  [OK  ] H metadata：已退掉")

    # I 注释
    ki = rd("entry/src/main/ets/pages/KeyboardIndex.ets")
    if ki is None:
        fails.append(u"I 注释：KeyboardIndex.ets 读不到")
    else:
        lines = ki.split("\n")
        idx = next((i for i, l in enumerate(lines) if u"短按展开" in l and u"长按折叠" in l), None)
        if idx is None:
            print(u"  [OK  ] I 注释：未发现「短按展开/长按折叠」旧注释")
        else:
            # 看它下面 12 行内是不是条件分支
            seg = "\n".join(lines[idx:idx + 12])
            if "candidates.length" in seg or "preedit.length" in seg or "hideKeyboard" in seg:
                fails.append(u"I 注释：KeyboardIndex.ets:%d 注释写「短按展开/长按折叠」，但代码已是条件分支（无候选折叠/有候选展开）⇒ 改注释" % (idx + 1))
            else:
                fails.append(u"I 注释：KeyboardIndex.ets:%d 附近疑似旧注释，需人工确认" % (idx + 1))

    # J 反斜杠
    dy = rd("entry/src/main/resources/rawfile/rime/default.yaml")
    if dy is None:
        fails.append(u"J 反斜杠：default.yaml 读不到")
    else:
        m = re.search(r"punctuator:\s*\n(?:.*\n)*?", dy)
        seg = dy[dy.find("punctuator:"):dy.find("punctuator:") + 2000] if "punctuator:" in dy else u""
        bs = chr(92)
        line = next((l for l in dy.split("\n")
                     if l.strip().startswith(u"'" + bs + u"':")), None)
        if line is None:
            print(u"  [OK  ] J 反斜杠：未找到半角反斜杠映射（不关它事）")
        else:
            val = line.split(":", 1)[1].strip()
            if len(val) >= 2 and val[0] in u"'\"" and val[-1] == val[0]:
                val = val[1:-1]
            if val == u"\\":
                print(u"  [OK  ] J 反斜杠：半角出半角")
            else:
                fails.append(u"J 反斜杠：%s ⇒ 半角反斜杠打成 %r，应为反斜杠本身（D-023／M-140，跑 `python scripts/check_rime_yaml.py`）"
                             % (line.strip(), val))

    if fails:
        print(u"结论：%d 件未过" % len(fails))
        for f in fails:
            print(u"  [FAIL] %s" % f)
        return 1 if a.strict else 0
    print(u"结论：五件全过 ⇒ H-096 可收口")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
