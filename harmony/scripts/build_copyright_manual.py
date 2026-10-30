#!/usr/bin/env python3
"""Render the copyright operation manual from Markdown to a print-ready HTML."""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

from build_legal_html import convert  # noqa: E402

LEGAL = ROOT / "docs" / "release" / "copyright"
SOURCE = LEGAL / "operation-manual.md"
OUTPUT = LEGAL / "operation-manual.html"

CSS = """
@page { size: A4 portrait; margin: 18mm 16mm 16mm; }
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; background: #e9edf2; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "HarmonyOS Sans SC", "PingFang SC",
    "Microsoft YaHei", "Segoe UI", sans-serif;
  color: #1f2328; line-height: 1.8;
}
.sheet {
  max-width: 900px; margin: 24px auto; padding: 44px 56px; background: #fff;
  box-shadow: 0 1px 6px rgba(0,0,0,.16);
}
.cover { text-align: center; padding: 26mm 0 0; page-break-after: always; break-after: page; }
.cover .kicker { font-size: 13pt; letter-spacing: 4px; color: #57606a; }
.cover h1 { font-size: 30pt; line-height: 1.4; margin: 18mm 0 6mm; }
.cover .subtitle { font-size: 14pt; color: #57606a; margin-bottom: 18mm; }
.cover table { width: 78%; margin: 0 auto; font-size: 11pt; }
.cover th, .cover td { border: 1px solid #c9d1d9; padding: 2.4mm 4mm; text-align: left; }
.cover th { width: 34%; background: #f6f8fa; font-weight: 600; }
.cover .foot { margin-top: 24mm; font-size: 10pt; color: #6e7781; }
h1 { font-size: 24px; }
h2 {
  font-size: 18px; margin: 26px 0 10px; padding-bottom: 5px;
  border-bottom: 1px solid #d8dee4; page-break-after: avoid; break-after: avoid;
}
h3 { font-size: 15px; margin: 18px 0 8px; page-break-after: avoid; break-after: avoid; }
p { margin: 8px 0; }
ul, ol { margin: 8px 0; padding-left: 24px; }
li { margin: 4px 0; }
table { width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 13px; }
th, td { border: 1px solid #d0d7de; padding: 6px 9px; text-align: left; vertical-align: top; }
th { background: #f6f8fa; }
code { background: #f6f8fa; padding: 1px 5px; border-radius: 4px; font-size: 13px; }
figure { margin: 16px 0; text-align: center; page-break-inside: avoid; break-inside: avoid; }
figure img { max-width: 64%; max-height: 165mm; height: auto; border: 1px solid #d0d7de; border-radius: 6px; }
figcaption { margin-top: 6px; color: #57606a; font-size: 12px; }
hr { border: 0; border-top: 1px solid #d8dee4; margin: 22px 0; }
@media print {
  html, body { background: #fff; }
  .sheet { max-width: none; margin: 0; padding: 0; box-shadow: none; }
  figure img { max-width: 62%; max-height: 155mm; }
}
"""

COVER = """
<section class="cover">
  <div class="kicker">软件著作权登记材料</div>
  <h1>三生输入法 1.0.0<br>操作说明书</h1>
  <div class="subtitle">HarmonyOS NEXT · 五笔 · 拼音 · 英文混输</div>
  <table>
    <tr><th>软件名称</th><td>三生输入法</td></tr>
    <tr><th>版本号</th><td>1.0.0</td></tr>
    <tr><th>应用版本</th><td>1.0.0（包名 com.sansheng.ime）</td></tr>
    <tr><th>运行平台</th><td>HarmonyOS NEXT</td></tr>
    <tr><th>开发语言</th><td>ArkTS / C++</td></tr>
    <tr><th>开发者</th><td>[机主姓名已脱敏]（个人开发者）</td></tr>
    <tr><th>编制日期</th><td>2026 年 10 月</td></tr>
    <tr><th>文档用途</th><td>软件著作权登记操作说明书</td></tr>
  </table>
  <div class="foot">本说明书基于 HUAWEI Mate 80 真机功能编写，截图与应用版本 1.0.0 对应。</div>
</section>
"""


def strip_html_comments(md: str) -> str:
    """去掉 Markdown 里的 HTML 注释块。

    2026-10-27 18:0x 修：说明书里 3 处 `<!-- FIG:... -->`（等最终包重拍插图的占位）
    被 `convert()` 当成普通段落印进了 PDF 正文，审查员会直接看到原始注释。
    只在说明书这一条链路上过滤，不动法律页共用的 `convert()`（那边有自己的同源比对）。
    """
    return re.sub(r"<!--.*?-->", "", md, flags=re.S)


def main() -> None:
    md = strip_html_comments(SOURCE.read_text(encoding="utf-8"))
    body = convert(md)
    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>三生输入法 1.0.0 操作说明书</title>
<style>{CSS}</style>
</head>
<body>
<div class="sheet">
{COVER}
{body}
</div>
</body>
</html>
"""
    OUTPUT.write_text(html, encoding="utf-8", newline="\n")
    print(f"operation-manual.html: {len(html)} chars")


if __name__ == "__main__":
    main()
