# -*- coding: utf-8 -*-
"""Windows enWord_Filter 自调频台架（Qoder 2026-10-29）

目的：证明「用过谁谁在前」这条口径真的落到滤镜里，而不是只改注释。
做法：lupa 跑 Lua 5.4，dofile 待测文件，数据目录指向临时目录
      （拷贝 en_word_gloss/trans/codes 三张表，调频记录也落在临时目录，不碰 G:\\RimeUser）。
覆盖：
  1) tit 默认：tit #1、山雀 #2、秒 在后
  2) 上屏一次「秒」→ 重打 tit：秒 #1（自调频生效）
  3) 重新加载模块：调频记录仍生效（落盘）
  4) cat 默认不变：cat #1、猫 #2
  5) 上屏「戏」→ 重打 cat：戏 #1
  6) 英文本词连按：上屏 tits → tits 排到中文前
  7) c 前缀：英文仍限 5 个、拉取不爆量
  8) z 单字母：也走限量（补 2026-10-29 的单字母门）
  9) good 精确词：good #1、好的 #2
"""
import io
import os
import shutil
import tempfile

import lupa.lua54 as l54

SRC = r'F:\qoderwork\sansheng-ime-harmony\_probe\enWord_Filter.userfreq.lua'
DATA = r'G:\RimeUser'

LUA = l54.LuaRuntime(unpack_returned_tuples=True)


def setup_data_dir():
    d = tempfile.mkdtemp(prefix='enword_freq_')
    for name in ('en_word_gloss.tsv', 'en_word_trans.tsv', 'en_word_codes.txt', 'en_word_rev.tsv'):
        shutil.copyfile(os.path.join(DATA, name), os.path.join(d, name))
    return d.replace('\\', '/')


LUA.execute(r"""
OUT = {}
CALLS = 0
CB = nil
COMMITTED = ''
function yield(c) OUT[#OUT + 1] = c end
function mk(t, cm) local c = {text = t, comment = cm or ''}; c.get_genuine = function(self) return self end; return c end
function Candidate(typ, s, e, txt, cm) local c = mk(txt, cm); c.type = typ; return c end
function build(list)
  local t = {}
  for i = 1, #list do t[i] = mk(list[i]) end
  return t
end
function make_input(list)
  local i = 0
  return { iter = function(self)
    return function()
      i = i + 1
      CALLS = CALLS + 1
      return list[i]
    end
  end }
end
function new_ctx()
  CTX = {
    input = '',
    commit_notifier = { connect = function(self, fn) CB = fn; NCONNECT = (NCONNECT or 0) + 1 end },
  }
  CTX.get_commit_text = function(self) return COMMITTED end
  ENV = { engine = { context = CTX } }
  CB = nil
  return CTX
end
function run(fn, stream, raw)
  OUT = {}; CALLS = 0
  if not CTX then new_ctx() end
  CTX.input = raw
  fn(make_input(stream), ENV)
  return CTX
end
function commit(ctx, text)
  COMMITTED = text
  if CB then CB(ctx) end
end
function head(n)
  local r = {}
  for i = 1, math.min(#OUT, n or 8) do r[i] = OUT[i].text end
  return table.concat(r, ' | ')
end
function count_en(from_i)
  local n = 0
  for i = (from_i or 1), #OUT do
    if tostring(OUT[i].text):match('^[a-zA-Z]+$') then n = n + 1 end
  end
  return n
end
""")


def lua_list(items):
    t = LUA.table()
    for i, v in enumerate(items, 1):
        t[i] = v
    return t


def load(data_dir, path=SRC):
    g = LUA.globals()
    g.DATA_DIR = data_dir
    g.FILTER_PATH = path
    LUA.execute("""
CTX = nil; ENV = nil; CB = nil; NCONNECT = 0
rime = { get_api = function() return { get_user_data_dir = function(self) return DATA_DIR end } end }
ENWORD = dofile(FILTER_PATH)
""")
    return g.ENWORD


def run_case(fn, zh, en, raw):
    g = LUA.globals()
    stream = g.build(lua_list(zh + en))
    ctx = g.run(fn, stream, raw)
    return ctx


def head(n=8):
    return LUA.globals().head(n)


def commit(ctx, text):
    LUA.globals().commit(ctx, text)


