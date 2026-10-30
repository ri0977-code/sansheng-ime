#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""法律文本四层一致性检查（只读，不写任何文件）。

背景：AGC 驳回项 TOP6 就是「应用内文本与提审/托管内容不一致」，而 H-099/H-100 这类
问题都出在「同一句话存在于多个表面，其中一处忘了改」。以往我靠临时逐句对照，
跑一次就忘一次。这条脚本把对照做成可重复的闸门：

  L1 master   —— docs/release/legal/*.md（唯一真源）
  L2 inapp    —— entry/src/main/resources/rawfile/legal/*.html（下一版包里会有的）
  L3 packaged —— 最新构建产物 .hap 里的同名文件（上一版包里实际有的）
  L4 hosted   —— docs/release/legal/*.html（AGC 隐私声明托管/自定义网址要贴的）

L1 先经 scripts/build_legal_html.py / scripts/build_notice_html.py 的纯函数渲染成
期望文本，再与 L2/L3/L4 逐字节比较；不一致时给出行级差异样本，方便判断是谁忘了重生成。

用法：
    PYTHONIOENCODING=utf-8 python scripts/legal_drift.py
    PYTHONIOENCODING=utf-8 python scripts/legal_drift.py --json

退出码：0=四层全一致；1=有 DIFF/MISSING；2=脚本自身无法完成（缺生成器/缺产物）。
"""

from __future__ import annotations

import glob
import hashlib
import io
import json
import os
import re
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)

LEGAL_DIR = os.path.join(REPO, "docs", "release", "legal")
INAPP_DIR = os.path.join(REPO, "entry", "src", "main", "resources", "rawfile", "legal")

# (逻辑名, master md 或 None, 标题, 在包内/托管目录的文件名)
PAGES = [
    ("privacy", "privacy-policy.md", "三生输入法隐私政策", "privacy.html", True),
    ("terms", "user-agreement.md", "三生输入法用户协议", "terms.html", True),
    ("notice", None, "三生输入法 · 完整许可声明", "notice.html", False),
]


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()[:16]


def read_bytes(p):
    if not os.path.exists(p):
        return None
    with io.open(p, "rb") as f:
        return f.read()


def expected_inapp(md_name, title):
    import build_legal_html as blh
    return blh.inapp_text(md_name, title).encode("utf-8")


def expected_notice():
    import build_notice_html as bn
    return bn.render().encode("utf-8")


def expected_hosted(md_name, title):
    import build_legal_html as blh
    md = io.open(os.path.join(LEGAL_DIR, md_name), encoding="utf-8").read()
    body = blh.convert(md)
    draft = "【待主人确认" in md or "（草案" in md
    return blh.page(title, body, draft).encode("utf-8")


def newest_artifacts():
    """Return (hap_path, app_path) — 优先 release 血缘产物（提审件），没有才退回最新构建。

    优先级写在代码里是有原因的：2026-10-23 的实测发现 13:25 的 release `.app` 与
    release-signed HAP 都不在 `entry/build` 里了（被 00:08 的 hvigorw clean 清掉），
    目录里只剩 debug 签名的 01:17 那对。若只按 mtime 取最新，脚本会把 debug 包当成
    提审件比对——那是另一种「看着像但不是」。
    """
    haps = []
    for pat in ("entry/build/**/*.hap", "dist/**/*.hap", "*.hap"):
        haps += glob.glob(os.path.join(REPO, pat), recursive=True)
    apps = []
    for pat in ("entry/build/**/*.app", "dist/**/*.app", "*.app"):
        apps += glob.glob(os.path.join(REPO, pat), recursive=True)
    haps = [r for r in haps if os.path.isfile(r)]
    apps = [r for r in apps if os.path.isfile(r)]

    def rank_release_lineage(p):
        n = os.path.basename(p).lower()
        is_release = ("release" in n) or n.endswith(".app")
        return (1 if is_release else 0, os.path.getmtime(p))

    hap = max(haps, key=rank_release_lineage) if haps else None
    app = max(apps, key=lambda p: (1, os.path.getmtime(p))) if apps else None
    return hap, app


