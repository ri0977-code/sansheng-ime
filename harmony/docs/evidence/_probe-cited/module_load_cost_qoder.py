# -*- coding: utf-8 -*-
"""三端「模块加载＝首键成本」实测台架 · Qoder 2026-10-29 15:2x

主人纠的几条里最要命的一条是「安卓也卡、鸿蒙也卡，CodeArts 一直没解决」。
他给的是真手感；我这侧要给的是可复跑的数——成本到底落在哪一段。

本脚本只量一件事：**把引擎在用的那一份 Lua 滤镜/翻译器真正加载一次要多久、
它顺带读了多少字节的数据表**。这是「换窗口／新建会话就可能重来一遍」的成本，
不是「每键」成本（每键已由 win_filter_bench.py / bench_enword_translator_qoder.py
量过：0.001–0.706 ms/键，撑不起 1 秒）。

口径与局限（结论里一并带上）：
  · lupa 的 Lua 5.4 与 librime / fcitx5-rime 内嵌 Lua 同大版本，但宿主不同；
    桌面绝对值只作量级参照，跨端真正可比的是「读了多少字节／多少行」与相对倍数。
  · 不猜手机比桌面慢几倍——手机侧数字要由真机日志量（见 M-351 给的命令）。
  · 数据表按文件真实字节数计，行数用 Lua 逐行迭代计数，与生产代码同一份源码。
"""
import io
import os
import sys
import time

import lupa.lua54 as l54

CASES = [
    ('Windows 部署版滤镜', r'G:/RimeUser', r'G:/RimeUser/lua/enWord_Filter.lua',
     ['en_word_gloss.tsv', 'en_word_trans.tsv', 'en_word_rev.tsv']),
    ('Android seed 内滤镜', r'F:/dshdesktopwork/sansheng-ime-android/rime',
     r'F:/dshdesktopwork/sansheng-ime-android/rime/lua/enWord_Filter.lua',
     ['en_word_gloss.tsv', 'en_word_trans.tsv', 'en_word_rev.tsv']),
    ('鸿蒙 现树 translator',
     r'F:/qoderwork/sansheng-ime-harmony/entry/src/main/resources/rawfile/rime/lua',
     r'F:/qoderwork/sansheng-ime-harmony/entry/src/main/resources/rawfile/rime/lua/enWord_translator.lua',
     ['en_word_bucket.txt']),
]

COUNT_SRC = r'''
return function(p)
local f = io.open(p, 'rb')
if not f then return -1, 0 end
local n = 0
for _ in f:lines() do n = n + 1 end
local sz = f:seek('end')
f:close()
  return n, sz
end
'''

LOAD_SRC = r'''
return function(p)
  local f = assert(loadfile(p))
  return f()
end
'''


def main():
    counter = l54.LuaRuntime(unpack_returned_tuples=True).execute(COUNT_SRC)
    for label, root, path, data in CASES:
        print('=' * 74)
        print('%s  ←  %s' % (label, path))
        if not os.path.exists(path):
            print('  MISSING')
            continue
        print('  滤镜/翻译器本体：%d B  mtime %s' % (
            os.path.getsize(path),
            time.strftime('%m-%d %H:%M:%S', time.localtime(os.path.getmtime(path)))))
        total_bytes = total_lines = 0
        for name in data:
            fp = None
            for base in (os.path.dirname(root), root,
                         os.path.join(root, 'entry', 'src', 'main', 'resources', 'rawfile', 'rime')):
                cand = os.path.join(base, name)
                if os.path.exists(cand):
                    fp = cand
                    break
            if fp is None:
                print('    %-24s 未找到' % name)
                continue
            n, sz = int(counter(fp.replace('\\', '/'))[0]), int(counter(fp.replace('\\', '/'))[1])
            total_lines += n
            total_bytes += sz
            print('    %-24s %10d B  %8d 行' % (name, sz, n))
        print('    合计 %d B / %d 行' % (total_bytes, total_lines))

        cwd = os.getcwd()
        times = []
        err = None
        for _ in range(3):
            rt = l54.LuaRuntime(unpack_returned_tuples=True)
            fn = rt.execute(LOAD_SRC)
            os.chdir(root)
            t0 = time.perf_counter()
            try:
                fn(path.replace('\\', '/'))
                times.append((time.perf_counter() - t0) * 1000.0)
            except Exception as e:  # noqa: BLE001
                err = repr(e)[:200]
                break
        os.chdir(cwd)
        if times:
            print('  加载耗时（每次新建一个 Lua VM，3 次）：min %.0f ms / max %.0f ms'
                  % (min(times), max(times)))
        else:
            print('  加载失败：%s' % err)
    return 0


if __name__ == '__main__':
    sys.exit(main())
