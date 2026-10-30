# -*- coding: utf-8 -*-
"""Qoder 2026-10-29：给 ISSUES.md 补 H-272（英文链分桶惰性读，代码注释已引用）+ H-273（seed 五笔词库与桌面发布输入包不一致）。

规矩照旧：先建行再让别处引用（H-185/H-222 的教训）；7 列，内容里不许出现半角竖线。
"""
import io

P = r'F:\qoderwork\sansheng-ime-harmony\docs\ISSUES.md'
src = io.open(P, encoding='utf-8').read()
lines = src.split('\n')

h272 = (
    '| H-272 | FIXED | P1 | Q | '
    '**安卓英文链每个输入窗口把 gloss/trans/codes 三张表整表读进 Lua**（librime 每个输入窗口一个全新 Lua VM，滤镜一加载就全读）'
    '⇒ 本机 load 中位 241.2 ms／窗口，nova6 的 CPU 当天实测比本机慢 3.6 倍 ⇒ 折算约 868 ms，'
    '正对上主人连说的两句「有点卡」「还是有点卡 nova6」。改法不复制任何词表：新增 en_word_ltr_idx.tsv（1,942 B，只记字节偏移），'
    '按键首字母 seek+read 只读那一桶（最大 158 KB，整表 3.5 MB）；索引缺／坏／键首字符非字母一律退回整表读＝旧行为。 | '
    '`_probe/h272-bucket-eq-cost-20261029.txt`：18 个场景 × 三版本（旧整表／新桶读／新代码无索引退回整表）输出「文本{注释}」逐字节一致；'
    '本机 load 中位 241.2 → 17.6 ms，首键 5.1 ms（折算 nova6 868 → 约 80 ms）；三条兜底（坏索引／只有 a 桶／缺反查表）也逐字节一致。'
    '`_probe/h272-win-suite-20261029.txt`：主人点头的 16 条断言，带索引与不带索引两条路都 PASS。'
    '顺带修：三张表是 CRLF，Linux/安卓上每个值末尾挂着看不见的 \\r（Windows 文本模式自动去掉，所以以前没暴露），两条读法统一 chomp。'
    '模拟器 1966 装机：8 个关键文件 md5 与 seed 逐字节一致，librime 加载 rime 插件无 failed to compile，无 ANR。 | '
    '待真机观感：nova6 装 1966（1.10.8）后打几个字确认不卡了。'
    '模拟器上无法注入自绘键盘（tap 进不了 IME 窗口、keyevent 被 EditText 直接吃掉），'
    '「出候选」这一环只能在真机看，与历史一致。'
)

h273 = (
    '| H-273 | OPEN | P2 | Q | '
    '**安卓 seed 里的五笔主词库 wubi86.dict.yaml 与桌面发布输入包不是同一份**：'
    'build-android-qoder.py 的权威源 SRC（packaging/release/config）是 2,352,069 B（10-26 21:27），'
    '而桌面发布输入包 stage-v1.10.4 里是 2,488,821 B（带 stem 的那份，10-22 的 1916 包验过 md5 b9bca39020d10029aa4b185342455526）。'
    '这轮 1966 包用的是 2,352,069 B 那份 ⇒ 安卓五笔词条与桌面/鸿蒙可能不同步，'
    '且 #A13 的 kanmengou=看门狗 这类靠带 stem 表修好的码，在安卓上可能又缺。 | '
    '`seed/sansheng_seed.zip` 内 data/rime/wubi86.dict.yaml 2,352,069 B；'
    'SRC 同名文件同大小同时间；`_probe/nova6-1916-upgrade.txt` 记的 1916 包是 2,488,821 B；'
    '`F:\\workbuddywork\\三生输入法\\_probe\\build-inputs\\stage-v1.10.4\\...\\wubi86.dict.yaml` 2,488,821 B。 | '
    '按「词库跨机对齐＝逐条决定」的口径，先不动：把两份 wubi86 的差异（词条数、kanmengou 之类样本）量出来写进台账，'
    '再问主人要不要让安卓跟着桌面发布输入包走。不自行整包替换。'
)

idx271 = None
for i, ln in enumerate(lines):
    if ln.startswith('| H-271 |'):
        idx271 = i
        break
assert idx271 is not None, '找不到 H-271 行'

# H-271 的下一步补一句：本轮已手工把 1966 包 bump 到 1.10.8（脚本强制化仍未做）
cell = lines[idx271]
assert cell.endswith(' |'), cell[-30:]
add = ('　2026-10-29 17:5x Qoder 补记：本轮出 1966 包时已手工把 manifest 与 apktool.yml 一起 bump 到 '
       'versionCode 1966 / versionName 1.10.8（原来 pkg_main 里是 1949 / 1.10.5，与上一版已发布的 1965 / 1.10.7 都对不上），'
       '但「脚本强制递增 + 自检比对上一版已发布包」还没做，所以本条继续 OPEN。')
lines[idx271] = cell[:-2] + add + ' |'

lines[idx271 + 1:idx271 + 1] = [h272, h273]

for name, row in (('H-272', h272), ('H-273', h273)):
    assert len(row.split(' | ')) == 7, (name, len(row.split(' | ')))
    body = row.strip()[1:-1]
    assert '|' not in body.replace(' | ', ''), name

out = '\n'.join(lines)
io.open(P, 'w', encoding='utf-8', newline='\n').write(out)
print('已写入：H-272 / H-273，H-271 补记。总行数 %d' % len(lines))
