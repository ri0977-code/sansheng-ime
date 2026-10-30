# -*- coding: utf-8 -*-
"""15:1x 合并更正：手机读数＋第 4 版 v34＋把「落笔前先量」做成工具（Qoder）

我自己连错两次现状（14:58 写信时树里已是 v33；15:01 写读首时手机已是 14:58:29 那次装机），
根因都不是判断错，是**引用记忆里的数字没重测**（H-222 同族）。所以这一支脚本：
① 只在同格内追加带时间戳的更正，原句一字不删（H-139 先例＝10-28 那格「15:0x 补记」）；
② 所有数字全部来自 `scripts/h269_state_snapshot_qoder.py` 与两份量具的现测输出；
③ 幂等：行内已含「15:1x」标记就跳过。
"""
import io
import os
import re
import sys

ROOT = r'F:\qoderwork\sansheng-ime-harmony'

HF_UPDATE = (
    "⑦**15:1x 再更正（并把「量」这步做成工具）**：这棵树在我写信的当口仍被连续改写——15:05:48 又出现第 4 版 v34"
    "（3,570 B／sha1 571ed6c00b5d）＝只在输入长度 ≥5 时执行（头注「五笔编码最长4字母，>=5一定是英文」）。"
    "我立刻重测：`app`／`cpu`／`ok`／`url`／`tv`／`core`／`cat` **一条候选都不出**，只有 `apple` 出 1 条；"
    "122 个前缀查询 **111 条与基线不同**；稳态 0.019 ms/键、冷启动 0 ms、常驻 48 KB（短输入根本不读桶）。"
    "**⇒ 主人报的那件事在 v34 下更严重**：他点名的 app／CPU／OK／URL／TV 全是 2–4 字母，v34 连第 1 条都不给。"
    "读代码另可见一条隐患：≥5 那条分支用 `pairs(bucket)` 整桶扫、命中第一条就 `break`，"
    "既没有表内原顺序也没有 5 条上限（注释自己写着「后续再加」）。逐字归档 "
    "`_probe/rawfile-backups-20261029/enWord_translator.lua.peer-v34-20261029-150548`，v33／v34 两条读数都记在 H-269。"
    "同时把规矩从散文升级成工具：`scripts/h269_state_snapshot_qoder.py`（只读；一次打印工作区三件套＋本地两份 HAP "
    "与**包内**字节＋设备 `updateTime`＋守卫退出码），以后台账与信里凡引字节数／时间戳，照抄它的输出并注明时刻——"
    "我自己这一小时里连错两次就是因为抄了十分钟前的记忆。"
)

HF_BLOCK = (
    "⑧**15:1x 更正手机与包（上面 ④ 的 14:10:04 已过期）**：真机读数 `bm dump -n com.sansheng.ime` ⇒ "
    "updateTime＝**2026-10-29 14:58:29**（不是 14:10:04），对应本地 14:58:27 那份 signed HAP "
    "**34,098,808 B**／sha1 8309110d1390（unsigned 33,975,374 B／sha1 78e092c10169）；**包内实测** "
    "`enWord_translator.lua`＝3,886 B／sha1 773275948dce（＝v33）、桶＝1,508,284 B／sha1 99eb445a1d4b 与工作区同字节"
    "（75 个补词确在机内）、`.bak` 残留 0 条、条目 93。**⇒ 手机上现在跑的就是「只精确匹配、无前缀联想、无第二条中文」那一版**："
    "打 `app` 出 1 条带中文注释的 app，打 `appl` 不出英文联想。15:05:48 的第 4 版 v34（`app` 一条都不出）**还没进包**。"
    "⑨请他署名确认的交付行随之改成 14:58:27 那份（14:31:13 那份已被它覆盖，别再报旧的）；"
    "我这侧本轮仍**零构建、零签名、零装机、零注入**，数字口径今后一律由 `scripts/h269_state_snapshot_qoder.py` 现量现抄。"
)

HF_OWNER = (
    "⑤**15:1x 更正「手机上现在能试出什么」**：你手机现在跑的已是 14:58:29 那次装机的那份（那次装机不是我做的，"
    "我这侧本轮零构建零装机）。所以现在打 `app` 只出 1 条带中文注释的 app、**打 `appl` 不出英文联想**、"
    "也没有第二条可选中文——那是 CodeArts 排障实验第 3 版（v33）的取舍，我已按你的口径开账 H-269 请他定版；"
    "15:05:48 他还在树上写了第 4 版（长度 ≥5 才执行 ⇒ 打 `app` 连一条都不出），那版还没进包。"
    "Windows 那一拍（托盘「重新部署」）不变，仍然只能你点。"
)

