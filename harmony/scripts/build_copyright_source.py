#!/usr/bin/env python3
"""Build the software-copyright source-code document (front 30 + back 30 pages).

Rules used here:
- Only self-authored ArkTS/C++ application source is included.
- Third-party libraries, Rime data, build scripts, probes and mocks are excluded.
- 50 source lines per page; A4 portrait; page header with software name/version.
- If the concatenated source exceeds 60 pages, submit the first 30 and last 30 pages.
"""

from __future__ import annotations

import hashlib
import html
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "release" / "copyright"

SOFTWARE = "三生输入法"
VERSION = "1.0.0"  # 2026-10-27 20:xx 与安装包 versionName 及易版权表单「版本号」统一
APP_VERSION = "1.0.0"
PACKAGE = "com.sansheng.ime"
PAGE_LINES = 50
FRONT_PAGES = 30
BACK_PAGES = 30

SOURCES = [
    "entry/src/main/ets/inputmethod/InputMethodService.ets",
    "entry/src/main/ets/inputmethod/KeyboardController.ets",
    "entry/src/main/ets/pages/KeyboardIndex.ets",
    "entry/src/main/ets/pages/AboutPage.ets",
    "entry/src/main/ets/engine/EngineProvider.ets",
    "entry/src/main/ets/engine/RimeEngine.ets",
    "entry/src/main/ets/engine/RealRimeEngine.ets",
    "entry/src/main/ets/engine/RimeDataInstaller.ets",
    "entry/src/main/ets/entryability/EntryAbility.ets",
    "entry/src/main/ets/common/PrivacyConsent.ets",
    "entry/src/main/ets/common/SettingsModels.ets",
    "entry/src/main/ets/pages/Index.ets",
    "entry/src/main/ets/pages/LegalPage.ets",
    "entry/src/main/ets/components/ToolPanels.ets",
    "entry/src/main/cpp/fanxing_napi.cpp",
]

EXCLUDED = [
    ("fanxing_rime_har/**", "上游 MIT 引擎工程，非本项目原创"),
    ("**/build/**", "构建产物，不是源程序"),
    ("entry/src/main/cpp/include/**", "上游头文件（librime/opencc/marisa/leveldb/yaml-cpp），非本项目原创"),
    ("entry/src/main/cpp/lib/**", "预编译上游库（.a/.so），不是源程序"),
    ("entry/src/main/resources/rawfile/rime/**", "第三方词库与方案数据，不属于源程序"),
    ("entry/src/main/resources/rawfile/legal/**", "法律文本，不属于源程序"),
    ("entry/src/main/ets/pages/M3Probe.ets", "调试探针，不属于产品功能"),
    ("entry/src/main/ets/pages/LandscapeProbe.ets", "调试探针，不属于产品功能"),
    ("entry/src/main/ets/engine/MockRimeEngine.ets", "测试用 Mock，不属于产品实现"),
    # 2026-10-23 02:0x 补：这两个页面此前既不在 SOURCES 也不在这里 ⇒ 属「静默漏掉」。
    # 实测依据：main_pages.json 注册了它们（随包编译），但 Index.ets 的 openSettings()
    # 在 entry/src/main 全目录 0 处调用（H-090 定案：1.0.0 摘掉应用内设置入口），说明书也未描述这两页。
    ("entry/src/main/ets/pages/SettingsPage.ets",
     "设置主页：1.0.0 已摘掉入口，随包但未挂载，说明书未描述"),
    ("entry/src/main/ets/pages/SettingsCategoryPage.ets",
     "设置分类页：同上，1.0.0 未挂载，说明书未描述"),
    ("scripts/**", "构建与验证脚本，不属于应用源程序"),
    ("entry/src/test/**、entry/src/ohosTest/**", "测试代码，不属于产品实现"),
]

