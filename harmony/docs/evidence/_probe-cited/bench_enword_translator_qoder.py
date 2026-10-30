# -*- coding: utf-8 -*-
"""H-267 英文翻译器：整桶扫 vs 桶内二分 —— 离线用真 Lua 实测（Qoder 2026-10-29 14:3x）

为什么写：CodeArts 14:29:36 把 `lua_translator@enWord_translator` 整条注释掉了
（「v30 暂禁用，排查卡顿原因」）。他的判断有依据：旧实现**每按一个键把命中桶从头扫两遍**，
最大桶 's' 有 5,973 条 ⇒ 一次按键上万次字符串比较＋等量 `:lower()` 分配。
但「禁用」＝主人的英文候选没了（口径：五笔／拼音／英文占前三），所以先把成本量出来再决定。

本脚本证两件事，缺一不可：
  ① 产出逐条一致（改写没有把候选改样）——对每个查询比 (text, comment) 全序列；
  ② 成本降下来（同一台机器、同一个真 Lua、同一份桶，只换代码）。

单位口径：ms 是本机（桌面 CPU）单线程 Lua CPU 时间，只用于**前后对比**，
不代表 Mate 80 的绝对值；设备无关的硬指标是「一次按键要做多少次字符串比较」。
驱动全在 Lua 里跑（Candidate/yield 都是 Lua 函数），避免 Python↔Lua 边界污染计时。
"""
import io
import os
import sys
import time

import lupa

ROOT = r'F:\qoderwork\sansheng-ime-harmony'
LUA_DIR = os.path.join(ROOT, 'entry', 'src', 'main', 'resources', 'rawfile', 'rime', 'lua')
NEW = os.path.join(LUA_DIR, 'enWord_translator.lua')
OLD = os.path.join(ROOT, '_probe', 'rawfile-backups-20261029',
                   'enWord_translator.lua.bak-qoder-20261029-143x-before-bisect')

# 真实打字形状：把一串常用词按「逐字母前缀」展开，模拟连打（每次按键都调一遍翻译器）
WORDS = ['app', 'apple', 'application', 'cpu', 'central', 'computer', 'ok', 'okay',
         'url', 'uniform', 'string', 'strong', 'structure', 'consider', 'container',
         'create', 'dream', 'present', 'tv', 'television', 'dna', 'dynamic', 'cat',
         'category', 'vip', 'view', 'good', 'google']
EXTRA = ['ap', 'q', 'co', 'con', 'comp', 's', 'st', 'str', 'zz', 'zzz', 'zzzz',
         'abcdefgh', 'tv', 'ok', 'i', 'to', 'the']

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
  return OUT
end

local function collect(list)
  local res = {}
  for i = 1, #list do
    local o = once(list[i])
    local one = {}
    for j = 1, #o do one[j] = o[j].text .. '\001' .. o[j].comment end
    res[i] = table.concat(one, '\002')
  end
  return res
end

local queries = QUERY_PLACEHOLDER

-- 冷启动：第一次调用里含「读桶＋建索引」
local t0 = os.clock()
once(queries[1])
local cold_ms = (os.clock() - t0) * 1000
collectgarbage("collect")
local mem_kb = collectgarbage("count")

-- 稳态：后面每次按键的成本（先跑一轮热身排除 JIT/GC 首帧噪声）
once('apple')
local t1 = os.clock()
for rep = 1, 20 do
  for i = 1, #queries do once(queries[i]) end