P24 = (
    "⑧**15:1x 再更正（同格追加，原句不删）**：①手机读数我写错了——`bm dump` 实测 updateTime＝**14:58:29**，"
    "装的是本地 14:58:27 那份 signed **34,098,808 B**（unsigned 33,975,374 B），包内 translator＝v33"
    "（3,886 B／sha1 773275948dce）、桶与工作区同字节（75 补词在机内）、`.bak` 残留 0 条／条目 93 ⇒ "
    "现在手机上就是「无联想、无第二条中文」那一版；②15:05:48 树里又出现第 4 版 v34（3,570 B／sha1 571ed6c00b5d＝"
    "长度 ≥5 才执行），实测 `app`／`cpu`／`ok`／`cat` 一条不出、122 个查询 111 条与基线不同（主人点名的 2–4 字母缩写词全失效），"
    "尚未进包，逐字已归档 `enWord_translator.lua.peer-v34-20261029-150548`；③这两次错都源于「抄记忆没重测」，"
    "已把取数做成工具 `scripts/h269_state_snapshot_qoder.py`（工作区＋HAP 包内＋设备 updateTime＋守卫 rc 一次打印），"
    "今后凡引字节数与时间戳照抄它的输出并标时刻。H-269 同格已带 v34 读数与署名交付行改口（14:58:27 那份）。"
)

H269 = (
    "【15:1x 追加读数：他 15:05:48 又写了第 4 版 v34（3,570 B／sha1 571ed6c00b5d）＝只在长度 ≥5 时执行"
    "（头注「五笔编码最长4字母，>=5一定是英文」）。实测 `_probe/run_harmony_translator_offline_qoder.py`：`app`／`cpu`／"
    "`ok`／`url`／`tv`／`core`／`cat` **一条候选都不出**，只有 `apple` 出 1 条；`_probe/bench_enword_translator_qoder.py`："
    "122 个前缀查询 **111 条与基线不同**，稳态 0.019 ms/键、冷启动 0 ms、常驻 48 KB（短输入不读桶）。"
    "这条假设的代价正打在主人报的事上：他点名的 app／CPU／OK／URL／TV 全是 2–4 字母 ⇒ v34 下连第 1 条都没有。"
    "「≥5 一定是英文」对本方案也不成立：拼音与多字五笔名次的输入常常 ≥5 字母（`yingyong`／`zhongguo`），"
    "那正是英文链该闭嘴的时候。另一处读代码可见的隐患：≥5 分支用 `pairs(bucket)` 整桶扫、命中第一条就 `break`，"
    "既无表内原顺序也无 5 条上限（注释自陈「后续再加」），等于把他在 v30 抱怨的整桶扫又请回来一次。"
    "逐字已归档 `enWord_translator.lua.peer-v34-20261029-150548`；真机现跑 14:58:29 那份（包内＝v33，"
    "signed 34,098,808 B／unsigned 33,975,374 B）。**署名交付行请改成这一份**，定版后我一次构建装机，"
    "同验 `app`→应用 与 `appl`→apple 五连，别让主人输第二次密码。】"
)

# (文件, 行首匹配, 目标格下标(split 后 parts 下标), 文本, 期望格数, 搜索上限)
TARGETS = [
    ('docs/HANDOFF.md', r'^\|\s*最近更新\s*\|', 2, HF_UPDATE, 2, 60),
    ('docs/HANDOFF.md', r'^\|\s*\*\*当前阻断\*\*\s*\|', 2, HF_BLOCK, 2, 60),
    ('docs/HANDOFF.md', r'^\|\s*\*\*等主人\*\*\s*\|', 2, HF_OWNER, 2, 60),
    ('docs/PROGRESS.md', r'^\|\s*㉔', 4, P24, 5, None),
    ('docs/ISSUES.md', r'^\|\s*H-269\s*\|', 7, H269, 7, None),
]


def main():
    changed, skipped = [], []
    for rel, pat, pidx, text, want, upto in TARGETS:
        p = os.path.join(ROOT, rel)
        lines = io.open(p, encoding='utf-8').read().split('\n')
        scope = lines[:upto] if upto else lines
        hit = [i for i, l in enumerate(scope) if re.match(pat, l)]
        if len(hit) != 1:
            print('FAIL %s 匹配 %s 的行有 %d 条' % (rel, pat, len(hit)))
            return 1
        i = hit[0]
        parts = lines[i].split('|')
        if len(parts) - 2 != want:
            print('FAIL %s 行 %d 是 %d 格，应为 %d' % (rel, i + 1, len(parts) - 2, want))
            return 1
        if '15:1x' in parts[pidx]:
            skipped.append('%s 行 %d' % (rel, i + 1))
            continue
        parts[pidx] = parts[pidx].rstrip() + ' ' + text + ' '
        new = '|'.join(parts)
        if len(new.split('|')) - 2 != want:
            print('FAIL 追加后 %s 行 %d 变 %d 格（文本里有裸竖线）'
                  % (rel, i + 1, len(new.split('|')) - 2))
            return 1
        lines[i] = new
        io.open(p, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines))
        changed.append('%s 行 %d（+%d 字符）' % (rel, i + 1, len(text)))
    for c in changed:
        print('已更正 ' + c)
    for s in skipped:
        print('已存在，跳过（幂等） ' + s)
    return 0


if __name__ == '__main__':
    sys.exit(main())
