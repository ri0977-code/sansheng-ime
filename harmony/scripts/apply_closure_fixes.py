#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""H-096 收口五件的现成补丁（给 CodeArts 跑；Qoder 只写脚本、不动他的文件）

为什么有它：14:4x 我把收口清单做成 `scripts/check_closure_items.py`，它能量出「哪件没过、
差多少」，但不告诉他「怎么改」。他四轮没动，很可能就是卡在「改哪儿、改成什么」。
本脚本把五件全部变成**一处一改、改完可验**的补丁，默认 dry-run，`--apply` 才落盘。

分工边界：`entry/src/**`、`AppScope/**` 归 CodeArts。本脚本**不自动跑**，
由他在自己会话里执行；Qoder 只负责把补丁写对、并把「改完怎么验」写清。

五件（M-134／M-140 派单）：
  F 探针页   main_pages.json 删 pages/LandscapeProbe、pages/M3Probe 两行
  G 图标     用 scripts/make_store_icon.py 的 512/1024 件覆盖 app_icon.png 与 foreground.png
  H metadata module.json5 的 ohos.entry.mainability 删掉（并留一行注释说明为什么删）
  I 注释     KeyboardIndex.ets:1005 的旧注释改成与代码一致
  J 反斜杠   default.yaml 的 '\\': '、' 改成 '\\': '\\'

用法（CodeArts 侧）：
  python scripts/apply_closure_fixes.py            #  dry-run，打印每处 old/new
  python scripts/apply_closure_fixes.py --apply    #  落盘（写前自动备份到 .bak-<时间戳>）
  python scripts/check_closure_items.py            #  改完验一遍（应全 OK）
