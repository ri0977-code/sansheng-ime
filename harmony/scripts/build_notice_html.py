"""
把根 NOTICE + LICENSES/*.txt 合成为一个应用内可读的 HTML（notice.html），
供 AboutPage 里「完整许可声明」按钮打开。

背景（H-099）：About 页写着「查看应用安装目录下的 NOTICE 文件及 LICENSES/ 目录」，
但 HarmonyOS 沙箱下用户根本进不去安装目录，且包里也确实没有这两个东西。
Apache-2.0 §4(d) 要求分发包内含 NOTICE 时一并分发 —— 所以做成应用内页面最稳妥。

用法：
    python scripts/build_notice_html.py             # 只写应用内那份
    python scripts/build_notice_html.py --public    # 同时写公示版
输出：
    entry/src/main/resources/rawfile/legal/notice.html   （应用内）
    docs/release/legal/notice.html                    （公示，AGC 托管页要点得到）

13:5x 加 --public 的原因：公示目录 `docs/release/legal/` 原先只有 privacy/terms 两份，
缺 NOTICE 这一份 —— AGC 托管页要能一路点到许可公示件，否则用户从商店进来看不到第三方许可。
"""
import html
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOTICE = os.path.join(ROOT, "NOTICE")
LIC_DIR = os.path.join(ROOT, "LICENSES")
OUT = os.path.join(ROOT, "entry", "src", "main", "resources", "rawfile", "legal", "notice.html")
PUBLIC_OUT = os.path.join(ROOT, "docs", "release", "legal", "notice.html")

CSS = """
:root { color-scheme: light; }
* { box-sizing: border-box; }
body {
  margin: 0; background: #f6f8fa; color: #1f2328;
  font-family: -apple-system, BlinkMacSystemFont, "HarmonyOS Sans SC",
    "PingFang SC", "Microsoft YaHei", "Segoe UI", sans-serif;
  line-height: 1.75;
}
main { max-width: none; margin: 0; padding: 24px 18px 40px; background: #fff; }
h1 { font-size: 24px; line-height: 1.35; margin: 0 0 10px; }
h2 { font-size: 18px; margin: 28px 0 10px; padding-bottom: 6px; border-bottom: 1px solid #eaeef2; }
p { margin: 9px 0; }
hr { border: 0; border-top: 1px solid #d8dee4; margin: 26px 0; }
pre {
  margin: 0; padding: 12px 14px; background: #f6f8fa; border: 1px solid #e1e4e8;
  border-radius: 8px; font-size: 12px; line-height: 1.6; white-space: pre-wrap;
  word-break: break-word; overflow-wrap: anywhere;
  font-family: "SFMono-Regular", Consolas, "Liberation Mono", monospace;
}
.toc { font-size: 14px; margin: 12px 0 24px; }
.toc a { color: #0a59f7; text-decoration: none; display: block; margin: 4px 0; }
.summary { padding: 10px 14px; background: #f0f6ff; border: 1px solid #c8dcff; border-radius: 8px; font-size: 14px; }
footer { margin-top: 32px; color: #6e7781; font-size: 12px; }
"""


def read(p):
    with io.open(p, "r", encoding="utf-8") as f:
        return f.read()


def slug(name):
    return "lic-" + re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def render():
    """Pure: the complete in-app notice HTML as text (no writes)."""
    notice = read(NOTICE)
    licenses = sorted(f for f in os.listdir(LIC_DIR) if f.endswith(".txt"))
    if not licenses:
        raise SystemExit("LICENSES/ 下没有 .txt，先检查")

    out = ['<!doctype html>', '<html lang="zh-CN">', '<head>', '<meta charset="utf-8">',
           '<meta name="viewport" content="width=device-width, initial-scale=1">',
           '<title>三生输入法 · 完整许可声明</title>', '<style>%s</style>' % CSS.strip(),
           '</head>', '<body>', '<main>', '<h1>完整许可声明</h1>']

    out.append(
        '<p class="summary">本页是 <code>NOTICE</code> 的完整正文，以及随包分发的全部第三方许可全文'
        '（共 %d 份）。本应用基于 Apache License 2.0 发布；页面内容与应用安装包内的一致。</p>' % len(licenses))

    # 目录
    out.append('<div class="toc">')
    out.append('<a href="#notice">NOTICE 正文</a>')
    for f in licenses:
        out.append('<a href="#%s">%s</a>' % (slug(f), html.escape(f)))
    out.append('</div>')

    # NOTICE 正文
    out.append('<h2 id="notice">NOTICE</h2>')
    out.append('<pre>%s</pre>' % html.escape(notice.rstrip("\n")))

    # 各许可全文
    for f in licenses:
        body = read(os.path.join(LIC_DIR, f))
        out.append('<hr>')
        out.append('<h2 id="%s">%s</h2>' % (slug(f), html.escape(f)))
        out.append('<pre>%s</pre>' % html.escape(body.rstrip("\n")))

    out.append('<footer>三生输入法 V1.0 · 本页内容随应用版本更新 · 由 scripts/build_notice_html.py 生成</footer>')
    out.append('</main>')
    out.append('</body>')
    out.append('</html>')

    text = "\n".join(out) + "\n"
    return text


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    public = "--public" in argv
    notice = read(NOTICE)
    licenses = sorted(f for f in os.listdir(LIC_DIR) if f.endswith(".txt"))
    text = render()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    if public:
        os.makedirs(os.path.dirname(PUBLIC_OUT), exist_ok=True)
        with io.open(PUBLIC_OUT, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        print("written:", PUBLIC_OUT)

    print("written:", OUT)
    print("  NOTICE %d chars" % len(notice))
    print("  licenses: %d (%s)" % (len(licenses), ", ".join(licenses)))
    print("  html %d chars / %d B" % (len(text), len(text.encode("utf-8"))))


if __name__ == "__main__":
    main()
