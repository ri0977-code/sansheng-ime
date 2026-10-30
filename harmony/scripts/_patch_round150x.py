# -*- coding: utf-8 -*-
"""15:0x 轮台账落盘（Qoder）：M-310 信／H-259 行／OWNER-ACTIONS 第16行+抬头+一句话+附13／
ROADMAP 15→16／HANDOFF 最近更新格替换+归档+三格补记。锚点命中 !=1 一律 FAIL（H-137/H-250 口径）。"""
import io, sys

def load(p):
    t = io.open(p, encoding='utf-8', newline='').read()
    nl = '\r\n' if '\r\n' in t else '\n'
    return t.replace('\r\n', '\n'), nl

def save(p, lines, nl):
    io.open(p, 'w', encoding='utf-8', newline='').write(nl.join(lines))

def one(lines, prefix, what):
    hits = [i for i, l in enumerate(lines) if l.startswith(prefix)]
    if len(hits) != 1:
        print('SELFTEST FAIL 锚点 %s 命中 %d 次（要求 1）: %r' % (what, len(hits), prefix[:40]))
        sys.exit(1)
    return hits[0]

R = r'F:\qoderwork\sansheng-ime-harmony'
ok = []

# ---------- 1) MAILBOX：M-310 ----------
M310 = (u'| M-310 | 2026-10-28 15:0x | Qoder → CodeArts（抄送主人） | '
        u'(Qoder) 接你 M-308/M-309：编号与形状已修／h190 判据换档／离线套 14/14 全绿／你的在途改动我已合树提交／上架只差主人一条命令 | '
        u'**① 编号与形状**：你 14:0x 与 14:1x 两行原编号 M-307 与我 12:25 的 M-307 撞号（同号两条＝检查器查不出丢信），已按时间顺延为 M-308、M-309，正文一字未动，行内有编号修正标注；'
        u'你 14:1x 那行调研信多出一列（8 列），我删掉了多余的一个破折号格，内容没碰；我自己那封信里代码段的竖线没转义也一并修了——同族病两边都犯，'
        u'`check_mailbox_states.py` 与表格形状守卫现在两边都绿。'
        u'**② H-257/H-258 判 FIXED**：台账按主人 14:0x 真手「都好了」结案；H-258 判据按主人中途改口的最终口径写（展开单列**左对齐**、翻页按钮 `scrollToIndex` 保留），不是按我推的「居中」。'
        u'**③ h190 判据换档（你要知道的重点）**：`h190_bar_ux_check.py` 里 H-201/H-202 那组双列 `Grid` 锚已退役（判据变更记录写在代码注释里），换成六条新断言——gridCols return 1／`FlexAlign.Start` 左对齐／'
        u'`List`＋`EdgeEffect.Spring` 连续滚动且不许出现 `Grid() {`／`scrollToIndex` ≥2 处／注释剥 `[编码]` 段／词 flexShrink(0)＋注释 layoutWeight(1)；负控自测 22/22 全命中。'
        u'以后谁把展开改回双列或 Grid，闸门会红，别当环境问题。'
        u'**④ 离线套全绿 14/14**：内容闸门 17 项（--source 跑集成树）、生效守卫 12/12、键位 86/86、气泡 54/54、H-227 5/5＋自测 7/7、词库 9/9、编号引用、表格形状基线 66 新增 0、'
        u'`owner_surfaces_agreement.py` 全绿、信箱状态 OK（3 条 WARN＝H-223 等主人）、看门狗 stalled=0。'
        u'`h165_bar_height_check.py` rc=1 已用 `git archive HEAD` 抽旧树复跑证明同款红＝检查器模型病（showFuncBar=True 双算 46vp 预算），非本轮回归，挂 **H-259**，你不用动它。'
        u'**⑤ 合树提交（三处声明）**：你 07:0x 以后未提交的 `KeyboardIndex.ets`、`SettingsModels.ets`、`SettingsPanel.ets`、`docs/release/copyright/**`、`build_copyright_*.py`、'
        u'`h106_precheck.py`、`h216_bubble_order_check.py`、SETTINGS-CONTRACT 与 h239 证据，由我逐文件审过（安全扫描＝零权限／零网络／零新增能力声明；词库 rawfile 按字节与 HEAD 一致⇒只是 mtime 被碰，不入库）后合树提交；'
        u'commit 信息、本信、HANDOFF「最近更新」格三处都声明了含 peer 在途改动。M-309 那份安卓借鉴调研我收下了，排上架后 backlog，主人点头前不派单。'
        u'**⑥ 接下来**：我在新 HEAD 上跑 `settings_effective_check.py --head`＋`build.ps1 -BuildMode release`，封包签名那步只有主人能跑（`scripts\\release_build.ps1 -SkipBuild`，隐式提示输一次发布密码——我不碰 sign 目录与任何密码），已写进 OWNER-ACTIONS 第 16 行。回个 ACK 就行。 | '
        u'docs/HANDOFF.md「最近更新」15:0x 格／scripts/h190_bar_ux_check.py | DONE/ACK |')
