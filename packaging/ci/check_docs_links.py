#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Qoder 2026-11-02：主页/文档链接自检。

扫所有进 git 的 .md，把「相对路径链接」（不是 http(s)/#锚点/邮箱）拆出来，
逐条检查目标文件/目录在仓库里是否真的存在；顺带把外链里的 releases/tag/xxx
与仓库真实 tag 对一遍（需要联网时加 --net）。

用法：
  python packaging/ci/check_docs_links.py            # 只看本地相对链接
  python packaging/ci/check_docs_links.py --net      # 再加 GitHub tag/链接 HTTP 状态
退出码：0=全部可解析；1=有死链。
"""
import os
import re
import subprocess
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LINK = re.compile(r'\[[^\]]*\]\(([^)\s]+)(?:\s+"[^"]*")?\)')
RAWLINK = re.compile(r'(?<![\w/])https?://[^\s)>\]`"]+')


def tracked_md():
    out = subprocess.run(
        ["git", "-c", "core.quotepath=false", "ls-files", "*.md"],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=True).stdout
    return [l for l in out.splitlines() if l.strip()]


def local_check():
    bad = []
    for rel in tracked_md():
        base = os.path.dirname(os.path.join(ROOT, rel))
        with open(os.path.join(ROOT, rel), encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        for m in LINK.finditer(text):
            tgt = m.group(1)
            if tgt.startswith(("http://", "https://", "mailto:", "#", "tel:")):
                continue
            tgt = tgt.split("#")[0]
            if not tgt:
                continue
            p = os.path.normpath(os.path.join(base, tgt.replace("/", os.sep)))
            if not os.path.exists(p):
                bad.append((rel, tgt))
    return bad


def repo_tags():
    txt = subprocess.run(["git", "ls-remote", "--tags", "origin"],
                         cwd=ROOT, capture_output=True, text=True, encoding="utf-8").stdout
    return {l.split("refs/tags/")[-1].rstrip("^{}") for l in txt.splitlines() if "refs/tags/" in l}


def net_check():
    tags = repo_tags()
    bad = []
    seen = {}
    for rel in tracked_md():
        with open(os.path.join(ROOT, rel), encoding="utf-8", errors="replace") as fh:
            for m in RAWLINK.finditer(fh.read()):
                url = m.group(0).rstrip(".,;，。；、")
                key = url
                if key in seen:
                    if not seen[key]:
                        bad.append((rel, url, "cached-fail"))
                    continue
                ok = True
                mt = re.search(r"/releases/tag/([^/?#]+)", url)
                if mt and "ri0977-code/sansheng-ime" in url:
                    ok = mt.group(1) in tags
                    why = "tag 不存在"
                else:
                    try:
                        req = urllib.request.Request(url, headers={"User-Agent": "qoder-linkcheck"})
                        code = urllib.request.urlopen(req, timeout=20).getcode()
                        ok, why = code < 400, "HTTP %s" % code
                    except Exception as ex:
                        ok, why = False, repr(ex)[:60]
                seen[key] = ok
                if not ok:
                    bad.append((rel, url, why))
    return bad, seen


def main():
    net = "--net" in sys.argv
    bad = local_check()
    print("== 相对链接（进 git 的 .md）==")
    if bad:
        for rel, tgt in bad:
            print("  [MISS] %s -> %s" % (rel, tgt))
    else:
        print("  全部可解析（共扫 %d 个 md）" % len(tracked_md()))
    rc = 1 if bad else 0
    if net:
        nb, seen = net_check()
        print("== 外链 ==")
        print("  检查 %d 个唯一 URL" % len(seen))
        for rel, url, why in nb:
            print("  [DEAD] %s -> %s (%s)" % (rel, url, why))
        rc = rc or (1 if nb else 0)
    print("exit=%d" % rc)
    return rc


if __name__ == "__main__":
    sys.exit(main())
