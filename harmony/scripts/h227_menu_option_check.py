#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""H-227(Qoder) `···` 菜单五枚滤镜开关的「接线链」守卫（2026-10-28 08:0x）。

为什么要它（不是形式主义）：这五枚的来历是 **滤镜和数据早就在包里、UI 没有门**
（M-271 逐项核过：`encnDic`／`phraseExt`／`phraseReplace`／`abbrEn`／`pinyin`）。
「菜单里多了一行字」和「点它引擎真的换态、且有一个滤镜真的读这个态」是两件事——
H-090 那轮 71 项 0 项生效就是这个形状，D-021「只留真实生效的项」就是为它拍的。
所以把一条链写成机器判据，**缺任何一环都 FAIL**（退出码 1，不是 WARN＝H-130/H-238 口径）。

每枚开关要齐的六环：
  ① 菜单里有一行 `this.FuncMenuItem('文案', '<opt>')`（且在 FuncMenu 体内）；
  ② 回填目标 `this.X` 必须是 `@State X: boolean`（不是 @State 就不重渲染＝H-165 ③ 同款坑）；
  ③ `syncEngineOptions()` 里有 `this.X = keyboardController.getOption('<opt>')`
     （镜像字段名**从这一行推出来**，不猜命名——`pinyin` 的镜像叫 `pinyinAnnot` 也算过）；
  ④ `funcOptionOn()` 里 `case '<opt>'` 返回那个镜像（条目内部按 name 读，防 H-213 按值参数冻结）；
  ⑤ `toggleFuncOption()` 里 `case '<opt>'` 把镜像写成 `!cur`；
  ⑥ **包里的 Lua 滤镜真的读它**：`get_option("<opt>")`，且它在 `wubi_pinyin.custom.yaml` 的
     `switches/+` 里声明过（没声明＝引擎里根本没有这个态）；
  ⑦ 只在 wubi_pinyin 声明的 ⇒ 必须进 `WUBI_ONLY_OPTIONS`（九键置灰，否则＝假按钮）。

另两条全局判据：FuncMenu 必须仍是「定高壳＋内层 Scroll」（契约 §3.1 r4：加行必须自带滚动，
236vp 是硬天花板）；外加 ⑧「菜单里每一行的开关名都在册」（拼错一个字母＝又造一个假按钮，
只查这五枚各自那一行是查不出来的）；⑨ 置灰名单必须真的接在条目上（点击闸门在不在）；
自测＝六种坏形状必须全部判红。

用法：
  python scripts/h227_menu_option_check.py            # 真树，红=退出码 1
  python scripts/h227_menu_option_check.py --selftest # 只跑已知坏样本