CSS = """
@page { size: A4 portrait; margin: 0; }
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; background: #e9edf2; }
body {
  font-family: "Courier New", Consolas, "HarmonyOS Sans SC", monospace;
  color: #111;
}
.page {
  width: 210mm; min-height: 297mm; margin: 0 auto 10mm; padding: 14mm 12mm 10mm;
  background: #fff; box-shadow: 0 1px 5px rgba(0,0,0,.18);
  page-break-after: always; break-after: page;
}
.page:last-child { page-break-after: auto; break-after: auto; }
.run {
  display: flex; justify-content: space-between; align-items: baseline;
  font-family: "HarmonyOS Sans SC", "Microsoft YaHei", sans-serif;
  font-size: 9pt; color: #222; border-bottom: 0.6pt solid #777; padding-bottom: 2mm;
}
.file {
  font-family: "HarmonyOS Sans SC", "Microsoft YaHei", sans-serif;
  font-size: 7.5pt; color: #555; margin: 2mm 0 1.5mm;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.code { margin: 0; font-size: 7.2pt; line-height: 1.3; }
.ln { display: flex; align-items: flex-start; }
.no {
  flex: 0 0 11mm; text-align: right; padding-right: 2.5mm;
  color: #888; user-select: none;
}
.tx { flex: 1; white-space: pre-wrap; word-break: break-all; }
.foot {
  display: flex; justify-content: space-between;
  font-family: "HarmonyOS Sans SC", "Microsoft YaHei", sans-serif;
  font-size: 7.5pt; color: #666; border-top: 0.5pt solid #bbb;
  margin-top: 3mm; padding-top: 1.5mm;
}
.note { font-family: "HarmonyOS Sans SC", "Microsoft YaHei", sans-serif; font-size: 8pt; color: #444; }
@media print {
  html, body { background: #fff; }
  .page { margin: 0; box-shadow: none; width: 210mm; min-height: 297mm; }
}
"""


@dataclass
class Line:
    path: str
    file_line: int
    text: str
    global_line: int = 0


def load_lines() -> list[Line]:
    lines: list[Line] = []
    for rel in SOURCES:
        path = ROOT / rel
        if not path.exists():
            raise SystemExit(f"missing source: {rel}")
        for idx, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            text = raw.expandtabs(2).rstrip()
            lines.append(Line(rel, idx, text))
    for n, line in enumerate(lines, start=1):
        line.global_line = n
    return lines


def paginate(lines: list[Line]) -> tuple[list[list[Line]], str, int, int]:
    total = len(lines)
    capacity = PAGE_LINES * (FRONT_PAGES + BACK_PAGES)
    if total <= capacity:
        pages = [lines[i:i + PAGE_LINES] for i in range(0, total, PAGE_LINES)]
        return pages, "全部源码", 1, total
    front = lines[:FRONT_PAGES * PAGE_LINES]
    back = lines[-BACK_PAGES * PAGE_LINES:]
    pages = [front[i:i + PAGE_LINES] for i in range(0, len(front), PAGE_LINES)]
    pages += [back[i:i + PAGE_LINES] for i in range(0, len(back), PAGE_LINES)]
    return pages, "前 30 页 + 后 30 页", back[0].global_line, total


def render_page(page: list[Line], page_no: int, page_count: int, part: str,
                part_page: str) -> str:
    paths: list[str] = []
    for line in page:
        if not paths or paths[-1] != line.path:
            paths.append(line.path)
    if len(paths) == 1:
        file_label = paths[0]
    else:
        file_label = f"{paths[0]} 等 {len(paths)} 个文件"
    rows = []
    for line in page:
        rows.append(
            '<div class="ln"><span class="no">%d</span><span class="tx">%s</span></div>'
            % (line.global_line, html.escape(line.text))
        )
    return f"""<section class="page">
<div class="run"><span>{SOFTWARE} {VERSION} 源程序</span><span>第 {page_no} 页 / 共 {page_count} 页</span></div>
<div class="file">文件：{html.escape(file_label)}</div>
<pre class="code">{''.join(rows)}</pre>
<div class="foot"><span>每页 50 行 · {part_page}</span><span>{SOFTWARE} {VERSION}</span></div>
</section>"""


def build_html(pages: list[list[Line]], part: str) -> str:
    def page_part(index: int) -> str:
        if part == "全部源码":
            return "全部源码"
        return "前 30 页" if index <= FRONT_PAGES else "后 30 页"

    body = "\n".join(
        render_page(page, i, len(pages), part, page_part(i))
        for i, page in enumerate(pages, start=1)
    )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{SOFTWARE} {VERSION} 源程序</title>
