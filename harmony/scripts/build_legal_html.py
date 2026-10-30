#!/usr/bin/env python3
"""Render docs/release/legal/*.md to self-contained HTML for AppGallery hosting.

Only the Markdown subset used by the legal documents is supported:
headings, paragraphs, unordered/ordered lists, tables, bold, inline code, hr.
No third-party dependencies.
"""

from __future__ import annotations

import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEGAL_DIR = ROOT / "docs" / "release" / "legal"
OUT_DIR = LEGAL_DIR
INAPP_DIR = ROOT / "entry" / "src" / "main" / "resources" / "rawfile" / "legal"

CSS = """
:root { color-scheme: light; }
* { box-sizing: border-box; }
body {
  margin: 0; background: #f6f8fa; color: #1f2328;
  font-family: -apple-system, BlinkMacSystemFont, "HarmonyOS Sans SC",
    "PingFang SC", "Microsoft YaHei", "Segoe UI", sans-serif;
  line-height: 1.8;
}
main {
  max-width: 860px; margin: 24px auto; padding: 40px 48px;
  background: #fff; border: 1px solid #d0d7de; border-radius: 12px;
}
main.inapp {
  max-width: none; margin: 0; padding: 24px 18px 40px;
  border: 0; border-radius: 0;
}
nav { margin-bottom: 24px; font-size: 14px; }
nav a { color: #0a59f7; text-decoration: none; margin-right: 16px; }
nav a:hover { text-decoration: underline; }
h1 { font-size: 28px; line-height: 1.35; margin: 0 0 8px; }
h2 { font-size: 20px; margin: 32px 0 12px; padding-bottom: 6px; border-bottom: 1px solid #eaeef2; }
h3 { font-size: 16px; margin: 24px 0 8px; }
p { margin: 10px 0; }
ul, ol { margin: 10px 0; padding-left: 26px; }
li { margin: 6px 0; }
hr { border: 0; border-top: 1px solid #d8dee4; margin: 28px 0; }
table { width: 100%; border-collapse: collapse; margin: 14px 0; font-size: 14px; }
th, td { border: 1px solid #d0d7de; padding: 8px 10px; text-align: left; vertical-align: top; }
th { background: #f6f8fa; }
code { background: #f6f8fa; padding: 1px 5px; border-radius: 4px; font-size: 13px; }
figure { margin: 18px 0; text-align: center; }
figure img { max-width: 86%; height: auto; border: 1px solid #d0d7de; border-radius: 8px; }
figcaption { margin-top: 6px; color: #57606a; font-size: 13px; }
.draft {
  margin: 0 0 20px; padding: 10px 14px; border-radius: 8px;
  background: #fff8c5; border: 1px solid #d4a72c; font-size: 14px;
}
footer { margin-top: 32px; color: #6e7781; font-size: 12px; }
@media (max-width: 640px) {
  main { margin: 0; border: 0; border-radius: 0; padding: 24px 18px; }
  h1 { font-size: 24px; }
  table { font-size: 13px; }
}
"""


def inline(text: str) -> str:
    text = html.escape(text, quote=False)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    return text


def split_row(line: str) -> list[str]:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [cell.strip() for cell in line.split("|")]


def render_table(rows: list[str]) -> str:
    header = split_row(rows[0])
    body = rows[2:] if len(rows) > 1 else []
    out = ["<table>", "<thead><tr>"]
    out.extend(f"<th>{inline(cell)}</th>" for cell in header)
    out.append("</tr></thead><tbody>")
    for row in body:
        cells = split_row(row)
        out.append("<tr>")
        out.extend(f"<td>{inline(cell)}</td>" for cell in cells)
        out.append("</tr>")
    out.append("</tbody></table>")
    return "\n".join(out)


