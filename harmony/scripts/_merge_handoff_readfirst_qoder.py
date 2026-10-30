# -*- coding: utf-8 -*-
"""合并 HANDOFF「当前状态」读首三格（Qoder 2026-10-29 14:2x）

规则（H-139）：读首每一格只留**一个带时间戳的段落**；被合并掉的原文**逐字**进文件末尾附录。
本脚本：① 把 21/23/24 三行的原格文逐字搬到末尾新附录块；② 用本轮合并后的文本替换该格。
备份：_probe/rawfile-backups-20261029/HANDOFF.md.bak-qoder-20261029-1422-before-readfirst
幂等：文末已存在本轮附录块就只报「已归档过」，不重复搬。
"""
import io
import os
import re
import sys

ROOT = r'F:\qoderwork\sansheng-ime-harmony'
P = os.path.join(ROOT, 'docs', 'HANDOFF.md')
MARK = '### 2026-10-29 14:2x · Qoder（归档：本轮合并掉的「当前状态」三格原文）'

KEYS = ['最近更新', '当前阻断', '等主人']

NEW = {
    '最近更新': (
        "**2026-10-29 14:2x（Qoder·「app 没有中文」三端补完，Windows 差主人一拍、鸿蒙差一次装机）**："
        "主人原话「这个app对吗，后面都是联想，没有中文，看万能五笔的截图」＋两张截图（我们 app 出 appa／appy／appl／appo／apps 五条全英文；"
        "万能五笔出 1.应用 2.蒙冤q 3.劳神y 4.禁寨f 5.app 6.劳军l）。**根因是我们自己的词库生成器**："
        "`gen_en_word.py` 的 `eligible()` 只收「全小写」和「首字母大写」两种写法 ⇒ ECDICT 里只有全大写形式的缩写词"
        "（APP／CPU／OK／URL／TV／DNA…）从没进过 `en_word.dict.yaml`，gloss 表和鸿蒙分桶表跟着一起缺；"
        "而滤镜场景1 要求「输入本身是库里有的词」才接管 ⇒ app 完全不接管，只剩前缀联想，"
        "违反已定口径「一位二位，是给本义和翻译的」。①**Windows／安卓**＝滤镜 24,271 B（sha1 cc786d1adbdc）新增**场景1b**"
        "（第1条英文本词带「应用 yiet／yingyong」＋反查码、第2条中文译词、其余中文在前、英文联想仍≤5、码感知不排），"
        "`_probe/run_1b_regression.py` 16 条断言全过＋真实 rime.dll 双会话验「点一次应用即升第1位」；"
        "四份权威拷贝逐文件同字节。②**安卓**＝seed SEED_VERSION 15＋APK 1967（63,084,064 B／sha256 d4d1c50f39e87618…，"
        "相对 1966 只差 seed zip 与 classes3.dex）装 emulator-5554，cat／qtal／mao／app 四条全绿。"
        "③**鸿蒙断在数据不在滤镜**（滤镜为躲大 TSV 卡顿被注释，走 H-260 方向1 的 Lua translator＋桶）："
        "`scripts/_patch_bucket_add_abbrev_qoder.py` 把 `en_word_trans.tsv` 有、桶里没有的 **75 个**缩写词按桶内字典序插进"
        " `en_word_bucket.txt`（55,792→55,867 行，difflib 判 insert=75 delete=0 replace=0）；"
        "`lua/enWord_translator.lua` 5,025→6,478 B 再加**第二条中文候选**（用桶里已有释义，不新读文件、不占联想名额，"
        "且改在 CodeArts 14:07:56 那版之后、他的性能重排一行没动）；"
        "`_probe/run_harmony_translator_offline_qoder.py` 用 lupa **真跑在用的这份 Lua＋补词后的这份桶**："
        "app→「app[应用 yiet／yingyong] 应用[app] apparent…」cpu→「cpu 中央处理器」单字母不出联想≤5 ⇒ PASS。"
        "④**自查纠两条**：我把 `.bak-*` 备份就地留在 rawfile ⇒ 被 hvigor 打进 HAP 白背 5.8 MB（已挪进 "
        "`_probe/rawfile-backups-20261029/`，一个没删，H-266）；M-264／M-269 状态列 14:00 已回收 DONE，"
        "`check_mailbox_states.py` exit 0 ⇒ CodeArts 那 22 封「仍 OPEN」ACK 是从旧副本检出的，已回信（M-346）请他停追加。"
        "⑤**值守相关的新事实**：CodeArts 此刻仍在动这棵树（14:07:56 translator、14:08:27 桶 CRLF→LF、14:10:04 装机、14:26 又动 "
        "`sansheng_t9.schema.yaml`），他还没按台账报 unsigned 字节数；另外他 M-332 起的信写着**未来时间**（超前本机约 10 小时）"
        "⇒ 值守「最新行 20 分钟内只读」会算出负龄，已在 M-346 里点名请他落笔前先 `date`（H-134）。"
    ),
    '当前阻断': (
        "**2026-10-29 14:2x 刷新（Qoder）：本轮鸿蒙不构建不装机，阻断在交付手续不是代码**。"
        "①`scripts/h106_precheck.py` 14:18 跑出的三条阻断：工作区 16 项未提交（含 CodeArts 在途的 `RimeDataInstaller.ets`、"
        "`KeyboardIndex.ets`）、台账无「CodeArts 署名＋真实字节数＋未回抄」的待验收交付行、交付行无 unsigned 字节数"
        "⇒ 按第 0 步口径**不构建**（exit 2 只写信不装机）。②CodeArts 14:0x 那批（DATA_VERSION→`h260-enword-translator-v29`、"
        "translator 性能改版、桶 CRLF→LF、14:26 的 `sansheng_t9.schema.yaml`）**我没碰也没提交**，"
        "他报交付行后由那一轮统一合树。③手机现状＝Mate 80（7GL0226408083897）`updateTime` 14:10:04，"
        "装的是 14:09:51 那份 signed HAP 39,923,890 B：包内桶与工作区 sha1 一致（**75 个补词已在手机里**），"
        "但 translator 还是 5,025 B 旧版（**第二条中文候选没进包**）⇒ 要看那条中文需再构建＋装一次。"
        "④进度阻断清零：CodeArts 不再是零回执，他今晚一直在写这棵树。"
    ),
    '等主人': (
        "**2026-10-29 14:2x 刷新（Qoder）：等你两拍，都不用输密码**。"
        "**① Windows 托盘「重新部署」（约 10 秒，只能你点）**——13:15 换的 24,271 B 滤镜还没进 `build/`，"
        "线上跑的还是旧字节；我没替你点：`WeaselDeployer /deploy` 会弹「方案选单设定」模态且不写 build，"
        "我只关了窗，**没碰你那些方案勾选**。点完再打 app 应看到「1.app 注释 应用 yiet／yingyong 2.应用 3.＋中文…」。"
        "**② 手机上现在可以直接试打 app**（14:10 装的那份已带补词）：应出「app ＋注释 应用」；"
        "但**第二条可选中文**要等我下一次构建装机——每次华为装机都要你输一次密码，所以我想把这条和 CodeArts 在途那批并成**一次**再装，"
        "你说装我就装。③其余旧的等验项（H-261 退格撤销三下、九键五枚置灰、H-264 主人已确认）见 ISSUES 对应行，未新增。"
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
        for i, l in enumerate(lines):
            name, cells = split_row(l)
            if name == key and cells and len(cells) == 2:
                archived[key] = (i, l)
                break
        if key not in archived:
            print('FAIL 没找到「%s」格（应为 2 列行）' % key)
            return 1
    # 1) 文末附录：三格原文逐字
    block = ['', MARK, '',
             '> 合并口径（H-139）：读首每格只留一个带时间戳的段落，被合并掉的原文逐字留这里，一字不改。', '']
    for key in KEYS:
        block.append('#### 旧「%s」格（2026-10-29 14:2x 合并 ⇒ 原文逐字留此）' % key)
        block.append('')
        block.append(archived[key][1])
        block.append('')
    # 2) 替换三格（值列整体换成新格文；原值里有转义竖线也不受影响，因为整格替换）
    for key in KEYS:
        i, old = archived[key]
        _, cells = split_row(old)
        lines[i] = '|' + cells[0] + '| ' + NEW[key] + ' |'
    lines.extend(block)
    io.open(P, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines))
    print('已替换三格（行 %s）并归档原文；文件 %d 行'
          % (','.join(str(archived[k][0] + 1) for k in KEYS), len(lines))
    )
    return 0


if __name__ == '__main__':
    sys.exit(main())
