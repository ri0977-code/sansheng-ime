"""
提审包（.app）内容核验 —— 把 docs/release/app-content-checklist.md 的清单变成可执行断言。
现 18 条（① ~ ⑮ ＋派生 9b/4b/16b）；清单里的 ⑯「桌面真看得见图标」是人工/真机项，脚本测不了。

用法：
    python scripts/check_app_content.py [.app 路径]
    python scripts/check_app_content.py --allow-fail   # 只报告，不以失败退出

为什么需要它：构建绿、签名成功、文件存在，都不等于包内容是对的。
2026-10-22 13:25 那份 .app 签名有效、能装能用，但里面同时有要清掉的第三方文件、
缺掉的拼音修复、和一句与实测不符的隐私承诺。每次重打都按同一张表核一遍。
"""
import argparse
import io
import os
import sys
import zipfile

# 控制台编码：PowerShell 重定向/管道下 Python 用本地代码页（这台机器是 GBK），
# 输出里的「⇒」「←」会抛 UnicodeEncodeError，把整条提审闸门打成异常退出。
# 统一切到 UTF-8 并对写不出的字符降级，保证「打印」永远不可能掩盖真实检查结果。
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

DEFAULT_APP = "entry/build/default/outputs/default/sansheng-ime-1.0.0-release.app"
DEFAULT_HAP = "entry/build/default/outputs/default/entry-default-unsigned.hap"

def _regen(kind):
    """用仓库里当前的源文件现场重跑生成器，返回 {文件名: 文本}。

    用途：内容闸门要能判「包里的 notice.html / privacy.html / terms.html 是不是用当前
    NOTICE、LICENSES/、docs/release/legal/*.md 生成的」。只看「页面存在 + 有关键词」
    挡不住这一类：改了源文件忘了重跑生成器，包里就带着旧的对外声明出包，
    而公示版和应用内版还互相对得上（⑦ 的原判据看不出来）。

    kind="notice" → {"notice.html": ...}；kind="legal" → {"privacy.html":..., "terms.html":...}
    生成器跑不起来时抛异常，由调用方按阻断处理（判不了同源就不许出包）。
    """
    import contextlib
    import importlib.util
    import tempfile
    from pathlib import Path

    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    tmp = tempfile.mkdtemp(prefix="sansheng-gate-regen-")
    quiet = io.StringIO()

    names = ("privacy.html", "terms.html")
    if kind == "notice":
        spec = importlib.util.spec_from_file_location(
            "_gate_notice_gen", os.path.join(scripts_dir, "build_notice_html.py"))
        g = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(g)
        out = os.path.join(tmp, "notice.html")
        g.OUT = out
        with contextlib.redirect_stdout(quiet):
            g.main()
        return {"inapp": {"notice.html": io.open(out, encoding="utf-8").read()}}

    spec = importlib.util.spec_from_file_location(
        "_gate_legal_gen", os.path.join(scripts_dir, "build_legal_html.py"))
    g = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(g)
    inapp = Path(tmp) / "inapp"
    hosted = Path(tmp) / "hosted"
    inapp.mkdir(parents=True, exist_ok=True)
    hosted.mkdir(parents=True, exist_ok=True)
    g.INAPP_DIR = inapp
    g.OUT_DIR = hosted
    with contextlib.redirect_stdout(quiet):
        g.main()
    # 两套产物分开返回：build() 出的是 AGC 公示版（带 nav/footer/草案横幅），
    # build_inapp() 出的是应用内版，两者正文一致但页面外壳不同，混比一定误报。
    return {"inapp": dict((n, (inapp / n).read_text(encoding="utf-8")) for n in names),
            "hosted": dict((n, (hosted / n).read_text(encoding="utf-8")) for n in names)}


# (名称, 是否阻断提审, 说明)
CHECKS = []


def check(name, blocking=True, why=""):
    def deco(fn):
        CHECKS.append((name, blocking, why, fn))
        return fn
    return deco


