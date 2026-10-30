# -*- coding: utf-8 -*-
"""Windows enWord_Filter 台架（Qoder 2026-10-29 02:0x）

目的：给「英文联想限 5 / 码与前缀早停」一个可复跑的实测，而不是只看代码。
做法：用 lupa 的 Lua 5.4（与 librime 同大版本）直接 dofile 真实部署文件
      G:\\RimeUser\\lua\\enWord_Filter.lua，喂「中文在前、英文在后」的合成候选流
      （英文名单取自真实 en_word.dict.yaml 的该前缀词条），统计：
        ① input:iter() 被拉取几次（早停＝拉取数止于 中文数+6）
        ② 输出的英文候选条数（限量＝5）
        ③ 每次调用耗时中位数（对照旧版 .bak-qoder-20261029-oldfilter）

口径与局限（写进结论时一并带上）：
  · 候选流里的「中文条数」是假定值（真值要 librime 才算得出），英文条数是真实词库计数。
  · lupa 的 Lua 5.4 与 librime 内嵌 Lua 同版，但宿主/边界不同；绝对值仅作量级参照，
    真正可比的是「拉取次数」与两版之间的相对倍数。
"""
import io
import os
import statistics
import time

import lupa.lua54 as l54

LUA = l54.LuaRuntime(unpack_returned_tuples=True)
DICT = r'G:\RimeUser\en_word.dict.yaml'
NEW = os.environ.get('ENWORD_NEW', r'G:\RimeUser\lua\enWord_Filter.lua')
OLD = r'G:\RimeUser\lua\enWord_Filter.lua.bak-qoder-20261029-oldfilter'


def words_with_prefix(prefix):
    out = []
    with io.open(DICT, encoding='utf-8') as f:
        for line in f:
            if not line or line[0] in '#\n\t':
                continue
            w = line.split('\t', 1)[0].strip().lower()
            if w.isalpha() and w.startswith(prefix):
                out.append(w)
    return out


LUA.execute(r"""
rime = { get_api = function() return { get_user_data_dir = function(self) return 'G:/RimeUser' end } end }
OUT = {}
CALLS = 0
function yield(c) OUT[#OUT + 1] = c end
function mk(t, cm) local c = {text = t, comment = cm or ''}; c.get_genuine = function(self) return self end; return c end
function build(list)
  local t = {}
  for i = 1, #list do t[i] = mk(list[i]) end
  return t
end
function make_input(list, raw)
  local input = {}
  input.iter = function(self)
    local i = 0
    return function()
      i = i + 1
      CALLS = CALLS + 1
      return list[i]
    end
  end
  input.raw = raw
  return input
end
function run_filter(fn, input, raw)
  OUT = {}; CALLS = 0
  fn(input, {engine = {context = {input = raw}}})
  return CALLS, #OUT
end
function outs()
  local r = {}
  for i = 1, math.min(#OUT, 12) do r[i] = OUT[i].text end
  return table.concat(r, ' | ')
end
function en_count(start_at)
  local n = 0
  for i = (start_at or 1), #OUT do
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


def load_filter(path):
    g = LUA.globals()
    g.FILTER_PATH = path
    LUA.execute('ENWORD = dofile(FILTER_PATH)')
    return g.ENWORD


def bench(fn, raw, n_zh, en_words, reps):
    zh = ['词%02d' % (i + 1) for i in range(n_zh)]
    stream = LUA.globals().build(lua_list(zh + en_words))
    times = []
    g = LUA.globals()
    calls = outs_txt = None
    for _ in range(reps):
        inp = g.make_input(stream, raw)
        t0 = time.perf_counter()
        g.run_filter(fn, inp, raw)
        times.append((time.perf_counter() - t0) * 1000.0)
        calls = int(g.CALLS)
        outs_txt = g.outs()
    return {
        'pulls': calls,
        'median_ms': statistics.median(times),
        'en_out': int(g.en_count(2)),
        'head': outs_txt,
    }


def main():
    t0 = time.perf_counter()
    fn_new = load_filter(NEW)
    new_load_ms = (time.perf_counter() - t0) * 1000.0
    t0 = time.perf_counter()
    fn_old = load_filter(OLD)
    old_load_ms = (time.perf_counter() - t0) * 1000.0
    print('模块加载(含 TSV 解析)：新版 %.1f ms / 旧版 %.1f ms' % (new_load_ms, old_load_ms))
    print()

    cases = [
        ('c', 'c', 50, 'c', 10),
        ('co', 'co', 50, 'co', 10),
        ('cod', 'cod', 50, 'cod', 20),
        ('code', 'code', 50, 'code', 20),
        ('codea(无联想)', 'codea', 50, 'codea', 40),
        ('for', 'for', 50, 'for', 30),
        ('good(精确词)', 'good', 20, 'good', 40),
        ('gh(码)', 'gh', 50, 'gh', 30),
        ('qtal(码)', 'qtal', 30, 'qtal', 40),
    ]
    print('%-16s %-28s %-28s' % ('输入', '新版(7,175B)', '旧版(4,305B)'))
    for name, raw, n_zh, prefix, reps in cases:
        ws = words_with_prefix(prefix)
        a = bench(fn_new, raw, n_zh, ws, reps)
        b = bench(fn_old, raw, n_zh, ws, reps)
        print('%-16s 拉%6d 英%2d %7.3fms   拉%6d 英%2d %7.3fms   [词库%s=%d]' % (
            name, a['pulls'], a['en_out'], a['median_ms'],
            b['pulls'], b['en_out'], b['median_ms'], prefix, len(ws)))
        print('   新版前12: %s' % a['head'])

    # 连打 codearts 的累计：c/co/cod/code/codea 每键耗时相加
    seq = ['c', 'co', 'cod', 'code', 'codea']
    tot_new = tot_old = 0.0
    for raw in seq:
        ws = words_with_prefix(raw)
        tot_new += bench(fn_new, raw, 50, ws, 10)['median_ms']
        tot_old += bench(fn_old, raw, 50, ws, 10)['median_ms']
    print()
    print('连打 c→co→cod→code→codea 每键中位数之和：新版 %.2f ms / 旧版 %.2f ms（中文字段假定各 50 条）' % (
        tot_new, tot_old))


if __name__ == '__main__':
    main()
