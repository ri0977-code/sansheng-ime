# -*- coding: utf-8 -*-
"""往 docs/PROGRESS.md 追加一行 ㉔（Qoder 2026-10-29 14:5x，撞车处置＋卡顿前提被自己的数字推翻）
列口径＝日期 | 从 | 到 | 内容 | 状态（5 格＝6 条竖线）；幂等：已有 ㉔ 就跳过。
"""
import io
import sys
import time

P = r'F:\qoderwork\sansheng-ime-harmony\docs\PROGRESS.md'
NOW = time.strftime('%H:%M')

ROW = ('| ㉔ 10-29 14:5x（真实时钟＝`date` __NOW__；**零构建、零签名、零装机、零注入；只改台账＋两份文档＋一封信**） | Qoder | CodeArts＋主人 | '
       '**「打 app 没中文」这一单元的后半段：撞车处置、消融实验的读数、以及一条我之前没看见的交付风险（H-268）**。'
       '①**撞车**：我 14:4x 写进树的 8,553 B 索引版（判据 ⑦ 第二条中文＋⑧ 三张保序索引）在 14:43:38 被 CodeArts 覆盖成他的 v31'
       '（5,887 B／sha1 8bb4181cefcc：`b.data[word]` 哈希＋`table.sort(b.words)`＋`lowerBound` 二分），14:48:10 树里又换成 505 B 消融桩'
       '（只 `yield` 一条原样回吐），而他 14:43:55 把 `wubi_pinyin.custom.yaml:32` 的挂载行**打开**了 ⇒ 现在这棵树要是构建，'
       '英文候选＝打什么吐什么。处置按既定口径：**不 revert、不来回覆盖**（我这侧不再往这个文件写）、**逐字保住他的字节**'
       '（v31 归档 `_probe/rawfile-backups-20261029/enWord_translator.lua.peer-v31-20261029-144338`）、'
       '我的实现停到打包树外 `_probe/patches-20261029/enWord_translator.lua.qoder-v32-indexed`（8,547 B／sha1 921bf7439e8d，'
       '与丢失那版只差表头 6 字节排版，基准证明 122 个查询产出与 6,478 B 基线**逐条全等**），'
       '回退＝`python scripts/_apply_translator_v32_qoder.py`（默认试运行，`--apply` 才写盘且写盘前自动备份树内那份）。'
       '②**两份实现的差距是数字不是感觉**：拿 `_probe/bench_enword_translator_qoder.py` 对 122 个逐字母前缀查询与 6,478 B 基线比，'
       '他的 v31 **109 条产出不同**（两类：`app` 只剩「app」没有第二条中文＝主人报的那件事本身；`table.sort` 抹平了桶里那 51 处'
       '非字典序相邻＝数据自带优先级，`appl` 首条 apple→applaud、`ap` 首条 apart→apace），505 B 桩 **119 条产出不同**；'
       '我这版 122/122 全等、稳态 0.007 ms/键（基线线性扫 0.706 ms ⇒ 101×）、冷启动 75→86 ms（一次性＋14 ms）、'
       '常驻 12,877→12,800 KB。性能上他的结构不比我的差（0.004 ms/键），**要留他的结构也行**，条件是补回第二条中文并让联想按表内原顺序走。'
       '③**我自己那个前提被推翻**：我给 M-348 的理由是「整桶扫两遍＝卡的那条成本」，但桌面真 Lua 量下来旧写法也只要 0.70 ms/键，'
       'Mate 80 按 3–5 倍算 2–3 ms，一帧预算 16 ms ⇒ **查找逻辑解释不了他感觉到的卡**，这条已在 M-349 里当面向他更正，'
       '并把更普遍的候选原因指向 **H-263**（`fanxing_napi.cpp:545-560` 每次冷启动无条件 prebuild＋deploy＋4 次 deploy_schema＋'
       'start_maintenance，与主人 10-29 早上「重新部署大概 10 秒才好」同方向）。④**新查出的交付风险**：'
       '本轮 16 项 dirty＝7 项 tracked 修改＋9 项 untracked，而那 9 项恰好是英文链的全部实物'
       '（dict 54,496／schema 1,162／codes 755,914／gloss 1,339,067／rev 373,202／trans 1,396,651／Filter 24,271／'
       'translator 505／bucket 1,508,284＝合计 5,453,552 B），`git ls-files` 里一个都不在册 ⇒ 一次 `git clean -fd entry/src` '
       '或换机器 clone 就把主人的英文链整条删掉、我补进桶里的 75 个缩写词也只活在这份未入库的文件里；'
       '这同时解释了我俩为什么能互相覆盖而没有 git 冲突提示。已发 **M-350** 请他在 A（他署名提交）／B（授权我提交这 9 个文件＋两份守卫、'
       '不碰他 5 个在途文件）之间定一个并写进行。⑤**自家两处纠偏**：㉓ 行脚本拼接时漏了 `% NOW` ⇒ 台账里字面落了 `%s` 等于没有时间，'
       '按本文件 mtime 量到写入时刻 14:45:30 就地补号并留更正注（`scripts/_fix_progress_23_placeholder_qoder.py`）；'
       'h267 守卫第一轮自测抓到它自己假绿（`lua-files.txt` 按子串判发布把注释行也算成已发布）⇒ 改按行解析＋剔注释行。'
       '⑥**闸门现状**：`h106_precheck.py` 14:53 重跑阻断 3 项不变（未提交 16 项／无 CodeArts 署名交付行／交付行无 unsigned 字节数）'
       '⇒ **本轮不构建不装机**；`h266_package_hygiene_check.py` rc=0（14:09 旧包内实测 5 条 `.bak` 条目／2.7 MB 未压缩死字节，'
       '14:30 新包 92 条目 0 备份、包体 −5.8 MB）；`h267_english_candidates_check.py` 对真树如实 rc=1（当前是 505 B 桩）；'
       '信箱状态 OK；形状守卫新增 0（基线 66）。台账 H-266／H-267／H-268 三行在册，信 M-348／M-349／M-350 已发。 | '
       '等 CodeArts 回 M-349＋M-350（定 translator 版本＋英文链入库归属）并补署名交付行，之后我一次构建装机验 app→应用；'
       '待主人一拍（Windows 托盘「重新部署」约 10 秒，只能他点） |').replace('__NOW__', NOW)


def main():
    if ROW.count('|') != 6:
        print('FAIL 竖线数 %d，应为 6（5 格）' % ROW.count('|'))
        return 1
    txt = io.open(P, encoding='utf-8').read()
    if '㉔ 10-29 14:5x' in txt:
        print('已存在 ㉔，跳过（幂等）')
        return 0
    body = txt.rstrip('\n') + '\n' + ROW + '\n'
    io.open(P, 'w', encoding='utf-8', newline='\n').write(body)
    print('已追加 ㉔（%d 字符，真实时钟 %s）' % (len(ROW), NOW))
    return 0


if __name__ == '__main__':
    sys.exit(main())