class Ctx:
    """接受两种输入：提审用 .app（外层 zip 里套 entry-default.hap），
    或裸 HAP（debug 构建的 entry-default-unsigned.hap）。

    为什么要支持裸 HAP：布局/数据改动后的第一道验收必须能在**还没签名**时跑，
    否则要等到第 4 站才发现内容不对，白跑一圈构建+签名。"""

    def __init__(self, path):
        self.app_path = path
        self.inner_hap_name = None
        z = zipfile.ZipFile(path)
        names = z.namelist()
        haps = [n for n in names if n.endswith(".hap")]
        if haps:
            # .app: 取出内层 HAP 再解析
            self.app = z
            self.outer = names
            self.inner_hap_name = haps[0]
            self.hap_bytes = z.read(self.inner_hap_name)
            self.hap = zipfile.ZipFile(io.BytesIO(self.hap_bytes))
        else:
            # 裸 HAP: 直接就是我们要查的那棵树
            self.app = None
            self.outer = names
            self.hap = z
            self.hap_bytes = open(path, "rb").read()
        self.names = self.hap.namelist()

    def read(self, suffix):
        hits = [n for n in self.names if n.endswith(suffix)]
        if not hits:
            raise FileNotFoundError(suffix)
        return self.hap.read(hits[0])

    def read_text(self, suffix):
        return self.read(suffix).decode("utf-8", "replace")

    def ui_blob(self):
        """界面文案载体：包内就是 modules.abc（编译后的字符串表）。"""
        abc = [n for n in self.names if n.endswith("modules.abc")]
        if not abc:
            raise FileNotFoundError("modules.abc")
        return self.hap.read(abc[0])


class SrcCtx:
    """源码级上下文：同一张表（18 条断言），跑在**工作区源码**上，而不是包上。

    为什么要有这一层：13:25 那份 .app 落后于当前源码（源码后来把 symbols 并进
    default.yaml、补了 notice.html、换了图标），拿旧包判一次「10 项阻断」会把
    「已经改好的」和「还没改的」混在一起，CodeArts 接到的活就会跑偏。
    源码级这一遍先把两拨分开，省掉一轮构建。

    口径纪律：源码里**测不出来**的项（打包后才有的 modules.abc）必须显式写成
    「须构建后核」，不许悄悄当成通过 —— grep-0 ≠ 提审过。"""

    # 源码里与包内路径的对应关系（后缀匹配，取唯一命中）
    SPECIAL = {
        # 包内 module.json 是 module.json5 + app.json5 的合并结果（versionName 来自 app.json5）
        "module.json": ["entry/src/main/module.json5", "AppScope/app.json5"],
    }
    ROOTS = [
        "entry/src/main/resources",
        "entry/src/main",
        "AppScope/resources",
        "AppScope",
    ]

    def __init__(self, root):
        self.root = root
        self.app_path = None
        self.inner_hap_name = None
        self.app = None
        self.outer = []
        self.hap = None
        self.hap_bytes = b""
        files = []
        for r in self.ROOTS:
            base = os.path.join(root, r)
            for dirpath, _dirs, names in os.walk(base):
                for n in names:
                    full = os.path.join(dirpath, n)
                    rel = os.path.relpath(full, root).replace("\\", "/")
                    files.append(rel)
        self.files = files
        # 检查 1 用的名字表：只保留会被检查点到的那几类
        self.names = [f for f in files
                      if "/rawfile/" in f or f.endswith("main_pages.json")
                      or f.endswith(".json5") or "/media/" in f]

    def _full(self, suffix):
        if suffix in self.SPECIAL:
            for rel in self.SPECIAL[suffix]:
                p = os.path.join(self.root, rel)
                if os.path.exists(p):
                    return p
            raise FileNotFoundError(suffix)
        hits = [f for f in self.files if f.endswith(suffix)]
        if not hits:
            raise FileNotFoundError(suffix)
        hits.sort(key=lambda f: (len(f), f))
        return os.path.join(self.root, hits[0])

    def read(self, suffix):
        if suffix == "module.json":
            # 合并两份 json5，模拟打包后的 module.json
            buf = []
            for rel in self.SPECIAL["module.json"]:
                buf.append(open(os.path.join(self.root, rel), "rb").read())
            return b"\n".join(buf)
        with open(self._full(suffix), "rb") as f:
            return f.read()

    def read_text(self, suffix):
        return self.read(suffix).decode("utf-8", "replace")

    def ui_blob(self):
        """界面文案载体：包内是 modules.abc，源码级用 ets + string 资源近似。

        abc 由这些源文件编译而来，所以源码级查同一批字符串是等价的；
        但**最终仍须在包上复核**（脚本会在该两项后标注）。"""
        buf = []
        ets_root = os.path.join(self.root, "entry/src/main/ets")
        for dirpath, _dirs, names in os.walk(ets_root):
            for n in names:
                if n.endswith(".ets"):
                    buf.append(open(os.path.join(dirpath, n), "rb").read())
        strf = os.path.join(self.root, "entry/src/main/resources/base/element/string.json")
        if os.path.exists(strf):
            buf.append(open(strf, "rb").read())
        return b"\n".join(buf)


