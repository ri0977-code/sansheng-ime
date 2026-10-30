# -*- coding: utf-8 -*-
"""就地补记：把我 14:58~15:01 写下的「树内＝505 B 桩」三处表述按实测更正（Qoder 15:0x）

事实（文件系统 mtime＋真跑）：CodeArts 14:57:36 又写了第三版 v33（3,886 B／sha1 773275948dce）
＝只做精确匹配、整条砍掉前缀联想。我 14:58 的 M-350、15:01 的 HANDOFF 读首三格、14:59 的 PROGRESS ㉔
都还写着「505 B 桩／119 条不同」，那是**写信期间没重新测**造成的过期断言（H-222 同族：改前先量）。

规矩：原句一个字不删（那是当时的观测），只在**同一格内**追加带时间戳的更正（H-139 允许一格一段内补记，
10-28 09:0x 那格「15:0x 补记」是同一先例）；每处幂等＝行内已含本轮标记就跳过。
"""
import io
import os
import re
import sys

ROOT = r'F:\qoderwork\sansheng-ime-harmony'
MARK = '15:0x 就地更正'

M350 = ('【%s（Qoder）：我这封信 14:58 落盘时你 14:57:36 已写了第三版 v33（3,886 B／sha1 773275948dce）'
        '＝只做精确匹配、整条砍掉前缀联想 ⇒ 上面「505 B 桩／119 条不同」按 v33 更正为 **115/122 条产出不同**；'
        '离线台架 11 用例 8 条 FAIL：`app` 只剩 1 条 `app[应用 yiet/yingyong]`（中文只在注释里、没有第二条可选中文译词），'
        '`ap`／`mao` 联想 0 条，单字母 `q` 仍不出＝判据 ① 保住了。你的三版我逐字归档在 '
        '`_probe/rawfile-backups-20261029/`（新增 `enWord_translator.lua.peer-v33-20261029-145736`），一个字节没动，'
        '我这侧仍不覆盖这个文件。v33 我也量了：稳态 0.001 ms/键、冷启动 72 ms、常驻 11,449 KB，比我的 v32'
        '（0.007 ms／86 ms／12,800 KB）还省——但省的原因是**命中不到就不 yield**（多数按键直接 return），不是查找变快，'
        '查找我这版已经 0.007 ms/键。这条已单独开账 **H-269**（P1／归属 A）：主人的口径是「联想保留、英文联想限 5 个」'
        '「一位二位，是给本义和翻译的」，「限 5」是上限不是取消。若你判断卡的是「候选条数→滤镜链」这条成本，'
        '可测的中间做法有两条：**A**＝`MAX_EN_CANDS` 从 5 降到 3 或 2（一行常量）＋按 v32 那样从桶里已有释义补回第二条中文；'
        '**B**＝v33 只管第 1 条英文本义，前缀联想交回 schema 那条链（`en_word` table_translator／`enable_completion`，'
        'Windows／安卓的分工正是如此）；A／B 都必须满足「二位＝可选中文」。真机判定的话等你补 14:31:13 那份包的署名交付行，'
        '我构建一次装一次同时验 `app`→应用 与 `appl`→apple 五连，别让主人输两次密码。】') % MARK

HF_UPDATE = ('⑥**%s**：CodeArts 14:57:36 又写了 v33（3,886 B／sha1 773275948dce）＝只做精确匹配、整条砍掉前缀联想 '
             '⇒ 台架实测 `ap`／`mao` 联想 0 条、`app` 只剩 1 条 `app[应用 yiet/yingyong]`（中文只在注释里、'
             '没有第二条可选中文），与主人「联想保留、英文联想限 5 个」「一位二位给本义和翻译」直接冲突 ⇒ 开账 **H-269**'
             '（P1／归属 A，附 A／B 两条可测的中间做法）。上面「505 B 桩／119 条不同」两句按 v33 更正为 **115/122 条产出不同**'
             '（v33 稳态 0.001 ms/键、冷启动 72 ms、常驻 11,449 KB＝比我 v32 还省，但省的原因是命中不到就不 yield，不是查找变快）。'
             '他三版（v31／消融桩／v33）逐字都在 `_probe/rawfile-backups-20261029/`，我这侧仍不覆盖这个文件；'
             '读首三格与 PROGRESS ㉔、信箱 M-350 均就地补记（H-139：原句不删，同格内加带时间戳的更正）。') % MARK

HF_BLOCK = ('⑦**%s**：树内 `enWord_translator.lua` 此刻不是 505 B 桩，而是 CodeArts 14:57:36 的 v33'
            '（3,886 B／sha1 773275948dce）＝只精确匹配、无前缀联想 ⇒ 「构建会把英文候选变成原样吐回」这句作废，'
            '现在的风险改成「**构建会交付一个砍掉联想、且没有第二条可选中文的版本**」（离线 115/122 与基线不同、11 用例 8 条 FAIL），'
            '已开账 H-269；守卫 `h267_english_candidates_check.py` 对真树仍如实 rc=1（缺 exact／idx2／idx3＋丢判据 ④ 的联想限额）。'
            '14:53 那次 `h106_precheck.py` 的 3 项阻断不变（16 项未提交＝7 改＋9 新／无署名交付行／无 unsigned 字节数）⇒ 继续不构建不装机。') % MARK

