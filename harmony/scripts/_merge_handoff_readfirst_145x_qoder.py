# -*- coding: utf-8 -*-
"""合并 HANDOFF「当前状态」读首三格到 14:5x（Qoder 2026-10-29 14:5x）

规则（H-139）：读首每一格只留**一个带时间戳的段落**；被合并掉的原文**逐字**进文件末尾附录。
本脚本：① 把 21/23/24 三行（14:4x 版）的原格文逐字搬到末尾新附录块；② 用本轮合并后的文本替换该格。
备份：_probe/rawfile-backups-20261029/HANDOFF.md.bak-qoder-20261029-145x-before-readfirst
幂等：文末已存在本轮附录块就只报「已归档过」，不重复搬。
"""
import io
import os
import shutil
import sys
import time

ROOT = r'F:\qoderwork\sansheng-ime-harmony'
P = os.path.join(ROOT, 'docs', 'HANDOFF.md')
BAK = os.path.join(ROOT, '_probe', 'rawfile-backups-20261029',
                   'HANDOFF.md.bak-qoder-20261029-145x-before-readfirst')
MARK = '### 2026-10-29 14:5x · Qoder（归档：本轮合并掉的「当前状态」三格原文＝14:4x 版）'

KEYS = ['最近更新', '当前阻断', '等主人']

