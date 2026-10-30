#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""H-266 打包卫生守卫（Qoder，2026-10-29 14:3x）

为什么写（H-250/H-238 口径：第二次犯同一件事 ⇒ 散文不算修好，必须有拦截）：
我为了改 `en_word_bucket.txt`，在 **rawfile 目录原地**留了三个 `.bak-qoder-20261029-140x`
（每个 1,562,235 B）和一个 1,115,199 B 的 `en_word.dict.yaml.bak-v23-full`，外加一支
18,006 B 的滤镜旧版。hvigor 把 `resources/rawfile/` 整目录打包 ⇒ **2026-10-29 14:09 那个
signed HAP（39,923,890 B）里真带着 5 个备份文件、2.7 MB 死字节**（当场从包里数出来的，
见下「取证」）。这类字节不只胖，还会「假绿」：包里同时有两版滤镜，出问题时按哪版判断都没法肯定。

取证（本机实际跑过，不是推理）：
    zipfile(entry/build/default/outputs/default/entry-default-signed.hap) 的 .bak 条目
      resources/rawfile/rime/en_word.dict.yaml.bak-v23-full            1,115,199 B
      resources/rawfile/rime/lua/enWord_Filter.lua.bak-20261029-1315-before-1b   18,006 B
      resources/rawfile/rime/lua/en_word_bucket.txt.bak-qoder-20261029-1403   1,562,235 B
      resources/rawfile/rime/lua/en_word_bucket.txt.bak-qoder-20261029-1404   1,562,235 B
      resources/rawfile/rime/lua/en_word_bucket.txt.bak-qoder-20261029-1407   1,562,235 B

规矩（不是建议，是 rc=1）：
  ① `entry/src/main/resources/rawfile/**` 里不许出现备份/临时文件（正则见 BANNED）。
  ② 已构建的 HAP（signed／unsigned，取 mtime 最新那批）里也不许出现 ⇒ 直查产物，不只看源码树
     （H-245 口径：「zip 没解开就别说发出去了什么」）。
  ③ 备份一律放 `_probe/rawfile-backups-<ymd>/`（已在 .gitignore 侧、且 hvigor 看不见）。

用法：
    python scripts/h266_package_hygiene_check.py            # 真树 + 最新产物
    python scripts/h266_package_hygiene_check.py --selftest  # 正控＋负控（自己造坏样本）