<style>{CSS}</style>
</head>
<body>
{body}
</body>
</html>
"""


def build_txt(pages: list[list[Line]], part: str) -> str:
    out = [f"{SOFTWARE} {VERSION} 源程序（{part}，每页 50 行）", ""]
    for page_no, page in enumerate(pages, start=1):
        label = "全部源码" if part == "全部源码" else ("前 30 页" if page_no <= FRONT_PAGES else "后 30 页")
        out.append(f"===== 第 {page_no} 页 / 共 {len(pages)} 页（{label}）=====")
        out.append(f"文件：{page[0].path}")
        for line in page:
            out.append(f"{line.global_line:6d}  {line.text}")
        out.append("")
    return "\n".join(out)


def build_manifest(lines: list[Line], pages: list[list[Line]], part: str,
                   back_start: int, total: int, html_text: str, txt_text: str) -> str:
    rows = []
    for rel in SOURCES:
        count = sum(1 for line in lines if line.path == rel)
        rows.append(f"| `{rel}` | {count} |")
    excluded = "\n".join(f"- `{path}`：{reason}" for path, reason in EXCLUDED)
    digest_html = hashlib.sha256(html_text.encode("utf-8")).hexdigest()
    digest_txt = hashlib.sha256(txt_text.encode("utf-8")).hexdigest()
    return f"""# 软件著作权源程序文档说明

| 项 | 内容 |
|---|---|
| 软件名称 | {SOFTWARE} |
| 版本号 | {VERSION} |
| 对应应用版本 | {APP_VERSION}（包名 `{PACKAGE}`） |
| 生成日期 | {date.today().isoformat()} |
| 源文件数 | {len(SOURCES)} |
| 源码总行数 | {total} |
| 提交页数 | {len(pages)} |
| 每页行数 | {PAGE_LINES} |
| 选取方式 | {part} |
| 后 30 页起始全局行号 | {back_start if part != "全部源码" else 1} |

## 一、包含的源文件

| 文件 | 行数 |
|---|---:|
{chr(10).join(rows)}

## 二、未包含的内容与原因

{excluded}

## 三、文档说明

1. 源程序按「输入法服务 → 键盘控制器 → 键盘界面 → 关于页 → 引擎接口 → 真实引擎 → 数据安装器 → NAPI 桥」顺序连续拼接，全局行号连续。
2. 源码总行数超过 60 页，按登记要求提交**前 30 页 + 后 30 页**，每页 50 行；后 30 页从全局第 {back_start if part != "全部源码" else 1} 行开始。
3. 页面为 A4 纵向，页眉含软件名称、版本与页码，页脚标注「每页 50 行」；超长代码行自动换行，不截断源码。
4. 文档仅包含本项目自研 ArkTS/C++ 源码；不包含上游第三方库、词库数据、测试/探针与构建脚本。UI 与桥接文件头部保留了对 Apache-2.0 / MIT 参考项目的改动与署名声明，符合许可证要求。

## 四、打印方式

- 打开 `source-code.html`，浏览器打印，纸张 A4 纵向，缩放 100%，不要勾选「适应页面」。
- 建议双面打印；如登记机构要求单面，按单面提交。
- 打印后核对页码连续、每页 50 行、页眉页脚完整。

## 五、文件校验