end
local hot_ms = (os.clock() - t1) * 1000 / (20 * #queries)

return {cold = cold_ms, per_key = hot_ms, mem = mem_kb, outs = collect(queries), n = #queries}
'''


def main():
    if not (os.path.exists(NEW) and os.path.exists(OLD)):
        print('FAIL 缺被测文件'); return 1
    queries = []
    for w in WORDS:
        for n in range(2, len(w) + 1):
            q = w[:n].lower()
            if q not in queries:
                queries.append(q)
    for q in EXTRA:
        if q not in queries:
            queries.append(q)

    # 可命令行指定被测／对照文件（撞车时要能拿任意两份对比）：
    #   python _probe/bench_enword_translator_qoder.py [新文件] [对照文件]
    if len(sys.argv) >= 2:
        globals()['NEW'] = os.path.abspath(sys.argv[1])
    if len(sys.argv) >= 3:
        globals()['OLD'] = os.path.abspath(sys.argv[2])
    os.chdir(LUA_DIR)   # debug.getinfo 拿不到真路径 ⇒ 走 './' 兜底，读的就是被测的桶
    print('查询数（模拟连打的每次按键）：%d' % len(queries))
    print('被测新版：%s（%d B）' % (os.path.relpath(NEW, ROOT), os.path.getsize(NEW)))
    print('对照旧版：%s（%d B）' % (os.path.relpath(OLD, ROOT), os.path.getsize(OLD)))

    results = {}
    for tag, path in (('old', OLD), ('new', NEW)):
        rt = lupa.LuaRuntime(unpack_returned_tuples=True)
        q_lua = '({' + ','.join('"%s"' % q for q in queries) + '})'
        src = io.open(path, encoding='utf-8').read()
        assert ']==]' not in src
        prog = DRIVER.replace('SRC_PLACEHOLDER', '[==[' + src + ']==]').replace('QUERY_PLACEHOLDER', q_lua)
        t_wall = time.time()
        res = rt.execute(prog)
        results[tag] = {
            'cold': float(res['cold']),
            'per_key': float(res['per_key']),
            'mem': float(res['mem']),
            'outs': [str(res['outs'][i]) for i in range(1, len(queries) + 1)],
            'wall': time.time() - t_wall,
        }

    old, new = results['old'], results['new']
    print()
    print('冷启动（首次调用＝读桶＋建表＋排序）：旧 %.1f ms  新 %.1f ms'
          % (old['cold'], new['cold']))
    print('常驻内存（建完索引后 Lua GC 计量）： 旧 %.0f KB  新 %.0f KB'
          % (old['mem'], new['mem']))
    print('稳态每按键：                       旧 %.3f ms  新 %.3f ms  ⇒ %s%.1f×'
          % (old['per_key'], new['per_key'], '降 ' if new['per_key'] < old['per_key'] else '不降！',
             (old['per_key'] / new['per_key']) if new['per_key'] > 0 else 0))

    fails = []
    diff = 0
    for i, q in enumerate(queries):
        if old['outs'][i] != new['outs'][i]:
            diff += 1
            if diff <= 5:
                print('DIFF %-10s 旧: %s' % (q, old['outs'][i].replace('\001', '/').replace('\002', ' | ')))
                print('     %-10s 新: %s' % ('', new['outs'][i].replace('\001', '/').replace('\002', ' | ')))
    if diff:
        fails.append('%d 个查询的新旧产出不一致' % diff)

    # 语义底线（新版必须仍然满足主人的口径）
    for i, q in enumerate(queries):
        cands = [c.split('\001') for c in new['outs'][i].split('\002') if c] if new['outs'][i] else []
        en = [c for c in cands if c[0][:1].isascii()]
        if len(en) > 6:
            fails.append('%s：英文候选 %d 条超名额' % (q, len(en)))
        if len(cands) > 7:
            fails.append('%s：总候选 %d 条超上限' % (q, len(cands)))
    if new['per_key'] >= old['per_key']:
        fails.append('每按键成本没有下降（%.3f ≥ %.3f）——改写白做' % (new['per_key'], old['per_key']))

    print()
    if fails:
        for f in fails:
            print('FAIL ' + f)
        return 1
    print('PASS 产出逐条一致（%d 个查询），每按键 Lua CPU 时间 %.3f ms → %.3f ms；'
          '冷启动 %.1f ms → %.1f ms'
          % (len(queries), old['per_key'], new['per_key'], old['cold'], new['cold']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
