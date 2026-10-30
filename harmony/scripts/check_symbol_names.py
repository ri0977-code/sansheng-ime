#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""H-179 闸门：App 源码里用到的每个 `$r('sys.symbol.X')` 必须真的存在于 SDK 的符号资源表。

为什么要有这道闸门
------------------
2026-10-25 一天之内同一类错犯了三次，全在真机上才被主人抓出来：
  16:1x  用 `return_down_left`(回车) 冒充撤销、`delete_left`(退格) 冒充剪贴板 —— 图形完全不对；
  16:4x  三枚图标全落到 default 分支的 `chevron_down` —— 三枚一模一样，比文字更糟；
  16:5x  工具栏三角用 `Text('▶')` —— U+25B6 命中系统 emoji 字体，渲成蓝底白箭头徽章。
前两次的根因是「凭感觉写符号名」，Symptom 都只在装机后才看得见。

真正的权威表是编译器的资源清单：
  <SDK>/openharmony/ets/build-tools/ets-loader/sysResource.js  →  4043 个 sys.symbol.* 名字
名字写错时 hvigor 的报错很不直观（有时只是运行时空白），所以这道闸门在构建前用**零成本**
的方式把「写了一个不存在的名字」变成红灯。

判据
----
1. 扫描 entry/src/main/ets/**/*.ets 里所有 `$r('sys.symbol.<name>')`，逐个到资源表里查；
   查不到 ⇒ FAIL（阻断）。
2. 资源表本身读不到 ⇒ FAIL（闸门不许静默通过）。
3. 负控（--selftest）：注入一个不存在的名字必须变红；清空资源表必须变红。
   —— 闸门自己也要有牙齿，这是 H-169/H-170 的教训。

用法
----
  python scripts/check_symbol_names.py            # 构建前跑
  python scripts/check_symbol_names.py --selftest # 验闸门自己
"""
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ETS_DIR = os.path.join(ROOT, "entry", "src", "main", "ets")
SDK_DEFAULT = os.environ.get(
    "DEVECO_SDK_DEFAULT", r"D:\DevTools\DevEco\DevEco Studio\sdk\default")
SYS_RESOURCE = os.path.join(
    SDK_DEFAULT, "openharmony", "ets", "build-tools", "ets-loader", "sysResource.js")

SYMBOL_RE = re.compile(r"\$r\(\s*['\"]sys\.symbol\.([A-Za-z0-9_]+)['\"]\s*\)")


def load_symbol_names(path=SYS_RESOURCE):
    """从 sysResource.js 里只取 symbol 节的名字（别的节里也有同名键，混进来会放过错名）。"""
    try:
        s = io.open(path, encoding="utf-8", errors="ignore").read()
    except OSError:
        return None
    i = s.find("\n    symbol:")
    if i < 0:
        return None
    j = s.find("\n    string:", i)
    blk = s[i:(j if j > 0 else len(s))]
    names = set(m.group(1) for m in re.finditer(r"^\s+(\w+):\s*\d+,", blk, re.M))
    return names or None


def collect_usages(ets_dir=ETS_DIR):
    """源码里每个 sys.symbol.X 的用处：{name: [file:line, ...]}"""
    found = {}
    for base, _dirs, files in os.walk(ets_dir):
        for fn in files:
            if not fn.endswith(".ets"):
                continue
            p = os.path.join(base, fn)
            rel = os.path.relpath(p, ROOT)
            with io.open(p, encoding="utf-8", errors="ignore") as f:
                for ln, line in enumerate(f, 1):
                    for m in SYMBOL_RE.finditer(line):
                        found.setdefault(m.group(1), []).append("%s:%d" % (rel, ln))
    return found


def check(names, usages):
    """返回 (fails, warns)。names=None 表示资源表读不到。"""
    fails, warns = [], []
    if not names:
        fails.append("读不到符号资源表：%s（闸门不许静默通过）" % SYS_RESOURCE)
        return fails, warns
    if not usages:
        warns.append("源码里一个 sys.symbol.* 都没扫到——扫描路径写错了？(%s)" % ETS_DIR)
    for name in sorted(usages):
        if name in names:
            continue
        fails.append("符号名不存在：sys.symbol.%s —— %s" % (name, ", ".join(usages[name][:3])))
    return fails, warns


def main():
    selftest = "--selftest" in sys.argv
    names = load_symbol_names()
    usages = collect_usages()

    if selftest:
        bad = 0
        # 负控①：不存在的名字必须被抓住
        f, _ = check(names, {"definitely_not_a_symbol_zzz": ["fake.ets:1"]})
        if not f:
            bad += 1
            print("SELFTEST FAIL: 不存在的符号名没有变红")
        # 负控②：资源表缺失必须变红（而不是当成「全都不存在」之外的情况静默通过）
        f2, _ = check(None, usages)
        if not f2:
            bad += 1
            print("SELFTEST FAIL: 资源表缺失时闸门没变红")
        # 正控：真实用到的名字必须全绿
        f3, _ = check(names, usages)
        if f3:
            bad += 1
            print("SELFTEST FAIL: 真实符号名被误判：%s" % f3[:2])
        print("SELFTEST %s: 负控①（错名变红）／负控②（表缺失变红）／正控（现用名全绿）"
              % ("OK" if bad == 0 else "FAIL %d 例" % bad))
        return 0 if bad == 0 else 1

    fails, warns = check(names, usages)
    for w in warns:
        print("[WARN] %s" % w)
    if fails:
        for f in fails:
            print("[FAIL] %s" % f)
        print("结论：符号名闸门未过（%d 处）。名字请在 sysResource.js 的 symbol 节查实，不要猜。"
              % len(fails))
        return 1
    print("符号名：%d 个全部在资源表中（资源表共 %d 个 sys.symbol.*）"
          % (len(usages), len(names)))
    print("结论：OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
