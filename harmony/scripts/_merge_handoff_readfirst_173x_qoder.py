# -*- coding: utf-8 -*-
"""合并 HANDOFF「当前状态」读首三格到 17:3x（Qoder 2026-10-29 17:3x）

规则（H-139）：读首每格只留一个带时间戳段落；被合并掉的 15:5x 原文逐字进文末附录。
本轮三件事：①收回我引用错的「nova6 禁止触碰（H-223）」；②nova6 真机装上 1968 并闭环 H-270；
③「有点卡」量出 nova6 裸刻度并折算；另开 H-271（versionName 不 bump）。
备份：_probe/rawfile-backups-20261029/HANDOFF.md.bak-qoder-20261029-173x-before-readfirst
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
                   'HANDOFF.md.bak-qoder-20261029-173x-before-readfirst')
MARK = '### 2026-10-29 17:3x · Qoder（归档：本轮合并掉的「当前状态」三格原文＝15:5x 版）'
KEYS = ['最近更新', '当前阻断', '等主人']

NEW = {
    '最近更新': (
        "**2026-10-29 17:3x（Qoder·nova6 真机装上了，卡顿也量到手机刻度）**："
        "①**先收回一句错话**：我上一格写「安卓真机我没装、nova6 禁止触碰（H-223）」——"
        "回查 H-223 讲的是值守看门狗误报与它的回写逻辑等你点头，跟 nova6 一点关系没有；"
        "仓库里对 nova6 的真实规矩只有两条（MAILBOX §⑤ 占用／释放防撞、一台手机一次会话只装一次），"
        "我拿一条不存在的禁令把自己挡住了，你那句「nova6为啥不给弄啊，那边还不能用呢」是对的。"
        "②**装前 nova6 确实不能用**（只读探查）：包 1961／1.10.7，设备 rime/ 里 "
        "`cn_pinyin_jidian_wp.dict.yaml` 不存在（＝H-270 那张从没进过 seed 的表），"
        "`build/wubi86.table.bin` 停在 10-22 12:54 而 prism 是 10-28 12:04（不成对）"
        "⇒ 主方案依赖的五笔词典每次重编／编译失败，和你那句「打不了字了nova6」同一形状。"
        "③**17:08:37 覆盖安装 1968 包 Success**（1961→1965）：点框只点了一个控件"
        "（纯净模式页「继续安装」，全程没碰「取消」，没在你打开的记事本里注入任何按键）；"
        "装后该表 972,458 B 落到设备、`build/wubi86.prism.bin` 重编成 13,648,224 B（17:09）"
        "⇒ **H-270 真机闭环，状态转 FIXED**。"
        "④**你的数据一条没动**：`user.txt` 9,669 B md5 装前后一致（32b047e35125）、"
        "`Custom_phrase.txt` 9 行 457 B 只有第 9 行 ssbz 探针戳换了时间戳、"
        "`user.yaml` 只变 last_build_time 与 wubi_pinyin 两个部署时间、sync 目录仍 dc6cbd16-…；"
        "备份在 `_probe/nova6-backup-20261029-170x/`。"
        "⑤**「有点卡」量出刻度**（`_probe/nova6-speed-20261029.txt`，已扣 adb 基线 39 ms）："
        "三张英文表合计 3,491,632 B，nova6 热读 117 ms＝PC 66.8 ms 的 1.8 倍，"
        "sha256 33 ms＝PC 9.2 ms 的 3.6 倍 ⇒ **这台手机 CPU 比桌面慢 3.6 倍**；"
        "把 PC 量到的「每个输入窗口整表解析 245-291 ms」按此折算＝"
        "**nova6 一个窗口约 0.9-1.05 s**，正好是你说的「开始打等一下的时候，等1秒吧大概」。"
        "口径写死：这是按已量到的 IO／CPU 比值折算的估计，不是端到端实测"
        "（华为挡住往输入法窗口的触摸注入，CodeArts 10-22 实测 `input tap` 键区像素零变化）。"
        "⑥**新开 H-271（P2）**：这包文件名叫 1968，manifest 实为 versionCode=1965／versionName=1.10.7，"
        "而你手机上上一版就是 1.10.7 ⇒ `检查更新.ps1` 按版本号比对不会提示这一版；"
        "出包自检（`assemble-apk-qoder.py:183`）只拿 manifest 自己比自己，拦不住这件事，"
        "1916 那轮 README 定过的「版本号承载」口径这次丢了。"
        "⑦**更正一处我自己的落笔错**：M-357 里我写「缺 wubi86_jidian_wp 与 cn_pinyin_jidian_wp 两张表」，"
        "`wubi86_jidian_wp.dict.yaml` 这个文件名是我编的（源树／seed／设备三处都没有），"
        "实际只缺 `cn_pinyin_jidian_wp` 一张，已在 M-357 原行内逐字更正；"
        "教训同 H-185：写台账数字前没回读 seed 清单。"),
    '当前阻断': (
        "**2026-10-29 17:3x 刷新（Qoder）：阻断不在安卓装机，在鸿蒙定版＋安卓两件待办**。"
        "①**安卓 nova6 这条路已经通**：1968 包装上、缺的表落地、五笔词典重编成功，"
        "你「打不了字」那个形状在真机上消掉了；剩下的「有点卡」有两条明确解法，都在我能力内——"
        "(a) 把 14 张预编译 `build/*.bin` 打进 seed（学鸿蒙），消掉每次安装从头编译；"
        "(b) 英文链别再每个窗口整表解析，按前缀分桶惰性读（鸿蒙 `en_word_bucket.txt` 同形状），"
        "把折算出来的 0.9-1.05 s 压到读数以下。"
        "②**鸿蒙侧仍等 CodeArts 定版**：M-355 给的 A（保联想、降条数）／B（联想交回 schema 链）"
        "两条都必须满足你定过的「1 位本词、2 位中文译词、联想≤5」；"
        "他 15:55 的 M-356 只写「转主会话处理」，没定版；他 v36 是 380 B 空函数，别在真机上消融。"
        "③**H-271 出包版本号**要你一句话：下一版把 versionName 一起递增，"
        "否则这一版永远不进 `检查更新` 的提示。"
        "④**英文链 9 个文件（5,453,552 B）仍全 untracked**：M-350 的归属（A＝CodeArts 署名 checkpoint／"
        "B＝我提）他也没回，新克隆一次英文功能就整条消失。"),
    '等主人': (
        "**2026-10-29 17:3x 刷新（Qoder）：只有一件非你手不可，其余都不用你输密码**。"
        "①**nova6 端到端手感只能你真手**：华为挡住对输入法窗口的触摸注入（不是我偷懒），"
        "所以「按一下键到候选出来多少毫秒」这一寸我量不了；"
        "新包已装好（versionCode 1965、seed v16），你想验就顺手打 cat／qtal／mao／app 四条，"
        "不想验我就按台账数字走，不催你。"
        "②**H-271 一句话**：下一版是否把 versionName 一起 bump"
        "（不 bump 的话 `检查更新.ps1` 永远不会提示这一版，等于包发不出去）。"
        "③**鸿蒙定版（M-355 A／B）与英文链 9 文件入库（M-350）不用你选**——那是 CodeArts 的活，我在催；"
        "他不回我就按你定过的「1 位本词＋2 位中文＋联想≤5」判据自己出实现，把差异报给你。"
        "④nova6 占用牌已按规矩挂过（M-357）并在 M-358 释放，17:45 前我不再动它；"
        "Mate 80 全程只读，没装没注入。"),
}


def split_row(line):
    line = line.strip()
    if not (line.startswith('|') and line.endswith('|') and not line.startswith('|--')):
        return None, None
    cells = line[1:-1].split('|')
    return cells[0].strip().strip('*').strip(), cells


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
            if name == key and cells and len(cells) == 2:
                archived[key] = (i, l)
                break
        if key not in archived:
            print('FAIL 没找到「%s」格（应为 2 列行）' % key)
            return 1
    if not os.path.exists(BAK):
        shutil.copy2(P, BAK)
        print('已备份 HANDOFF ⇒ %s（%d B）' % (os.path.basename(BAK), os.path.getsize(BAK)))
    block = ['', MARK, '',
             '> 合并口径（H-139）：读首每格只留一个带时间戳段落，被合并掉的原文逐字留这里，一字不改。', '']
    for key in KEYS:
        block.append('#### 旧「%s」格（2026-10-29 17:3x 合并 ⇒ 原文逐字留此）' % key)
        block.append('')
        block.append(archived[key][1])
        block.append('')
    for key in KEYS:
        i, old = archived[key]
        _, cells = split_row(old)
        if '|' in NEW[key]:
            print('FAIL 新格文里有裸竖线：%s' % key)
            return 1
        lines[i] = '|' + cells[0] + '| ' + NEW[key] + ' |'
    lines.extend(block)
    io.open(P, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines))
    print('已替换三格（行 %s）并归档原文；文件 %d 行（真实时钟 %s）'
          % (','.join(str(archived[k][0] + 1) for k in KEYS), len(lines), time.strftime('%H:%M')))
    return 0


if __name__ == '__main__':
    sys.exit(main())
