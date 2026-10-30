#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Pre-commit guard: no signing password and no key container may appear in anything git can see.

AGENTS.md rule 5 says sign/, *.p12, *.p7b, *.cer, agconnect-services.json and any password never
enter git.  .gitignore covers the *files*, but a password pasted into a ledger row, a probe script
or a temporary build wrapper would still be committed.  This guard reads the real secret values
from sign/keys.local.json and searches every path `git status` reports as changed (tracked
modifications and untracked files alike; ignored paths are not reported, so they are not checked).

It prints file names and offsets only - never the matched value.

Usage (run before every commit):
    python scripts/check_secrets_in_worktree.py
Exit 0 = clean;  exit 1 = a secret value or a stray key container is visible to git.
"""
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEYS = os.path.join(REPO, "sign", "keys.local.json")

# Key containers must live inside sign/ (which is gitignored).
KEY_EXT = (".p12", ".p7b", ".cer", ".csr")
# Only these extensions are searched for plaintext secrets.
TEXT_EXT = (".md", ".txt", ".json", ".json5", ".yaml", ".yml", ".ps1", ".py", ".ets", ".cpp",
            ".h", ".ts", ".sh", ".csv")
# sign/ legitimately holds the passwords and keys; it is never a candidate.
SKIP_TOP = ("sign/", ".git/")


def changed_paths():
    """Every path git considers changed, repo-relative with forward slashes."""
    proc = subprocess.run(["git", "status", "--porcelain"], cwd=REPO,
                          capture_output=True, text=True, encoding="utf-8")
    paths = []
    for line in proc.stdout.splitlines():
        body = line[3:].strip().strip('"')
        if " -> " in body:                      # "a -> b" rename entries: take the target
            body = body.split(" -> ")[-1]
        body = body.split(":", 1)[-1] if body.startswith(("R ", "C ")) else body
        if body:
            paths.append(body.replace("\\", "/"))
    return paths


def secret_values():
    """Password-shaped values from keys.local.json (aliases are not secrets)."""
    if not os.path.isfile(KEYS):
        return {}
    with open(KEYS, encoding="utf-8-sig") as fh:   # utf-8-sig: the file is written by PowerShell 5.1 and carries a BOM
        data = json.load(fh)
    out = {}
    for key, value in _flatten(data):
        if isinstance(value, str) and len(value) >= 6 and "pwd" in key.lower():
            out[key] = value
    return out


def _flatten(node, prefix=""):
    """Walk nested JSON; label a leaf by its own key (parents kept only for readability)."""
    if isinstance(node, dict):
        for key, value in node.items():
            label = "%s.%s" % (prefix, key) if prefix else str(key)
            if isinstance(value, (dict, list)):
                yield from _flatten(value, label)
            else:
                yield str(key), value
    elif isinstance(node, list):
        for item in node:
            if isinstance(item, (dict, list)):
                yield from _flatten(item, prefix)
            else:
                yield prefix, item


def files_under(path):
    for dirpath, _names, filenames in os.walk(path):
        for fn in filenames:
            yield os.path.join(dirpath, fn)


def scan_file(full, rel, secrets, hits, stray_keys):
    ext = os.path.splitext(full)[1].lower()
    if ext in KEY_EXT and "sign/" not in rel.replace(os.sep, "/"):
        stray_keys.append(rel)
        return
    if ext not in TEXT_EXT or not os.path.isfile(full):
        return
    data = open(full, "rb").read()
    for label, value in secrets.items():
        idx = data.find(value.encode("utf-8"))
        if idx >= 0:
            hits.append((rel, label, idx))


def main():
    secrets = secret_values()
    print("sign/keys.local.json: %d password-shaped value(s) loaded (values not printed)" % len(secrets))
    if not secrets:
        print("NOTE: nothing to search for - keys.local.json missing or holds no *Pwd fields")

    hits = []
    stray_keys = []
    checked = 0
    for rel in changed_paths():
        if rel.startswith(SKIP_TOP):
            continue
        full = os.path.join(REPO, rel.replace("/", os.sep))
        if os.path.isdir(full):
            for child in files_under(full):
                checked += 1
                scan_file(child, os.path.relpath(child, REPO).replace("\\", "/"),
                          secrets, hits, stray_keys)
        elif os.path.isfile(full):
            checked += 1
            scan_file(full, rel, secrets, hits, stray_keys)

    for rel in stray_keys:
        print("KEY CONTAINER VISIBLE TO GIT: %s" % rel)
    for rel, label, offset in hits:
        print("SECRET VALUE (%s) in %s at byte offset %d" % (label, rel, offset))
    if hits or stray_keys:
        print("FAIL: %d secret occurrence(s), %d stray key container(s) across %d file(s) checked"
              % (len(hits), len(stray_keys), checked))
        return 1
    print("PASS: no password value, no stray key container in %d changed file(s)" % checked)
    return 0


if __name__ == "__main__":
    sys.exit(main())