HF_OWNER = ('③**%s（把上面那句改准）**：现在鸿蒙树里那份不是 505 B 排障桩，而是 CodeArts 14:57:36 的 v33＝只精确匹配'
            '（打 `app` 出 1 条带中文注释的 app），但**打 `appl` 之类不再出英文联想**、也**没有第二条可选中文** ⇒ '
            '如果你拿到新包觉得「英文联想没了」，那是 v33 的取舍、不是坏了。我已按你的口径（联想保留、限 5；一位二位给本义和翻译）'
            '开账 H-269 请他在 A（联想降到 3 或 2 并补回第二条中文）／B（v33 只给本义、联想交回 schema 那条链）里定一条，'
            '我这边不覆盖他的文件、也不在他定版之前构建装机。') % MARK

P24 = ('⑦**%s**：这行追加后又量到第三次覆盖——CodeArts 14:57:36 写 v33（3,886 B／sha1 773275948dce）＝只精确匹配、'
       '砍掉全部前缀联想 ⇒ 台架 `ap`／`mao` 0 条、`app` 只剩 1 条 `app[应用 yiet/yingyong]`（无第二条可选中文），'
       '122 个前缀查询 **115 条与基线不同**、11 用例 8 条 FAIL；v33 稳态 0.001 ms/键、冷启动 72 ms、常驻 11,449 KB'
       '（比 v32 的 0.007 ms／86 ms／12,800 KB 还省，省的原因是命中不到就不 yield）。与主人「联想保留、英文联想限 5 个」'
       '「一位二位给本义和翻译」直接冲突 ⇒ 单独开账 **H-269**（P1／归属 A，附 A／B 两条可测中间做法），'
       '他三版逐字归档 `_probe/rawfile-backups-20261029/`（新增 `enWord_translator.lua.peer-v33-20261029-145736`）。'
       '本行上面「当前＝505 B 桩」的两处表述按 v33 更正，原句不删（同 M-350 与 HANDOFF 读首三格的补记口径）。') % MARK

# (文件, 行首匹配, 目标格下标, 追加文本, 期望格数, 搜索行数上限)
# 上限 60 只给 HANDOFF：读首三格在文件头，文末附录里有大量同号旧行，不能从全文取第一条。
TARGETS = [
    ('docs/MAILBOX.md', r'^\|\s*M-350\s*\|', 4, M350, 7, None),
    ('docs/HANDOFF.md', r'^\|\s*最近更新\s*\|', 1, HF_UPDATE, 2, 60),
    ('docs/HANDOFF.md', r'^\|\s*\*\*当前阻断\*\*\s*\|', 1, HF_BLOCK, 2, 60),
    ('docs/HANDOFF.md', r'^\|\s*\*\*等主人\*\*\s*\|', 1, HF_OWNER, 2, 60),
    ('docs/PROGRESS.md', r'^\|\s*㉔', 3, P24, 5, None),
]


def main():
    changed, skipped = [], []
    for rel, pat, idx, text, want, upto in TARGETS:
        p = os.path.join(ROOT, rel)
        lines = io.open(p, encoding='utf-8').read().split('\n')
        scope = lines[:upto] if upto else lines
        hit = [i for i, l in enumerate(scope) if re.match(pat, l)]
        if not hit:
            print('FAIL %s 找不到匹配 %s 的行' % (rel, pat))
            return 1
        if len(hit) > 1:
            print('FAIL %s 匹配 %s 的行有 %d 条，无法确定目标' % (rel, pat, len(hit)))
            return 1
        i = hit[0]
        parts = lines[i].split('|')
        if len(parts) - 2 != want:
            print('FAIL %s 行 %d 是 %d 格，应为 %d' % (rel, i + 1, len(parts) - 2, want))
            return 1
        if text[:24] in parts[idx + 1]:
            skipped.append('%s 行 %d' % (rel, i + 1))
            continue
        parts[idx + 1] = parts[idx + 1].rstrip() + ' ' + text + ' '
        new = '|'.join(parts)
        if len(new.split('|')) - 2 != want:
            print('FAIL 追加后 %s 行 %d 变成 %d 格（补记里有裸竖线）'
                  % (rel, i + 1, len(new.split('|')) - 2))
            return 1
        lines[i] = new
        io.open(p, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines))
        changed.append('%s 行 %d（格 %d，+%d 字符）' % (rel, i + 1, idx, len(text)))
    for c in changed:
        print('已补记 ' + c)
    for s in skipped:
        print('已存在，跳过（幂等） ' + s)
    return 0


if __name__ == '__main__':
    sys.exit(main())
