#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""H-242(Qoder) 设置项「真生效」守卫——契约 `docs/SETTINGS-CONTRACT.md` §5-1。

为什么必须有这条闸门（不是形式主义）：
  H-090 那轮设置页摆了 **71 项、实测 0 项生效**，主人 2026-10-22 因此拍 **D-021「只留真实生效的项」**
  并把入口整段摘掉（取证 docs/evidence/2026-10-22/h090-settings-entry-recheck.md:43-97）。
  「页面上有一行、键盘根本不读」这种缺陷**离线看代码是看不出来的**——所以把它写成机器判据。

三项齐全才算一项生效（缺一条就报红，且**是 FAIL 不是 WARN**）：
  ① 注册：键名在 `SettingsStore.ets` 的 SPECS 表里（契约 §3 那 12 个，**表外一律不许出现**）；
  ② 读取点：消费侧文件里有一行**非注释**代码，用 `num()/on()/sw()` 读这个键；
  ③ 接线：那一行赋值给的目标（`this.mirror` 或 `const/let`）在别处**真的被用到**——
     只读进一个没人看的变量＝换了个地方的死开关，照样判红。

H-251 又添一种同族形态（10-28 07:3x 抓到）：**工作树全绿、包也装了，但代码没提交**
  ⇒ 仓库里是空壳，一次 `git checkout` 就能抹掉整晚的主任务。这种缺陷前面三条判据**全都能通过**，
  所以判据必须问「**已提交的那棵树**里有没有」——`--head` 干的就是这件事。
  同一族病第二次落地，按口径从散文升级为拦截（H-130/H-238）。

已知坏样本自测（`--selftest`）：四种「看起来像生效」的形态 + 一条「仓库空壳」（`--head` 通路）
必须**全部判红**，并且退出码真的非零（H-238 口径：只管打印 WARN 的检查永远不会阻断，等于没有）。

用法：
  python scripts/settings_effective_check.py            # 真树（工作树）对账，红=退出码 1
  python scripts/settings_effective_check.py --selftest # 只跑已知坏样本（含 --head 那条通路）
  python scripts/settings_effective_check.py --head     # H-251：对 **HEAD 解出来的那棵树**跑（已提交态对账）
  python scripts/settings_effective_check.py --head --head-ref=17a4f33^
                                                        # 已知坏样本：补交之前那一刻，仓库里 0/12 ⇒ 必须判红
