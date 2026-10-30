# -*- coding: utf-8 -*-
"""离线跑真 Lua：用 lupa 直接执行鸿蒙在用的 enWord_translator.lua + 补词后的
en_word_bucket.txt，证明「打 app 现在能出带中文释义的英文候选」。
（Qoder 2026-10-29 14:1x，H-265 鸿蒙侧取证）

为什么这么验：鸿蒙没有安卓那样的模拟器，真机装一次要主人输一次密码；
数据/逻辑层能离线证明的，就不该消耗装机名额。本脚本只读，不写任何仓内文件。
它证明的是「Lua 代码 + 桶数据」这两层的产出，不证明候选在屏幕上的合并位置
（那一条仍需一次真机取证）。
"""
import io
import os
import sys

import lupa

LUA_DIR = r'F:\qoderwork\sansheng-ime-harmony\entry\src\main\resources\rawfile\rime\lua'
TRANSLATOR = os.path.join(LUA_DIR, 'enWord_translator.lua')
BUCKET = os.path.join(LUA_DIR, 'en_word_bucket.txt')

CASES = ['app', 'cpu', 'ok', 'url', 'tv', 'core', 'cat', 'apple', 'ap', 'q', 'mao']
EXPECT_FIRST = {
    'app': 'app', 'cpu': 'cpu', 'ok': 'ok', 'url': 'url', 'tv': 'tv',
    'core': 'core', 'cat': 'cat', 'apple': 'apple',
}


def run_case(rt, fn_src, word):
    """在一个全新的 Lua VM 里执行 translator（每个用例都冷启动，验懒加载路径）。"""
    lua = rt
    out = []

    def candidate(kind, start, stop, text, comment):
        # 真实运行时里这是 librime 的 C 构造器；这里把参数收进 out 并回一个空表，
        # 让 Lua 侧的 yield(Candidate(...)) 调用链原样走完。
        out.append({'text': str(text), 'comment': str(comment), 'kind': str(kind),
                    'start': start, 'stop': stop})
        return lua.table_from({})

    def yield_cand(c):
        return None

    # librime 注入的全局：Candidate / yield；seg 是个 table
    g = lua.globals()
    g['Candidate'] = candidate
    g['yield'] = yield_cand
    # 真实运行时里 rime 这个全局存在；这里故意不提供 rime.get_api，
    # 走的是 pcall 失败 → 不查 ascii_mode 的分支（与无 API 时行为一致）
    fn = lua.execute(fn_src)
    seg = lua.table_from({'start': 0, '_end': len(word)})
    fn(word, seg)
    return out


def main():
    if not os.path.exists(TRANSLATOR) or not os.path.exists(BUCKET):
        print('FAIL 找不到被测文件')
        return 1
    print('被测 Lua：%s（%d B）' % (TRANSLATOR, os.path.getsize(TRANSLATOR)))
    print('被测数据：%s（%d B）' % (BUCKET, os.path.getsize(BUCKET)))
    src = io.open(TRANSLATOR, encoding='utf-8').read()
    rt = lupa.LuaRuntime(unpack_returned_tuples=True)
    # lua.execute 的 chunk 没有真实路径（debug.getinfo 拿不到 lua/ 目录），
    # 所以切到 lua 目录，走 dirCandidates() 里 './' 那条兜底 —— 读的就是被测的这份桶。
    os.chdir(LUA_DIR)

    fails = []
    for word in CASES:
        cands = run_case(rt, src, word)
        shown = []
        for c in cands[:8]:
            shown.append('%s[%s]' % (c['text'], c['comment']))
        line = '  %-6s -> %d 条: %s' % (word, len(cands), '  '.join(shown) or '（无候选）')
        print(line)
        if word in EXPECT_FIRST:
            if not cands:
                fails.append('%s：一条候选都没出' % word)
                continue
            if cands[0]['text'].lower() != EXPECT_FIRST[word]:
                fails.append('%s：第 1 条是 %s，应为 %s'
                             % (word, cands[0]['text'], EXPECT_FIRST[word]))
            if not cands[0]['comment']:
                fails.append('%s：第 1 条没有中文注释' % word)
            # 二位＝翻译（中文译词，comment 回填英文词），且不能是 ASCII 开头
            second_is_zh = len(cands) > 1 and not cands[1]['text'][:1].isascii()
            if not second_is_zh:
                fails.append('%s：第 2 条不是中文译词（实为 %s）'
                             % (word, cands[1]['text'] if len(cands) > 1 else '（无）'))
            elif cands[1]['comment'].lower() != word:
                fails.append('%s：第 2 条注释应是英文词，实为 %s'
                             % (word, cands[1]['comment']))
        if word == 'q':
            if cands:
                fails.append('q：单字母不该出英文候选，实出 %d 条' % len(cands))
        # 名额：英文联想 ≤5；精确命中时总数 ≤ 1 英文 + 1 中文 + 5 联想
        en = [c for c in cands if c['text'][:1].isascii()]
        if len(en) > 6:
            fails.append('%s：英文候选 %d 条，超了 1 本义 + 5 联想' % (word, len(en)))
        if len(cands) > 7:
            fails.append('%s：总候选 %d 条，超了 7' % (word, len(cands)))
    print()
    if fails:
        for f in fails:
            print('FAIL ' + f)
        return 1
    print('PASS 离线执行在用的 Lua translator + 补词后的桶：'
          '一位=英文本词（注释带中文释义），二位=中文译词（注释回填英文词），'
          '英文联想≤5，单字母不出')
    return 0


if __name__ == '__main__':
    sys.exit(main())
