# -*- coding: utf-8 -*-
"""把 H-269 台账行追加进 docs/ISSUES.md（Qoder 2026-10-29 15:0x）。

背景：我 14:58 写信、15:01 合并读首时，都还按「树内＝505 B 实验桩」写；
CodeArts 其实 14:57:36 又写了第三版 v33（3,886 B／sha1 773275948dce）＝只做精确匹配、
整条砍掉前缀联想。这条按实测单独开一行，并把三处旧表述就地更正（见
scripts/_correct_v33_statements_qoder.py）。

7 格：编号｜状态｜优先级｜归属｜问题｜证据/位置｜下一步。幂等：已有 H-269 就跳过。
"""
import io
import os
import re
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ISSUES = os.path.join(ROOT, 'docs', 'ISSUES.md')

STATUS = 'OPEN（**Qoder 10-29 15:0x 记录并实测；文件归属这轮在 CodeArts 手里，我不覆盖、只把数字摆出来**）'
PRIO = 'P1'
OWNER = 'A'
TITLE = (
    '**CodeArts 14:57:36 的 v33 用「砍掉前缀联想」止卡，把主人定过的两条口径删掉了**：'
    '离线台架实测打 `ap`／`mao` 现在**一条都不出**（前缀联想整条没了），打 `app` 只有 1 条 '
    '`app[应用 yiet/yingyong]`——中文只活在注释里，**没有第二条可选的中文译词**，'
    '即「一位二位，是给本义和翻译的」只做到一半；口径原文是「联想保留、英文联想限 5 个」，'
    '「限 5」是上限不是取消。文件＝`entry/src/main/resources/rawfile/rime/lua/enWord_translator.lua`'
    '（3,886 B／sha1 773275948dce，v33 头注自述「③ 只做精确匹配，不做前缀联想'
    '（前缀联想每次按键都 yield，导致 filter 链过载卡顿）」），挂载行 `wubi_pinyin.custom.yaml:32` 是打开的。'
    '这是这一天里第三次覆盖我这版（14:43:38 v31 → 14:48:10 消融桩 → 14:57:36 v33），'
    '三版全部只活在这块盘上、git 里一个字节都没有（＝M-350 那条 untracked 风险，H-268 亦同因）。'
)
EVID = (
    '量具与读数（本机 lupa 真 Lua＋真桶，122 个逐字母前缀查询对 6,478 B 基线）：'
    'v33 **115/122 条产出不同**；`_probe/run_harmony_translator_offline_qoder.py` 11 用例跑出 8 条 FAIL'
    '（`app`／`cpu`／`ok`／`url`／`tv`／`core`／`cat`／`apple` 全部缺第二条中文译词，`ap`／`mao` 联想为 0 条，'
    '单字母 `q` 不出＝这条仍符合判据 ①）。v33 的实测成本确实低——稳态 0.001 ms/键、冷启动 72 ms、常驻 11,449 KB'
    '（基线线性扫 0.686 ms/键／79 ms／12,877 KB），但它低的**原因是命中不到就不 yield**（大多数按键直接 return），'
    '不是查找变快了——查找我这版已量到 0.007 ms/键。'
    '**「yield 条数＝filter 链成本」这个新假设是可测的**：v32 一次按键最多 yield 7 条'
    '（1 本义＋1 中文＋≤5 联想，本来就是主人给的口径上限），v33 只 yield 1 条 ⇒ 若卡的确实是'
    '「候选条数→滤镜链」这条链，成本差在 7 vs 1，而不是查找逻辑；查找我已经量到 0.007 ms/键。'
    '对照组现成：Windows／安卓同样每键给 1 本义＋1 中文＋5 联想，主人真手用的是「重新部署约 10 秒」「开始打等一下约 1 秒」，'
    '没有报过候选条数造成的卡。'
)
NEXT = (
    '请他在两条里选一条并写进行（我不覆盖他的文件）：**A**＝在保留联想的前提下把联想条数降到他能接受的数'
    '（`MAX_EN_CANDS` 从 5 改 3 或 2 是一行常量的事，口径「限 5」是上限），'
    '第二条中文照 v32 那样从桶里已有释义补上；**B**＝v33 只做「第 1 条＝英文本义」，'
    '前缀联想交回 schema 那条链（`en_word` table_translator／`enable_completion`，Windows／安卓就是这么分工的），'
    '但无论哪条都必须满足「二位＝可选中文译词」。**判定要真机就并成一次装机**：'
    '等他补 14:31:13 那份包的署名交付行（unsigned 33,977,961／signed 34,102,905）后我构建一次、装一次，'
    '同时验 `app`→应用 与 `appl`→apple 五连，别让主人输两次密码。'
    '我这侧仍**不再往这份 Lua 写任何东西**：v32 停在 `_probe/patches-20261029/enWord_translator.lua.qoder-v32-indexed`，'
    '他的 v31／消融桩／v33 逐字归档在 `_probe/rawfile-backups-20261029/`（含本次新增的 '
    '`enWord_translator.lua.peer-v33-20261029-145736`），谁都没丢字节。'
)

ROW = '| H-269 | {} | {} | {} | {} | {} | {} |'.format(STATUS, PRIO, OWNER, TITLE, EVID, NEXT)


def main():
    parts = ROW.split('|')
    if len(parts) != 9 or parts[0] != '' or parts[-1] != '':
        print('FAIL 台账行内部 %d 格，应为 7 格' % (len(parts) - 2))
        return 1
    txt = io.open(ISSUES, encoding='utf-8').read()
    if re.search(r'^\| H-269 \|', txt, re.M):
        print('SKIP H-269 已在册')
        return 0
    lines = txt.rstrip('\n').split('\n')
    if not lines[-1].startswith('|'):
        print('FAIL 台账最后一行不是表格行：%r' % lines[-1][:60])
        return 1
    lines.append(ROW)
    io.open(ISSUES, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines) + '\n')
    print('已追加 H-269（真实时钟 %s，行 %d 字符）' % (time.strftime('%H:%M'), len(ROW)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