@check("1. 不含上游符号文件 symbols.yaml / symbols.custom.yaml", True,
       "D-020：这两个文件上游无许可，1.0.0 不得随包")
def _c1(c):
    bad = [n for n in c.names if n.endswith(("rime/symbols.yaml", "rime/symbols.custom.yaml"))]
    return (not bad), ("包内仍含: " + ", ".join(bad)) if bad else "已移除"


@check("2. 斜杠符号已并入自有 default.yaml（9 组）", True,
       "D-020-A 的合并结果必须真的在包里")
def _c2(c):
    import yaml
    raw = c.read("rawfile/rime/default.yaml")
    doc = yaml.safe_load(raw)
    sym = (doc.get("punctuator") or {}).get("symbols") or {}
    n = len(sym)
    return (n >= 9), "punctuator/symbols 组数=%d（要求 ≥9）" % n


@check("3. default.yaml 通过标准 YAML 解析", True, "H-093：不能只靠引擎容错")
def _c3(c):
    import yaml
    try:
        yaml.safe_load(c.read("rawfile/rime/default.yaml"))
        return True, "yaml.safe_load PASS"
    except Exception as e:
        return False, "yaml.safe_load FAIL: %s" % str(e).replace("\n", " ")[:120]


# D-033（Qoder 2026-10-30）：第 4 项的判据从「punctuator 数组含中文引号」改成「符号面板格子里有中文引号」。
# 为什么必须改（不是判据写松了，是承载物换了）：
#   · 原判据是 H-093 时期写的，属性＝「1.0.0 必须能打中文引号」。
#   · CodeArts 的 h275（M-368）把 `half_shape` 里 `' " ` _ # $ ^ [ ]` 9 个符号从**多候选数组压成单值**，
#     因为 librime 只要值是 list 就弹候选菜单（长度 1 也弹）——不压就没法一键直出。
#     主人已真机验过压后的行为（M-369：9 个键逐条 `menu=0 num=0`、正文原样落字）。
#   · 中文引号真正的产品入口是符号面板「常用」页的 “ ” ‘ ’ 「 」 格子：多字节 UTF-8 ⇒
#     走 `fanxing_napi.cpp` 的「直接上屏、不进引擎」分支，与 punctuator 是两条独立路径。
#     2026-10-30 06:48–06:53 Mate 80 逐格点验：每点一格、正文恰好多一个对应字符，无菜单、不需空格
#     （证据 docs/evidence/2026-10-30/h280-quote/）。
#   ⇒ 恢复数组＝为满足一条旧判据去破坏主人刚验过的一键直出。所以改判属性本身，另加 4b 反向守卫。
QUOTE_CELLS = ["“", "”", "‘", "’", "「", "」"]          # 常用页第 0 页必须有的六格
PANEL_PAGE_CELLS = 19                                     # KeyboardIndex：每页 19 格（7+6+6）
PANEL_SCALARS = ["'", '"', "`", "_", "#", "$", "^", "[", "]"]   # M-368 压成单值的那 9 个


@check("4. 中文引号一键可打（符号面板「常用」页第 0 页含 “ ” ‘ ’ 「 」）", True,
       "H-093 的属性＝1.0.0 必须能打中文引号；D-033 起承载物是面板格子，不再是 punctuator 数组")
