#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Check whether the off-tree copy of sign/ still matches the working copy (H-281, Qoder).

Why a script and not a shell one-liner: the 2026-10-30 ledger damage (see
docs/evidence/2026-10-30/release-app/H-280-app-1.0.0-release-build.md section 8) was caused by
Windows paths passing through shell quoting, which ate backslashes. A published one-liner would
carry the same trap. This file has no backslashes outside raw string literals.

Prints only booleans and sizes - never the key bytes, never the password, never the hash.
Exit 0 = every watched file present in both trees and byte-identical.
Usage:
    python scripts/verify_sign_backup_match.py
"""
import hashlib
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK_SIGN = os.path.join(REPO, "sign")

# The only known copy that left the working tree so far.  It is on another *disk* of the same
# machine - that is exactly what H-281 is about.
BACKUP_SIGN = os.path.join("E:", os.sep, "sansheng-sign-backup", "20261022-132646", "sign")

WATCHED = (
    os.path.join("release", "sansheng-release.p12"),
    os.path.join("release", "sansheng-release.cer"),
    os.path.join("release", "sansheng-release.p7b"),
    os.path.join("release", "release-csr.info.txt"),
    "keys.local.json",
)


def digest(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def main():
    # Optional: point at another copy (used to prove the FAIL branch fires; also lets the owner
    # re-check a cloud/USB copy later by pasting its path).
    backup = sys.argv[1] if len(sys.argv) > 1 else BACKUP_SIGN
    print("working tree : %s" % WORK_SIGN)
    print("backup copy  : %s  (exists=%s)" % (backup, os.path.isdir(backup)))
    if not os.path.isdir(backup):
        print("FAIL: no backup tree at the path above - H-281 stays open, nothing to compare")
        return 1
    bad = 0
    for rel in WATCHED:
        a = os.path.join(WORK_SIGN, rel)
        b = os.path.join(backup, rel)
        if not os.path.isfile(a):
            print("  MISSING-IN-WORKING-TREE  %s" % rel)
            bad += 1
            continue
        if not os.path.isfile(b):
            print("  NOT-BACKED-UP            %s" % rel)
            bad += 1
            continue
        same = digest(a) == digest(b)
        size = os.path.getsize(a)
        print("  %-22s %8d B  match=%s" % ("MATCH" if same else "DIFFERS", size, same))
        if not same:
            bad += 1
    if bad:
        print("FAIL: %d of %d watched files are not recoverable from the backup" % (bad, len(WATCHED)))
        return 1
    print("PASS: all %d watched files identical - but the copy is on the SAME MACHINE (H-281 is about that)"
          % len(WATCHED))
    return 0


if __name__ == "__main__":
    sys.exit(main())