def main():
    data_dir = setup_data_dir()
    freq_file = os.path.join(data_dir, 'en_word_userfreq.tsv')
    print('临时数据目录：%s' % data_dir)
    fn = load(data_dir)
    print('模块已加载')
    print()

    # 1) tit 默认
    ctx = run_case(fn, ['秒', '山雀', '题'], ['tit', 'tits', 'title', 'tithe'], 'tit')
    print('1) tit 默认            : %s' % head())
    assert head().split(' | ')[0:2] == ['tit', '山雀'], head()

    # 2) 上屏「秒」→ 重打
    commit(ctx, '秒')
    print('   调频文件已写       : %s (%d B)' % (os.path.exists(freq_file), os.path.getsize(freq_file) if os.path.exists(freq_file) else 0))
    ctx = run_case(fn, ['秒', '山雀', '题'], ['tit', 'tits', 'title', 'tithe'], 'tit')
    print('2) 按过「秒」后 tit    : %s' % head())
    assert head().split(' | ')[0] == '秒', head()

    # 3) 重新加载模块（模拟重启）后仍生效
    fn = load(data_dir)
    ctx = run_case(fn, ['秒', '山雀', '题'], ['tit', 'tits', 'title', 'tithe'], 'tit')
    print('3) 重启后重打 tit      : %s' % head())
    assert head().split(' | ')[0] == '秒', head()

    # 4) cat 默认
    ctx = run_case(fn, ['戏', '猫', '擦'], ['cat', 'cats', 'cate'], 'cat')
    print('4) cat 默认            : %s' % head())
    assert head().split(' | ')[0:2] == ['cat', '猫'], head()

    # 5) 上屏「戏」→ 重打
    commit(ctx, '戏')
    ctx = run_case(fn, ['戏', '猫', '擦'], ['cat', 'cats', 'cate'], 'cat')
    print('5) 按过「戏」后 cat    : %s' % head())
    assert head().split(' | ')[0] == '戏', head()

    # 6) 英文词连按：tits 上屏后要能压过中文（同次数按原顺序，故按两次）
    ctx = run_case(fn, ['秒', '山雀', '题'], ['tit', 'tits', 'title'], 'tit')
    commit(ctx, 'tits')
    ctx = run_case(fn, ['秒', '山雀', '题'], ['tit', 'tits', 'title'], 'tit')
    commit(ctx, 'tits')
    ctx = run_case(fn, ['秒', '山雀', '题'], ['tit', 'tits', 'title'], 'tit')
    print('6) 连按两次 tits 后 tit: %s' % head())
    assert head().split(' | ')[0] == 'tits', head()

    # 7) c 前缀限量与拉取
    # 用真实词库造 100 个 c 词，确认只出 5 个英文、拉取不爆
    words = []
    with io.open(os.path.join(DATA, 'en_word.dict.yaml'), encoding='utf-8') as f:
        for line in f:
            w = line.split('\t', 1)[0].strip()
            if w.isalpha() and w.startswith('c'):
                words.append(w.lower())
            if len(words) >= 120:
                break
    ctx = run_case(fn, ['词%02d' % i for i in range(1, 51)], words, 'c')
    g = LUA.globals()
    print('7) c：拉取 %d 条、出英文 %d 个：%s' % (int(g.CALLS), int(g.count_en(1)), head()))
    assert int(g.CALLS) <= 51 + 21, int(g.CALLS)
    assert int(g.count_en(1)) <= 5, int(g.count_en(1))

    # 8) z 单字母（非五笔码）也限量
    zs = []
    with io.open(os.path.join(DATA, 'en_word.dict.yaml'), encoding='utf-8') as f:
        for line in f:
            w = line.split('\t', 1)[0].strip()
            if w.isalpha() and w.startswith('z'):
                zs.append(w.lower())
            if len(zs) >= 120:
                break
    ctx = run_case(fn, ['词%02d' % i for i in range(1, 11)], zs, 'z')
    print('8) z：拉取 %d 条、出英文 %d 个' % (int(g.CALLS), int(g.count_en(1))))
    assert int(g.count_en(1)) <= 5, int(g.count_en(1))

    # 9) good 精确词
    ctx = run_case(fn, ['好的', '善行', '货物'], ['good', 'goods', 'goody'], 'good')
    print('9) good：%s' % head())
    assert head().split(' | ')[0:2] == ['good', '好的'], head()

    # 10) qtal（猫的五笔码）：第2位补出 cat
    ctx = run_case(fn, ['猫', '苗', '描'], [], 'qtal')
    print('10) qtal：%s' % head())
    assert head().split(' | ')[0:2] == ['猫', 'cat'], head()

    # 11) mao（拼音）：第2位补出 cat
    ctx = run_case(fn, ['猫', '毛', '冒'], ['maoism'], 'mao')
    print('11) mao：%s' % head())
    assert head().split(' | ')[0:2] == ['猫', 'cat'], head()

    # 12) 首位中文没有英文映射：不硬补
    ctx = run_case(fn, ['词01', '词02'], ['word1', 'word2'], 'gh')
    print('12) gh（无映射）：%s' % head())
    assert 'cat' not in head().split(' | '), head()

    # 13) cat 精确词场景不受补位影响（不重复）
    ctx = run_case(fn, ['戏', '猫', '擦'], ['cat', 'cats', 'cate'], 'cat')
    print('13) cat 不重复：%s' % head())
    assert head().split(' | ').count('cat') == 1, head()

    # ---- 14~16：2026-10-29 11:5x 真机双会话台架查出的三条口径 ----
    # 换一个干净的临时目录，预先塞入「猫 已用过 2 次」的记录，模拟主人的真实状态
    d2 = setup_data_dir()
    with io.open(os.path.join(d2, 'en_word_userfreq.tsv'), 'w', encoding='utf-8') as f:
        f.write('qtal\t猫\t2\t5\nqtal\tqtal\t2\t6\n')
    fn2 = load(d2)
    freq2 = os.path.join(d2, 'en_word_userfreq.tsv')

    # 14) 猫已有 2 次记录时，点一次 cat 就该上第一位（旧版按次数排，点一次永远追不上）
    ctx2 = run_case(fn2, ['猫', '独苗'], ['cat', 'only child'], 'qtal')
    print('14a) qtal 默认          : %s' % head())
    assert head().split(' | ')[0:2] == ['猫', 'cat'], head()
    commit(ctx2, 'cat')
    # 15) 同一次上屏里如果通知被触发了多次（重复挂接），只能记一笔
    nconn = int(LUA.globals().NCONNECT)
    LUA.globals().CB(ctx2)
    with io.open(freq2, encoding='utf-8') as f:
        body = f.read()
    print('15) 挂接次数=%d，重复回调后 qtal/cat 行: %s' % (
        nconn, [ln for ln in body.splitlines() if ln.startswith('qtal\tcat')]))
    assert nconn == 1, nconn                      # 同一会话只挂一次
    assert [ln for ln in body.splitlines() if ln.startswith('qtal\tcat')] == ['qtal\tcat\t1\t7'], body
    ctx2 = run_case(fn2, ['猫', '独苗'], ['cat', 'only child'], 'qtal')
    print('14b) 点过一次 cat 之后   : %s' % head())
    assert head().split(' | ')[0] == 'cat', head()

    # 16) 别的输入窗口（别的 Lua 虚拟机）写的记录，这边整文件重写时不能抹掉
    with io.open(freq2, 'a', encoding='utf-8') as f:
        f.write('mao\thair\t3\t77\n')
    commit(ctx2, '猫')
    with io.open(freq2, encoding='utf-8') as f:
        body2 = f.read()
    print('16) 别窗口写的 mao/hair 是否还在: %s' %
          [ln for ln in body2.splitlines() if ln.startswith('mao')])
    assert 'mao\thair\t3\t77' in body2, body2
    ctx2 = run_case(fn2, ['猫', '独苗'], ['cat', 'only child'], 'qtal')
    print('    再打一次 qtal        : %s' % head())
    assert head().split(' | ')[0] == '猫', head()   # 刚用了猫 → 猫回到第一位

    # 记录文件内容
    print()
    print('--- en_word_userfreq.tsv ---')
    with io.open(freq_file, encoding='utf-8') as f:
        print(f.read().strip())
    print('全部断言通过')


if __name__ == '__main__':
    main()