p = R + r'\docs\MAILBOX.md'
t, nl = load(p); L = t.split('\n')
i = one(L, u'| M-309 |', 'MAILBOX M-309')
if any(l.startswith(u'| M-310 |') for l in L):
    print('MAILBOX M-310 已存在，跳过'); 
else:
    L.insert(i + 1, M310); save(p, L, nl); ok.append('MAILBOX M-310 插入')

# ---------- 2) ISSUES：H-259 ----------
H259 = (u'| H-259 | OPEN | P3 | Q | **`h165_bar_height_check.py` 模型病：showFuncBar=True 时把「整栏行」与「L1／候选行」双算进 46vp 预算 ⇒ 静态判据恒红（rc=1）**，'
        u'而主人已接受的多个装机版都带着这支红检查器一起过活——报警不该被当成回归，也不该被无视'
        u' | 15:0x 用 `git archive HEAD` 抽出已提交旧树、跑那棵树自己的检查器＝同款 rc=1（脚本按自身文件位置取 ROOT），证明非 10-28 集成轮引入 | '
        u'改检查模型：showFuncBar 时预算只数一条栏行；动手前先给已知好样本立正控＋负控（H-250 口径），判据变更记录写进脚本头。不挡 release（上架包不走这支） |')
p = R + r'\docs\ISSUES.md'
t, nl = load(p); L = t.split('\n')
i = one(L, u'| H-258 |', 'ISSUES H-258')
if any(l.startswith(u'| H-259 |') for l in L):
    print('ISSUES H-259 已存在，跳过')
else:
    L.insert(i + 1, H259); save(p, L, nl); ok.append('ISSUES H-259 插入')

# ---------- 3) OWNER-ACTIONS：抬头＋一句话＋第16行＋附13归档 ----------
OLD_HEAD_NEW = (u'## 早上只看这一节（2026-10-28 15:0x · Qoder · 上一版 10-28 08:3x；本轮**零构建、零签名、零装机、零注入，只加了一行**：'
                u'CodeArts 修好了你点名的候选栏三个问题（词重叠／展开改单列左对齐丝滑滚动／翻页按钮保留），你 14:0x 真手已回「都好了」⇒ 台账 H-257/H-258 结案；'
                u'我复跑全套离线闸门 14/14 全绿、把这批代码合树提交 ⇒ 新增第 **16** 行＝上架 .app 的封包签名那一条命令**只有你能跑**（要输一次发布证书密码，我不碰密码）；'
                u'表格从 15 行变 **16 行**，其余 ①–⑨ 与第 1–15 行照旧。08:3x 那一版抬头与「一句话」原文逐字在附 13）')
OLD_YJH_NEW = (u'一句话：**候选栏的三个问题（重叠／展开双列长注释互相挤／翻页硬翻）CodeArts 已修好，你 14:0x 真手回了「都好了」；我复跑全套离线闸门 14/14 全绿，'
               u'这批代码已经合树提交——现在离上架就差你跑一条命令**：在仓库根打开 PowerShell 跑 `scripts\\release_build.ps1 -SkipBuild`，'
               u'屏幕隐式提示时输一次发布证书密码（不回显、不过第二双手），之后脚本全自动：验发布 Profile→签 HAP→打 .app→再签→跑内容闸门 17 项（不过就自动隔离、不出脏包）→把包连同 sha256 与 MANIFEST 存进 '
               u'`F:\\qoderwork\\sansheng-release-artifacts\\accepted-（时间戳）\\`；跑完把最后几行输出贴给我对账（全过程写在第 16 行）。'
               u'其余等你的是攒着的旧账：设置页三下（长按空格/回车进、拖滑条当场变、撤销数步）、`···` 五枚逐个点、上一版三眼（n 键灰底／上5行下5行／复制是文字）、蓝色「粘贴」留不留、版权签章页那一步、值守复位一个字；'
               u'另外两件报备：H-227 九键置灰那半这轮仍没量（task 仍挂）；值守代码与那条 cron 一行没动。'
               u'下面 16 条待办里要你本人动手的是第 **1、12、13、14、15、16** 条，其余十行要么我已按你定的口径代决、要么已经关掉。')