本条**不挂进内容闸门** `check_app_content.py`：闸门管的是「这个包」，项数一变就要全体重跑基线；
这条是源码级接线判据，放在夜间离线套（命令见 `docs/NIGHT-WATCH-V10.md` §3）。
"""
import io
import os
import re
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf8'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

ROOT = os.environ.get('SS_H227_ROOT') or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KI = os.path.join(ROOT, 'entry', 'src', 'main', 'ets', 'pages', 'KeyboardIndex.ets')
LUA_DIR = os.path.join(ROOT, 'entry', 'src', 'main', 'resources', 'rawfile', 'rime', 'lua')
CUSTOM = os.path.join(ROOT, 'entry', 'src', 'main', 'resources', 'rawfile', 'rime', 'wubi_pinyin.custom.yaml')

# opt -> 菜单文案（文案照 custom.yaml 各开关自己的 states 名，不自造说法＝H-119）
OPTIONS = [
    ('encnDic', '中英对照'),
    ('pinyin', '拼音注音'),
    ('abbrEn', '英文缩写'),
    ('phraseExt', '短语扩展'),
    ('phraseReplace', '敏感词替换'),
]


def read(path):
    if not os.path.exists(path):
        return None
    with io.open(path, encoding='utf-8', errors='replace') as f:
        return f.read()


def func_menu_body(src):
    """取 `FuncMenu()` 这个 @Builder 的函数体（按大括号配平，别用「到下一个 @Builder 为止」——会被注释打断）。"""
    i = src.find('FuncMenu() {')
    if i < 0:
        return ''
    j = src.index('{', i)
    depth = 0
    for k in range(j, len(src)):
        if src[k] == '{':
            depth += 1
        elif src[k] == '}':
            depth -= 1
            if depth == 0:
                return src[j:k + 1]
    return src[j:]


def method_body(src, name):
    # 允许 `private foo(...)`（普通方法）与 `@Builder foo(...)`（条目/面板构造器）两种声明形态。
    m = re.search(r'(?:@Builder\s+)?(?:private\s+)?%s\s*\([^)]*\)\s*(?::\s*\w+\s*)?\{' % re.escape(name), src)
    if not m:
        return ''
    j = src.index('{', m.end() - 1)
    depth = 0
    for k in range(j, len(src)):
        if src[k] == '{':
            depth += 1
        elif src[k] == '}':
            depth -= 1
            if depth == 0:
                return src[j:k + 1]
    return src[j:]


def lua_reads(opt):
    """包里是否真有滤镜读这个 option（注释行不算）。"""
    if not os.path.isdir(LUA_DIR):
        return []
    hits = []
    pat = re.compile(r'get_option\(\s*["\']%s["\']\s*\)' % re.escape(opt))
    for fn in sorted(os.listdir(LUA_DIR)):
        if not fn.endswith('.lua'):
            continue
        txt = read(os.path.join(LUA_DIR, fn)) or ''
        for n, line in enumerate(txt.split('\n'), 1):
            if pat.search(line) and not line.strip().startswith('--'):
                hits.append('%s:%d' % (fn, n))
    return hits


def declared_in_schema(opt, custom_txt):
    return bool(custom_txt and
               re.search(r'-\s*name:\s*%s\s*(?:#.*)?$' % re.escape(opt), custom_txt, re.M))


def check_all():
    src = read(KI)
    if src is None:
        return ['读不到 %s' % KI], 0
    custom = read(CUSTOM)
    if custom is None:
        return ['读不到 %s' % CUSTOM], 0
    body = func_menu_body(src)
    sync = method_body(src, 'syncEngineOptions')
    on = method_body(src, 'funcOptionOn')
    tog = method_body(src, 'toggleFuncOption')
    fails = []
    for opt, label in OPTIONS:
        # ① 菜单行
        if ("this.FuncMenuItem('%s', '%s')" % (label, opt)) not in body:
            fails.append('%s：① 菜单里没有这一行 FuncMenuItem(%r, %r)' % (opt, label, opt))
        # ②③ 镜像字段**从回填那一行推出来**（不猜命名：`pinyin` 的镜像可能叫 `pinyinAnnot`，
        #     猜名字会让守卫既漏判又误判——判据是「链」不是「命名风格」）
        m = re.search(r"this\.(\w+)\s*=\s*keyboardController\.getOption\('%s'\)" % re.escape(opt), sync)
        if not m:
            fails.append('%s：②③ syncEngineOptions 里没有 `this.X = getOption(%r)` 这条回填'
                         '（态没从引擎读＝写死默认值，键面显示的是假的）' % (opt, opt))
            continue
        ms = m.group(1)
        if not re.search(r'@State\s+%s\s*:\s*boolean' % re.escape(ms), src):
            fails.append('%s：② 回填目标 `this.%s` 不是 @State 字段 ⇒ 改了不重渲染（H-165 ③ 同款坑）'
                         % (opt, ms))
        # ④ 当前态读取点（按 name 读，不许按值传参）
        if ("case '%s':" % opt) not in on or ('return this.%s;' % ms) not in on:
            fails.append('%s：④ funcOptionOn 没有 case %r -> return this.%s（条目会冻在旧态，H-213 同款）'
                         % (opt, opt, ms))
        # ⑤ 切换
        if ("case '%s':" % opt) not in tog or ('this.%s = !cur;' % ms) not in tog:
            fails.append('%s：⑤ toggleFuncOption 没有 case %r -> this.%s = !cur（点它不做事＝假按钮）'
                         % (opt, opt, ms))
        # ⑥ 包里的滤镜真读它 + schema 声明
        hits = lua_reads(opt)
        if not hits:
            fails.append('%s：⑥ 包里没有任何 Lua 滤镜读 get_option("%s") ⇒ 引擎里换了也没人看（H-090 形态）'
                         % (opt, opt))
        if not declared_in_schema(opt, custom):
            fails.append('%s：⑥ 未在 `wubi_pinyin.custom.yaml` 的 switches 里声明 ⇒ 引擎不认这个态' % opt)
        # ⑦ 九键置灰
        wm = re.search(r'WUBI_ONLY_OPTIONS[^\n]*=\s*\[([^\]]*)\]', src, re.S)
        if not wm or ("'%s'" % opt) not in wm.group(1):
            fails.append('%s：⑦ 不在 WUBI_ONLY_OPTIONS 里 ⇒ 九键（sansheng_t9 没这些滤镜）点了没反应' % opt)
    # ⑧ 菜单里每一行的第二个参数都必须是「真的存在」的开关名
    #    （第一版只查了这五枚各自那一行，于是「多加一行但名字拼错」会静默通过＝又变回一个假按钮）
    KNOWN = set(o for o, _ in OPTIONS) | {'full_shape', 'extended_charset', 'phraseComment',
                                          'ascii_punct', 'zh_trad', 'ascii_mode'}
    for m in re.finditer(r"this\.FuncMenuItem\('([^']*)',\s*'([^']*)'\)", body):
        if m.group(2) not in KNOWN:
            fails.append('FuncMenu：菜单行「%s」指向的开关 %r 不在已知清单里（拼错＝点了没反应；'
                         '真加了新开关，就在本脚本 OPTIONS/KNOWN 里登记）' % (m.group(1), m.group(2)))
    # ⑨ 置灰名单必须真的接在条目上（只是把一个名字写进 WUBI_ONLY_OPTIONS 却没人读＝九键下照样能点，
    #    点了引擎不认＝假按钮）。FuncMenuItem 体内既要有颜色回退，也要有点击闸门。
    item = method_body(src, 'FuncMenuItem')
    if not item:
        fails.append('FuncMenuItem：找不到这个 @Builder ⇒ 菜单条目实现变了，本守卫的 ④⑤⑨ 都失去依据')
    else:
        if 'funcTileEnabled(name)' not in item:
            fails.append('FuncMenuItem：体内没有 funcTileEnabled(name) ⇒ WUBI_ONLY_OPTIONS 只是死名单，'
                         '九键下这些开关仍可点、点了没反应＝假按钮')
        # 只有颜色变灰不够——**点击闸门**必须在（`if (this.funcTileEnabled(name)) {` 那一句）
        if 'if (this.funcTileEnabled(name)) {' not in item:
            fails.append('FuncMenuItem：点击没被 funcTileEnabled 挡住 ⇒ 九键下灰字照样能点，'
                         '引擎不认这个开关，等于假按钮')
        if "this.toggleFuncOption(name" not in item:
            fails.append('FuncMenuItem：体内没有 toggleFuncOption(name, …) ⇒ 点条目不写引擎（摆了样子）')
    # ⑩ H-254（Qoder 2026-10-28 08:5x）：菜单行的按下态**不许**再挂回框架的 stateStyles(pressed)。
    #    真机实测量到的：点过一行，底色停在 #DCE2EC 不复位，直到关菜单重开——与 H-238 顶栏图标
    #    同一根因（框架 pressed 状态抬手不复位）。H-238 修过一处、散文写过一次，08:5x 在菜单行上
    #    第二次落地 ⇒ 按本仓口径从散文升级为拦截：菜单体内出现 stateStyles 的 pressed 分支即 FAIL。
    if re.search(r'stateStyles\s*\(\s*\{\s*pressed', body) or re.search(r'stateStyles\s*\(\s*\{\s*pressed', item or ''):
        fails.append('FuncMenu/FuncMenuItem：还挂着 stateStyles({pressed: …}) ⇒ 点过的行会停在按压色'
                     '（H-254 实测 (219,226,236) 不复位）。照 FuncIcon 的通路：显式 @State + onTouch')
    if 'pressedMenuItem' not in body:
        fails.append("FuncMenu：菜单行没有走 `pressedMenuItem`（显式按下态）⇒ 要么没按压反馈，"
                     "要么又回到 stateStyles 那条抬手不复位的通路（H-254）")
    # 全局：定高壳＋Scroll（契约 §3.1 r4）
    if 'Scroll()' not in body:
        fails.append('FuncMenu：内层没有 Scroll() ⇒ 加行会被 236vp 硬天花板静默裁掉（H-213/H-241r2 事故）')
    if ".height('92%')" not in body and not re.search(r"\.height\('9[0-9]%'\)", body):
        fails.append("FuncMenu：外壳不是定高（92%）⇒ 与 H-241r2 已验通路不一致，末行可能又出窗")
    return fails, len(OPTIONS)


def selftest():
    """六种坏形状必须全部判红；否则说明守卫本身不可信。"""
    src = read(KI)
    if src is None:
        print('[selftest] 读不到真树 KeyboardIndex.ets ⇒ 自测无法进行')
        return 1
    cases = []
    # 坏 1：菜单行整行删掉（摆了别的东西、其实没入口）
    cases.append(('删掉菜单行', src.replace("this.FuncMenuItem('中英对照', 'encnDic')", '// 没了')))
    # 坏 2：态写死不回填（H-090 那种「页面有一行、键面显示假的」）
    cases.append(('引擎回填被删',
                  src.replace("this.encnDic = keyboardController.getOption('encnDic');", '')))
    # 坏 3：点了不做事（只有态、没有 setOption 分支）
    cases.append(('切换分支缺失', src.replace("""      case 'abbrEn':
        this.abbrEn = !cur;
        break;""", '')))
    # 坏 4：Scroll 外壳退回硬行（加行被裁）
    cases.append(('外壳失去 Scroll', src.replace('      Scroll() {', '      Column({ space: 2 }) {', 1)))
    # 坏 5：多一行但开关名拼错（① 查的是这五枚各自那一行，拼错会静默变成又一个假按钮）
    cases.append(('菜单名拼错',
                  src.replace("this.FuncMenuItem('英文缩写', 'abbrEn')",
                              "this.FuncMenuItem('英文缩写', 'abbrEnX')")))
    # 坏 6：置灰名单写了却没人读（条目体内去掉点击闸门 ⇒ 九键下灰字照样能点）
    #      注意文件是 CRLF，所以这里用正则替换而不是带 \n 的字符串替换（第一版就是这么漏判的）
    cases.append(('置灰没接线',
                  re.sub(r'if \(this\.funcTileEnabled\(name\)\) \{', 'if (true) {', src, count=1)))
    # 坏 7：菜单行挂回 stateStyles(pressed)（H-254 的真形状：点过的行底色不收）
    cases.append(('按下态退回 stateStyles',
                  src.replace("    .backgroundColor(this.pressedMenuItem === name ? FUNC_ICON_PRESSED : Color.Transparent)",
                              "    .stateStyles({ pressed: funcIconPressed })")))
    bad = 0
    for desc, patched in cases:
        # 用「打坏的内容」判：把真树内容替换成 patched，其余文件照旧
        tmp = patched
        global ROOT
        orig_func_menu = func_menu_body
        # 直接跑逻辑：临时把 KI 的内容换掉最容易的做法是改 read() 的返回——这里用闭包代理
        real_read = read

        def fake_read(path, _c=tmp, _rr=real_read):
            if os.path.normpath(path).lower() == os.path.normpath(KI).lower():
                return _c
            return _rr(path)
        globals()['read'] = fake_read
        try:
            fails, _n = check_all()
        finally:
            globals()['read'] = real_read
        hit = bool(fails)
        print('[selftest] %-14s -> %s（FAIL %d 条：%s）'
              % (desc, 'RED 正确' if hit else 'GREEN 漏判！', len(fails),
                 (fails[0][:70] if fails else '')))
        if not hit:
            bad += 1
    if bad:
        print('H-227 自测失败: %d 个已知坏样本没被判红 ⇒ 检查本身失效，别信它的结论' % bad)
        return 1
    print('H-227 自测通过: 7 个坏形状（没入口/态写死/点了不做事/加行被裁/菜单名拼错/置灰没接线/'
          '按下态退回 stateStyles）全部判红。')
    return 0


def run_check(verbose=True):
    fails, n = check_all()
    for f in fails:
        print('[FAIL] %s' % f)
    if verbose:
        print('H-227 菜单接线守卫: %d/%d 枚开关六环齐全（① 菜单行 ② @State ③ 引擎回填 ④ 当前态 ⑤ 切换 ⑥ Lua 真读+schema 声明）⑦ 九键置灰 ⑧ 菜单行开关名在册 ⑨ 置灰接在点击闸门上 ⑩ 按下态显式持有（H-254）'
              % (n - len(set(x.split('：')[0] for x in fails)), n))
    return 1 if fails else 0


def main():
    if '--selftest' in sys.argv:
        return selftest()
    return run_check()


if __name__ == '__main__':
    sys.exit(main())
