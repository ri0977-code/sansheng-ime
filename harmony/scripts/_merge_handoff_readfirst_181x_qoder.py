# -*- coding: utf-8 -*-
"""合并 HANDOFF「当前状态」读首三格到 18:1x（Qoder 2026-10-29 18:1x）

规则（H-139）：读首每格只留一个带时间戳段落；被合并掉的 17:1x 原文逐字进文末附录。
本轮：H-272 英文链分桶惰性读完成、1966／1.10.8 包已出、模拟器验收边界、新开 H-273。
备份：_probe/rawfile-backups-20261029/HANDOFF.md.bak-qoder-20261029-181x-before-readfirst
幂等：文末已存在本轮附录块就退出。
"""
import io
import os
import shutil
import sys
import time

ROOT = r'F:\qoderwork\sansheng-ime-harmony'
P = os.path.join(ROOT, 'docs', 'HANDOFF.md')
BAK = os.path.join(ROOT, '_probe', 'rawfile-backups-20261029',
                   'HANDOFF.md.bak-qoder-20261029-181x-before-readfirst')
MARK = '### 2026-10-29 18:1x · Qoder（归档：本轮合并掉的「当前状态」三格原文＝17:1x 版）'
KEYS = ['最近更新', '当前阻断', '等主人']

NEW = {
    '最近更新': (
        '**2026-10-29 18:1x（Qoder·安卓英文链改成「按首字母只读一段」，卡顿的最后一刀）**：'
        '①**你一句「还是有点卡nova6」，把最后一段可量的成本找出来了**：librime 每个输入窗口是一个全新 Lua VM，'
        '滤镜一进窗口就把 gloss／trans／codes 三张表整表读进来。本机台架量到 load 中位 241.2 ms／窗口，'
        '按昨天真机实测的 3.6 倍 CPU 差折算 nova6 约 868 ms。'
        '②**改法不复制任何词表**：新增 `en_word_ltr_idx.tsv`（1,942 B，只记字节偏移），'
        '按键首字母 seek+read 只读那一桶（最大 158 KB，整表 3.5 MB）。'
        '台架：本机 load 17.6 ms ＋ 首键 5.1 ms ⇒ nova6 约 80 ms。'
        '③**先证「一条功能都没少」再谈快**：18 个场景 × 三版本（旧整表／新桶读／新代码但没索引退回整表）'
        '输出「文本{注释}」逐字节一致；你点头的 16 条断言，带索引与不带索引两条路都 PASS；'
        '坏索引／只有 a 桶／缺反查表三条兜底也逐字节一致（`_probe/h272-bucket-eq-cost-20261029.txt`、'
        '`_probe/h272-win-suite-20261029.txt`）。'
        '④**顺手修一条隐形病**：三张英文表是 CRLF，Windows 读文本会自动去掉 `\\r`，安卓不会 '
        '⇒ 手机上每个值末尾一直挂着一个看不见的回车（注释里跟着走）。两条读法现在统一 chomp。'
        '⑤**出包 1966／1.10.8，seed v17**：57,781,015 B，sha256 afb4f941…335a6，自检 4 项 PASS；'
        '`en_word_ltr_idx.tsv` 进了 seed、导入包与三处白名单，并加了出包硬门（索引和词表对不上就报错不出包）。'
        'H-271 这轮只做到手工 bump 版本号（manifest 与 apktool.yml 一起 1966／1.10.8），'
        '「脚本强制递增＋比对上一版已发布包」仍未做。'
        '⑥**模拟器验收的真实边界**：这台模拟器主机负载高，seeder 两次在启动超时内解压不完被系统判 ANR'
        '（failed to complete startup），我改用 root 把同一份 seed push 到目标目录并手写 v17 标记；'
        '8 个关键文件 md5 与 seed 逐字节一致、librime 无 failed to compile、启动无 ANR、键盘正常渲染。'
        '**「打字出候选」这一环模拟器上验不了**（tap 进不了自绘键盘、keyevent 被 EditText 直接吃掉），'
        '和之前真机的限制同一个形状。'
        '⑦**新开 H-273**：seed 里的 `wubi86.dict.yaml` 是 2,352,069 B，桌面发布输入包 stage-v1.10.4 是 '
        '2,488,821 B（带 stem）。按「词库跨机对齐＝逐条决定」我没有替换，先把差异量出来再问你。'
    ),
    '当前阻断': (
        '**2026-10-29 18:1x 刷新（Qoder）：安卓卡顿这条已经解到底，剩下都不是卡顿**。'
        '①**安卓侧**：英文链分桶惰性读已完成（H-272 FIXED），1966／1.10.8 包出好、模拟器落地校验通过；'
        '还差真机观感一句话。另一件老待办＝把 14 张预编译 `build/*.bin` 打进 seed（学鸿蒙，消掉每次安装从头编译），'
        '这轮没做，仍是冷启动那条的主项。'
        '②**H-273 等你一句话**：安卓五笔主词库比桌面发布输入包少一版（2,352,069 vs 2,488,821 B，'
        '差的可能就是带 stem 的那批词条）。我不自行整包替换，先把差异列出来。'
        '③**鸿蒙侧仍等 CodeArts 定版**：M-355 的 A／B 两条都必须满足你定过的「1 位本词、2 位中文译词、联想≤5」；'
        '他 15:55 的 M-356 只写「转主会话处理」，没定版。'
        '④**英文链 9 个文件（5,453,552 B）仍全 untracked**：M-350 的归属他也没回，新克隆一次英文功能就整条消失。'
        '⑤**H-271 仍未闭环**：这轮手工 bump 了版本号，但脚本强制递增＋自检比对上一版已发布包还没做。'
    ),
    '等主人': (
        '**2026-10-29 18:1x 刷新（Qoder）：只有一件非你手不可**。'
        '①**nova6 装 1966（1.10.8）打几个字看手感**：这是唯一能判断「还卡不卡」的证据——'
        '华为挡住对输入法窗口的触摸注入，我量不到端到端。想验就顺手打 cat／qtal／mao／app 四条；'
        '不想验我就按台架数字走，不催你。装之前我先按规矩挂占用牌，一次会话只装一次。'
        '②**H-273 词库对齐**不用你现在决定，我先把两份 wubi86 的差异量出来给你看，再问你走不走桌面那份。'
        '③鸿蒙定版（M-355 A／B）与英文链 9 文件入库（M-350）不用你选——那是 CodeArts 的活，我在催。'
        '④Mate 80 全程只读，没装没注入；模拟器这轮装过一次 1966。'
    ),
}