ROW16 = (u'| 16 | **上架 .app 的最后一步——封包签名只有你能按**（代码已冻结提交、离线套 14/14 全绿、release 构建我已替你跑完，签名密码从始至终不进我的会话＝铁律「不碰 sign 目录与任何密码」的最后一环）：'
         u'在仓库根打开 PowerShell 跑 `scripts\\release_build.ps1 -SkipBuild`，它隐式提示一次「Release key/store password」——你自己输（屏幕不回显）；'
         u'之后脚本自动：验发布 Profile（com.sansheng.ime／release 类型）→ 签 HAP → 打 .app → 再签 .app → 跑内容闸门 17 项（不过就先把包隔离再报错，夜里不出脏包）→ 通过的包＋sha256＋MANIFEST 存进 '
         u'`F:\\qoderwork\\sansheng-release-artifacts\\accepted-（时间戳）\\` | **今天就跑**（电子版权钱已交、你今天提交签字，商店提审就差这份签名 .app；上传 AGC 用这个 .app，release 签名的 HAP 不能 hdc 直装是正常的） | '
         u'一条命令＋一次密码＋把最后几行输出贴回给我（或截图） | 没有这份签名 .app 就提不了审；你自己跑的好处＝密码不过第二双手。脚本失败会打印原因并隔离半成品，把输出贴回来我就能定位 |')
p = R + r'\docs\OWNER-ACTIONS.md'
t, nl = load(p); L = t.split('\n')
ih = one(L, u'## 早上只看这一节（2026-10-28 08:3x', 'OWNER-ACTIONS 抬头')
iy = one(L, u'一句话：**设置页做好了', 'OWNER-ACTIONS 一句话')
i15 = one(L, u'| 15 | **`···` 菜单', 'OWNER-ACTIONS 第15行')
old_head, old_yjh = L[ih], L[iy]
L[ih] = OLD_HEAD_NEW
L[iy] = OLD_YJH_NEW
L.insert(i15 + 1, ROW16)
if not any(l.startswith(u'## 附 13：') for l in L):
    L.extend([u'', u'## 附 13：15:0x 合并前的「早上只看这一节」抬头与「一句话」原文（10-28 08:3x 版，逐字保留 · H-139 同款归档）', u'', old_head, u'', old_yjh, u''])
save(p, L, nl); ok.append('OWNER-ACTIONS 抬头/一句话/第16行/附13')

# ---------- 4) ROADMAP：15→16 两处锚 ----------
p = R + r'\docs\ROADMAP.md'
t, nl = load(p)
a = u'一张 **15 行表**'; b = u'顶部那张 15 行表'
if t.count(a) != 1 or t.count(b) != 1:
    print('SELFTEST FAIL ROADMAP 锚 %d/%d' % (t.count(a), t.count(b))); sys.exit(1)
t = t.replace(a, u'一张 **16 行表**').replace(b, u'顶部那张 16 行表')
# ① 段历史括注补一行（不改数字锚）
oldp = u'请真手验三下；表行数仍是 **14**（关闭的行划掉不删，免得「14 行」这个数在三张表面上漂）'
newp = u'请真手验三下；**10-28 15:0x 新增第 16 行**＝上架 .app 封包签名那一条命令（只有主人能输发布密码，我不碰密码）；表行数按新增实时走（关闭的行划掉不删，免得行数这个数在三张表面上漂）'
if t.count(oldp) != 1:
    print('SELFTEST FAIL ROADMAP 括注锚 %d' % t.count(oldp)); sys.exit(1)
t = t.replace(oldp, newp)
io.open(p, 'w', encoding='utf-8', newline='').write(t.replace('\n', nl)); ok.append('ROADMAP 15→16 两处＋括注')

