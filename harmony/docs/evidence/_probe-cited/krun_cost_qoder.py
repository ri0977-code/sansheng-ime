# -*- coding: utf-8 -*-
"""连打 k 的成本实测 · Qoder 2026-10-29 15:3x

主人 15:2x 在部署后连打了 22 个 k（「看我部署后打了多少个 k」），CodeArts 15:24:49
据此下的结论是「v34 的前缀联想 for-pairs 整桶扫 O(n) ＝ 卡顿根因」，并写 v35 把前缀联想
整段删掉。这个判断对不对，要用同一个真 Lua、同一份桶、同一种打字形状量出来，不能靠说。

本脚本对每个版本分别报四个数：
  ① 首键触发读桶的那一次成本（load_ms）——这是「开始打要等一下」那一段；
  ② 连打 22 个 k 的总 Lua CPU 时间（sum_ms）与最慢一键（max_ms）；
  ③ 每一键出几条候选（app / kkkkk 两条探针的输出文本）——用来判「删联想」删掉了什么口径。

单位口径（写进结论时一并带上）：桌面单机单线程 Lua CPU 时间，只用于版本之间对比，
不是 Mate 80 的绝对值；跨端可比的硬指标是「这一键要做多少次字符串比较／读了多少字节」。
"""
import io
import os
import sys

import lupa

ROOT = r'F:\qoderwork\sansheng-ime-harmony'
LUA_DIR = os.path.join(ROOT, 'entry', 'src', 'main', 'resources', 'rawfile', 'rime', 'lua')
BK = os.path.join(ROOT, '_probe', 'rawfile-backups-20261029')

VERSIONS = [
    ('v35 现树(精确only)', os.path.join(LUA_DIR, 'enWord_translator.lua')),
    ('v34 peer', os.path.join(BK, 'enWord_translator.lua.peer-v34-20261029-150548')),
    ('v33 peer', os.path.join(BK, 'enWord_translator.lua.peer-v33-20261029-145736')),
    ('v32 qoder索引', os.path.join(ROOT, '_probe', 'patches-20261029', 'enWord_translator.lua.qoder-v32-indexed')),
    ('基线6478', os.path.join(BK, 'enWord_translator.lua.bak-qoder-20261029-143x-before-bisect')),
]

DRIVER = r'''
local src = SRC_PLACEHOLDER
local OUT = {}
function Candidate(kind, start, stop, text, comment)
  OUT[#OUT + 1] = {text = tostring(text), comment = tostring(comment)}
  return {}
end
function yield(c) return nil end

local mod = assert(load(src))()

local function once(input)
  OUT = {}
  local seg = {start = 0, _end = #input}
  mod(input, seg)
  local one = {}
  for j = 1, #OUT do one[j] = OUT[j].text .. '[' .. OUT[j].comment .. ']' end
  return table.concat(one, ' '), #OUT
end

-- ① 首键成本：拿一个 5 字母输入去触发读桶（各版本读桶时机不同，这里统一探一次）
local t0 = os.clock()
local s1, n1 = once('kkkkk')
local load_ms = (os.clock() - t0) * 1000

-- ② 主人那一串：连打 1..22 个 k，逐键计时（os.clock 粒度只有 1 ms ⇒ 每键重复 REP 次取均值）
local REP = 200
local times = {}
local cnts = {}
for i = 1, 22 do
  local t = os.clock()
  for r = 1, REP do once(string.rep('k', i)) end
  times[i] = (os.clock() - t) * 1000 / REP
  local _, n = once(string.rep('k', i))
  cnts[i] = n
end

-- 最坏前缀：'s' 桶 5,973 条且没有以 sxxyz 开头的词 ⇒ 整桶扫到底
local worstq = 'sxxyz'
local t2 = os.clock()
for r = 1, REP do once(worstq) end
local worst_ms = (os.clock() - t2) * 1000 / REP
local worst_n = select(2, once(worstq))

-- ③ 产出探针
local probes = {}
for _, q in ipairs({'app', 'kkkkk', 'cpu', 'appl'}) do
  local s, n = once(q)
  probes[q] = {n, s}
end

local sum = 0
local mx = 0
for i = 1, 22 do sum = sum + times[i]; if times[i] > mx then mx = times[i] end end

return {load = load_ms, sum = sum, max = mx, worst = worst_ms, worstn = worst_n,
        first5 = times, cnt22 = cnts[22], probes = probes, mem = collectgarbage('count')}
'''


def main():
    os.chdir(LUA_DIR)
    print('%-20s %8s %9s %9s %9s %7s %7s' % ('version', 'load_ms', '22键sum', 'max键', 's桶最坏', 'cand@22', 'mem_KB'))
    print('-' * 72)
    rows = []
    for label, path in VERSIONS:
        if not os.path.exists(path):
            print('%-20s MISSING %s' % (label, path))
            continue
        src = io.open(path, encoding='utf-8').read()
        assert ']==]' not in src, path
        rt = lupa.LuaRuntime(unpack_returned_tuples=True)
        prog = DRIVER.replace('SRC_PLACEHOLDER', '[==[' + src + ']==]')
        r = rt.execute(prog)
        load = float(r['load']); summ = float(r['sum']); mx = float(r['max'])
        c22 = int(r['cnt22']); mem = float(r['mem'])
        worst = float(r['worst'])
        print('%-20s %8.0f %9.2f %9.3f %9.3f %7d %7.0f' % (label, load, summ, mx, worst, c22, mem))
        rows.append((label, path, r))
    print()
    print('== 产出探针（判「删联想」删掉了什么）==')
    for label, path, r in rows:
        p = r['probes']
        for q in ('app', 'appl', 'kkkkk'):
            one = p[q]
            n = int(one[1])
            txt = str(one[2])
            print('%-20s %-6s n=%d  %s' % (label, q, n, txt[:150]))
        print()
    return 0


if __name__ == '__main__':
    sys.exit(main())