- `source-code.html` SHA-256：`{digest_html}`
- `source-code.txt` SHA-256：`{digest_txt}`
"""


SKIP_DIRS = {".git", ".hvigor", ".idea", ".cxx", "build", "node_modules", "oh_modules",
             "__pycache__", "resources"}


def _pattern_rx(pat: str):
    """把清单里的 glob 翻成正则：** ⇒ 任意层级，* ⇒ 单层内任意字符。"""
    out, i = [], 0
    while i < len(pat):
        if pat.startswith("**", i):
            out.append(".*")
            i += 2
        elif pat[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pat[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pat[i]))
            i += 1
    return re.compile("^" + "".join(out) + "$")


def _excluded_rxs() -> list:
    pats = []
    for path, _reason in EXCLUDED:
        pats.extend([p.strip() for p in path.split("、") if p.strip()])
    return [_pattern_rx(p) for p in pats]


def _scan_tree() -> list[str]:
    """扫全仓库的 .ets/.cpp（相对 posix 路径），构建产物与被裁掉的目录不进扫描。"""
    found = []
    for root, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        rel_root = Path(root).relative_to(ROOT).as_posix()
        if rel_root == ".":
            rel_root = ""
        for f in files:
            if f.endswith((".ets", ".cpp")):
                rel = f"{rel_root}/{f}" if rel_root else f
                found.append(rel)
    return sorted(found)


def _live_count(rel: str) -> int:
    p = ROOT / rel
    if not p.exists():
        return -1
    return len(p.read_text(encoding="utf-8", errors="replace").splitlines())


def _manifest_declared() -> dict[str, int]:
    """从已提交的 source-code-manifest.md 读回「当时登记的每个文件行数」。"""
    p = OUT / "source-code-manifest.md"
    if not p.exists():
        return {}
    table = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\|\s*`([^`]+)`\s*\|\s*(\d+)\s*\|$", line.strip())
        if m:
            table[m.group(1)] = int(m.group(2))
    return table


def check_coverage(strict: bool = False) -> int:
    """不生成文档，只回答两个问题：① 有没有源码文件既没进清单也没写「为什么不含」；
    ② 已打印的那套文档还配不配得上现在的代码。

    2026-10-23 02:0x 加这条的原因：SOURCES 是硬编码白名单，昨天 03:57 那版 PDF
    就静默漏了 5 个真实模块（README 有记录），今天实测又抓到 2 个未声明的文件。
    判据用「已知坏样本」验过：当前工作树必须报出来，补进 EXCLUDED 后才转干净。
    """
    tree = _scan_tree()
    rx = _excluded_rxs()
    declared_excluded, undeclared, missing = [], [], []
    for rel in tree:
        if rel in SOURCES:
            continue
        if any(p.match(rel) for p in rx):
            declared_excluded.append(rel)
        else:
            undeclared.append(rel)
    for rel in SOURCES:
        if not (ROOT / rel).exists():
            missing.append(rel)

    table = _manifest_declared()
    drift = []
    if table:
        for rel, was in sorted(table.items()):
            now = _live_count(rel)
            if now != was:
                drift.append((rel, was, now))
    total_now = sum(_live_count(r) for r in SOURCES)
    back_start = total_now - PAGE_LINES * BACK_PAGES + 1

    print("扫描 .ets/.cpp：%d 个 ⇒ 清单内 %d / 已声明不含 %d / 未声明 %d / 清单里但文件已不在 %d"
          % (len(tree), len(SOURCES), len(declared_excluded), len(undeclared), len(missing)))
    for rel in undeclared:
        print("  [未声明] %s（%d 行）—— 既不在 SOURCES，也没在 EXCLUDED 写理由" % (rel, _live_count(rel)))
    for rel in missing:
        print("  [已消失] %s —— 清单还写着它，文件却没了" % rel)
    if table:
        print("已打印文档登记的 %d 个文件 / %d 行；当前实际 %d 行 ⇒ 行数漂移 %d 个文件"
              % (len(table), sum(table.values()), total_now, len(drift)))
        for rel, was, now in drift:
            print("  [漂移] %-58s %5d -> %5d (%+d)" % (rel, was, now, now - was))
        print("  后 %d 页起始全局行号：文档口径 %d，当前应为 %d"
              % (BACK_PAGES, sum(table.values()) - PAGE_LINES * BACK_PAGES + 1, back_start))
    else:
        print("没有可读的 source-code-manifest.md，跳过漂移比对")
    try:
        head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True).stdout.strip()
        dirty = [l for l in subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain", "--", "entry/src"],
                                           capture_output=True, text=True).stdout.splitlines() if l.strip()]
        print("代码树指纹：HEAD %s，entry/src 未提交改动 %d 个文件" % (head or "?", len(dirty)))
    except Exception as exc:  # git 不可用时不阻断
        print("git 指纹读取失败（不影响上面两项判据）：%s" % exc)

    fail = bool(undeclared or missing)
    if drift and strict:
        fail = True
    print("结论：%s" % ("不通过（有未声明/已消失的文件%s）"
                        % ("、且文档与代码不同步" if drift and strict else "") if fail else "通过"))
    return 1 if fail else 0


def main() -> None:
    args = sys.argv[1:]
    if "--check" in args:
        raise SystemExit(check_coverage(strict="--strict" in args))
    OUT.mkdir(parents=True, exist_ok=True)
    lines = load_lines()
    pages, part, back_start, total = paginate(lines)
    html_text = build_html(pages, part)
    txt_text = build_txt(pages, part)
    (OUT / "source-code.html").write_text(html_text, encoding="utf-8", newline="\n")
    (OUT / "source-code.txt").write_text(txt_text, encoding="utf-8", newline="\n")
    manifest = build_manifest(lines, pages, part, back_start, total, html_text, txt_text)
    (OUT / "source-code-manifest.md").write_text(manifest, encoding="utf-8", newline="\n")
    print(f"total lines: {total}")
    print(f"pages: {len(pages)} ({part})")
    print(f"back start line: {back_start}")
    print(f"html: {len(html_text)} chars; txt: {len(txt_text)} chars")


if __name__ == "__main__":
    main()
