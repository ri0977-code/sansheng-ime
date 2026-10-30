#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""eol_audit.py —— 检查「当前工作区的字节」与「全新检出会得到什么字节」是否同源。

为什么需要它：本机 core.autocrlf=true。工作区里有些文本文件是脚本用 Windows 文本模式
写出来的（\\n 变成 \\r\\n），而索引里的 blob 是 LF ⇒ `git status` 显示干净，
`git ls-files --eol` 也要读对列号才看得出来。结果就是：**同一份 commit，
在我这台机器上构建出的 HAP，和一次全新检出后构建出的 HAP，字节不一样**。
rawfile 在 HAP 里是 ZIP_STORED（不压缩），所以每多一个 CR 就多一个字节，逐字节比对当场失效。

判据不用克隆仓库：对每个跟踪文件比较「工作区字节」与「索引 blob 字节」。
  相等                      -> 同源
  工作区 == blob 的 LF->CRLF -> eol-drift（全新检出会是 LF，本机是 CRLF，差值 = CR 数）
  其他不等                  -> 内容差异（可能只是未提交的改动，单独计数，不谎报成 eol）

用法：
  python scripts/eol_audit.py                 # 全仓汇总，按「是否进包」分组
  python scripts/eol_audit.py --packaged      # 只看进包的 rawfile
  python scripts/eol_audit.py --strict        # 进包文件里出现 eol-drift 就 exit 1
退出码：0 正常；1 = --strict 且进包文件存在 eol-drift。
"""
import argparse
import subprocess
import sys
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CR = b"\r\n"


def tracked_files():
    out = subprocess.run(["git", "-C", REPO, "ls-files", "-z"],
                         capture_output=True).stdout
    return [p.decode("utf-8", "surrogateescape") for p in out.split(b"\0") if p]


def blob_of(path):
    r = subprocess.run(["git", "-C", REPO, "cat-file", "blob", "HEAD:" + path],
                       capture_output=True)
    return r.stdout if r.returncode == 0 else None


def classify(path):
    if path.startswith("entry/src/main/resources/rawfile/"):
        return "rawfile(进包)"
    if path.startswith("LICENSES/"):
        return "LICENSES(生成器输入)"
    if path.startswith("docs/release/legal/"):
        return "docs/release/legal(对外文本源)"
    if path == "NOTICE":
        return "NOTICE(对外文本源)"
    if path.startswith("scripts/"):
        return "scripts(闸门工具)"
    if path.startswith("entry/src/main/ets/"):
        return "ets(应用代码)"
    return "其他"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--packaged", action="store_true", help="只列进包的 rawfile")
    ap.add_argument("--strict", action="store_true",
                    help="进包文件存在 eol-drift 时 exit 1")
    a = ap.parse_args()

    drift, other = {}, {}
    for p in tracked_files():
        fp = os.path.join(REPO, p.replace("/", os.sep))
        if not os.path.isfile(fp):
            continue
        wt = open(fp, "rb").read()
        if wt == b"":
            continue
        bl = blob_of(p)
        if bl is None or wt == bl:
            continue
        if wt == bl.replace(b"\n", CR):
            drift[p] = bl.count(b"\n")
        else:
            other[p] = len(wt) - (len(bl) if bl is not None else 0)

    groups = {}
    for p, cr in drift.items():
        groups.setdefault(classify(p), []).append((p, cr))
    for g in groups:
        groups[g].sort(key=lambda x: -x[1])

    print("工作区 vs 全新检出：eol-drift 文件 %d 个，多出的 CR 字节合计 %d"
          % (len(drift), sum(drift.values())))
    for g in sorted(groups, key=lambda x: -sum(c for _, c in groups[x])):
        print("\n[%s] %d 个，%d B" % (g, len(groups[g]), sum(c for _, c in groups[g])))
        if a.packaged and not g.startswith("rawfile"):
            continue
        for p, c in groups[g][:25]:
            print("   CRLF=%-7d %s" % (c, p))
        if len(groups[g]) > 25:
            print("   ... 其余 %d 个省略" % (len(groups[g]) - 25))
    print("\n非 eol 的内容差异（未提交改动等，不计入漂移）：%d 个" % len(other))
    for p in sorted(other)[:12]:
        print("   %+9d B  %s" % (other[p], p))
    if len(other) > 12:
        print("   ... 其余 %d 个省略" % (len(other) - 12))

    pkg_bad = sum(c for p, c in drift.items() if p.startswith("entry/src/main/resources/rawfile/"))
    print("\n结论：进包 rawfile 的 eol 漂移 = %d B；一次全新检出构建出的 HAP 会比现在小 %d B"
          % (pkg_bad, pkg_bad))
    if a.strict and pkg_bad:
        print("--strict：进包字节与全新检出不同源，判失败")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
