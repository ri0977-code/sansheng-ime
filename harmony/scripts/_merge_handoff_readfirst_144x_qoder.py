# -*- coding: utf-8 -*-
"""合并 HANDOFF「当前状态」读首三格（Qoder 2026-10-29 14:4x）

规则（H-139）：读首每一格只留**一个带时间戳的段落**；被合并掉的原文**逐字**进文件末尾附录。
本轮合并掉的是 14:2x 那三格（逐字归档），换上去的是 14:4x 版：把「CodeArts 14:29:36 把英文
translator 整条注释掉 ⇒ 排查卡顿」这件新事实并进去。
备份：_probe/rawfile-backups-20261029/HANDOFF.md.bak-qoder-20261029-144x-before-readfirst
幂等：文末已存在本轮附录块就只报「已归档过」，不重复搬。
"""
import io
import os
import sys

ROOT = r'F:\qoderwork\sansheng-ime-harmony'
P = os.path.join(ROOT, 'docs', 'HANDOFF.md')
MARK = '### 2026-10-29 14:4x · Qoder（归档：本轮合并掉的「当前状态」三格原文＝14:2x 版）'

KEYS = ['最近更新', '当前阻断', '等主人']

NEW = {
    '最近更新': (
        "**2026-10-29 14:4x（Qoder·「app 没有中文」三端补完 ＋ 英文链的卡顿我量了也修了；"
        "鸿蒙这轮仍不构建不装机）**：主人原话「这个app对吗，后面都是联想，没有中文，看万能五笔的截图」"
        "＋两张截图（我们 app 出 appa／appy／appl／appo／apps 五条全英文；万能五笔出 1.应用…5.app）。"
        "**根因在我们自己的词库生成器**：`gen_en_word.py` 的 `eligible()` 只收「全小写」与「首字母大写」两种写法 "
        "⇒ ECDICT 里只有全大写形式的缩写词（APP／CPU／OK／URL／TV／DNA…）从没进过 `en_word.dict.yaml`，"
        "gloss 表与鸿蒙分桶表跟着一起缺；滤镜场景1 又要求「输入本身是库里有的词」才接管 ⇒ app 完全不接管。"
        "①**Windows／安卓**＝滤镜 24,271 B（sha1 cc786d1adbdc）新增**场景1b**（第1条英文本词带「应用 yiet／yingyong」"
        "＋反查码、第2条中文译词、其余中文在前、英文联想仍≤5、码感知不排），`_probe/run_1b_regression.py` 16 条断言全过"
        "＋真实 rime.dll 双会话验「点一次应用即升第1位」；四份权威拷贝逐文件同字节。"
        "②**安卓**＝seed SEED_VERSION 15＋APK 1967（63,084,064 B）装 emulator-5554，cat／qtal／mao／app 四条全绿。"
        "③**鸿蒙断在数据不在滤镜**：`scripts/_patch_bucket_add_abbrev_qoder.py` 把 **75 个**缩写词插进 "
        "`en_word_bucket.txt`（55,792→55,867 行，difflib 判 insert=75 delete=0 replace=0）；"
        "translator 加**第二条中文候选**（用桶里已有释义，不新读文件、不占联想名额）。"
        "④**本轮新事实（14:29:36）**：CodeArts 把 `wubi_pinyin.custom.yaml:32` 的 "
        "`- lua_translator@enWord_translator` **整条注释掉**（「v30 暂禁用，排查卡顿原因」）⇒ 那一版包里英文候选是关的。"
        "他观察成立、归因不完整：**旧 translator 每按一个键把命中桶整桶扫两遍**（最大桶 `s` 5,973 条 ⇒ ≈1.2 万次比较"
        "＋等量 `:lower()` 分配），这正是「卡」的那条成本（我 M-324-re 的判据 ③ 只做到分桶、红线是空的，我认）。"
        "**修法＝改成本不是关功能**：`enWord_translator.lua` 现在 8,553 B（sha1 cdebb6fa96c3），加载时建 "
        "`exact`／`idx2`／`idx3` 三张**保持表内原顺序**的索引，按输入长度选表；"
        "`_probe/bench_enword_translator_qoder.py`（lupa 跑真文件真 Lua，驱动不出 Python 边界）对 122 个逐字母前缀查询实测："
        "**新旧产出逐条全等**，每按键 0.688 ms → 0.007 ms（98.7×），冷启动 74→88 ms（一次性 ＋14 ms），"
        "常驻内存 12,877→12,800 KB。新守卫 `scripts/h267_english_candidates_check.py`（三层：桶数据／发布清单／"
        "代码是索引式，并**禁止对桶 `table.sort`**）自测 6/6；`scripts/h266_package_hygiene_check.py` 管住我上一轮"
        "把 `.bak` 就地留在 rawfile 被打包的 5.8 MB（已挪 `_probe/rawfile-backups-20261029/`，一个没删）。"
        "**踩过并写进 H-267**：我先做的「桶内排序＋二分」被基准当场判红——桶里那 51 处非字典序相邻是数据自带的优先级，"
        "排完 `appl` 首条联想从 apple 变成 applaud ⇒ 那是改行为不是改性能。**回信 M-348 已发**：挂不挂由 CodeArts 定，"
        "但请把决定写进行里，禁用理由已被这份数字消掉。"
    ),
    '当前阻断': (
        "**2026-10-29 14:4x 刷新（Qoder）：本轮鸿蒙不构建不装机，阻断在交付手续＋一个被人关掉的开关**。"
        "①`scripts/h106_precheck.py` 14:4x 重跑仍阻断 3 项：工作区 16 项未提交（含 CodeArts 在途的 "
        "`RimeDataInstaller.ets`、`KeyboardIndex.ets`）、台账无「CodeArts 署名＋真实字节数＋未回抄」的待验收交付行、"
        "交付行无 unsigned 字节数 ⇒ 按第 0 步口径**不构建**（我只写了数据与 Lua，没构建／没签名／没装机／没注入）。"
        "②他 M-347 说「v29 交付行需构建才能报真实字节数，值守不允许构建，主会话处理」，随后 14:30:30／14:31:13 "
        "树里确实出了包（unsigned 33,977,961／signed 34,102,905 B，比 14:09 那份少 5.8 MB＝我挪掉备份掉的），"
        "**但台账里还没有他那行署名交付数字**——我不代他署（H-133：字节数只在同一人同一工作区里可比对）。"
        "③**功能面阻断**：`wubi_pinyin.custom.yaml:32` 的英文 translator 挂载当前是注释状态，"
        "且 `enWord_Filter` 也没挂（鸿蒙不挂滤镜是既定设计，靠 translator＋桶）⇒ 现在这版**不会出英文候选**；"
        "守卫 `h267_english_candidates_check.py` 对此只 INFO 不拦（挂不挂是 CodeArts 的归属区），已写信要求把决定写进台账。"
        "④手机现状：Mate 80（7GL0226408083897）仍跑 14:10:04 那份 signed 39,923,890 B——"
        "包内桶与工作区 sha1 一致（**75 个补词已在手机里**），translator 是 5,025 B 旧版（**第二条中文候选没进包**）。"
        "⑤我这侧没有零回执问题：CodeArts 今晚持续在写这棵树，时间戳也已按 H-134 回到真实时钟。"
    ),
    '等主人': (
        "**2026-10-29 14:4x 刷新（Qoder）：等你两拍，都不用输密码**。"
        "**① Windows 托盘「重新部署」（约 10 秒，只能你点）**——13:15 换的 24,271 B 滤镜还没进 `build/`，"
        "线上跑的还是旧字节；我没替你点：`WeaselDeployer /deploy` 会弹「方案选单设定」模态且不写 build，"
        "我只关了窗，**没碰你那些方案勾选**。点完再打 app 应看到「1.app 注释 应用 yiet／yingyong 2.应用 3.＋中文…」。"
        "**② 手机上现在可以直接试打 app**（14:10 装的那份已带补词）：应出「app ＋注释 应用」；"
        "但**第二条可选中文**要等下一次装机——每次华为装机都要你输一次密码，所以我想把这条和 CodeArts 在途那批并成**一次**再装，"
        "你说装我就装。③**一件你可能会察觉的相反变化**：CodeArts 14:29 那版把英文 translator 关了（他在校卡顿），"
        "如果你拿到新包后发现**打英文不出英文词了**，那不是回退，是那个开关；我已在 M-348 里给了"
        "「关掉的理由不成立」的实测数字（每按键 0.688 ms→0.007 ms、122 个查询产出全等），等他挂回。"
        "④其余旧等验项（H-261 退格撤销三下、九键五枚置灰、H-264 你已确认）见 ISSUES 对应行，未新增。"
    ),
}


def split_row(line):
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
        for i, l in enumerate(lines):
            name, cells = split_row(l)
            if name == key and cells and len(cells) == 2:
                archived[key] = (i, l)
                break
        if key not in archived:
            print('FAIL 没找到「%s」格（应为 2 列行）' % key)
            return 1
    block = ['', MARK, '',
             '> 合并口径（H-139）：读首每格只留一个带时间戳的段落，被合并掉的原文逐字留这里，一字不改。', '']
    for key in KEYS:
        block.append('#### 旧「%s」格（2026-10-29 14:4x 合并 ⇒ 原文逐字留此）' % key)
        block.append('')
        block.append(archived[key][1])
        block.append('')
    for key in KEYS:
        i, old = archived[key]
        _, cells = split_row(old)
        lines[i] = '|' + cells[0] + '| ' + NEW[key] + ' |'
    lines.extend(block)
    io.open(P, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines))
    print('已替换三格（行 %s）并归档 14:2x 原文；文件 %d 行'
          % (','.join(str(archived[k][0] + 1) for k in KEYS), len(lines)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
