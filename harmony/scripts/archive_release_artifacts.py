#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把发布产物归档到「构建树之外」—— 修 H-144 的真教训（Qoder 归属，M6 ②）

为什么有这个脚本（H-144，2026-10-23）
--------------------------------------
2026-10-22 13:25 那份 release `.app`（11,791,326 B）与 release-signed HAP 在 00:08
随一次 `hvigorw clean` 清空 `entry/build` 一起没了，**机器上没有第三处副本**。
当时以为「闸门会把不合格件改名 `.rejected-<时间戳>` 就安全了」——错：改名后的文件
还住在同一棵树里，**整棵树被删时一起没**。

教训一句话：**就地改名 ≠ 保留；归档必须是「树外 + 只读 + 带清单」**。

本脚本做三件事（不碰 sign/** 密钥内容，只搬产物）：
  1. 把 `entry/build/**/outputs/**` 里的 `.app`／`*.hap`／`*.sha256` 复制到
     `<archive>/<YYYY-MM-DD>/<HHMMSS>/`，文件名保留原样；
  2. 每个文件算 sha256 + 字节数，写 `MANIFEST.json`（含 git HEAD、时间、来源路径）；
  3. 归档目录设只读（Windows 用 attrib +R），防误删；**不删任何源文件**。

默认归档根：`F:/qoderwork/_release-archive`（构建树之外、与仓库同一块盘但不同目录）。
**真正的异地备份（U 盘/另一台机器）仍要主人做** —— 本脚本只保证「clean 删不掉」。

用法：
  python scripts/archive_release_artifacts.py            # 列出将归档什么（dry run）
  python scripts/archive_release_artifacts.py --write    # 真的复制并写清单
  python scripts/archive_release_artifacts.py --root E:/somewhere --write
"""
import argparse
import datetime
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 与 release_build.ps1 的 $ArchiveDir 同一个位置（ProjectRoot 的上一级），
# 不另起炉灶 —— H-144 的教训之一就是「两套归档约定，谁也没真正执行」。
DEFAULT_ARCHIVE = "F:/qoderwork/sansheng-release-artifacts"
PATTERNS = (".app", ".hap", ".sha256")


def find_artifacts():
    """扫 entry/build 下的产物；只认扩展名，不递归进 .git。"""
    out = []
    base = os.path.join(ROOT, "entry", "build")
    if not os.path.isdir(base):
        return out
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in (".git", "node_modules")]
        for fn in filenames:
            if fn.endswith(PATTERNS):
                p = os.path.join(dirpath, fn)
                out.append(p)
    return sorted(out)


def sha256(p):
    h = hashlib.sha256()
    with io.open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_head():
    try:
        return subprocess.run(["git", "-C", ROOT, "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True).stdout.strip() or "?"
    except Exception:
        return "?"


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=DEFAULT_ARCHIVE)
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args(argv)

    arts = find_artifacts()
    if not arts:
        print("entry/build 下没有 .app/.hap/.sha256 产物（先构建）")
        return 1

    now = datetime.datetime.now()
    dest = os.path.join(a.root, now.strftime("%Y-%m-%d"), now.strftime("%H%M%S"))
    print("归档根: %s" % a.root)
    print("目标  : %s" % dest)
    print("产物 %d 个：" % len(arts))
    rows = []
    for p in arts:
        rel = os.path.relpath(p, ROOT).replace("\\", "/")
        size = os.path.getsize(p)
        digest = sha256(p)
        print("  %-64s %10d B  %s" % (rel, size, digest[:16]))
        rows.append({"source": rel, "name": os.path.basename(p), "bytes": size, "sha256": digest})

    if not a.write:
        print("\ndry run：加 --write 才复制并写清单")
        return 0

    os.makedirs(dest, exist_ok=True)
    for r in rows:
        src = os.path.join(ROOT, r["source"].replace("/", os.sep))
        dst = os.path.join(dest, r["name"])
        shutil.copy2(src, dst)
        # 只读，防误删
        if os.name == "nt":
            subprocess.run(["attrib", "+R", dst], capture_output=True)
        else:
            os.chmod(dst, 0o444)
    manifest = {
        "archived_at": now.isoformat(timespec="seconds"),
        "git_head": git_head(),
        "repo": ROOT.replace("\\", "/"),
        "files": rows,
        "note": "H-144: 归档在构建树之外，clean 删不到；异地备份仍需主人做",
    }
    mp = os.path.join(dest, "MANIFEST.json")
    io.open(mp, "w", encoding="utf-8", newline="\n").write(
        json.dumps(manifest, ensure_ascii=False, indent=2))
    if os.name == "nt":
        subprocess.run(["attrib", "+R", mp], capture_output=True)
    print("\n已归档 %d 个文件 → %s" % (len(rows), dest))
    print("清单: %s" % mp)
    print("提醒：这只防 clean；异地备份（U 盘/另一台机）仍要主人做")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