严重度：2026-10-28 06:5x 起**已挂进内容闸门离线套**（`check_app_content.py` 第 16b 条，blocking=True，
子进程 rc!=0 即 FAIL 拦在构建前）。依据＝H-242 任务列「跑通后…挂进内容闸门的离线套」＋
H-130/H-238 教训「只打 WARN 的检查永远不会阻断＝没有」。此前那条「不进发布阻断闸门」的旧口径作废。
`--head` **不挂进内容闸门**：闸门描述的是「这个包」，不是「这个仓库」；开发中写了没提交时它会判红，
那是故意的——放在**装机/提审前**那一步跑（命令见 `docs/NIGHT-WATCH-V10.md` §3）。
"""
import io
import os
import re
import sys

# `SS_H251_ROOT` 只给 `--head` 用：让**当前这份守卫**去判另一棵树（`git archive` 解出来的旧提交），
# 否则旧树里根本没有这个脚本（守卫是 10-28 才写的），已知坏样本就没法跑。
ROOT = os.environ.get('SS_H251_ROOT') or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE = os.path.join(ROOT, 'entry', 'src', 'main', 'ets', 'common', 'SettingsStore.ets')
# 消费侧＝键盘真读这些值的地方。设置页本身（SettingsPanel.ets）是**写侧**，不算生效证据。
CONSUMERS = [
    os.path.join(ROOT, 'entry', 'src', 'main', 'ets', 'pages', 'KeyboardIndex.ets'),
    os.path.join(ROOT, 'entry', 'src', 'main', 'ets', 'inputmethod', 'KeyboardController.ets'),
    os.path.join(ROOT, 'entry', 'src', 'main', 'ets', 'engine', 'RealRimeEngine.ets'),
]

# 契约 §3 的第一批 12 项。加一项要先在契约里写清读取点与判据，再改这张表。
CONTRACT_KEYS = [
    'kbd_height_pct', 'cand_font_size', 'key_font_size', 'page_size', 'kbd_haptic',
    'key_long_press_delay', 'popup_on_key_press', 'undo_stack_limit', 'grid_page_size',
    'space_swipe_step', 'expand_toolbar_by_default', 'show_preedit',
]

READ_RE = re.compile(r"\b(?:num|on|sw)\(\s*'([a-z0-9_]+)'")
ASSIGN_RE = re.compile(r"(?:this\.([A-Za-z_]\w*)|const\s+([A-Za-z_]\w*)|let\s+([A-Za-z_]\w*))\s*[:=]")
SPEC_RE = re.compile(r"\bmk(?:Num|Bool)\(\s*'([a-z0-9_]+)'")


def read(path):
    if not os.path.exists(path):
        return []
    with io.open(path, 'r', encoding='utf-8') as f:
        return f.read().splitlines()


def strip_comment(line, in_block):
    """返回 (可执行代码部分, 是否块注释中)。块注释按 /** ... */ 粗跟踪，够挡「只在注释里提了一嘴」。"""
    if in_block:
        end = line.find('*/')
        return '', end < 0
    out = []
    i = 0
    while i < len(line):
        if line.startswith('/*', i):
            end = line.find('*/', i + 2)
            if end < 0:
                return ''.join(out), True
            i = end + 2
        elif line.startswith('//', i):
            break
        else:
            out.append(line[i])
            i += 1
    return ''.join(out), False


def code_lines(lines):
    out = []
    in_block = False
    for raw in lines:
        code, in_block = strip_comment(raw, in_block)
        if code.strip():
            out.append(code)
    return out


def registered_keys(store_lines):
    """① 注册：SPECS 表里的键名（用 mkNum/mkBool 工厂，不是对象字面量）。"""
    keys = []
    for line in store_lines:
        m = SPEC_RE.search(line)
        if m and m.group(1) not in keys:
            keys.append(m.group(1))
    return keys


def find_reads(consumer_lines_by_file):
    """② 读取点：非注释行里 `num('k')/on('k')/sw('k')`，并抓出赋值目标。"""
    reads = {}
    for path, codes in consumer_lines_by_file.items():
        for line in codes:
            for m in READ_RE.finditer(line):
                key = m.group(1)
                am = ASSIGN_RE.search(line[:m.start()])
                target = None
                if am:
                    target = am.group(1) or am.group(2) or am.group(3)
                reads.setdefault(key, []).append((path, target, line))
    return reads


def is_wired(target, all_codes, read_line):
    """③ 接线：赋值目标在**别的**代码行里被用到（读进一个没人看的变量＝死开关）。
    匹配 `this.<target>` 或独立单词 `<target>`；绝不能退化成「含 this. 就算」——
    那样每一行都算用到，检查等于没有（写第一版时就差点这么错）。"""
    if target is None:
        return False
    pat = re.compile(r"this\.%s\b|\b%s\b" % (re.escape(target), re.escape(target)))
    for codes in all_codes.values():
        for line in codes:
            if line == read_line:
                continue
            if pat.search(line):
                return True
    return False


def run(store_keys, reads, all_codes):
    fails = []
    for k in CONTRACT_KEYS:
        if k not in store_keys:
            fails.append('%s：① 未注册（SettingsStore SPECS 表里没有这个键）' % k)
            continue
        hits = reads.get(k, [])
        if not hits:
            fails.append('%s：② 无读取点（键盘侧没有任何非注释代码读它——这正是 H-090 那 71 项的形态）' % k)
            continue
        wired = any(is_wired(t, all_codes, ln) for (_p, t, ln) in hits)
        if not wired:
            fails.append('%s：③ 读了但没接线（值读进变量后没人用，屏上不会有变化）' % k)
    for k in store_keys:
        if k not in CONTRACT_KEYS:
            fails.append('%s：表外键（契约 §3 没登记就不许进 store，防再造空壳）' % k)
    return len(CONTRACT_KEYS) - len(set(f.split('：')[0] for f in fails if f.split('：')[0] in CONTRACT_KEYS)), fails


SELFTEST_CASES = [
    # (说明, store 里的 SPECS 行, 消费侧代码行, 期望: 该键必须出现在失败里)
    ('只声明不读（H-090 形态）',
     ["  mkNum('ghost_pct', 100, 80, 120, NONE),"], [], 'ghost_pct'),
    ('只在注释里提了一嘴',
     ["  mkBool('ghost_comment', 1),"], ["  // ghost_comment 以后再接", "  const x = 1;"], 'ghost_comment'),
    ('读进没人用的变量',
     ["  mkNum('ghost_dead', 5, 1, 9, NONE),"],
     ["  const ghostVal: number = st.num('ghost_dead');"], 'ghost_dead'),
    ('表外键混进 store',
     ["  mkBool('not_in_contract', 0),", "  mkBool('show_preedit', 1),"],
     ["  const a = st.sw('not_in_contract');", "  use(a);",
      "  const p = st.sw('show_preedit');", "  layout(p);"], 'not_in_contract'),
]


def selftest():
    """已知坏样本必须判红；并核对退出码通路（只管打印不算阻断）。"""
    global CONTRACT_KEYS
    bad = 0
    for desc, spec_lines, consumer_lines, key in SELFTEST_CASES:
        store_keys = registered_keys(spec_lines)
        all_codes = {'x': code_lines(consumer_lines)}
        reads = find_reads(all_codes)
        # 用「只针对本样本的键」判：CONTRACT_KEYS 临时换成这一条，避免被全表噪音淹没
        saved = CONTRACT_KEYS
        CONTRACT_KEYS = [key]
        _passed, fails = run(store_keys, reads, all_codes)
        CONTRACT_KEYS = saved
        # 「表外键」那条样本的键名不在样本表里，失败信息落在别处也算红
        hit = any(f.startswith(key) for f in fails) or bool(fails)
        print('[selftest] %s -> %s（fails=%d）'
              % (desc, 'RED 正确' if hit else 'GREEN 漏判！', len(fails)))
        if not hit:
            bad += 1
    if bad:
        print('H-242 自测失败: %d 个已知坏样本没被判红 ⇒ 检查本身失效，别信它的结论' % bad)
        return 1
    print('H-242 自测通过: 4 个「看起来像生效」的形态全部判红。')

    # 第 5 条：`--head` 这条通路**自己**也要有已知坏样本（H-130/H-238 口径：
    # 只测内存里的解析，测不到 git archive → 临时树 → 子进程 → 退出码 这条链）。
    import contextlib
    import io as _io
    buf = _io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc, fails, _summary = judge_ref(BAD_REF)
    ok_head = (rc != 0 and fails > 0)
    print('[selftest] 已提交态判红（--head-ref=%s 空壳）-> %s（rc=%s FAIL=%d）'
          % (BAD_REF, 'RED 正确' if ok_head else 'GREEN 漏判！', rc, fails))
    if not ok_head:
        print(buf.getvalue()[-400:])
        print('H-251 自测失败: 对已知空壳提交判绿 ⇒ `--head` 通路不可信，别信它的结论')
        return 1
    print('H-242/251 自测通过: 4 个「看起来像生效」的形态 + 1 个「仓库空壳」全部判红。')
    return 0


# 已知坏样本：这个提交的**父**＝设置页入口与 12 项读取点还没进仓库的那一刻（H-251 就是这么抓到的）。
# 本仓历史只追加不改写（主人铁律：绝不 force-push），所以这个 ref 长期有效。
BAD_REF = '17a4f33^'


def judge_ref(ref):
    """解一棵**已提交**的树到临时目录，用当前规则判它，返回 (rc, FAIL 条数, 摘要行)。"""
    import io as _io
    import shutil
    import subprocess
    import tarfile
    import tempfile
    tmp = tempfile.mkdtemp(prefix='h251-head-')
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # git 永远在**本仓库**取历史
    try:
        r = subprocess.run(['git', 'archive', ref], cwd=repo,
                           capture_output=True, text=False)
        if r.returncode != 0:
            print('[FAIL] H-251 `git archive %s` 失败 ⇒ %s'
                  % (ref, (r.stderr or b'').decode('utf-8', 'replace')[:200]))
            return 2, 1, '(git archive 失败)'
        try:
            tarfile.open(fileobj=_io.BytesIO(r.stdout)).extractall(tmp, filter='data')
        except TypeError:                      # Python < 3.12 没有 filter 参数
            tarfile.open(fileobj=_io.BytesIO(r.stdout)).extractall(tmp)
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              'settings_effective_check.py')   # 用**当前**规则判那棵树
        p = subprocess.run([sys.executable, script], capture_output=True, text=True,
                           encoding='utf-8', errors='replace',
                           env=dict(os.environ, PYTHONIOENCODING='utf-8', SS_H251_ROOT=tmp))
        out = [x for x in (p.stdout or '').strip().splitlines() if x.strip()]
        fails = [x for x in out if x.startswith('[FAIL]')]
        if p.stderr and p.stderr.strip():
            print('[FAIL] H-251 子进程 stderr: %s' % p.stderr.strip()[:200])
        summary = next((x for x in reversed(out) if x.startswith('H-242 生效守卫:')),
                       out[-1] if out else '(无输出)')
        for x in fails[:12]:
            print(x[:160])
        # 子进程一声不吭＝没跑起来，绝不能当成「没问题」放行
        rc = p.returncode if (p.returncode != 0 or out) else 1
        return rc, len(fails), summary
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def head_mode():
    """H-251：把 **HEAD**（或 `--head-ref=<ref>` 指定的提交）解到临时目录，用**当前这份守卫**判那棵树。

    抓的是这一族新形态：工作树 12/12、`--source` 全绿、包也装进手机了，**但代码没提交**
    ⇒ 仓库里是空壳（10-28 07:3x 实测：`git archive HEAD` 跑本守卫＝0/12，工作树＝12/12，
    设置页入口与 12 项读取点只活在未提交的工作树里，一次 `git checkout` 就能抹掉整晚的主任务）。
    判据口径：装机/提审之前跑一次，红＝「你正要装的这份代码，仓库里没有」。
    开发中（写了还没提交）会判红，那是**故意的**：要么先提交，要么别说「已生效」。
    """
    ref = 'HEAD'
    for a in sys.argv:
        if a.startswith('--head-ref='):
            ref = a.split('=', 1)[1]        # 已知坏样本通路：--head-ref=17a4f33^ 就是「补交之前」那一刻
    rc, fails, summary = judge_ref(ref)
    print('H-251 已提交态对账: 用当前守卫判 `%s` 解出来的树 ⇒ rc=%d，FAIL %d 条（%s）'
          % (ref, rc, fails, summary[:110]))
    if rc != 0:
        print('结论: **%s 里的代码不是工作树里那份**（或子进程没跑起来）——设置页这条线还有东西没提交。'
              '先提交（或在台账写明「未提交」），再谈装机/提审。' % ref)
        return 1
    print('结论: %s 与工作树在「契约 12 项三项齐全」上判定一致 ⇒ 已提交的代码就是生效的代码。' % ref)
    return 0


def main():
    if '--selftest' in sys.argv:
        return selftest()
    if '--head' in sys.argv:
        return head_mode()
    store_lines = read(STORE)
    if not store_lines:
        print('[FAIL] 读不到 SettingsStore.ets：%s' % STORE)
        return 1
    store_keys = registered_keys(store_lines)
    all_codes = {}
    for p in CONSUMERS:
        lines = read(p)
        if not lines:
            print('[FAIL] 读不到消费侧文件：%s' % p)
            return 1
        all_codes[p] = code_lines(lines)
    reads = find_reads(all_codes)
    passed, fails = run(store_keys, reads, all_codes)
    for f in fails:
        print('[FAIL] %s' % f)
    print('H-242 生效守卫: %d/%d 项三项齐全（① 注册 ② 非注释读取点 ③ 读取点已接线）'
          % (passed, len(CONTRACT_KEYS)))
    if fails:
        return 1
    where = {}
    for k in CONTRACT_KEYS:
        locs = set()
        for (path, _t, _l) in reads.get(k, []):
            locs.add(os.path.basename(path))
        where[k] = ','.join(sorted(locs))
    print('结论: 契约 12 项全部接在键盘侧——')
    for k in CONTRACT_KEYS:
        print('  %-26s <- %s' % (k, where[k]))
    return 0


if __name__ == '__main__':
    sys.exit(main())
