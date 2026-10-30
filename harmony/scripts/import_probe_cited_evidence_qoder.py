#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""H-282 (Qoder 2026-10-30 07:5x): make the `_probe/` evidence the ledgers cite reachable in git.

D-034 keeps the 26.8 MB `_probe/` scratch directory out of the repository, but 133 ledger
references across 16 markdown files point into it - on GitHub those would be dead links, and this
repo's rule is that every claim must be checkable.  Instead of rewriting 133 rows (which would
also rewrite CodeArts's rows), this script COPIES just the cited files into
`docs/evidence/_probe-cited/`, mirrors their relative sub-path, and writes a manifest.

Copies only - `_probe/` itself is untouched (AGENTS.md rule 3: never delete prior work).
Each copied file is byte-compared against its source after the write, and the manifest records
size plus sha256 so a reader can prove the packaged copy is the same file.

Usage:
    python scripts/import_probe_cited_evidence_qoder.py           # copy + manifest
    python scripts/import_probe_cited_evidence_qoder.py --check   # verify only, no writes
Exit 0 = every cited file that exists on disk is (or was) copied and byte-identical;
exit 1 = a copy is missing or differs.
"""
import hashlib
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEST_REL = "docs/evidence/_probe-cited"
CITE_RE = re.compile(r"_probe/[A-Za-z0-9_][^\s`|)\u3010\u3011\"'，。;:]*")
SKIP_NAME_PARTS = ("__pycache__", ".pyc")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def cited_paths():
    """Distinct `_probe/...` file references found in docs/**/*.md (tmp drafts excluded)."""
    found = {}
    for dirpath, dirnames, filenames in os.walk(os.path.join(REPO, "docs")):
        dirnames[:] = [d for d in dirnames if d != "tmp"]
        for fn in filenames:
            if not fn.endswith(".md"):
                continue
            text = open(os.path.join(dirpath, fn), encoding="utf-8", errors="ignore").read()
            for m in CITE_RE.finditer(text):
                raw = m.group().rstrip(".,;:")
                # Drop line-number suffixes (`_probe/x.txt:10402`) and CJK-run damage markers.
                if ":" in raw.split("/")[-1]:
                    raw = raw.split(":")[0]
                if any(ch in raw for ch in ("\u2026", "\ufffd")) or any(ord(c) > 0x2fff for c in raw):
                    continue
                if any(part in raw for part in SKIP_NAME_PARTS):
                    continue
                found.setdefault(raw, set()).add(os.path.relpath(
                    os.path.join(dirpath, fn), REPO).replace("\\", "/"))
    return found


def main():
    check = "--check" in sys.argv
    cited = cited_paths()
    os.makedirs(os.path.join(REPO, DEST_REL), exist_ok=True)
    rows = []
    missing_src = []
    bad = []
    for rel in sorted(cited):
        src = os.path.join(REPO, rel.replace("/", os.sep))
        if not os.path.isfile(src):
            missing_src.append((rel, sorted(cited[rel])))
            continue
        dst = os.path.join(REPO, DEST_REL, rel[len("_probe/"):].replace("/", os.sep))
        if not check:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(src, "rb") as a, open(dst, "wb") as b:
                b.write(a.read())
        if not os.path.isfile(dst):
            bad.append((rel, "copy missing"))
            continue
        if os.path.getsize(src) != os.path.getsize(dst):
            bad.append((rel, "size differs: src=%d dst=%d" % (os.path.getsize(src), os.path.getsize(dst))))
            continue
        hs, hd = sha256(src), sha256(dst)
        if hs != hd:
            bad.append((rel, "sha256 differs"))
            continue
        rows.append("| `%s` | %d B | `%s` | %s |" % (
            dst.replace(os.sep, "/")[len(REPO) + 1:], os.path.getsize(dst), hs[:16],
            ", ".join("`%s`" % p for p in sorted(cited[rel]))))
    if not check:
        manifest = [os.path.join(REPO, DEST_REL, "MANIFEST.md")]
        with open(manifest[0], "w", encoding="utf-8", newline="\n") as fh:
            fh.write("# `_probe/` 里被台账引用的证据副本\n\n")
            fh.write("整理：Qoder　登记：2026-10-30 07:5x　工单：H-282　口径：D-034\n\n")
            fh.write("`_probe/` 是 26.8 MB 的调研草稿目录，按 D-034 不入 git；但 docs/ 里有 133 处引用"
                     "指向它，仓库推到 GitHub 后那些就是死链。本目录把这些**被点名引用**的原件逐字节复制过来"
                     "（不是移动，`_probe/` 原样留在本地），并把每条被哪几行台账引用一并列出，"
                     "所以旧写法 `_probe/xxx` 在这里能按文件名找到对应副本。\n\n")
            fh.write("生成命令：`python scripts/import_probe_cited_evidence_qoder.py`"
                     "（`--check` 只核对不写盘）。副本与源文件 sha256 逐条相等，下表哈希取前 16 位。\n\n")
            fh.write("| 副本路径 | 字节 | sha256(前16) | 引用它的台账文件 |\n|---|---|---|---|\n")
            for r in rows:
                fh.write(r + "\n")
            if missing_src:
                fh.write("\n## 台账里提到但磁盘上没有的路径（写法本身是省略/坏行，不是丢文件）\n\n")
                for rel, srcs in sorted(missing_src):
                    fh.write("- `%s`（出现于 %s）\n" % (rel, ", ".join("`%s`" % s for s in srcs)))
        print("manifest: %s (%d copied, %d cited-but-absent)"
              % (manifest[0].replace(os.sep, "/"), len(rows), len(missing_src)))
    print("copied/verified: %d ; byte-mismatch: %d" % (len(rows), len(bad)))
    for rel, why in bad:
        print("  MISMATCH %s: %s" % (rel, why))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
