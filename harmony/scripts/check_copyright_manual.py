#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""软著《操作说明书》格式自检（H-152 · Qoder 归属）

为什么要这个脚本：软著补正十个里有八个栽在**格式**，不是内容。官方/实务口径的四条硬指标：
  1. 页眉左上角＝软件名称+版本号，且与申请表**一字不差**；
  2. 页眉右上角＝连续页码（1..N）；
  3. 文档中出现的**日期不得晚于**申请表「开发完成日期」（截图里的状态栏日期也算）；
  4. 文档中不得出现**作者姓名/笔名**（表里的「开发者/著作权人」是登记必需项，不算违规）。
另外查两条我们自己的：页数是否达到建议值、PDF 单文件是否 ≤10 MB。

**2026-10-29 加第 5 条：版本号字面量一致性（这次是真的被退过补正才加的）**
  易版权 10-28 意见原文：**「文档说明第一页文字中'V1.0'与基本信息中版本号不一致」**。
  本脚本第 1 条当时**查不出来**，两个原因都记在这里免得再犯：
    a) 只查 md —— 而封面是 `build_copyright_manual.py` 里 `COVER` 的**硬编码字符串**，改 md 改不到第 1 页；
    b) 判据是「VERSION 在文档里出现过」＝**presence 检查**，只要正文任何地方有 1.0.0 就永远绿。
  ⇒ 现在改成：扫**生成器封面**、**HTML 母版封面与 `<title>`**、**PDF 第 1 页**三处，
     要求版本号字面量**只允许 VERSION 一个值**，且全文禁 `V` 前缀写法；配 `--selftest` 两个已知坏样本验它真能红。

本脚本只读，不写任何文件。exit 1 = 有风险项。

用法：
  python scripts/check_copyright_manual.py            # 查 md 母版
  python scripts/check_copyright_manual.py --pdf      # 连 PDF 页数、大小与第 1 页版本号一起查
  python scripts/check_copyright_manual.py --selftest # 用已知坏样本验第 5 条判据会红