NEW = {
    '最近更新': (
        "**2026-10-29 14:5x（Qoder·「app 没有中文」的后半段：撞车怎么处置、消融实验读出的数、以及一条我之前没看见的交付风险；"
        "鸿蒙仍零构建零装机）**：主人原话「这个app对吗，后面都是联想，没有中文，看万能五笔的截图」这件事，"
        "Windows／安卓／鸿蒙三端的代码与数据在 14:2x 已全部落地并离线验过（滤镜 24,271 B 场景1b＝16 条断言＋真实 rime.dll 双会话；"
        "安卓 seed v15＋APK 1967 模拟器 cat／qtal／mao／app 四条全绿；鸿蒙＝桶补 75 个缩写词 55,792→55,867 行＋translator 第二条中文，"
        "lupa 真跑在用的 Lua 与补词后的桶 PASS）；14:4x 那格记的是 CodeArts 14:29:36 把 `- lua_translator@enWord_translator` 注释掉"
        "「排查卡顿」＋我据此把查找成本索引化。**本轮（14:4x→14:5x）新增四件事实**："
        "①**撞车两次，按口径处置**：我 14:4x 写进树的 8,553 B 索引版在 14:43:38 被他的 v31（5,887 B／sha1 8bb4181cefcc："
        "哈希精确匹配＋`table.sort`＋二分）覆盖，14:48:10 树里又换成 505 B 消融桩（只 yield 一条原样回吐），"
        "而他 14:43:55 把挂载行**打开**了 ⇒ 现在这棵树要是构建，英文候选＝打什么吐什么。我不 revert、不来回覆盖（这侧停止写这份 Lua），"
        "把他的 v31 逐字归档（`_probe/rawfile-backups-20261029/enWord_translator.lua.peer-v31-20261029-144338`），"
        "我的实现停到打包树外 `_probe/patches-20261029/enWord_translator.lua.qoder-v32-indexed`（8,547 B／sha1 921bf7439e8d），"
        "放回＝`python scripts/_apply_translator_v32_qoder.py`（默认试运行，`--apply` 才写盘且先自动备份树内那份）。"
        "②**版本差距是数字**：`_probe/bench_enword_translator_qoder.py` 对 122 个逐字母前缀查询与 6,478 B 基线比——"
        "我的 v32 **122/122 产出逐条全等**、稳态 0.007 ms/键（基线 0.706 ms ⇒ 101×）、冷启动 75→86 ms、常驻 12,877→12,800 KB；"
        "他的 v31 **109/122 产出不同**（`app` 丢了第二条中文＝主人报的那件事本身；`table.sort` 抹平桶里 51 处非字典序相邻的自带优先级，"
        "`appl` 首条 apple→applaud、`ap` 首条 apart→apace）；505 B 桩 **119/122 不同**。性能上他的结构不比我的差（0.004 ms/键），"
        "保留他的结构也行，条件是补回第二条中文＋联想按表内原顺序走。"
        "③**我自己的前提被推翻并当面更正（M-349）**：我说「整桶扫两遍＝卡的那条成本」，但桌面真 Lua 里旧写法也只要 0.70 ms/键，"
        "Mate 80 按 3–5 倍算 2–3 ms，一帧预算 16 ms ⇒ **查找逻辑解释不了他感觉到的卡**；"
        "更普遍的候选原因是 **H-263**（`fanxing_napi.cpp:545-560` 每次冷启动无条件 prebuild＋deploy＋4 次 deploy_schema＋start_maintenance，"
        "与主人 10-29 早上「重新部署大概 10 秒才好」同方向）。"
        "④**新查出的交付风险（M-350）**：`h106_precheck.py` 报的 16 项 dirty 我自己数了＝7 项 tracked 修改＋**9 项 untracked**，"
        "而那 9 项恰好是英文链的全部实物（dict 54,496／schema 1,162／codes 755,914／gloss 1,339,067／rev 373,202／trans 1,396,651／"
        "Filter 24,271／translator 505／bucket 1,508,284＝5,453,552 B），`git ls-files` 一个都不在册 ⇒ "
        "一次 `git clean -fd entry/src` 或换机器 clone 就把主人的英文链整条删掉、我补的 75 个词也只活在这份未入库的文件里，"
        "而 tracked 的 schema 仍挂着引用；这也解释了你我为什么能互相覆盖却没有 git 冲突提示。请他在 A（他署名提交）／"
        "B（授权我提交这 9 个＋两份守卫，不碰他 5 个在途文件）之间定一个。"
        "⑤**自家两处纠偏**：㉓ 行脚本漏 `% NOW` ⇒ 台账字面落了 `%s`（等于没有时间），按 mtime 量到写入时刻 14:45:30 就地补号留注；"
        "h267 守卫第一轮自测抓到它自己假绿（`lua-files.txt` 按子串判发布把注释行也算进去）⇒ 改按行解析＋剔注释行。"
        "台账 H-266／H-267／H-268 三行在册，信 M-348／M-349／M-350 已发；"
        "本轮**零构建、零签名、零装机、零注入**，改的是台账＋文档＋两份守卫＋一份桶数据。"
    ),
    '当前阻断': (
        "**2026-10-29 14:5x 刷新（Qoder）：不构建不装机，阻断是三条手续＋一个开关状态**。"
        "①`scripts/h106_precheck.py` 14:53 重跑阻断 3 项：「已做 checkpoint 提交」（entry/src＋AppScope 16 项未提交＝7 改＋9 新，"
        "含 CodeArts 在途的 `RimeDataInstaller.ets` 14:48:15、`KeyboardIndex.ets`）、"
        "「台账有待验收的 CodeArts 交付行」、「交付行含 unsigned 字节数」⇒ 按第 0 步口径**不构建**（我只写数据／Lua／文档，"
        "没构建、没签名、没装机、没注入）。②**功能面**：树内 `enWord_translator.lua`＝CodeArts 的 505 B 消融桩，"
        "而 `wubi_pinyin.custom.yaml:32` 挂载行是**打开**的 ⇒ 现在构建会把英文候选变成「打什么吐什么」"
        "（122 个前缀查询里 119 条与 6,478 B 基线不同：无中文注释、无联想、无第二条中文）；"
        "守卫 `scripts/h267_english_candidates_check.py` 对真树如实 rc=1，**实验桩不得进包**已记 H-268。"
        "③**数据面**：整条英文链 9 个文件／5,453,552 B 未入 git ⇒ 只存在这一块盘＋手机包内两处，"
        "谁做一次 clean／新 clone 就整条消失且从 git 查不出删过东西；已发 M-350 请 CodeArts 定 A／B（归属是他的，我不代他署）。"
        "④**手机现状**：Mate 80（7GL0226408083897）仍跑 14:10:04 那份 signed HAP 39,923,890 B——"
        "包内桶与工作区 sha1 一致（**75 个补词已在手机里**），translator 是 5,025 B 旧版（**第二条中文没进包**）⇒ 要看那条中文需再装一次；"
        "我按 M-349 的口径把它和 CodeArts 在途那批并成**一次**装机，不让他输两次密码。"
        "⑤**时间戳**：`h106_precheck.py` 现在 WARN 6 条「未来时间戳」（M-335～M-340 超前本机 182～482 分钟）——"
        "那是他那台机器的时钟，已在 M-346 点名请他落笔前先 `date`（H-134），我这侧全部按本机真实时钟写。"
        "⑥进度阻断清零：CodeArts 今晚持续在写这棵树，不是零回执。"
    ),
    '等主人': (
        "**2026-10-29 14:5x 刷新（Qoder）：等你两拍，都不用输密码**。"
        "**① Windows 托盘「重新部署」（约 10 秒，只能你点）**——13:15 换的 24,271 B 滤镜还没进 `build/`，线上跑的还是旧字节；"
        "我没替你点：`WeaselDeployer /deploy` 会弹「方案选单设定」模态且不写 build，我只关了窗，**没碰你那些方案勾选**。"
        "点完再打 app 应看到「1.app 注释 应用 yiet／yingyong 2.应用 3.＋中文…」。"
        "**② 手机上现在可以直接试打 app**（14:10 装的那份已带 75 个补词）：应出「app ＋注释 应用」；"
        "但**第二条可选中文**要等下一次构建装机——每次华为装机都要你输一次密码，所以我把这条和 CodeArts 在途那批并成**一次**再装，"
        "你说装我就装。③**一件你可能会察觉的反常**：现在鸿蒙树里那份英文翻译器被换成了 505 B 的排障桩（CodeArts 在校卡顿），"
        "如果你拿到新包后**打英文只是把字母原样吐回一条、没有中文也没有联想**，那不是功能回退，是那个实验桩；"
        "我已把实现版本与恢复命令写进信箱（M-349／M-350），等他定版。"
        "④其余旧的等验项（H-261 退格撤销三下、九键下五枚置灰、H-264 你已确认）见 ISSUES 对应行，本轮未新增。"
    ),
}