def convert(md: str) -> str:
    lines = md.splitlines()
    out: list[str] = []
    para: list[str] = []
    list_tag: str | None = None
    i = 0

    def close_para() -> None:
        if para:
            out.append(f"<p>{inline(''.join(para))}</p>")
            para.clear()

    def close_list() -> None:
        nonlocal list_tag
        if list_tag:
            out.append(f"</{list_tag}>")
            list_tag = None

    while i < len(lines):
        raw = lines[i]
        line = raw.strip()

        image = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)$", line)
        if image:
            close_para()
            close_list()
            alt, src = image.group(1), image.group(2)
            out.append(
                f'<figure><img src="{html.escape(src)}" alt="{html.escape(alt)}">'
                f"<figcaption>{inline(alt)}</figcaption></figure>"
            )
            i += 1
            continue

        if line.startswith("|"):
            close_para()
            close_list()
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(lines[i])
                i += 1
            out.append(render_table(rows))
            continue

        if line.startswith("#"):
            close_para()
            close_list()
            level = len(line) - len(line.lstrip("#"))
            out.append(f"<h{level}>{inline(line[level:].strip())}</h{level}>")
            i += 1
            continue

        if line == "---":
            close_para()
            close_list()
            out.append("<hr>")
            i += 1
            continue

        if line.startswith("- "):
            close_para()
            if list_tag != "ul":
                close_list()
                out.append("<ul>")
                list_tag = "ul"
            out.append(f"<li>{inline(line[2:])}</li>")
            i += 1
            continue

        if re.match(r"^\d+\.\s+", line):
            close_para()
            if list_tag != "ol":
                close_list()
                out.append("<ol>")
                list_tag = "ol"
            out.append(f"<li>{inline(re.sub(r'^\d+\.\s+', '', line))}</li>")
            i += 1
            continue

        if line == "":
            close_para()
            close_list()
            i += 1
            continue

        close_list()
        para.append(line)
        i += 1

    close_para()
    close_list()
    return "\n".join(out)


def page(title: str, body: str, draft: bool) -> str:
    banner = (
        '<div class="draft">草案：发布前需补齐联系邮箱、生效日期与主体信息，'
        "不得保留占位符。</div>"
        if draft
        else ""
    )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>{CSS}</style>
</head>
<body>
<main>
<nav><a href="index.html">三生输入法 · 法律文件</a><a href="privacy.html">隐私政策</a><a href="terms.html">用户协议</a></nav>
{banner}
{body}
<footer>三生输入法 V1.0 · 本页内容随应用版本更新</footer>
</main>
</body>
</html>
"""


def inapp_page(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>{CSS}</style>
</head>
<body>
<main class="inapp">
{body}
<footer>三生输入法 V1.0 · 本页内容随应用版本更新</footer>
</main>
</body>
</html>
"""


def build(md_name: str, html_name: str, title: str) -> None:
    md_path = LEGAL_DIR / md_name
    if not md_path.exists():
        raise SystemExit(f"missing source: {md_path}")
    md = md_path.read_text(encoding="utf-8")
    body = convert(md)
    draft = "【待主人确认" in md or "（草案" in md
    (OUT_DIR / html_name).write_text(page(title, body, draft), encoding="utf-8", newline="\n")
    print(f"{html_name}: {len(body)} chars")


def inapp_text(md_name: str, title: str) -> str:
    """Pure: the self-contained in-app HTML for one legal master (no writes)."""
    md = (LEGAL_DIR / md_name).read_text(encoding="utf-8")
    body = convert(md)
    body = body.replace(
        "【待主人确认，见 <code>docs/ISSUES.md</code> H-053】",
        "（以应用市场公示的联系方式为准）",
    )
    body = body.replace("【待主人确认】", "（以应用市场公示的联系方式为准）")
    body = body.replace("1.0（草案，发布前定稿）", "1.0")
    body = re.sub(
        r"<p><strong>说明</strong>：本(?:政策|协议)为发布前草案.*?</p>",
        "",
        body,
        flags=re.S,
    )
    return inapp_page(title, body)


def build_inapp(md_name: str, html_name: str, title: str) -> None:
    """Self-contained copy for the in-app legal viewer (no nav, no draft banner)."""
    text = inapp_text(md_name, title)
    body_len = len(text)
    (INAPP_DIR / html_name).write_text(text, encoding="utf-8", newline="\n")
    print(f"in-app {html_name}: {body_len} chars")


def build_index() -> None:
    body = """
<h1>三生输入法 · 法律文件</h1>
<p>本页用于向用户提供三生输入法（HarmonyOS 版）的隐私政策与用户协议。</p>
<ul>
<li><a href="privacy.html">三生输入法隐私政策</a></li>
<li><a href="terms.html">三生输入法用户协议</a></li>
</ul>
<p>开发者：[机主姓名已脱敏]（个人开发者）</p>
<p>应用包名：<code>com.sansheng.ime</code></p>
"""
    (OUT_DIR / "index.html").write_text(page("三生输入法 · 法律文件", body, True), encoding="utf-8", newline="\n")
    print("index.html: generated")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    INAPP_DIR.mkdir(parents=True, exist_ok=True)
    build("privacy-policy.md", "privacy.html", "三生输入法隐私政策")
    build("user-agreement.md", "terms.html", "三生输入法用户协议")
    build_inapp("privacy-policy.md", "privacy.html", "三生输入法隐私政策")
    build_inapp("user-agreement.md", "terms.html", "三生输入法用户协议")
    build_index()


if __name__ == "__main__":
    main()
