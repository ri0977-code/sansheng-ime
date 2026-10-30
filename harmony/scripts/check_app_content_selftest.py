"""内容闸门自测：用「已知坏」的包验证每一项检查真的会响。

为什么需要它：check_app_content.py 的 18 项断言本身也会写错。历史上第 ⑨ 项第一版
把 DevEco 四宫格误判成 PASS，就是「检查写了、但从没在坏样本上跑过」。这个脚本
以当前最新 unsigned HAP 为底，逐项做一处定向破坏，确认对应检查从 PASS 变 FAIL/WARN；
再做一份「两项 WARN 都修掉」的包，确认 18/18 可达。

2026-10-28 07:1x（Qoder，H-242）：第 16b 条是「读工作区源码的子进程」型检查，破坏注入不进包里、
改走 env（`SS_H242_GUARD_SCRIPT`，仅自测设置；真构建从不设、默认路径不受影响）。
末尾三条＝两条 env 注入（守卫 rc!=0／守卫文件不存在）＋一条**退出码断言**（16b FAIL 时不带
--allow-fail 的闸门必须 rc=1）——只打 WARN 的检查永远不会阻断，等于没有（H-130/H-238）。

用法：
    python scripts/check_app_content_selftest.py [--hap 路径] [--workdir 目录] [--keep]

产物写在临时目录（默认系统 temp），不留在仓库里；--keep 保留以便手工复查。
只读原始 HAP，不构建、不签名、不装机。
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile

from PIL import Image

DEFAULT_HAP = "entry/build/default/outputs/default/entry-default-unsigned.hap"


def two_bars_png():
    """左右两条不透明竖条：任何一行都有 2 段，等价于四宫格的按行指纹。"""
    im = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    px = im.load()
    for x in range(512):
        if x < 200 or x > 311:
            for y in range(512):
                px[x, y] = (40, 120, 220, 255)
    b = io.BytesIO()
    im.save(b, "PNG")
    return b.getvalue()


def opaque_small_png():
    """48x48 全不透明：DevEco 模板图指纹。"""
    im = Image.new("RGBA", (48, 48), (20, 90, 200, 255))
    b = io.BytesIO()
    im.save(b, "PNG")
    return b.getvalue()


def run_checker(checker, path, env=None):
    env_full = dict(os.environ, PYTHONIOENCODING="utf-8")
    if env:
        env_full.update(env)
    p = subprocess.run([sys.executable, checker, path, "--allow-fail"],
                       capture_output=True, env=env_full)
    out = p.stdout.decode("utf-8", "replace")
    marks = {}
    for line in out.splitlines():
        m = re.match(r"\[(PASS|FAIL|WARN)\] (\d+b?)\.", line)
        if m:
            marks[m.group(2)] = m.group(1)
    tail = [l for l in out.splitlines() if l.startswith("结果:")]
    return marks, (tail[-1] if tail else "?"), out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hap", default=DEFAULT_HAP)
    ap.add_argument("--workdir", default=None)
    ap.add_argument("--keep", action="store_true")
    a = ap.parse_args()

    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    hap = a.hap if os.path.isabs(a.hap) else os.path.join(repo, a.hap)
    checker = os.path.join(repo, "scripts", "check_app_content.py")
    if not os.path.exists(hap):
        print("找不到 HAP:", hap)
        return 2
    good_icon = os.path.join(repo, "docs", "release", "store", "icon", "gen-appicon-216.png")
    if not os.path.exists(good_icon):
        print("缺少已知合格的 app_icon 素材:", good_icon)
        return 2
    good_icon = open(good_icon, "rb").read()

    work = a.workdir or tempfile.mkdtemp(prefix="gate-selftest-")
    os.makedirs(work, exist_ok=True)
    print("底包:", hap)
    print("临时目录:", work)

    z = zipfile.ZipFile(hap)
    base = [(i.filename, z.read(i.filename)) for i in z.infolist()]
    src = dict(base)

    # 底包的三个对外页面一律换成**工作区当前的生成产物**（2026-10-23 04:0x 补，H-126 的后续坑）。
    # 为什么必须换：自测拿磁盘上「最新那份 HAP」当底，可那份包永远是上一次构建的结果；
    # 一改根 NOTICE 而还没重新构建，⑦/⑪ 就会在 00-baseline / 16-good 上报 FAIL ——
    # 那既不是判据坏也不是包坏，是自测把期望值绑在了过期产物上（本轮实测踩过：
    # NOTICE 从 20,988 B 改到 23,164 B 后 22 例里立刻 2 例 MISMATCH）。
    # 换完之后的语义：底包 = 「现在构建会得到什么」，与闸门 ⑦/⑪ 的同源基准同一条。
    legal_dir = os.path.join(repo, "entry", "src", "main", "resources", "rawfile", "legal")
    swapped = []
    for n in ("notice.html", "privacy.html", "terms.html"):
        p = os.path.join(legal_dir, n)
        key = "resources/rawfile/legal/" + n
        if os.path.exists(p) and key in src:
            d = open(p, "rb").read()
            if d != src[key]:
                swapped.append("%s %d→%d B" % (n, len(src[key]), len(d)))
                src[key] = d
    if swapped:
        base = [(k, src[k]) for k, _ in base]
        print("底包 legal 已换成工作区当前产物:", "; ".join(swapped))
    else:
        print("底包 legal 与工作区产物一致，未替换")

    def build(mods=None, add=None, drop=None):
        mods = dict(mods or {})
        items = []
        for n, d in base:
            if drop and n in drop:
                continue
            items.append((n, mods.pop(n, d)))
        for n, d in (add or {}).items():
            items.append((n, d))
        assert not mods, mods
        return items

    def write(path, items):
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as o:
            for n, d in items:
                o.writestr(n, d)

    def write_app(path, items, inner="entry-default.hap"):
        """合成 .app：外层 zip 套一个内层 HAP。检查器据此知道这是提审包（9b/10 转为阻断）。"""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as o:
            for n, d in items:
                o.writestr(n, d)
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as o:
            o.writestr(inner, buf.getvalue())

    mod = src["module.json"].decode("utf-8", "replace")
    wpy = src["resources/rawfile/rime/wubi_pinyin.custom.yaml"]
    # 坏样本方向反转（Qoder 2026-10-25 15:0x，H-169）：
    # 原写法是「从底包里删掉探针页注册 ⇒ ⑩ 应变 PASS」，前提是底包还注册着探针页。
    # `b5fda68`（2026-10-23 21:30，H-098 收口）把 main_pages 里的两枚探针页摘了，
    # 于是 mp_noprobe == mp，第 144 行的 assert 直接崩（exit 1），整个内容闸门自测从那天起再没跑起来过
    # ⇒ ⑩ 的已知坏样本永远验不了，检查器只剩「会说 PASS」这一种能力（正是 0020 那份自测要防的病）。
    # 现在底包是干净的，坏样本必须**正向注入**：往 main_pages 塞回一枚探针页注册，
    # 裸 HAP 应报 WARN、提审 .app 应报 FAIL（H-115 分级），干净基线应报 PASS。
    mp = src["resources/base/profile/main_pages.json"].decode("utf-8", "replace")
    mp_withprobe = mp.replace('"pages/KeyboardIndex",',
                              '"pages/KeyboardIndex","pages/M3Probe",', 1)
    assert mp_withprobe != mp, 'main_pages 里没有 "pages/KeyboardIndex", 锚点，无法注入探针页坏样本'
    terms = src["resources/rawfile/legal/terms.html"].decode("utf-8", "replace")
    terms_bad = terms.replace("</main>", "<p>用户词典与设置保存在应用沙箱。</p></main>", 1)
    assert terms_bad != terms, "terms.html 没有 </main>，无法注入旧口径"
    # H-126 同源判据的坏样本：只在页面尾部追加一段「源文件改了但没重生成」的残留，
    # 关键词全保留 ⇒ 只有「与当前源文件不同源」这一条能抓到它。
    notice = src["resources/rawfile/legal/notice.html"].decode("utf-8", "replace")
    notice_stale = notice.replace("</main>", "\n<p>旧版许可声明残留</p></main>", 1)
    assert notice_stale != notice, "notice.html 没有 </main>，无法注入旧版残留"
    privacy = src["resources/rawfile/legal/privacy.html"].decode("utf-8", "replace")
    privacy_stale = privacy.replace("</main>", "\n<p>旧版权益条款残留</p></main>", 1)
    assert privacy_stale != privacy, "privacy.html 没有 </main>，无法注入旧版残留"

    # —— D-033（Qoder 2026-10-30）第 4 / 4b 条的坏样本，两条各判一头 ——
    # 第 4 条：中文引号必须在符号面板「常用」组**第 0 页**（前 19 格，不划页就能点到）。
    #   坏样本不删字符、只把它们**挪到第 20 格之后**——这样只有「页内」这条判据能抓到，
    #   删字符的样本会让「格子还在文件里」这种半修好状态蒙混过关（H-130 口径：判据要能只坏在它自己身上）。
    # 第 4b 条：9 个面板符号必须仍是**单值**（M-368 压过、M-369 主人真机验过一键直出）。
    #   坏样本＝把 `'` 恢复成候选数组 ⇒ 正是「为了满足旧判据把主人验过的行为改回去」这个回归方向。
    QUOTE = ["\u201c", "\u201d", "\u2018", "\u2019", "\u300c", "\u300d"]   # “ ” ‘ ’ 「 」
    sj_key = "resources/rawfile/symbols/symbols.json"
    assert sj_key in src, "底包里没有 %s，第 4 条无法注入坏样本" % sj_key
    sj = json.loads(src[sj_key].decode("utf-8"))
    moved_n = 0
    for g in sj.get("groups") or []:
        if g.get("id") == "common":
            keep = [x for x in g["items"] if x not in QUOTE]
            moved = [x for x in g["items"] if x in QUOTE]
            moved_n = len(moved)
            g["items"] = keep + moved
    assert moved_n == len(QUOTE), "常用组里只找到 %d/6 个中文引号格子，坏样本前提不成立" % moved_n
    sj_offpage = json.dumps(sj, ensure_ascii=False).encode("utf-8")
    dy_key = "resources/rawfile/rime/default.yaml"
    dy = src[dy_key].decode("utf-8")
    q, dq = chr(39), chr(34)
    scalar_line = dq + q + dq + ": " + dq + q + dq                       # "'': ''"（单值）
    list_line = dq + q + dq + ": [" + dq + QUOTE[2] + dq + ", " + dq + QUOTE[3] + dq + "]"
    assert scalar_line in dy, "default.yaml 里找不到 %r，4b 坏样本注不进去" % scalar_line
    dy_list = dy.replace(scalar_line, list_line, 1).encode("utf-8")

    cases = [
        # 基线同时锁 ⑦/⑪ PASS：证明「同源判据」对当前真包不误报（当下三层确实同步）
        # 2026-10-23 13:3x：基线里 9b 的期望值改成**从基线包实测**（H-130 那类老病：写死「基线必然是模板」，
        # 树里的图标一换好就假报警）。
        # 2026-10-25 15:0x（H-169）：⑩ 的基线期望由 WARN 改 PASS——探针页 10-23 21:30 已从 main_pages 摘掉，
        # 干净包这里就该是 PASS；「⑩ 会响」这件事改由 10-withprobe / 17b-app-withprobe 两条注入用例证明。
        ("00-baseline", build(), {"10": "PASS", "7": "PASS", "11": "PASS", "16b": "PASS",
                                  "4": "PASS", "4b": "PASS"}),
        ("01-symbols", build(add={"resources/rawfile/rime/symbols.yaml": b"x: 1\n"}), {"1": "FAIL"}),
        # D-033 后第 4 条不再读 default.yaml（读的是 symbols.json＋ui_blob），
        # 这条「整份 default.yaml 换成桩」的样本现在只该触发 2/4b：
        # 4b 报 FAIL 是因为桩里 half_shape 只剩一枚 `'`，另 8 枚面板符号没了——
        # 这正是 4b 该有的反应（面板符号少一枚＝点下去没定义），顺手证明它不是永真判据。
        ("02-punct", build({"resources/rawfile/rime/default.yaml":
                            b'punctuator:\n  symbols:\n    x: [1]\n  half_shape:\n    "\'": x\n'}),
         {"2": "FAIL", "3": "PASS", "4": "PASS", "4b": "FAIL"}),
        ("03-yaml", build({"resources/rawfile/rime/default.yaml": b"punctuator: [\n"}), {"3": "FAIL"}),
        # D-033 第 4 条（中文引号在面板第 0 页）与 4b（9 符号仍是单值）的定向破坏
        ("04-quote-offpage", build({sj_key: sj_offpage}), {"4": "FAIL", "4b": "PASS"}),
        ("04b-nosymbolsjson", build(drop={sj_key}), {"4": "FAIL"}),
        ("04c-punct-back-to-list", build({dy_key: dy_list}), {"4b": "FAIL", "4": "PASS", "3": "PASS"}),
        ("05-pinyin", build({"resources/rawfile/rime/wubi_pinyin.custom.yaml":
                             wpy.replace(b"script_translator@pinyin", b"script_translator")}),
         {"5": "FAIL"}),
        ("06-preset", build({"resources/rawfile/rime/wubi_pinyin.custom.yaml":
                             wpy.replace(b"import_preset: default", b"import_preset: symbols")}),
         {"6": "FAIL"}),
        ("07-claim", build({"resources/rawfile/legal/terms.html": terms_bad.encode()}), {"7": "FAIL"}),
        ("08-internet", build({"module.json": mod.replace(
            '"name":"ohos.permission.VIBRATE"}',
            '"name":"ohos.permission.VIBRATE"},{"name":"ohos.permission.INTERNET"}').encode()}),
         {"8": "FAIL"}),
        ("09-grid", build({"resources/base/media/foreground.png": two_bars_png()}), {"9": "FAIL"}),
        ("09b-goodicon", build({"resources/base/media/app_icon.png": good_icon}), {"9b": "PASS"}),
        ("09b-template", build({"resources/base/media/app_icon.png": opaque_small_png()}), {"9b": "WARN"}),
        # H-169：坏样本方向反转后的 ⑩ 用例——底包本来干净（PASS），注入探针页注册才该响。
        # 裸 HAP 只 WARN（开发装机不受影响，H-115 分级），提审 .app 必须 FAIL。
        ("10-withprobe", build({"resources/base/profile/main_pages.json": mp_withprobe.encode()}),
         {"10": "WARN"}),
        ("11-nonotice", build(drop={"resources/rawfile/legal/notice.html"}), {"11": "FAIL"}),
        ("12-abcold", build({"ets/modules.abc": src["ets/modules.abc"] + "应用安装目录下的 NOTICE".encode()}),
         {"12": "FAIL"}),
        # modules.abc 换成 dummy ⇒ 13 该 FAIL；D-033 后第 4 条也读 ui_blob（回落表），
        # 所以同一样本顺带验到「回落表里没了中文引号」这一半也会响（Qoder 2026-10-30）。
        ("13-nolgpl", build({"ets/modules.abc": b"dummy"}), {"13": "FAIL", "12": "PASS", "4": "FAIL"}),
        ("14-version", build({"module.json": mod.replace('"versionName":"1.0.0"',
                                                        '"versionName":"0.9.0"').encode()}),
         {"14": "WARN"}),
        ("15-tablet", build({"module.json": mod.replace('"deviceTypes":["phone"]',
                                                       '"deviceTypes":["phone","tablet"]').encode()}),
         {"15": "FAIL"}),
        ("16-good", build({"resources/base/media/app_icon.png": good_icon}),
         {"9b": "PASS", "10": "PASS", "7": "PASS", "11": "PASS"}),
        # H-126：包里的对外声明与当前源文件不同源 ⇒ 必须是 FAIL（阻断），不能只是提示
        ("19-notice-stale", build({"resources/rawfile/legal/notice.html": notice_stale.encode()}),
         {"11": "FAIL"}),
        ("20-privacy-stale", build({"resources/rawfile/legal/privacy.html": privacy_stale.encode()}),
         {"7": "FAIL"}),
        # .app 包装：9b/⑩ 从 WARN 升级为阻断（H-115）
        # 同理：`.app` 基线只锁「⑩ 不阻断时是 PASS、注入探针后必须变 FAIL」（与图标状态无关）；
        # 9b 是否阻断由 09b-* 两组因果用例单独验。
        ("17-app-baseline", build(), {"10": "PASS"}, "app"),
        # H-169：⑩ 的 .app 阻断因果——只有「探针注册 + .app 包装」同时成立才该 FAIL，
        # 少了这条，分级逻辑（blk = 输入是 .app）写坏了也不会有人发现。
        ("17b-app-withprobe", build({"resources/base/profile/main_pages.json":
                                     mp_withprobe.encode()}), {"10": "FAIL"}, "app"),
        ("18-app-good", build({"resources/base/media/app_icon.png": good_icon}),
         {"9b": "PASS", "10": "PASS"}, "app"),
    ]

    mismatched = 0
    report = []
    for case in cases:
        name, items, exp = case[0], case[1], case[2]
        kind = case[3] if len(case) > 3 else "hap"
        path = os.path.join(work, name + (".app" if kind == "app" else ".hap"))
        if kind == "app":
            write_app(path, items)
        else:
            write(path, items)
        marks, tail, out = run_checker(checker, path)
        mism = {k: [v, marks.get(k)] for k, v in exp.items() if marks.get(k) != v}
        if mism:
            mismatched += 1
        report.append({"case": name, "result": tail, "mismatch": mism, "marks": marks})
        print("%-14s %-34s %s" % (name, tail, ("MISMATCH " + json.dumps(mism, ensure_ascii=False)) if mism else "ok"))
        if mism:
            print(out)

    # —— H-242 第 16b 条的定向破坏不注入在**包里**，而在 **env**（它是「读工作区源码的子进程」型检查）。
    # Qoder 2026-10-28 07:1x：上一轮只用手工「移走守卫文件」验过一次，那是散文不是判据（H-130 口径）；
    # 这里把它固化成两条用例＋一条**退出码**断言——只打 WARN 的检查永远不会阻断，等于没有。
    stub = os.path.join(work, "stub-guard-fail.py")
    with io.open(stub, "w", encoding="utf-8", newline="\n") as fp:
        fp.write("import sys\n"
                 "print('[FAIL] selftest 注入：kbd_height_pct 键盘侧没有读取点')\n"
                 "print('H-242 生效守卫: 11/12 项三项齐全')\n"
                 "sys.exit(1)\n")
    carrier = os.path.join(work, "16b-carrier.hap")
    write(carrier, build())
    for label, envx in (("16b-guard-fail", {"SS_H242_GUARD_SCRIPT": stub}),
                        ("16b-guard-missing", {"SS_H242_GUARD_SCRIPT":
                                               os.path.join(work, "no-such-guard.py")})):
        marks, tail, out = run_checker(checker, carrier, env=envx)
        mism = {} if marks.get("16b") == "FAIL" else {"16b": ["FAIL", marks.get("16b")]}
        if mism:
            mismatched += 1
        report.append({"case": label, "result": tail, "mismatch": mism, "marks": marks})
        print("%-14s %-34s %s" % (label, tail,
                                  ("MISMATCH " + json.dumps(mism, ensure_ascii=False)) if mism else "ok"))
        if mism:
            print(out)

    # 严重度/通路断言：16b 是 blocking=True，所以**不带 --allow-fail** 时闸门必须 rc==1。
    p_rc = subprocess.run([sys.executable, checker, carrier],
                          capture_output=True,
                          env=dict(os.environ, PYTHONIOENCODING="utf-8",
                                   SS_H242_GUARD_SCRIPT=stub))
    rc_ok = (p_rc.returncode == 1)
    if not rc_ok:
        mismatched += 1
    print("%-14s %-34s %s" % ("16b-exit-code", "16b FAIL 时闸门 rc 必须=1（阻断通路）",
                               "ok" if rc_ok else "MISMATCH rc=%d" % p_rc.returncode))
    report.append({"case": "16b-exit-code", "result": "rc=%d" % p_rc.returncode,
                   "mismatch": {} if rc_ok else {"rc": [1, p_rc.returncode]}, "marks": {}})

    # 严重度断言（D-033，Qoder 2026-10-30）：4b 也声明了 blocking=True，
    # 所以「只有 4b 坏」的包（04c 那份把 `'` 恢复成候选数组）不带 --allow-fail 时必须 rc==1。
    # 少了这条，4b 就可能退化成「会报 FAIL 但不拦构建」的假闸门（H-130/H-238 同一味药）。
    carrier4b = os.path.join(work, "04c-exitcode.hap")
    write(carrier4b, build({dy_key: dy_list}))
    p_rc4 = subprocess.run([sys.executable, checker, carrier4b],
                           capture_output=True,
                           env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    rc4_ok = (p_rc4.returncode == 1)
    if not rc4_ok:
        mismatched += 1
    print("%-14s %-34s %s" % ("04c-exit-code", "4b FAIL 时闸门 rc 必须=1（阻断通路）",
                              "ok" if rc4_ok else "MISMATCH rc=%d" % p_rc4.returncode))
    report.append({"case": "04c-exit-code", "result": "rc=%d" % p_rc4.returncode,
                   "mismatch": {} if rc4_ok else {"rc": [1, p_rc4.returncode]}, "marks": {}})

    if not a.keep:
        for f in os.listdir(work):
            if f.endswith((".hap", ".app")):
                try:
                    os.remove(os.path.join(work, f))
                except OSError:
                    pass
    out_json = os.path.join(work, "selftest-result.json")
    with open(out_json, "w", encoding="utf-8", newline="\n") as fp:
        json.dump(report, fp, ensure_ascii=False, indent=1)
    print()
    # 「含 N 个 .app 包装用例」改成现算（Qoder 2026-10-25 15:0x，H-169）：
    # 原来写死 2，加一条 17b 就又变成一句假数字——同一类病（H-138 台账数字没跟着重算）。
    app_n = len([c for c in cases if len(c) > 3 and c[3] == "app"])
    # 总数改用 len(report)：16b 那三条（2 条 env 注入＋1 条退出码断言）不在 `cases` 里，
    # 用 len(cases) 报数就会少 3——同一类病再犯一次就是假数字（Qoder 2026-10-28 07:1x）。
    print("自测用例 %d 个（含 %d 个 .app 包装用例；16b 的 3 条 env/退出码断言不计入包用例，实报 %d 条），未按预期触发 %d 个"
          % (len(cases), app_n, len(report), mismatched))
    print("明细:", out_json)
    return 0 if mismatched == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
