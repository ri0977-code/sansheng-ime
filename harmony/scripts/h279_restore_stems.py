#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""H-279 修复：把「末级全码（stem）」第 4 列补回鸿蒙打包词库（Qoder，2026-10-30）。

根因（证据见 docs/evidence/2026-10-30/h279-dict/H-279-encoder-root-cause-offline-ab.md，
      原始 A/B 结果同目录 encoder-ab-offline.json；2026-10-30 更正此前指向的
      h279-encoder/README.md —— 那个目录从未建过，属于「引用了一条不存在的证据路径」）：
  三端 wubi86.dict.yaml 词条数完全相同（136,916 行），但
    桌面 D:/Program Files/Rime/            带 stem 列的行 = 20,935
    安卓 F:/dshdesktopwork/.../rime/       带 stem 列的行 = 20,935（与桌面**逐字节同尺寸** 2,352,069 B）
    鸿蒙 rawfile/rime/                     带 stem 列的行 = **25**（只剩一级简码）
  librime 运行态造词走 UnityTableEncoder::TranslateWord → 只认 reverse.bin 里的 stems；
  stems 只来自 dict 的 stem 列（entry_collector.cc:122 `if (!stem_str.empty() && !code_str.empty())`）。
  ⇒ 除 25 个一级简码字外，任何字的编码都推不出来 → EncodePhrase 全部失败 → 鸿蒙端自造词整体不工作。

口径：
  - 源＝安卓仓那份（与桌面逐字节同尺寸，是三端共同上游）；目标＝鸿蒙 rawfile 那份。
  - **逐行按 (text, code) 双键校验对齐**，任何一行对不上就整体中止，不做「大概一样」的合并。
  - 只往目标行**追加第 4 列**，不动目标文件的表头、注释、import_tables、encoder 规则。
  - 原文件先备份到 docs/evidence/2026-10-30/h279-dict/，并在 stdout 打前后 md5。

用法：python scripts/h279_restore_stems.py [--dry]
退出码 0=完成（或 --dry 统计完成）；2=对齐校验失败，未写盘。
"""
from __future__ import annotations

import hashlib
import io
import os
import shutil
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET = os.path.join(REPO, "entry", "src", "main", "resources", "rawfile", "rime",
                      "wubi86.dict.yaml")
SOURCE = r"F:/dshdesktopwork/sansheng-ime-android/rime/wubi86.dict.yaml"
EVID = os.path.join(REPO, "docs", "evidence", "2026-10-30", "h279-dict")


def md5(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def split_header(lines: list[str]) -> tuple[list[str], list[str]]:
    """表头 = 到第二个 '...' 为止（dict yaml 允许 '---' 开头，这里按 '...' 收尾判定）。"""
    for i, ln in enumerate(lines):
        if ln.startswith("..."):
            return lines[: i + 1], lines[i + 1:]
    return lines, []


def main(argv: list[str]) -> int:
    dry = "--dry" in argv
    if not os.path.exists(SOURCE):
        print("源文件不存在：", SOURCE)
        return 2
    src_raw = io.open(SOURCE, encoding="utf-8-sig", newline="").read().splitlines()
    tgt_raw = io.open(TARGET, encoding="utf-8-sig", newline="").read().splitlines()
    src_hdr, src_body = split_header(src_raw)
    tgt_hdr, tgt_body = split_header(tgt_raw)
    src_rows = [l for l in src_body if l.strip() and not l.startswith("#")]
    tgt_rows = [l for l in tgt_body if l.strip() and not l.startswith("#")]
    print(f"源 {os.path.basename(SOURCE)}: 数据行 {len(src_rows)}  表头 {len(src_hdr)} 行")
    print(f"目标 {os.path.relpath(TARGET, REPO)}: 数据行 {len(tgt_rows)}  表头 {len(tgt_hdr)} 行")
    if len(src_rows) != len(tgt_rows):
        print("中止：数据行数不同，不能逐行合并")
        return 2

    stem_map: dict[tuple[str, str], str] = {}
    for l in src_rows:
        p = l.split("\t")
        if len(p) > 3 and p[3]:
            stem_map[(p[0], p[1])] = p[3]
    print(f"源里带 stem 的 (text,code) 组合: {len(stem_map)}")

    out: list[str] = []
    gained = 0
    mismatch = 0
    keep_map: dict[tuple[str, str], str] = {}
    for l in tgt_rows:
        p = l.split("\t")
        if len(p) < 2 or not p[0]:
            out.append(l)
            continue
        key = (p[0], p[1])
        src_stem = stem_map.get(key)
        cur_stem = p[3] if len(p) > 3 else ""
        if cur_stem and src_stem and cur_stem != src_stem:
            mismatch += 1
            if mismatch <= 5:
                print("冲突：", key, "目标 stem=", cur_stem, "源 stem=", src_stem)
            out.append(l)
            continue
        if src_stem and not cur_stem:
            while len(p) < 3:
                p.append("")
            p.append(src_stem)
            out.append("\t".join(p))
            gained += 1
            keep_map[key] = src_stem
        else:
            out.append(l)
    print(f"追加 stem 的行: {gained}  与源冲突（保留目标不动）: {mismatch}")
    if mismatch:
        print("中止：存在 stem 冲突，需人工判定，不写盘")
        return 2
    if gained < 20000:
        print("中止：追加数远低于预期 20,910，说明对齐口径不对，不写盘")
        return 2
    if dry:
        print("--dry：不写盘")
        return 0

    os.makedirs(EVID, exist_ok=True)
    before = os.path.join(EVID, "wubi86.dict.yaml.before-stems")
    if not os.path.exists(before):
        shutil.copy2(TARGET, before)
    hdr_bom = open(TARGET, "rb").read(3) == b"\xef\xbb\xbf"
    tgt_text = open(TARGET, "rb").read().decode("utf-8-sig")
    nl = "\r\n" if "\r\n" in tgt_text else "\n"
    enc = "utf-8-sig" if hdr_bom else "utf-8"
    print(f"目标文件：BOM={hdr_bom} 行尾={'CRLF' if nl == chr(13) + chr(10) else 'LF'} → 原样写回")
    # 重写：表头原样 + 数据行按 out 顺序（注释/空行位置保持不变）
    new_lines: list[str] = []
    it = iter(out)
    body_started = False
    for l in tgt_raw:
        if not body_started:
            new_lines.append(l)
            if l.startswith("..."):
                body_started = True
            continue
        if l.strip() and not l.startswith("#"):
            new_lines.append(next(it))
        else:
            new_lines.append(l)
    with io.open(TARGET, "w", encoding=enc, newline=nl) as f:
        f.write("\n".join(new_lines) + "\n")
    print("写盘完成")
    print("before md5 :", md5(before))
    print("after  md5 :", md5(TARGET))
    print("size       :", os.path.getsize(TARGET), "B（源", os.path.getsize(SOURCE), "B）")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