def from_hap(hap_path, name):
    """Read resources/rawfile/legal/<name> out of a .hap (or a .app wrapping one)."""
    if not hap_path:
        return None
    try:
        with zipfile.ZipFile(hap_path) as z:
            inner = [n for n in z.namelist() if n.endswith(".hap")]
            if os.path.splitext(hap_path)[1].lower() == ".app" and inner:
                import tempfile
                with tempfile.TemporaryDirectory() as td:
                    data = z.read(inner[0])
                    p = os.path.join(td, "inner.hap")
                    with io.open(p, "wb") as f:
                        f.write(data)
                    return from_hap(p, name)
                return None
            want = "resources/rawfile/legal/" + name
            for n in z.namelist():
                if n == want or n.endswith("/" + want):
                    return z.read(n)
            return None
    except zipfile.BadZipFile:
        return None


def line_diff(a: bytes, b: bytes, limit=3):
    la = a.decode("utf-8", "replace").splitlines()
    lb = b.decode("utf-8", "replace").splitlines()
    n = max(len(la), len(lb))
    hits = []
    diff_lines = 0
    for i in range(n):
        x = la[i] if i < len(la) else "<无此行>"
        y = lb[i] if i < len(lb) else "<无此行>"
        if x != y:
            diff_lines += 1
            if len(hits) < limit:
                hits.append((i + 1, x[:90], y[:90]))
    return diff_lines, len(la), len(lb), hits


def main() -> int:
    as_json = "--json" in sys.argv
    hap, app = newest_artifacts()
    rows = []
    blockers = 0
    tool_errors = 0

    for logical, md_name, title, fname, has_hosted in PAGES:
        try:
            if md_name is None:
                exp = expected_notice()
            else:
                exp = expected_inapp(md_name, title)
        except Exception as exc:  # generator missing / master missing
            tool_errors += 1
            rows.append({"page": logical, "layer": "render", "verdict": "ERROR",
                         "detail": "%s: %s" % (type(exc).__name__, exc)})
            continue

        inapp = read_bytes(os.path.join(INAPP_DIR, fname))
        packaged = from_hap(hap, fname)
        hosted = expected_hosted(md_name, title) if has_hosted and md_name else None
        hosted_actual = read_bytes(os.path.join(LEGAL_DIR, fname)) if has_hosted else None

        for layer, actual, want in (
            ("L2-inapp(下版包)", inapp, exp),
            ("L3-packaged(上版包)", packaged, exp),
            ("L4-hosted(商店托管)", hosted_actual, hosted),
        ):
            if actual is None:
                if layer.startswith("L4") and hosted is None:
                    continue
                blockers += 1
                rows.append({"page": fname, "layer": layer, "verdict": "MISSING",
                             "detail": "文件不存在/包内没有该路径"})
                continue
            if want is None:
                tool_errors += 1
                rows.append({"page": fname, "layer": layer, "verdict": "ERROR",
                             "detail": "无法渲染期望文本"})
                continue
            if actual == want:
                rows.append({"page": fname, "layer": layer, "verdict": "MATCH",
                             "detail": "%d B / sha %s" % (len(actual), sha(actual))})
                continue
            dl, na, nb, hits = line_diff(want, actual)
            blockers += 1
            rows.append({"page": fname, "layer": layer, "verdict": "DIFF",
                         "detail": "%s: 期望 %d B/sha %s，实际 %d B/sha %s，差异 %d 行（期望 %d 行 / 实际 %d 行）"
                                   % ("期望≠实际", len(want), sha(want), len(actual), sha(actual), dl, na, nb),
                         "samples": [{"line": i, "expected": x, "actual": y} for i, x, y in hits]})

    if as_json:
        print(json.dumps({"hap": hap, "app": app, "rows": rows,
                          "blockers": blockers, "tool_errors": tool_errors},
                         ensure_ascii=False, indent=1))
    else:
        print("比对基准产物（只读，未构建）：")
        print("  HAP: %s" % (hap or "<无>"))
        print("  APP: %s" % (app or "<无 —— 提审件不在盘上>"))
        lineage = "release 血缘" if (app or (hap and "release" in os.path.basename(hap))) else \
                  "仅 debug 包（没有任何 release 件，L3 比的是上一版调试包，不是提审件）"
        print("  产物类别: %s" % lineage)
        print("")
        for r in rows:
            print("[%s] %-12s %s  %s" % (r["verdict"], r["page"], r["layer"], r["detail"]))
            for s in r.get("samples", []):
                print("        行 %d | 期望: %s" % (s["line"], s["expected"]))
                print("             | 实际: %s" % (s["actual"],))
        print("")
        print("结论：%s（差异/缺失 %d 项，脚本自身错误 %d 项）"
              % ("四层一致" if blockers == 0 else "存在不一致，提审前必须清零",
                 blockers, tool_errors))

    if tool_errors:
        return 2
    return 0 if blockers == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