"""
import argparse
import datetime
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MD = "docs/release/copyright/operation-manual.md"
PDF = "docs/release/copyright/pdf/operation-manual.pdf"
HTML = "docs/release/copyright/operation-manual.html"
GEN = "scripts/build_copyright_manual.py"

SOFTWARE_NAME = "三生输入法"
VERSION = "1.0.0"
# 申请表现载的开发完成日期（docs/release/copyright/application-draft.md）
COMPLETION_DATE = datetime.date(2026, 10, 22)
MIN_PAGES = 20          # 建议值（H-152）
PDF_MAX_BYTES = 10 * 1024 * 1024

DATE_PATTERNS = [
    re.compile(r"(20\d{2})[-/年](\d{1,2})[-/月](\d{1,2})"),
]

# 版本号字面量：V 前缀写法（V1.0 / v1.0.0 一律禁）＋ 任何 x.y / x.y.z 数字段
V_PREFIX = re.compile(r"[Vv]\s?\d+\.\d+")
VERSION_TOKEN = re.compile(r"(?<![\d.])\d+\.\d+(?:\.\d+)?(?![\d.])")


def version_findings(text, where):
    """第 5 条判据的纯函数：返回 (fails, notes)。

    只在「封面区」用 VERSION_TOKEN 全量比对（封面里除版本号外不该有别的 x.y 数字，
    正文里 HarmonyOS 6.0.2 之类是合法值，所以不能拿它去扫全文）。
    V 前缀禁令扫全文——真材料里实测 0 命中，命中即说明有人又把版本写成 V1.0。
    """
    fails, notes = [], []
    bad_prefix = sorted(set(V_PREFIX.findall(text)))
    if bad_prefix:
        fails.append("%s：出现 V 前缀版本号写法 %s —— 申请表口径是「%s」，一字不差"
                     % (where, "、".join(x.strip() for x in bad_prefix), VERSION))
    toks = sorted(set(VERSION_TOKEN.findall(text)))
    off = [t for t in toks if t != VERSION]
    if off:
        fails.append("%s：封面区版本号字面量是 %s，与申请表「%s」不一致（补正高频项）"
                     % (where, "、".join(off), VERSION))
    if not toks:
        fails.append("%s：封面区找不到任何版本号字面量——第 1 页必须与申请表一字不差" % where)
    elif not off:
        notes.append("%s：版本号字面量只有「%s」✔" % (where, VERSION))
    return fails, notes


def cover_from_html():
    """HTML 母版里的封面段（`<section class="cover">` 到它自己的 `</section>`）＋ `<title>`。"""
    p = os.path.join(ROOT, HTML)
    if not os.path.exists(p):
        return None
    s = io.open(p, encoding="utf-8").read()
    m = re.search(r'<section class="cover">.*?</section>', s, re.S)
    t = re.search(r"<title>(.*?)</title>", s, re.S)
    parts = [m.group(0)] if m else []
    if t:
        parts.append(t.group(1))
    if not parts:
        return None
    return "\n".join(parts), (s if m is None else s[:m.start()] + m.group(0) + s[m.end():])


def cover_from_generator():
    """生成器里 COVER 那个三引号硬编码块——10-28 那次补正的真根因就在这块里。"""
    p = os.path.join(ROOT, GEN)
    if not os.path.exists(p):
        return None
    s = io.open(p, encoding="utf-8").read()
    m = re.search(r'COVER\s*=\s*"""(.*?)"""', s, re.S)
    return m.group(1) if m else None


def check_version_literals():
    fails, notes = [], []
    cov = cover_from_generator()
    if cov is None:
        fails.append("生成器里没抓到 COVER 块（%s）——封面是硬编码，判据抓不到它＝瞎" % GEN)
    else:
        f, n = version_findings(cov, "生成器 COVER")
        fails += f
        notes += n
    hc = cover_from_html()
    if hc is None:
        notes.append("HTML 母版不存在或无封面段，跳过（跑 build_copyright_manual.py 后再查）")
    else:
        cover_only, whole = hc
        f, n = version_findings(cover_only, "HTML 封面")
        fails += f
        notes += n
        bp = sorted(set(V_PREFIX.findall(whole)))
        if bp:
            fails.append("HTML 母版全文出现 V 前缀版本号 %s" % "、".join(x.strip() for x in bp))
    ms = os.path.join(ROOT, MD)
    if os.path.exists(ms):
        bp = sorted(set(V_PREFIX.findall(io.open(ms, encoding="utf-8").read())))
        if bp:
            fails.append("md 母版出现 V 前缀版本号 %s" % "、".join(x.strip() for x in bp))
    return fails, notes


# --selftest：两个已知坏样本必须红、当前真封面必须绿（presence 检查当年就是靠「永远绿」放走了 V1.0）
SELFTEST_SAMPLES = [
    ("bad-v-prefix", "三生输入法 V1.0<br>操作说明书\n<tr><th>版本号</th><td>V1.0</td></tr>", True),
    ("bad-bare-minor", "三生输入法 操作说明书\n<tr><th>版本号</th><td>1.0</td></tr>", True),
    ("good", "三生输入法 1.0.0<br>操作说明书\n<tr><th>版本号</th><td>1.0.0</td></tr>", False),
]


def selftest():
    print("== 第 5 条判据自测（已知坏样本必须变红） ==")
    bad = 0
    for name, sample, expect_fail in SELFTEST_SAMPLES:
        f, _ = version_findings(sample, "样本 %s" % name)
        got = bool(f)
        ok = got == expect_fail
        if not ok:
            bad += 1
        print("  [%s] %s：期望%s／实际%s%s"
              % ("OK  " if ok else "FAIL", name,
                 "红" if expect_fail else "绿", "红" if got else "绿",
                 "" if ok else "（" + "；".join(f) + "）"))
    real = cover_from_generator()
    if real is None:
        print("  [FAIL] 真封面抓不到")
        bad += 1
    else:
        f, _ = version_findings(real, "真封面")
        if f:
            bad += 1
        print("  [%s] 真 COVER：期望绿／实际%s" % ("OK  " if not f else "FAIL", "红" if f else "绿"))
    print("自测 %d 例，未按预期触发 %d" % (len(SELFTEST_SAMPLES) + 1, bad))
    return 1 if bad else 0



def find_dates(text):
    out = []
    for pat in DATE_PATTERNS:
        for m in pat.finditer(text):
            y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
            try:
                out.append((m.group(0), datetime.date(y, mo, d)))
            except ValueError:
                pass
    return out


def check_md():
    fails, notes = [], []
    s = io.open(os.path.join(ROOT, MD), encoding="utf-8").read()

    # 1. 页眉：软件名 + 版本号
    if SOFTWARE_NAME not in s:
        fails.append("文档里找不到软件名称「%s」——页眉左上角必须标注且与申请表一致" % SOFTWARE_NAME)
    else:
        notes.append("软件名称「%s」在文档中 ✔" % SOFTWARE_NAME)
    if VERSION not in s:
        fails.append("文档里找不到版本号「%s」——页眉必须与申请表版本号一致" % VERSION)
    else:
        notes.append("版本号「%s」在文档中 ✔" % VERSION)

    # 2. 页码由生成器负责，这里只提示
    notes.append("页码（1..N 连续）由 build_copyright_manual.py 打印时生成，需在 PDF 里目视确认")

    # 3. 日期不得晚于开发完成日期
    late = [(t, d) for t, d in find_dates(s) if d > COMPLETION_DATE]
    if late:
        fails.append("文档中出现晚于「开发完成日期 %s」的日期：%s —— 官方要求文档内日期不得晚于开发完成日期"
                     % (COMPLETION_DATE, ", ".join(t for t, _ in late)))
    else:
        notes.append("文档内日期均不晚于开发完成日期 %s ✔（0 处命中）" % COMPLETION_DATE)

    # 4. 作者姓名/笔名（排除「开发者/著作权人」登记项所在行）
    author_hits = []
    for i, ln in enumerate(s.split("\n"), 1):
        if re.search(r"Qoder|CodeArts|AI 生成|人工智能生成", ln):
            author_hits.append("L%d 出现内部署名：%s" % (i, ln[:50]))
    if author_hits:
        fails.append("文档出现内部署名（软著材料不能出现代理/工具署名）：" + "；".join(author_hits))
    else:
        notes.append("无内部署名（Qoder/CodeArts/AI 生成）✔")

    # 5. 页数提示（md 行数粗估，真正页数以 PDF 为准）
    lines = len([l for l in s.split("\n") if l.strip()])
    notes.append("md 非空行 %d（PDF 实际页数用 --pdf 查）" % lines)

    # 6. 版本号字面量一致性（10-28 补正后新增；查的是生成器封面，不是这份 md）
    f6, n6 = check_version_literals()
    fails += f6
    notes += n6
    return fails, notes


def pdf_page1_text():
    """PDF 第 1 页文字（补正栽的就是第 1 页）。poppler 缺 CJK CMap，走 PyMuPDF。"""
    try:
        import pymupdf
    except ImportError:
        return None
    p = os.path.join(ROOT, PDF)
    if not os.path.exists(p):
        return None
    try:
        d = pymupdf.open(p)
        t = d[0].get_text()
        d.close()
        return t
    except Exception:
        return None


def check_pdf():
    fails, notes = [], []
    p = os.path.join(ROOT, PDF)
    if not os.path.exists(p):
        fails.append("PDF 不存在：%s（先跑 build_copyright_manual.py + Chrome 无头打印）" % PDF)
        return fails, notes
    data = io.open(p, "rb").read()
    if len(data) > PDF_MAX_BYTES:
        fails.append("PDF %.1f MB 超过 10 MB 上限，需压缩或拆分" % (len(data) / 1048576.0))
    else:
        notes.append("PDF %.2f MB ✔（≤10 MB）" % (len(data) / 1048576.0))
    pages = len(re.findall(rb"/Type\s*/Page[^s]", data))
    if pages < MIN_PAGES:
        fails.append("PDF 只有 %d 页，低于建议值 %d 页（H-152：官方底线 10 页、建议 ≥20 页，"
                     "补写清单见 docs/release/copyright/manual-expansion-tasklist.md）" % (pages, MIN_PAGES))
    else:
        notes.append("PDF %d 页 ✔（≥%d 页建议值）" % (pages, MIN_PAGES))
    t1 = pdf_page1_text()
    if t1 is None:
        notes.append("PDF 第 1 页文字未取到（缺 PyMuPDF 或文件读不动）——版本号一致性只在封面源上判过")
    else:
        f, n = version_findings(t1, "PDF 第 1 页")
        fails += f
        notes += n
    return fails, notes


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", action="store_true")
    ap.add_argument("--selftest", action="store_true", help="用已知坏样本验第 5 条判据会红")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    print("== 软著《操作说明书》格式自检（只读） ==")
    fails, notes = check_md()
    for n in notes:
        print("  [OK  ] %s" % n)
    if a.pdf:
        f2, n2 = check_pdf()
        for n in n2:
            print("  [OK  ] %s" % n)
        fails += f2
    if fails:
        print("结论：%d 项有风险，提审前必须处理" % len(fails))
        for f in fails:
            print("  [FAIL] %s" % f)
        return 1
    print("结论：通过")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