退出码：0＝干净；1＝有违规（拦构建/拦交付用）。
"""
from __future__ import annotations

import os
import re
import sys
import shutil
import zipfile
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

RAWFILE_DIR = os.path.join("entry", "src", "main", "resources", "rawfile")
HAP_DIRS = [
    os.path.join("entry", "build", "default", "outputs", "default"),
]

# 备份/临时/编辑器的残留特征。注意 `\.1b` 之类不在内：只拦「一看就不是发出去的东西」。
BANNED = re.compile(
    r"(\.bak(\b|[-_.])|\.orig\b|\.rej\b|\.tmp\b|\.sav\b|\.save\b|\.old\b|~$|^\s*$"
    r"|\.copy\b|-copy\b|副本|备份|\.swp\b|\.swo\b)",
    re.I,
)


def scan_tree(rawfile_root):
    """源码树里的 rawfile 目录：返回违规相对路径列表。"""
    hits = []
    if not os.path.isdir(rawfile_root):
        return hits
    for dirpath, dirnames, filenames in os.walk(rawfile_root):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for fn in filenames:
            if BANNED.search(fn):
                full = os.path.join(dirpath, fn)
                hits.append(os.path.relpath(full, os.path.dirname(rawfile_root)).replace("\\", "/"))
    return hits


def newest_haps(root):
    out = []
    for d in HAP_DIRS:
        dd = os.path.join(root, d)
        if not os.path.isdir(dd):
            continue
        for fn in os.listdir(dd):
            if fn.endswith(".hap"):
                p = os.path.join(dd, fn)
                out.append((os.path.getmtime(p), p))
    out.sort(reverse=True)
    if not out:
        return []
    newest = out[0][0]
    # 同一次构建会同时留 signed／unsigned，按 mtime 分钟级一起收
    return [p for ts, p in out if ts >= newest - 3600]


def scan_hap(hap_path):
    """产物里读条目名：返回 (违规条目, 总条目数, 违规字节数)。"""
    hits, total, dead = [], 0, 0
    try:
        with zipfile.ZipFile(hap_path) as z:
            for info in z.infolist():
                if info.is_dir():
                    continue
                total += 1
                base = info.filename.rsplit("/", 1)[-1]
                if BANNED.search(base):
                    hits.append((info.filename, info.file_size))
                    dead += info.file_size
    except Exception as exc:  # 读不动就是「没验过」，不许当通过
        raise SystemExit("读 HAP 失败（不是通过）：%s -> %r" % (hap_path, exc))
    return hits, total, dead


def newest_rawfile_mtime(rawfile_root):
    """树里最新 rawfile 文件时间。产物比它早 ⇒ 那是「改之前构建的旧包」，只报不拦
    （H-259 口径：报警不该被当成回归；但下一次构建必须干净）。"""
    newest = 0.0
    if not os.path.isdir(rawfile_root):
        return 0.0
    for dirpath, dirnames, filenames in os.walk(rawfile_root):
        for fn in filenames:
            try:
                newest = max(newest, os.path.getmtime(os.path.join(dirpath, fn)))
            except OSError:
                pass
    return newest


def run(root=ROOT, quiet=False):
    rawfile = os.path.join(root, RAWFILE_DIR)
    tree_hits = scan_tree(rawfile)
    fail = False

    if tree_hits:
        fail = True
        print("FAIL 源码树 rawfile 里有备份/临时文件 %d 个（hvigor 会把它们整包塞进 HAP）：" % len(tree_hits))
        for h in tree_hits:
            print("      %s" % h)
        print("      处理：移到 _probe/rawfile-backups-<ymd>/（H-266），不要就地删——先留证。")
    elif not quiet:
        print("OK   源码树 rawfile 干净（无 .bak/.orig/副本 等残留）")

    tree_newest = newest_rawfile_mtime(rawfile)
    haps = newest_haps(root)
    if not haps:
        if not quiet:
            print("SKIP 没有已构建的 HAP 可查（构建后再跑一次本守卫）")
    for hp in haps:
        try:
            hits, total, dead = scan_hap(hp)
        except SystemExit as exc:
            print(str(exc))
            fail = True
            continue
        rel = os.path.relpath(hp, root).replace("\\", "/")
        stale = os.path.getmtime(hp) < tree_newest
        if hits and stale:
            print("WARN 旧产物带死字节（构建时间早于树里最新 rawfile 改动，属改前留下的包，已由 H-266 记账）："
                  "%s —— %d 个备份条目 / %s B；重新构建后必须为 0，否则转 FAIL"
                  % (rel, len(hits), "{:,}".format(dead)))
        elif hits:
            fail = True
            print("FAIL 产物里有死字节：%s（%d 条目，其中 %d 个是备份，共 %s B）"
                  % (rel, total, len(hits), "{:,}".format(dead)))
            for name, size in hits:
                print("      %s  %s B" % (name, "{:,}".format(size)))
        elif not quiet:
            print("OK   产物干净：%s（%s 条目%s）"
                  % (rel, "{:,}".format(total), "，早于最新改动＝旧包" if stale else ""))

    print("结论：%s" % ("打包卫生不通过（rc=1）" if fail else "源码树与产物都没有备份残留"))
    return 1 if fail else 0


# ------------------------------------------------------------------ 自测（正控＋负控）

def selftest():
    ok = True

    def check(name, got, want):
        nonlocal ok
        good = got == want
        print("%s %-46s got=%r want=%r" % ("PASS" if good else "FAIL", name, got, want))
        ok = ok and good

    tmp = tempfile.mkdtemp(prefix="h266-selftest-")
    try:
        rf = os.path.join(tmp, RAWFILE_DIR)
        os.makedirs(os.path.join(rf, "lua"))

        # 正控 1：干净目录 ⇒ 0 违规
        with open(os.path.join(rf, "wubi_pinyin.custom.yaml"), "w") as f:
            f.write("patch: {}\n")
        with open(os.path.join(rf, "lua", "enWord_Filter.lua"), "w") as f:
            f.write("-- ok\n")
        check("正控:干净树", scan_tree(rf), [])

        # 负控 1：真树里出现过的形状（我这次犯的）
        for bad in ("en_word_bucket.txt.bak-qoder-20261029-1403",
                    "en_word.dict.yaml.bak-v23-full",
                    "lua/enWord_Filter.lua.bak-20261029-1315-before-1b"):
            p = os.path.join(rf, bad.replace("/", os.sep))
            with open(p, "w") as f:
                f.write("x")
        got = sorted(scan_tree(rf))
        check("负控:三种 .bak 形状全被抓到（3 个）", len(got), 3)
        check("负控:子目录里的也抓到", any("enWord_Filter.lua.bak" in g for g in got), True)

        # 负控 2：产物里藏一个备份 ⇒ 从 zip 条目名抓到
        hap = os.path.join(tmp, "entry", "build", "default", "outputs", "default")
        os.makedirs(hap, exist_ok=True)
        hp = os.path.join(hap, "entry-default-signed.hap")
        with zipfile.ZipFile(hp, "w") as z:
            z.writestr("resources/rawfile/rime/lua/en_word_bucket.txt", "a\tapp\t3\t应用\n")
            z.writestr("resources/rawfile/rime/lua/en_word_bucket.txt.bak-x", "old" * 100)
            z.writestr("module.json", "{}")
        hits, total, dead = scan_hap(hp)
        check("负控:产物里的备份被抓到（1 个）", len(hits), 1)
        check("负控:死字节按未压缩算", dead > 0, True)
        check("正控:产物里正常 rawfile 不误伤", total, 3)

        # 负控 3：`~` 结尾（编辑器 swap/backup）也拦
        with open(os.path.join(rf, "notes.md~"), "w") as f:
            f.write("x")
        check("负控:尾巴波浪号也被抓到", any(g.endswith("notes.md~") for g in scan_tree(rf)), True)

        # 清理后回到干净 ⇒ 守卫会放行（证明不是恒红，H-259 那类模型病）
        for bad in ("en_word_bucket.txt.bak-qoder-20261029-1403",
                    "en_word.dict.yaml.bak-v23-full", "notes.md~"):
            os.remove(os.path.join(rf, bad))
        os.remove(os.path.join(rf, "lua", "enWord_Filter.lua.bak-20261029-1315-before-1b"))
        check("正控:移干净后放行", scan_tree(rf), [])

        # 严重度／退出码路径（H-250 口径：WARN 不许拦，FAIL 必须拦）
        clean_hap_dir = os.path.dirname(hp)
        os.remove(hp)
        fresh = os.path.join(clean_hap_dir, "entry-default-unsigned.hap")
        with zipfile.ZipFile(fresh, "w") as z:
            z.writestr("resources/rawfile/rime/lua/en_word_bucket.txt", "a\tapp\t3\t应用\n")
            z.writestr("resources/rawfile/rime/lua/en_word_bucket.txt.bak-now", "old" * 100)
        # 树比包旧 ⇒ 这个包是「改之后构建的」，必须 rc=1
        os.utime(os.path.join(rf, "wubi_pinyin.custom.yaml"), (1000, 1000))
        check("退出码:新包带备份 ⇒ rc=1（拦构建）", run(tmp, quiet=True), 1)
        # 包比树旧 ⇒ 旧产物，只 WARN，rc=0（不误伤改前留下的包）
        os.remove(fresh)
        old_hap = os.path.join(clean_hap_dir, "entry-default-signed.hap")
        with zipfile.ZipFile(old_hap, "w") as z:
            z.writestr("resources/rawfile/rime/lua/en_word_bucket.txt", "a\tapp\t3\t应用\n")
            z.writestr("resources/rawfile/rime/lua/en_word_bucket.txt.bak-then", "old" * 100)
        os.utime(old_hap, (1000, 1000))
        check("退出码:旧包带备份 ⇒ rc=0（只 WARN）", run(tmp, quiet=True), 0)
        os.remove(old_hap)
        check("退出码:干净树+无产物 ⇒ rc=0", run(tmp, quiet=True), 0)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("自测结论：%s" % ("全部通过" if ok else "有断言失败"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else run())
