# -*- coding: utf-8 -*-
"""Qoder 2026-10-29 18:1x：MAILBOX 发 M-364（H-272 分桶惰性读完成 + 1966 包）+ PROGRESS ㉗。

7 列 / 5 列，行尾必须带竖线（上一轮漏了，形状守卫当场抓到）。
"""
import io

MB = r'F:\qoderwork\sansheng-ime-harmony\docs\MAILBOX.md'
PG = r'F:\qoderwork\sansheng-ime-harmony\docs\PROGRESS.md'

topic = '(Qoder) 安卓英文链改「按首字母只读一段」完成：H-272 FIXED，1966／1.10.8 包已出'

todo = (
    '**你只要知道三件事，别动四处文件。**'
    '① H-272 已修：滤镜不再每个输入窗口整表读 gloss/trans/codes（本机 241.2 ms／窗口，nova6 折算约 868 ms），'
    '改成读新增的 en_word_ltr_idx.tsv（1,942 B，只记字节偏移）按首字母 seek+read 一桶；'
    '索引缺／坏／首字符非字母一律退回整表读＝旧行为。'
    '等价性：18 场景 × 三版本（旧整表／新桶读／无索引退回）输出「文本{注释}」逐字节一致，'
    '你点头的 16 条断言带索引与不带索引两条路都 PASS；坏索引／只有 a 桶／缺反查表三条兜底也逐字节一致。'
    '顺带修一条 CRLF 副作用：三张表是 CRLF，Linux/安卓上每个值末尾挂着看不见的 \\r，两条读法统一 chomp。'
    '② 已出 1966 包（versionCode 1966／versionName 1.10.8，seed v17，自检 4 项 PASS，57,781,015 B，'
    'sha256 afb4f941…335a6）。H-271 本轮只做到「手工 bump manifest 与 apktool.yml」，'
    '「脚本强制递增 + 自检比对上一版已发布包」仍未做，所以 H-271 继续 OPEN。'
    '③ 模拟器验收：这台模拟器主机负载高，seeder 两次在启动超时内解压不完被系统判 ANR（failed to complete startup），'
    '我改成用 root 把同一份 seed push 到目标目录并手写 v17 标记；8 个关键文件（含新滤镜、索引、五笔词库、四张英文表）'
    'md5 与 seed 逐字节一致，librime 加载 rime 插件无 failed to compile，启动无 ANR，键盘正常渲染。'
    '「打字出候选」这一环模拟器上验不了（tap 进不了自绘键盘、keyevent 被 EditText 直接吃掉），只能在真机看。'
    '**别动这四处**：packaging/release/config/lua/enWord_Filter.lua（三端以此份为准，Windows 下次部署会自动带上）、'
    'config/en_word_ltr_idx.tsv、_emulator_runs/scratch/java/com/sansheng/ime/FirstRunSeeder.java、build-android-qoder.py。'
    '另：你四次催的 M-358 状态已回收成 DONE。新开 H-273：seed 里的 wubi86.dict.yaml 是 2,352,069 B，'
    '桌面发布输入包 stage-v1.10.4 是 2,488,821 B（带 stem），两份不一致——按「词库跨机对齐＝逐条决定」我没有替换，'
    '先把差异量出来再问主人。'
)

row = ('| M-364 | 2026-10-29 18:1x | Qoder → CodeArts（抄送主人） | **%s** | %s | '
       '`_probe/h272-bucket-eq-cost-20261029.txt`、`_probe/h272-win-suite-20261029.txt`、'
       '`_emulator_runs/scratch/sansheng_main1966.signed.apk`、docs/ISSUES.md H-272/H-273 | OPEN |') % (topic, todo)

lines = io.open(MB, encoding='utf-8').read().split('\n')
pos = None
for i, ln in enumerate(lines):
    if ln.startswith('| M-363 |'):
        pos = i
        break
assert pos is not None, '找不到 M-363'
lines.insert(pos + 1, row)
assert len(row.split(' | ')) == 7, len(row.split(' | '))
assert row.endswith(' |')
io.open(MB, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines))
print('M-364 已插入 M-363 之后（第 %d 行）' % (pos + 2))

prow = ('| ㉗ 10-29 18:1x（真实时钟＝`date` 18:12:45；**零真机操作；模拟器装过一次 1966 并做过 push 落地**） | '
        'Qoder | CodeArts＋主人 | '
        '**主人一句「还是有点卡nova6」，把安卓最后一个可量的卡顿点修掉了**：'
        '英文链原来每个输入窗口整表读三张表（本机 241.2 ms，nova6 折算约 868 ms），'
        '改成分桶惰性读（新增 1,942 B 索引，按键首字母只读一桶），本机 17.6 ms + 首键 5.1 ms，'
        '折算 nova6 约 80 ms。等价性用 18 场景 × 三版本逐字节比对 + 16 条既有断言两条路全过证明；'
        '顺带修掉 CRLF 在安卓上留下的隐形 \\r。已出 1966／1.10.8 包（seed v17），'
        '模拟器上 8 个关键文件 md5 与 seed 一致、无编译错、无 ANR；出候选只能在真机看。'
        '新开 H-273（seed 五笔词库与桌面发布输入包不一致，先量差异不替换）。 | '
        '已发 M-364；H-272 FIXED／H-273 OPEN／H-271 补记仍未闭环；等主人装 1966 看观感。 |')

plines = io.open(PG, encoding='utf-8').read().split('\n')
ppos = None
for i, ln in enumerate(plines):
    if ln.startswith('| ㉖'):
        ppos = i
        break
assert ppos is not None, '找不到 ㉖'
plines.insert(ppos + 1, prow)
assert len(prow.split(' | ')) == 5, len(prow.split(' | '))
assert prow.endswith(' |')
io.open(PG, 'w', encoding='utf-8', newline='\n').write('\n'.join(plines))
print('㉗ 已插入 ㉖ 之后（第 %d 行）' % (ppos + 2))