def _c4(c):
    import json
    problems = []
    try:
        raw = c.read_text("symbols/symbols.json")
    except FileNotFoundError:
        raw = None
        problems.append("包内没有 rawfile/symbols/symbols.json")
    if raw is not None:
        try:
            groups = (json.loads(raw) or {}).get("groups") or []
        except Exception as e:
            groups = []
            problems.append("symbols.json 解析失败: %s" % str(e)[:80])
        grp = None
        for g in groups:
            if (g or {}).get("id") == "common" or (g or {}).get("label") == "常用":
                grp = g
                break
        if grp is None and groups:
            grp = groups[0]
        if grp is None:
            problems.append("symbols.json 没有 groups")
        else:
            items = grp.get("items") or []
            page0 = items[:PANEL_PAGE_CELLS]
            miss = [x for x in QUOTE_CELLS if x not in page0]
            if miss:
                problems.append("「%s」组第 0 页（前 %d 格）缺 %s ⇒ 不划页打不出"
                                % (grp.get("label"), PANEL_PAGE_CELLS, miss))
    # 回落表：symbols.json 万一读不到时 UI 用的是写死那张（KeyboardIndex.FALLBACK_SYMBOL_GROUPS），
    # 它编译进 modules.abc ⇒ 查 ui_blob 才是「包内真的有」而不是「源码里有」。
    blob = c.ui_blob()
    miss2 = [x for x in QUOTE_CELLS if x.encode("utf-8") not in blob]
    if miss2:
        problems.append("编译产物里找不到中文引号 %s ⇒ 回落路径也打不出" % miss2)
    return (not problems), ("；".join(problems) if problems else
                            "面板「常用」页第 0 页含 %s；回落表（ui_blob）同样含这 6 个字符"
                            % " ".join(QUOTE_CELLS))


@check("4b. 面板 9 符号仍是单值 + 多字节直出链在位（D-033 反向守卫）", True,
       "M-369 主人真机验过的一键直出不能悄悄退化：数组加回来＝点一下弹菜单、不出字")
def _c4b(c):
    import yaml
    problems = []
    doc = yaml.safe_load(c.read("rawfile/rime/default.yaml"))
    hs = (doc.get("punctuator") or {}).get("half_shape") or {}
    back_to_list = [k for k in PANEL_SCALARS if isinstance(hs.get(k), list)]
    absent = [k for k in PANEL_SCALARS if k not in hs]
    if back_to_list:
        problems.append("half_shape 里 %s 又变回候选数组 ⇒ 点一下不直出" % back_to_list)
    if absent:
        problems.append("half_shape 缺 %s" % absent)
    # 下面两条在 native/ets 源里，包里查不出来（modules.abc/libso 里没有可判的锚点），
    # 所以按**工作区源码**判，并在结论里写清这一点：包内实际行为由真机证据覆盖。
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for rel, anchor, what in (
            ("entry/src/main/cpp/fanxing_napi.cpp", "key.size() > 1",
             "多字节面板字「直接上屏、不进引擎」分支"),
            ("entry/src/main/ets/pages/KeyboardIndex.ets", "this.typeChar(ch)",
             "符号格 onClick → typeChar 路由")):
        p = os.path.join(root, rel)
        if not os.path.exists(p):
            problems.append("%s 不存在 ⇒ 判不了「%s」" % (rel, what))
            continue
        if anchor not in io.open(p, encoding="utf-8", errors="replace").read():
            problems.append("%s 里找不到 %r ⇒「%s」可能被改掉" % (rel, anchor, what))
    return (not problems), ("；".join(problems) if problems else
                            "9 个面板符号仍是单值；直出分支与 typeChar 路由在位（源码级，"
                            "包内行为见 docs/evidence/2026-10-30/h280-quote/）")



@check("5. 26 键拼音翻译器在包内", True, "H-089：script_translator@pinyin 缺了就等于拼音功能没了")
def _c5(c):
    txt = c.read_text("wubi_pinyin.custom.yaml")
    return ("script_translator@pinyin" in txt), (
        "已含 script_translator@pinyin" if "script_translator@pinyin" in txt else "缺 script_translator@pinyin")


@check("6. punctuator 指向 default（不是已删除的 symbols 预设）", True,
       "指向 symbols 而基文件已删 ⇒ 标点整块失效")
def _c6(c):
    txt = c.read_text("wubi_pinyin.custom.yaml")
    lines = [l.strip() for l in txt.split("\n") if "import_preset" in l and "punctuator" not in l]
    has_default = any("default" in l for l in lines)
    has_symbols = any("symbols" in l for l in lines)
    return (has_default and not has_symbols), "import_preset 行: %r" % (lines,)


@check("7. 用户协议不再声称「设置保存在沙箱」，且公示版与应用内版正文一致", True,
       "与实测不符（H-086/H-090 同类）；AGC 驳回 TOP6＝应用内与提交信息不一致")
