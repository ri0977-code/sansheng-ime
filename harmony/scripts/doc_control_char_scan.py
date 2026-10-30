#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Scan repo text files for control characters and verify the artifact paths the ledgers name.

Why this exists (H-280/H-281, 2026-10-30 07:2x, Qoder):
    Ledger rows were written through a bash heredoc containing single-quoted Python strings with
    Windows paths.  Python turned backslash-a / backslash-202 / backslash-070 into escape sequences,
    so the committed text carried U+0007 / U+0082 and dropped backslashes - the archive paths could
    no longer be followed.  Three rows were damaged before anyone noticed.  This guard makes the
    defect class measurable instead of a prose reminder, and re-checks that the archive paths the
    ledgers name actually exist.

Usage:
    python scripts/doc_control_char_scan.py            # scan, exit 1 on findings
    python scripts/doc_control_char_scan.py --quiet    # only the summary line

Known exceptions (raw device logs, left verbatim):
    docs/evidence/2026-10-27/h231_hilog_full.txt:6560  U+0091
    _probe/mate80-cap4.txt:10402                       U+0091
    docs/evidence/_probe-cited/mate80-cap4.txt:10402   U+0091  (H-282 byte-identical copy)
"""
import os
import re
import sys

# Verbatim captures of on-device hilog: the odd byte came off the phone, not out of an editor.
# Editing them would falsify the evidence, so they are listed instead of silently tolerated.
CTRL_EXCEPTIONS = {
    ("docs/evidence/2026-10-27/h231_hilog_full.txt", 6560, "U+0091"),
    ("_probe/mate80-cap4.txt", 10402, "U+0091"),
    # H-282: the byte-identical copy that import_probe_cited_evidence_qoder.py put in git carries
    # the same odd byte from the phone.  Tolerating it keeps the copy verbatim; "fixing" it would
    # falsify the captured log.
    ("docs/evidence/_probe-cited/mate80-cap4.txt", 10402, "U+0091"),
}

TEXT_EXT = (".md", ".txt", ".json", ".json5", ".yaml", ".yml", ".ps1", ".py", ".ets", ".cpp", ".h", ".ts")
SKIP_DIRS = {".git", "node_modules", "build", ".cxx", "out", "oh_modules"}
# C0 controls (except tab/LF/CR) plus the C1 range, which is what an over-eager
# octal escape produces.
CTRL_RE = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")
# Zero-width and BOM characters: invisible in a rendered ledger, so a row damaged this way
# reads as if it were fine (a path carrying a zero-width space will not open).  Caught the same evening D-034 was written (one U+200B slipped
# into the row while I typed it).  A BOM at the very start of a file is legitimate - PowerShell 5.1
# writes UTF-8 with BOM and sign/keys.local.json is such a file - so position (1, 0) is tolerated.
INVISIBLE_RE = re.compile("[\u200b\u200c\u200d\u2060\ufeff]")
# Paths the ledgers point at for submission/install artefacts live outside the repo tree,
# so a mangled or moved path is invisible to every other checker.
ART_RE = re.compile(r"F:\\qoderwork\\sansheng-release-artifacts[^\s`|)\u3010\u3011]*")
# Trailing punctuation that is part of the sentence, not the path.
TRAIL = ".,;:\u3002\uff0c\uff1b\uff1a\u3001\"\u201d\u201c`'"


def walk(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if fn.endswith(TEXT_EXT):
                yield os.path.join(dirpath, fn)


def main():
    quiet = "--quiet" in sys.argv
    root = os.getcwd()
    ctrl = []
    invisible = []
    tolerated = 0
    missing = []
    seen = set()
    templates = set()
    for fp in walk(root):
        try:
            data = open(fp, encoding="utf-8").read()
        except (UnicodeDecodeError, OSError):
            continue
        rel = os.path.relpath(fp, root).replace("\\", "/")
        for lineno, line in enumerate(data.split("\n"), 1):
            for m in CTRL_RE.finditer(line):
                item = (rel, lineno, "U+%04X" % ord(m.group()))
                if item in CTRL_EXCEPTIONS:
                    tolerated += 1
                else:
                    ctrl.append(item)
            for m in INVISIBLE_RE.finditer(line):
                if lineno == 1 and m.start() == 0:
                    continue                      # leading BOM is legitimate
                if not rel.endswith(".md"):
                    continue                      # shipped data / device dumps legitimately carry
                    # emoji ZWJ sequences and zero-width joiners - 118 real occurrences measured
                    # 2026-10-30 07:4x in symbols.json, phraseExt esUnicode.txt, aapt-res.txt.
                    # This guard watches prose ledgers only; a ledger must not hide a damaged path.
                invisible.append((rel, lineno, "U+%04X" % ord(m.group())))
        for m in ART_RE.finditer(data):
            raw = m.group().rstrip(TRAIL)
            if not raw:
                continue
            seen.add(raw)
            # A path with a placeholder (`accepted-<时间戳>`) is a template in prose, not a pointer.
            if "<" in raw or "\u65f6\u95f4\u6233" in raw or raw.endswith("\\") and raw.count("\\") <= 2:
                templates.add(raw)
                continue
            probe = raw.rstrip("\\")
            if not os.path.exists(probe.replace("\\", "/")):
                missing.append((rel, raw))

    print("control characters: %d (listed exceptions tolerated: %d)" % (len(ctrl), tolerated))
    for rel, lineno, ch in ctrl:
        print("  %s:%s %s" % (rel, lineno, ch))
    print("invisible formatting chars: %d (leading BOM tolerated)" % len(invisible))
    for rel, lineno, ch in invisible:
        print("  %s:%s %s" % (rel, lineno, ch))
    print("artifact paths checked: %d (templates skipped: %d) ; missing: %d"
          % (len(seen) - len(templates), len(templates), len(missing)))
    for rel, raw in missing:
        print("  %s -> %s" % (rel, raw))
    if ctrl or invisible or missing:
        print("FAIL: %d control char(s), %d invisible char(s), %d broken artifact path(s)"
              % (len(ctrl), len(invisible), len(missing)))
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