def split_row(line):
    if not line.startswith('|'):
        return None, None
    cells = line.split('|')
    return cells[1].strip().strip('*').strip(), cells


def main():
    txt = io.open(P, encoding='utf-8').read()
    if MARK in txt:
        print('本轮附录已存在 ⇒ 不重复归档（幂等退出）')
        return 0
    lines = txt.split('\n')
    archived = {}
    for key in KEYS:
        for i, l in enumerate(lines[:60]):
            name, cells = split_row(l)
            if name == key and cells and len(cells) >= 3:
                archived[key] = (i, l)
                break
        if key not in archived:
            print('FAIL 没找到「%s」格' % key)
            return 1
    if not os.path.exists(BAK):
        shutil.copy2(P, BAK)
        print('已备份 HANDOFF ⇒ %s（%d B）' % (os.path.basename(BAK), os.path.getsize(BAK)))
    block = ['', MARK, '',
             '> 合并口径（H-139）：读首每格只留一个带时间戳段落，被合并掉的原文逐字留这里，一字不改。', '']
    for key in KEYS:
        block.append('#### 旧「%s」格（2026-10-29 18:1x 合并 ⇒ 原文逐字留此）' % key)
        block.append('')
        block.append(archived[key][1])
        block.append('')
    for key in KEYS:
        i, old = archived[key]
        _, cells = split_row(old)
        if '|' in NEW[key]:
            print('FAIL 新格文里有裸竖线：%s' % key)
            return 1
        lines[i] = '|' + cells[1] + '| ' + NEW[key] + ' |'
    lines.extend(block)
    io.open(P, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines))
    print('已替换三格（行 %s）并归档原文；文件 %d 行（真实时钟 %s）'
          % (','.join(str(archived[k][0] + 1) for k in KEYS), len(lines), time.strftime('%H:%M')))
    return 0


if __name__ == '__main__':
    sys.exit(main())