"""
import argparse
import datetime
import io
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BS = chr(92)

MAIN_PAGES = "entry/src/main/resources/base/profile/main_pages.json"
MODULE_JSON = "entry/src/main/module.json5"
KEYBOARD = "entry/src/main/ets/pages/KeyboardIndex.ets"
DEFAULT_YAML = "entry/src/main/resources/rawfile/rime/default.yaml"
APP_ICON = "entry/src/main/resources/base/media/app_icon.png"
FOREGROUND = "AppScope/resources/base/media/foreground.png"
ICON_512 = "docs/release/store/icon/gen-appicon-512.png"
ICON_1024 = "docs/release/store/icon/gen-appicon-1024.png"


def rd(rel):
    p = os.path.join(ROOT, rel.replace("/", os.sep))
    return io.open(p, encoding="utf-8").read()


def wr(rel, s, backup=True):
    p = os.path.join(ROOT, rel.replace("/", os.sep))
    if backup and os.path.exists(p):
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        shutil.copy2(p, p + ".bak-" + stamp)
    io.open(p, "w", encoding="utf-8", newline="\n").write(s)


def fix_probe_pages():
    s = rd(MAIN_PAGES)
    old = u'    "pages/LandscapeProbe",\n    "pages/M3Probe",\n'
    if old not in s:
        # 容忍顺序/空白差异
        m = re.search(r'\{\s*"src":\s*\[(.*?)\]\s*\}', s, re.S)
        return None, "main_pages.json 里没找到连续两行探针页注册（可能已摘或格式不同）", s
    new = u""
    return old, u"删掉两行探针页注册（H-098：内容闸门第 ⑩ 项在 .app 上会阻断）", s.replace(old, new, 1)


def fix_metadata():
    s = rd(MODULE_JSON)
    old = (u'        "metadata": [\n'
           u'          {\n'
           u'            "name": "ohos.entry.mainability",\n'
           u'            "value": "true"\n'
           u'          }\n'
           u'        ]\n')
    if old not in s:
        return None, "module.json5 里没找到 ohos.entry.mainability 那段（可能已退）", s
    new = (u'        // 14:4x 退掉 ohos.entry.mainability（M-143 收口件 H）：\n'
           u'        // 那是 11:06 追 isLauncherApp 时加的，DevEco/SDK 全目录 0 命中、基本确定不生效；\n'
           u'        // 现在 skills 已是官方文档要求的 entity.system.home + ohos.want.action.home，入口条件满足。\n')
    return old, u"删掉 metadata 段并留一行注释说明为什么删", s.replace(old, new, 1)


def fix_comment():
    s = rd(KEYBOARD)
    old = u"        // ▼/▲ 展开按钮（36vp 宽）——短按展开/收起候选网格，长按折叠键盘"
    if old not in s:
        return None, "KeyboardIndex.ets 里没找到 1005 行那条旧注释", s
    new = (u"        // ▼/▲ 智能键（36vp 宽，主人 10-23 定的「一个三角两个功能」）：\n"
           u"        //   有候选（打字中）→ 单击展开/收起候选网格；无候选（空闲）→ 单击收起键盘；长按恒为收起键盘。")
    return old, u"把「短按展开/长按折叠」改成与代码一致的三态描述", s.replace(old, new, 1)


def fix_backslash():
    s = rd(DEFAULT_YAML)
    old = u"    '" + BS + "': '" + u"\u3001" + u"'"
    if old not in s:
        return None, "default.yaml 里没找到半角反斜杠映射（可能已改）", s
    new = u"    '" + BS + "': '" + BS + u"'"
    return old, u"半角反斜杠改回出半角反斜杠（D-023：打不出反斜杠就没法输路径/命令）", s.replace(old, new, 1)


def fix_icons():
    """图标两件：直接复制，不用改文本。"""
    out = []
    for src, dst in ((ICON_512, APP_ICON), (ICON_1024, FOREGROUND)):
        sp = os.path.join(ROOT, src.replace("/", os.sep))
        dp = os.path.join(ROOT, dst.replace("/", os.sep))
        if not os.path.exists(sp):
            out.append((src, None, "母版不存在：先跑 python scripts/make_store_icon.py --write", dst))
            continue
        out.append((src, sp, u"用含环黑底金母版覆盖（H-147：内容占比 0.617→0.77、环厚 0.0127→0.026）", dp))
    return out


def _after(old, new_s):
    """dry-run 时把「改后那一小段」打出来（最多 120 字），别打占位符。

    做法：在 new_s 里定位 old 的起点，从那儿往后取一段。old 不在 new_s 里
    （被整段删掉／替换）就取 new_s 开头，并注明。
    """
    i = new_s.find(old[:40])
    if i < 0:
        return u"（该段已不在新内容里，即被删除/替换；新内容开头：）" \
               + new_s[:100].replace(u"\n", u" \u23ce ")
    j = i + len(old)
    return new_s[j:j + 120].replace(u"\n", u" \u23ce ")


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args(argv)

    print(u"== H-096 收口补丁（%s） ==" % (u"APPLY" if a.apply else u"DRY-RUN"))
    print(u"分工提醒：entry/src、AppScope 归 CodeArts；本脚本由他在自己会话里跑。\n")

    todo = []
    for label, fn in ((u"F 探针页（H-098）", fix_probe_pages),
                      (u"H metadata", fix_metadata),
                      (u"I 注释", fix_comment),
                      (u"J 反斜杠（D-023）", fix_backslash)):
        old, note, new_s = fn()
        if old is None:
            print(u"  [skip] %-18s %s" % (label, note))
            continue
        rel = {u"F 探针页（H-098）": MAIN_PAGES, u"H metadata": MODULE_JSON,
               u"I 注释": KEYBOARD, u"J 反斜杠（D-023）": DEFAULT_YAML}[label]
        print(u"  [todo] %-18s %s" % (label, note))
        print(u"        文件 %s" % rel)
        print(u"        - %s" % old.replace(u"\n", u" ⏎ ")[:120])
        print(u"        + %s" % _after(old, new_s))
        todo.append((rel, new_s))

    for src, sp, note, dp in fix_icons():
        if sp is None:
            print(u"  [skip] 图标 %-12s %s" % (os.path.basename(dp), note))
            continue
        print(u"  [todo] G 图标            %s" % note)
        print(u"        %s -> %s" % (src, dp))
        todo.append((dp, u"__COPY__:" + sp))

    if not a.apply:
        print(u"\ndry-run 结束：加 --apply 才落盘（会自动备份 .bak-<时间戳>）")
        return 0
    if not todo:
        print(u"\n没有待应用的补丁 ⇒ 直接跑 scripts/check_closure_items.py 验收")
        return 0
    for rel, payload in todo:
        if payload.startswith(u"__COPY__:"):
            sp = payload[len(u"__COPY__:"):]
            wr(rel, u"", backup=True)
            shutil.copy2(sp, os.path.join(ROOT, rel.replace("/", os.sep)))
            print(u"  已覆盖 %s" % rel)
        else:
            wr(rel, payload)
            print(u"  已写   %s" % rel)
    print(u"\n全部落盘。现在跑：python scripts/check_closure_items.py")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