def _c7(c):
    import os
    import re

    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    hosted_dir = os.path.join(repo, "docs", "release", "legal")
    bad_phrases = ("设置保存在应用沙箱", "与全部设置", "自造词与设置保存在", "用户词典与设置")

    def claim_hits(text):
        return [p for p in bad_phrases if p in text]

    def body_text(html):
        """正文纯文本：去掉 nav / footer / 草案横幅这些页面外壳，只比实质条款。"""
        m = re.search(r"<main[^>]*>(.*?)</main>", html, re.S)
        b = m.group(1) if m else html
        b = re.sub(r"<nav.*?</nav>", " ", b, flags=re.S)
        b = re.sub(r"<footer.*?</footer>", " ", b, flags=re.S)
        b = re.sub(r"<div class=\"draft\">.*?</div>", " ", b, flags=re.S)
        b = re.sub(r"<[^>]+>", " ", b)
        return re.sub(r"\s+", " ", b).strip()

    problems = []
    inapp = {}
    packaged = {}
    for doc in ("privacy", "terms"):
        name = "privacy.html" if doc == "privacy" else "terms.html"
        text = c.read_text("legal/" + name)
        inapp[doc] = text
        hits = claim_hits(text)
        if hits:
            problems.append("应用内 %s 仍含 %s" % (name, hits))
        hp = os.path.join(hosted_dir, name)
        if not os.path.exists(hp):
            problems.append("找不到 AGC 公示版 %s" % hp)
            continue
        hosted = open(hp, encoding="utf-8").read()
        hits = claim_hits(hosted)
        if hits:
            problems.append("公示版 %s 仍含 %s" % (name, hits))
        if body_text(hosted) != body_text(text):
            problems.append("公示版 %s 与应用内 %s 正文不一致" % (name, name))
        packaged[name] = text

    # 同源判据：包内 / 公示版都得等于用当前 docs/release/legal/*.md 现场重生成的结果。
    # 只比「公示版 vs 应用内」挡不住「改了 md 两版都没重跑」—— 那正是最容易一夜过期的一种。
    try:
        fresh = _regen("legal")
    except Exception as exc:
        problems.append("无法现场重跑 build_legal_html.py ⇒ 判不了与 md 同源（%s: %s）"
                        % (type(exc).__name__, exc))
    else:
        for name in sorted(fresh["inapp"]):
            t = fresh["inapp"][name]
            if packaged.get(name) is None:
                problems.append("包内缺应用内 %s，无法判同源" % name)
            elif packaged[name] != t:
                problems.append("应用内 %s 与当前 docs/release/legal/*.md 不同源（md 已改、页面是旧的）"
                                "⇒ 先跑 python scripts/build_legal_html.py 再构建" % name)
            hp = os.path.join(hosted_dir, name)
            ht = fresh["hosted"][name]
            if os.path.exists(hp) and io.open(hp, encoding="utf-8").read() != ht:
                problems.append("公示版 %s 与当前 md 重生成的结果不同源（公示版是旧的）"
                                "⇒ 先跑 python scripts/build_legal_html.py 再上传" % name)
    return (not problems), ("；".join(problems) if problems
                            else "两处均无「设置保存在沙箱」表述，公示版与应用内版正文逐条一致，"
                                 "且两者都等于当前 md 现场重生成的结果")


@check("8. 权限只有 VIBRATE、无 INTERNET", True, "「单机应用」申报的硬前提")
def _c8(c):
    import re
    b = c.read_text("module.json")
    perms = re.findall(r'"name"\s*:\s*"(ohos\.permission\.[^"]+)"', b)
    ok = perms == ["ohos.permission.VIBRATE"] and "INTERNET" not in b
    return ok, "perms=%r, INTERNET=%s" % (perms, "INTERNET" in b)