def split_row(line):
    """返回 (格名, [全部格])；只处理以 | 开头结尾的行。"""
    if not line.startswith('|') or not line.endswith('|'):
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
        for i, l in enumerate(lines[:40]):
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
    # 1) 文末附录：三格原文逐字
    block = ['', MARK, '',
             '> 合并口径（H-139）：读首每格只留一个带时间戳的段落，被合并掉的原文逐字留这里，一字不改。', '']
    for key in KEYS:
        block.append('#### 旧「%s」格（2026-10-29 14:5x 合并 ⇒ 原文逐字留此）' % key)
        block.append('')
        block.append(archived[key][1])
        block.append('')
    # 2) 替换三格（值列整体换成新格文；原值里有转义竖线也不受影响，因为整格替换）
    for key in KEYS:
        i, old = archived[key]
        _, cells = split_row(old)
        new = '|' + cells[0] + '| ' + NEW[key] + ' |'
        if '|' in NEW[key]:
            print('FAIL 新格文里有裸竖线：%s' % key)
            return 1
        lines[i] = new
    lines.extend(block)
    io.open(P, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines))
    print('已替换三格（行 %s）并归档原文；文件 %d 行（真实时钟 %s）'
          % (','.join(str(archived[k][0] + 1) for k in KEYS), len(lines), time.strftime('%H:%M')))
    return 0


if __name__ == '__main__':
    sys.exit(main())