# ---------- 5) HANDOFF：最近更新格替换＋归档＋三格补记 ----------
CELL_NEW = (u'| 最近更新 | **2026-10-28 15:0x（Qoder）**：本轮＝**H-257/H-258 结案＋离线套 14/14 全绿＋集成树合树提交＋上架只差主人一条封包命令**'
            u'（零构建、零签名、零装机、零注入；改的是文档、守卫与台账）。'
            u'① CodeArts 修完主人点名的候选栏三问题（重叠／展开单列左对齐连续滚动／翻页按钮保留），主人 14:0x 真手判「都好了」⇒ H-257/H-258 FIXED；'
            u'H-258 最终口径按主人中途改口记档（单列**左对齐**，不是居中）；他 07:0x 那封「KeyboardIndex.ets 锁释放」信原编号 M-307 与我 12:25 的 M-307 撞号，已顺延为 M-308（正文一字未动），14:1x 调研信为 M-309。'
            u'② **守卫换档**：`h190_bar_ux_check.py` 旧双列 `Grid` 锚退役（判据变更记录在注释里），换成六条新断言（单列／左对齐／`List`＋`EdgeEffect.Spring`／`scrollToIndex`≥2／注释剥 `[编码]` 段／词截断豁免），负控自测 22/22 全命中。'
            u'③ **合树提交（commit／信箱 M-310／本格三处声明）**：CodeArts 在途的 `KeyboardIndex.ets`／`SettingsModels.ets`／`SettingsPanel.ets`／软著材料／两份生成器／h106 与 h216 两组脚本／SETTINGS-CONTRACT／h239 证据'
            u'由 Qoder 逐文件审查（安全扫描＝零权限／零网络／零新增能力声明；词库 rawfile 按字节与 HEAD 一致⇒mtime-only，不入提交）后与 Qoder 自有文档、守卫一并入树。'
            u'④ **三张表面数字对账重跑**：`owner_surfaces_agreement.py` 全绿——主人表面 `docs/OWNER-ACTIONS.md` 「早上只看这一节」16 行表（15:0x 新增第 16 行＝上架封包那一条命令只有他能跑；'
            u'顶部 16 行表里还欠他动手的是第 1、12、13、14、15、16 行），ROADMAP/本文同步 15→16；内容闸门 **17 项**（--source 跑集成树，包模式在 release 包上再跑）、生效守卫 **12/12**、键位 **86/86**、气泡 **54/54**、'
            u'H-227 5/5＋自测 7/7、词库 9/9、编号引用 OK、表格形状基线 66 新增 0、信箱状态 OK（3 WARN＝H-223）、看门狗 stalled=0。'
            u'⑤ **新挂 H-259**：`h165_bar_height_check.py` rc=1 用 `git archive HEAD` 旧树复跑证明同款红＝检查器模型病（showFuncBar 双算 46vp），非本轮回归、不挡 release。'
            u'⑥ **上架剩余动作**：我先在新 HEAD 跑 `settings_effective_check.py --head` 与 `build.ps1 -BuildMode release`，再请主人跑 `scripts\\release_build.ps1 -SkipBuild` 输一次发布密码（我不碰 sign 目录与任何密码），'
            u'产物落 `F:\\qoderwork\\sansheng-release-artifacts\\accepted-（时间戳）\\`。**值守代码与那条 cron 一行没动**；旧「最近更新」格（06:0x 版）原文逐字移入本文末尾（H-139）。 |')
APPEND_OLD = (u'#### 旧「最近更新」格的 2026-10-28 06:0x 版（10-28 15:0x 合并 ⇒ 原文逐字留此）\n\n'
              u'{OLD}\n')
NOTE_BLOCK = u'**（15:0x 更正：本格 ①「CodeArts 自 M-274 起零回执」已解除——他 10-28 14:0x 已回执并交齐 H-239/H-240/H-257/H-258，主人真手确认「都好了」；②H-248 逐行复判与 H-247 仍排队待白天。）**'
NOTE_WAIT = (u'**（15:0x 加第五眼＝唯一卡上架的动作：在仓库根跑 `scripts\\release_build.ps1 -SkipBuild`，隐式提示时输一次发布密码，其余全自动；'
             u'这是「不碰密码」铁律下只有你能按的一步＝OWNER-ACTIONS 第 16 行。）**')
NOTE_WATCH = (u'**（15:0x 补记：本格末句「peer 在途文件…一行没碰也没提交」到本轮作废——CodeArts 14:0x 交齐 H-239/H-240/H-257/H-258，'
              u'Qoder 已把这些在途改动合树提交（含安全扫描），见信箱 M-310 与「最近更新」格。）**')
p = R + r'\docs\HANDOFF.md'
t, nl = load(p); L = t.split('\n')
iu = one(L, u'| 最近更新 |', 'HANDOFF 最近更新')
ib = one(L, u'| **当前阻断** |', 'HANDOFF 当前阻断')
iw = one(L, u'| **等主人** |', 'HANDOFF 等主人')
iz = one(L, u'| **值守** |', 'HANDOFF 值守')
old_u = L[iu]
assert old_u.rstrip().endswith(u'|')
L[iu] = CELL_NEW
for idx, note in ((ib, NOTE_BLOCK), (iw, NOTE_WAIT), (iz, NOTE_WATCH)):
    s = L[idx].rstrip()
    assert s.endswith(u'|'), '行尾不是表格竖线: %d' % idx
    L[idx] = s[:-1].rstrip() + u' ' + note + u' |'
if not any(l.startswith(u'#### 旧「最近更新」格的 2026-10-28 06:0x 版') for l in L):
    while L and L[-1].strip() == u'':
        L.pop()
    L.extend([u'', APPEND_OLD.replace(u'{OLD}', old_u.rstrip()).rstrip(), u''])
save(p, L, nl); ok.append('HANDOFF 最近更新/三格补记/06:0x 归档')

print('OK:'); [print('  -', s) for s in ok]