def _row_seg_report(png_bytes, step_rows=64):
    """按行统计不透明连通段 —— 用来区分「四宫格」与「通栏图形/圆环图形」。

    2026-10-23 13:3x 修正（我自己的一条假报警）：旧判据只看「某行有 ≥2 段」就判四宫格，
    但**带外环的图标**天然每行两段（左弧 + 右弧，各约 0.015 宽），被误判成四宫格。
    新判据看**段的宽度**：四宫格是两块**宽块**（每段 ≥0.15×宽），
    而圆环的两段是**细弧**（<0.05×宽）⇒ 只要每行的段要么很细、要么只有 1 段，就不是四宫格。
    """
    from PIL import Image
    im = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    w, h = im.size
    alpha = im.split()[3]

    def seg_widths(y):
        out, start = [], None
        for x in range(w):
            cur = alpha.getpixel((x, y)) > 128
            if cur and start is None:
                start = x
            elif not cur and start is not None:
                out.append(x - start)
                start = None
        if start is not None:
            out.append(w - start)
        return out

    rows = list(range(0, h, max(1, h // step_rows)))
    # 四宫格指纹：某行出现 ≥2 个「宽块」（每块 ≥0.15 宽）
    grid_rows = 0
    for y in rows:
        wide = [wd for wd in seg_widths(y) if wd >= 0.15 * w]
        if len(wide) >= 2:
            grid_rows += 1
    return im.size, len(rows), grid_rows


def _is_single_color(png_bytes):
    """整张图是否只有一个颜色（DevEco 模板蓝方块的特征）。"""
    from PIL import Image
    im = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    colors = im.getcolors(maxcolors=8)
    return bool(colors) and len(colors) == 1


def _is_fully_opaque(png_bytes):
    from PIL import Image
    im = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    lo, hi = im.split()[3].getextrema()
    return lo == 255


@check("9. 应用图标不是 DevEco 四宫格模板", True, "H-097：AGC 会比对包内图标与上传图标")
def _c9(c):
    """四宫格的指纹：前景被分成左右两块，所以**某些行会出现 2 段不透明**；
    三条键帽横条是通栏的，任何一行最多 1 段。
    2026-10-22 教训：我第一版只查「中心透明 + 两个象限不透明」，
    四宫格和键帽都满足 ⇒ 把四宫格误判成 PASS。这里改成按行的连通段数判断。"""
    (w, h), sampled, grid_rows = _row_seg_report(c.read("media/foreground.png"))
    is_grid = grid_rows >= sampled * 0.2
    return (not is_grid), ("foreground.png %dx%d，按行采样 %d 行，其中 %d 行出现 ≥2 个宽块（≥0.15×宽）⇒ %s"
                           % (w, h, sampled, grid_rows, "疑似四宫格" if is_grid else "是通栏横条或细环，不是四宫格"))


@check("9b. 入口声明引用的那张图标也不是 DevEco 模板", False,
       "H-105/H-108：第 ⑨ 项只看 layered 前景，而 module.json5 的 icon/startWindowIcon "
       "指向另一张图；桌面/启动窗真正用的可能是那张。图标必须三层分开核")
def _c9b(c):
    import re
    t = c.read_text("module.json")
    refs = sorted(set(re.findall(r'"(?:icon|startWindowIcon)"\s*:\s*"\$media:([A-Za-z0-9_]+)"', t)))
    # 提审 .app 里模板图标必须阻断；开发 HAP 仍只报 WARN（与 H-105 的「不单独出包」口径一致）
    blk = getattr(c, "app", None) is not None
    if not refs:
        return False, "module.json 里没找到任何 $media: 图标引用（口径变了，须手核）", blk
    findings, bad = [], []
    for name in refs:
        if name == "layered_image":
            try:
                c.read("media/layered_image.json")
                findings.append("layered_image.json 在")
            except FileNotFoundError:
                bad.append("layered_image 被引用但没有 layered_image.json")
            continue
        try:
            raw = c.read("media/%s.png" % name)
        except FileNotFoundError:
            bad.append("%s.png 被引用但不在包/源码树里" % name)
            continue
        (w, h) = _row_seg_report(raw, step_rows=8)[0]
        opaque = _is_fully_opaque(raw)
        flat = _is_single_color(raw)
        # DevEco 新建工程模板的指纹：**48×48 且整张一个颜色**（蓝方块）。
        # 2026-10-23 13:3x 修正（我自己的假报警）：旧判据是「w<=64 或 文件<2048B」且不透明，
        # 但黑底金图标本身是「不透明的纯黑底 + 金色图形」，216 件只有 1,374 B ⇒ 被误判成模板。
        # 换成「小尺寸 + 整张单色」才判模板：带图形的图永远不是单色。
        is_template = (w <= 64) and opaque and flat
        tag = "模板" if is_template else "OK"
        findings.append("%s.png %dx%d/%dB 全不透明=%s 单色=%s ⇒ %s"
                        % (name, w, h, len(raw), opaque, flat, tag))
        if is_template:
            bad.append("%s.png 是 %dx%d 全不透明的 DevEco 模板图（module.json5 的 icon/startWindowIcon 还指着它）"
                       % (name, w, h))
    msg = "；".join(findings)
    if bad:
        msg += ("   ← H-105/H-108：零代码修法——用仓库里的 "
                "docs/release/store/icon/gen-appicon-512.png（实测 512x512）覆盖 "
                "entry/src/main/resources/base/media/app_icon.png，引用名 $media:app_icon 不动；"
                "同批回退 module.json5 的 ohos.entry.mainability metadata，并把第 ⑯ 项桌面截图一起交")
        return False, msg, blk
    return True, msg, blk


@check("10. 提审包不含调试探针页", False, "H-098：M3Probe/LandscapeProbe 不该随提审包发布")
def _c10(c):
    t = c.read_text("profile/main_pages.json")
    bad = ("M3Probe" in t) or ("LandscapeProbe" in t)
    # 提审 .app 里探针页必须阻断（H-098）；开发 HAP 保留探针只报 WARN
    blk = getattr(c, "app", None) is not None
    return (not bad), ("main_pages 仍注册探针页" if bad else "未注册"), blk


@check("11. 包内能读到 NOTICE 与全部许可全文，且与当前 NOTICE/LICENSES 逐字节同源", True,
       "H-099：About 页指路却打不开，等于没提供；H-126：改了 NOTICE 没重生成页面 = 应用内还是旧的对外声明")
def _c11(c):
    hits = [n for n in c.names if n.endswith("rawfile/legal/notice.html")]
    if not hits:
        return False, "包里没有 rawfile/legal/notice.html（About 页那个入口会点空）"
    body = c.read_text("legal/notice.html")
    missing = [x for x in ("Apache License", "TERMS AND CONDITIONS",
                           "GNU LESSER GENERAL PUBLIC LICENSE", "Permission is hereby granted")
               if x not in body]
    problems = []
    if missing:
        problems.append("许可全文缺项: %s" % missing)
    try:
        fresh = _regen("notice")
    except Exception as exc:
        problems.append("无法现场重跑 build_notice_html.py ⇒ 判不了同源（%s: %s）"
                        % (type(exc).__name__, exc))
    else:
        stale = [n for n, t in fresh["inapp"].items() if t != body]
        if stale:
            problems.append("包内 %s 与当前 NOTICE/LICENSES 不同源（源文件已改、页面是旧的）"
                            "⇒ 先跑 python scripts/build_notice_html.py 再构建" % "、".join(stale))
    if not problems:
        return True, "notice.html %d B：许可全文齐、且等于当前 NOTICE+LICENSES/ 现场重生成的结果" % len(body.encode())
    return False, "；".join(problems) + "（现 %d B）" % len(body.encode())


@check("12. 界面文案不再让用户去「安装目录」找许可", True, "H-099：沙箱下用户进不去安装目录")
def _c12(c):
    blob = c.ui_blob()
    bad = "应用安装目录下的 NOTICE".encode("utf-8") in blob
    return (not bad), ("modules.abc 仍含「应用安装目录下的 NOTICE」" if bad else "已改为应用内路径")


@check("13. About 页词库来源标了 LGPL 的 wubi86", True, "H-100：主码表是 LGPL-3.0，不能只标 Apache 那层")
def _c13(c):
    blob = c.ui_blob()
    has_lgpl = "LGPL-3.0".encode("utf-8") in blob
    has_wubi = "五笔主码表".encode("utf-8") in blob
    return (has_lgpl and has_wubi), (
        "界面文案里 LGPL-3.0=%s, 五笔主码表=%s" % (has_lgpl, has_wubi))


@check("14. 版本号与发布版本一致", False, "改版本号要同步 AGC")
def _c14(c):
    import re
    b = c.read_text("module.json")
    m = re.search(r'"versionName"\s*:\s*"([^"]+)"', b)
    v = m.group(1) if m else None
    return (v == "1.0.0"), "versionName=%s" % v


@check("15. deviceTypes 与 AGC「只勾手机」一致", True,
       "H-102：声明 tablet 但我们零适配零验证，与申报口径冲突")
def _c15(c):
    import re
    b = c.read_text("module.json")
    m = re.search(r'"deviceTypes"\s*:\s*\[(.*?)\]', b, re.S)
    if not m:
        return False, "包内 module.json 找不到 deviceTypes"
    types = [x.strip().strip('"') for x in m.group(1).split(",") if x.strip()]
    ok = types == ["phone"]
    return ok, "deviceTypes=%r（AGC 只勾手机 ⇒ 要求恰好 [phone]）" % (types,)


# H-242 收口（Qoder 2026-10-28）：把「设置项真生效」守卫挂进内容闸门的离线套。
# 口径来源：H-242 任务列「跑通后随本轮一起提交，并挂进内容闸门的离线套」＋
# H-130/H-238 教训「只管打印 WARN 的检查永远不会阻断，等于没有」⇒ blocking=True。
# 为什么覆盖得住：守卫读的是**工作区源码**（SettingsStore.ets 的 SPECS 与键盘侧读取点），
# 而这一列检查在构建前的离线套里跑（契约 §5-1「内容闸门 16/16 阻断 0」是装机前置），
# 所以「页面摆一行、键盘根本不读」这种 H-090 型空壳回归会在构建前被拦下，而不是等真机。
@check("16b. 设置契约 12 项三项齐全（H-242 生效守卫子进程）", True,
       "H-090：71 项 0 生效的空壳回归离线看代码看不出来，必须机器判据拦在构建前")
def _c16b(c):
    import subprocess
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    script = os.path.join(root, "scripts", "settings_effective_check.py")
    # 自测注入通路：闸门自己也要能被「已知坏」验证（H-169/H-130 口径）。
    # 只有显式设 SS_H242_GUARD_SCRIPT 指向别处时才改道——真跑构建/装机从不设，默认路径不受影响；
    # 指向不存在的文件则走下面「守卫文件被删＝FAIL、不静默跳过」那条既有分支。
    override = os.environ.get("SS_H242_GUARD_SCRIPT")
    if override:
        script = override
    if not os.path.exists(script):
        return False, "找不到 %s —— 守卫文件被删＝判据失效，按 FAIL 处理（不许静默跳过）" % script
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    p = subprocess.run([sys.executable, script], cwd=root,
                       capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    tail = [x for x in (p.stdout or "").strip().splitlines() if x.strip()]
    summary = tail[0] if tail else "(无输出)"
    if p.returncode != 0:
        bad = [x for x in tail if x.startswith("[FAIL]")]
        detail = "; ".join(bad) if bad else summary
        return False, "settings_effective_check.py rc=%d ⇒ %s" % (p.returncode, detail[:300])
    return True, summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("app", nargs="?", default=None)
    ap.add_argument("--allow-fail", action="store_true")
    ap.add_argument("--source", action="store_true",
                    help="跑在当前工作区源码上（构建前的快检；测不出的项会标注须构建后核）")
    a = ap.parse_args()

    if a.source:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        print("对象: 源码树 %s" % root)
        c = SrcCtx(root)
        print("文件: %d 个候选资源" % len(c.names))
        print("注意: 源码级快检**不能替代包上复核**；12/13 两项以源码字符串近似，"
              "最终以 modules.abc 为准。")
        print()
    else:
        if a.app is None:
            # 默认选**最近构建**的那个：.app 存在但比 HAP 旧时，应当查 HAP
            cands = [x for x in (DEFAULT_APP, DEFAULT_HAP) if os.path.exists(x)]
            a.app = max(cands, key=os.path.getmtime) if cands else DEFAULT_HAP
        if not os.path.exists(a.app):
            print("找不到:", a.app)
            return 2

        import hashlib
        data = open(a.app, "rb").read()
        print("对象:", a.app)
        print("文件: %d B  sha256 %s" % (len(data), hashlib.sha256(data).hexdigest()))
        c = Ctx(a.app)
        if c.inner_hap_name:
            print("内层: %s %d B  %d 条目" % (c.inner_hap_name, len(c.hap_bytes), len(c.names)))
        else:
            print("裸 HAP（未签名）: %d 条目" % len(c.names))
        print()

    blocked = 0
    failed = 0
    for name, blocking, why, fn in CHECKS:
        blk = blocking
        try:
            res = fn(c)
            if len(res) == 3:
                ok, detail, blk = res
            else:
                ok, detail = res
        except Exception as e:
            ok, detail = False, "检查异常: %s: %s" % (type(e).__name__, str(e)[:100])
        mark = "PASS" if ok else ("FAIL" if blk else "WARN")
        if not ok:
            failed += 1
            if blk:
                blocked += 1
        print("[%s] %s\n       %s%s" % (mark, name, detail, "" if ok else "   ← " + why))

    print()
    print("结果: %d/%d 通过；阻断项未过 %d 个" % (len(CHECKS) - failed, len(CHECKS), blocked))
    if blocked:
        print("结论: 这份包**不能提审**。")
        return 0 if a.allow_fail else 1
    print("结论: 阻断项全部通过。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
