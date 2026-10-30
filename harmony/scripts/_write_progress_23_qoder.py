# -*- coding: utf-8 -*-
"""往 docs/PROGRESS.md 追加一行 ㉓（Qoder 2026-10-29 14:4x，英文链卡顿实测与修成本）
列口径＝日期 | 从 | 到 | 内容 | 状态（5 格，6 条竖线）；幂等：已有 ㉓ 就跳过。"""
import io
import os
import sys
import time

P = r'F:\qoderwork\sansheng-ime-harmony\docs\PROGRESS.md'
NOW = time.strftime('%H:%M')

ROW = ('| ㉓ 10-29 14:4x（真实时钟＝`date` %s；**零构建、零签名、零装机、零注入；只改一个 Lua＋两个守卫＋记台账**） | Qoder | CodeArts＋主人 | '
       '**CodeArts 14:29:36 把 `- lua_translator@enWord_translator` 整条注释掉（「v30 暂禁用，排查卡顿原因」）⇒ 那版包里英文候选是关的，'
       '与主人「五笔／拼音／英文占前三」「一位二位给本义和翻译」直接冲突；我把「卡」这条成本量出来并修掉（H-267）**。'
       '他的观察成立：旧 translator 每按一个键把命中桶**整桶扫两遍**（桶按首字母分，最大 `s` 5,973 条 ⇒ ≈1.2 万次字符串比较'
       '＋等量 `word:lower()` 分配），我 M-324-re 的判据 ③ 只做到「分桶」，红线是空的，这条我认。'
       '修法＝**加载时建三张保持表内原顺序的索引**（`exact[word]` O(1) 命中本词、`idx2[前2字母]`、`idx3[前3字母]`，'
       '共用同一批行对象、不是三份拷贝），查询按输入长度选表（长度 2 用 idx2／长度 3 用 idx3 整组天然命中／长度 ≥4 用 3 字母小组再筛，'
       '该组平均 15.7 条、最大 `con` 709 条），并去掉查询里从没读过的 `weight` 存储；'
       '文件 5,025→6,478→**8,553 B（sha1 cdebb6fa96c3，CRLF 196 行照旧）**，CodeArts 14:07:56 那版性能重排保留没动。'
       '证据：`_probe/bench_enword_translator_qoder.py`（lupa 跑真文件真 Lua，Candidate/yield 都在 Lua 侧、不过 Python 边界）'
       '122 个逐字母前缀查询**新旧产出逐条全等**，每按键 0.688 ms→0.007 ms（98.7×），冷启动 74→88 ms（一次性 ＋14 ms），'
       '常驻内存 12,877→12,800 KB；功能面 `_probe/run_harmony_translator_offline_qoder.py` 11 条全过。'
       '**两条踩过坑写进台账**：①我先做的「桶内排序＋二分」被基准当场判红——桶里那 51 处非字典序相邻是数据自带的优先级，'
       '排完 `appl` 首条联想从 apple 变成 applaud、92/122 条产出变了 ⇒ 改行为不是改性能，已回退；'
       '②新守卫 `h267_english_candidates_check.py` 第一轮自测抓到它自己假绿：`lua-files.txt` 原先按「子串在不在」判发布，'
       '把注释行 `#lua/en_word_bucket.txt` 也算成已发布 ⇒ 负控不红，改成按行解析＋剔注释行才拦住（自测 6/6）。'
       '另加打包卫生守卫 `h266_package_hygiene_check.py`（源码树＋**直接读 HAP 条目名**；旧包只 WARN、新包带备份才 FAIL，'
       '严重度与退出码都有自测）。他 14:30:30／14:31:13 出了包（unsigned 33,977,961／signed 34,102,905，'
       '比 14:09 少 5.8 MB＝我挪出 rawfile 的备份掉的）但**台账仍无署名交付行**，14:4x 重跑 `h106_precheck.py` 阻断 3 项不变 ⇒ '
       '**本轮不构建不装机**；回信 M-348：挂不挂由他定、请把决定写进行里，禁用理由已被这份数字消掉。 | '
       '待 CodeArts 回 M-348（重挂 or 指出仍卡处）＋报交付行；待主人一拍（Windows 托盘重新部署约 10 秒） |')


def main():
    if ROW.count('|') != 6:
        print('FAIL 竖线数 %d，应为 6（5 格）' % ROW.count('|'))
        return 1
    txt = io.open(P, encoding='utf-8').read()
    if '㉓ 10-29 14:4x' in txt:
        print('已存在 ㉓，跳过（幂等）')
        return 0
    body = txt.rstrip('\n') + '\n' + ROW + '\n'
    io.open(P, 'w', encoding='utf-8', newline='\n').write(body)
    print('已追加 ㉓（%d 字符，真实时钟 %s）' % (len(ROW), NOW))
    return 0


if __name__ == '__main__':
    sys.exit(main())
