# -*- coding: utf-8 -*-
"""把 H-268 台账行追加进 docs/ISSUES.md（Qoder 2026-10-29 14:5x）。

7 格：编号｜状态｜优先级｜归属｜问题（含位置）｜修法｜证据与下一步。
幂等：已有 H-268 就跳过。时间戳取真实时钟（H-134）。
"""
import io
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ISSUES = os.path.join(ROOT, 'docs', 'ISSUES.md')

STATUS = 'OPEN（**Qoder 10-29 14:5x 记录并给出可放回的实现；决定权在正拿真机做消融实验的 CodeArts**）'
PRIO = 'P1'
OWNER = 'A'
TITLE = ('**同一天里英文 translator 被写了三次，我这版在对方读到信之前就被覆盖；而他 14:43:38 那版 v31 '
         '把主人报的那件事本身弄丢了**。（位置：`entry/src/main/resources/rawfile/rime/lua/enWord_translator.lua` '
         '＋ `wubi_pinyin.custom.yaml:32` 挂载行）时序全部取自文件系统 mtime：14:29:36 挂载行被注释（v30 暂禁用排查卡顿）'
         '→ 14:43:38 换成他的「哈希＋排序＋二分」v31（5,887 B／sha1 8bb4181cefcc，**覆盖了我 14:4x 那版 8,553 B'
         '／sha1 cdebb6fa96c3，而我 M-348 那封信此刻他还没读**）→ 14:48:10 换成 505 B 最小化实验桩'
         '（只 yield 一条、不做查找），但挂载行是**打开的**（注释还写着「v31 优化版」）⇒ 现在这棵树若构建，'
         '英文候选＝把打的字母原样吐回一条，没有中文注释、没有联想、没有第二条中文译词。'
         'v31 本身有两处回归：①判据 ⑦ 丢了 ⇒ 主人 14:0x 报的「app 没有中文」在鸿蒙又回来了；'
         '②`table.sort` 抹平桶内优先级 ⇒ 联想顺序改行为（`appl` 首条从 apple 变 applaud）。'
         '另记一条**推翻我们自己前提**的数字：旧线性扫在桌面真 Lua 里只要 0.67 ms/键，手机按 3–5 倍也就 2–3 ms，'
         '一帧预算 16 ms ⇒ 「查找逻辑＝卡顿主因」站不住，他的消融实验如果仍卡，就该往 H-263 那条冷启动全量部署查，'
         '而不是继续删英文功能。')
FIX = ('我这侧**不再往这个文件写**（避免来回覆盖），改成交换件：我的实现停在打包树外 '
       '`_probe/patches-20261029/enWord_translator.lua.qoder-v32-indexed`（8,547 B／sha1 921bf7439e8d），'
       '放回＝`python scripts/_apply_translator_v32_qoder.py`（默认试运行，`--apply` 前先把树内那份逐字备份）；'
       '他的 v31 我也逐字归档在同一目录，谁都没丢字节。守卫 `scripts/h267_english_candidates_check.py` 现在对真树'
       '如实报 rc=1（缺 exact／idx2／idx3、丢联想限额＝正是那个 505 B 桩的形状），挂载状态只 INFO 报告不拦他。'
       '他若保留自己的哈希＋二分结构，只需补两件事：exact 分支加回第二条中文候选、联想改成按表内原顺序走。')
EVID = ('`_probe/bench_enword_translator_qoder.py`（可带两份文件路径对拍）：v31 对 6,478 B 基线 **109/122 条产出不同**'
        '（例：`app` 少了「应用」；`ap` 首条从 apart 变 apace），每按键 0.004 ms；'
        '我的 v32 索引版对同一基线 **122/122 条逐条全等**，每按键 0.007 ms，冷启动 70→88 ms，常驻内存 12,877→12,800 KB；'
        '旧线性扫 0.675 ms/键（这就是「卡」的全部查找成本）。功能面 11 用例：v31 跑出 16 条 FAIL（一条中文注释都没有），'
        'v32 全 PASS；505 B 桩跑 `app` 只回一条 `app[]`。'
        '本机 lupa 是 Lua 5.5、设备 librime 是 5.4 ⇒ 我的实现只用 5.1 就有的写法（`math.floor`，没用 `//`／goto），'
        '离线产出不能直接当设备结论，但「产出全等」这条是代码路径级证据。'
        '下一步（等他回 M-349）：①实验桩别进包；②决定挂哪版实现；③补 14:31:13 那份包的署名交付行'
        '（unsigned 33,977,961／signed 34,102,905），补齐我这边闸门才放行，然后与「第二条中文」并成一次装机。')

row = '| H-268 | %s | %s | %s | %s | %s | %s |' % (
    STATUS, PRIO, OWNER, TITLE, FIX, EVID)


def cells(line):
    return line.strip().split('|')


def main():
    inner = cells(row)[1:-1]
    if len(inner) != 7 or cells(row)[0] != '' or cells(row)[-1] != '':
        print('FAIL 台账行内部 %d 格，应为 7 格' % len(inner))
        return 1
    if any('|' in c for c in inner):
        print('FAIL 正文里有裸竖线')
        return 1
    txt = io.open(ISSUES, encoding='utf-8').read()
    if re.search(r'^\| H-268 \|', txt, re.M):
        print('SKIP H-268 已在册')
        return 0
    lines = txt.rstrip('\n').split('\n')
    if not lines[-1].startswith('|'):
        print('FAIL 台账最后一行不是表格行：%r' % lines[-1][:60])
        return 1
    lines.append(row)
    io.open(ISSUES, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines) + '\n')
    stamp = subprocess.run(['date', '+%Y-%m-%d %H:%M'], capture_output=True, text=True).stdout.strip()
    print('已追加 H-268（真实时钟 %s，行 %d 字符）' % (stamp, len(row)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
