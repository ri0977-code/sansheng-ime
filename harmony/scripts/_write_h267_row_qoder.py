#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 H-267 台账行追加进 docs/ISSUES.md（Qoder 2026-10-29 14:5x）。

为什么用脚本而不是手改：H-250 之后台账行的**形状**由守卫管（7 格、单行、正文无裸竖线），
手改容易写出拆格的行；脚本自检 7 格并在写入前拒绝。

H-267：CodeArts 14:29:36 把 `lua_translator@enWord_translator` 整条注释掉（v30 暂禁用，排查卡顿）。
他的观察成立、归因不完整——旧 translator 确实每按键整桶扫两遍；这条行记录我量到的数字与修法。
"""
import io
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ISSUES = os.path.join(ROOT, 'docs', 'ISSUES.md')

STATUS = 'FIXED（**Qoder 10-29 14:4x 改完并离线实测；挂载开关仍在 CodeArts 手里**）'
PRIO = 'P1'
OWNER = 'Q'
TITLE = ('**英文 Lua 翻译器每次按键整桶线扫 ⇒ 打字卡，CodeArts 14:29 直接把 '
         '`lua_translator@enWord_translator` 注释掉了（v30 暂禁用，排查卡顿原因）**。'
         '他的观察成立：桶按首字母分，最大桶 s 有 5,973 条，旧写法每按一个键把这个桶**扫两遍**'
         '（一遍找本词、一遍找联想），且每格现算 `word:lower()` ⇒ 一次按键 ≈1.2 万次比较＋等量字符串分配。'
         '但「禁用」的代价是主人的英文候选整条没了，与他定的口径冲突（五笔／拼音／英文占前三、'
         '一位二位给本义和翻译），所以我改的是成本而不是关掉功能。'
         '另一条要分清：他 14:0x 装的 v29 包内 translator 是 sha1 33c3cb1d（没中文第二条、也没二分），'
         '所以手机上现在连「app＋中文注释」都还没生效——这一版没进过真机，我下面所有数字都是离线数字。')
CAUSE = ('`entry/src/main/resources/rawfile/rime/lua/enWord_translator.lua` 的两条 `for i = 1, #bucket`'
         '（本词扫描＋联想扫描），以及判据 ③「按首字母分桶」其实没设上限——桶就是全表的 1/26，仍是线性。')
FIX = ('**加载时把表建成三张索引**：`exact[word]`（O(1) 命中本词）、`idx2[前2字母]`、`idx3[前3字母]`'
       '（都按表内原顺序存同一批行对象，不是三份拷贝）；查询按输入长度选索引——长度 2 用 idx2、'
       '长度 3 用 idx3（整组天然命中，不用筛）、长度 ≥4 用 idx3 的 3 字母小组再筛（该组平均 15.7 条、'
       '最大 con 709 条）。顺手去掉 weight 列的存储（查询里从来没读过它，已核对）。'
       '判据 ③ 同步校正成「不许全表线扫，也不许全桶线扫」，并写进文件头第 ⑧ 条。'
       '守卫：`scripts/h267_english_candidates_check.py`（要求桶数据里本词在位＋长度 2/≥4 两条查询路径'
       '＋**联想顺序＝表内原顺序**这条不变量）；`scripts/h266_package_hygiene_check.py` 管住我上一轮犯的打包脏字节。')
EVID = ('`_probe/bench_enword_translator_qoder.py`（lupa 跑真文件、驱动全在 Lua 内、Candidate/yield 都是 Lua 函数，'
        '避免 Python↔Lua 边界污染计时）对 122 个「逐字母前缀」查询做新旧对比：'
        '**产出逐条全等**（text＋comment 全序列一致）；每按键 Lua CPU 时间 0.688 ms → 0.007 ms（98.7×）；'
        '冷启动 74 ms → 88 ms（＋14 ms，一次性）；常驻内存 12,877 KB → 12,800 KB（基本不变，'
        '省掉的 weight 字段抵掉了索引槽）。功能用例 `_probe/run_harmony_translator_offline_qoder.py` 11 条全过'
        '（app→app［应用 yiet/yingyong］＋应用［app］＋联想 4 条；cpu/url 出「英文＋中文第二条」；q 单字母 0 条）。'
        '桶数据 55,867 行实测：词面 0 条含大写、letter 列与词首字母 0 条不一致、重复词面 0 条 ⇒ 索引口径站得住。'
        '**中途踩过的坑（已回退，别照抄）**：我先做的是「桶内排序＋二分」，基准当场判红——'
        '桶里那 51 处非字典序相邻是数据自带的优先级，排完序 `appl` 的首条联想从 apple 变成 applaud，'
        '92/122 条查询产出变了＝改行为不是改性能。'
        '守卫自测 6/6（正控＝真树形状副本，四种坏形状：缺词／清单没列／整桶线扫回来／加了 table.sort），'
        '并且自测**第一轮就抓到守卫自己是假的**：`lua-files.txt` 我原先用「子串在不在」判发布，'
        '把注释行 `#lua/en_word_bucket.txt` 也算成已发布 ⇒ 负控不红；改成按行解析＋剔注释行才拦住（H-250 口径）。')

# 台账实际是 7 格：编号｜状态｜优先级｜归属｜问题（含位置/根因）｜修法｜证据与下一步。
# （我第一版按 8 格写，被自己的校验拦下 —— 列数要照现表数，别照记忆。）
row = '| H-267 | %s | %s | %s | %s（位置：%s） | %s | %s |' % (
    STATUS, PRIO, OWNER, TITLE, CAUSE, FIX, EVID)


def cells(line):
    # 台账正文里本来就不许出现裸竖线（形状守卫会拆格），所以这里直接按竖线切；
    # 早先我用 `(?<!\\)\|` 想在正文字符串里保留转义竖线，结果 Python 把 `\|` 当正则元字符，
    # re.split 直接抛 unterminated subpattern ⇒ 校验函数自己坏了（SyntaxWarning 也是同一条）。
    return line.strip().split('|')


def main():
    if len(cells(row)) != 9 or cells(row)[0] != '' or cells(row)[-1] != '':
        print('FAIL 台账行不是 7 格（拆出来 %d 段）' % (len(cells(row)) - 2))
        return 1
    inner = cells(row)[1:-1]
    if any('\\|' in c or '|' in c for c in inner):
        print('FAIL 正文里有裸竖线')
        return 1
    if len(inner) != 7:
        print('FAIL 内部格数=%d，应为 7' % len(inner))
        return 1
    txt = io.open(ISSUES, encoding='utf-8').read()
    if re.search(r'^\| H-267 \|', txt, re.M):
        print('SKIP H-267 已在册')
        return 0
    stamp = subprocess.run(['date', '+%Y-%m-%d %H:%M'], capture_output=True, text=True).stdout.strip()
    lines = txt.rstrip('\n').split('\n')
    last = lines[-1]
    if not last.startswith('|'):
        print('FAIL 台账最后一行不是表格行，不敢追加：%r' % last[:60])
        return 1
    lines.append(row)
    io.open(ISSUES, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines) + '\n')
    print('已追加 H-267（真实时钟 %s，行 %d 字符）' % (stamp, len(row)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
