# 鸿蒙随包 rime 数据逐文件来源对账（2026-10-24）

方法：对 `rawfile/rime/**` 每个文件算 md5（前 16 位），与四组参照做**字节级**命中：
`F:/dshdesktopwork/sansheng-ime-android/rime`（主人安卓产品自己的数据根，76 文件）、
`D:/IDM/rime-wubi-master`（LGPL-3.0）、`D:/IDM/rime-wubi86-jidian-master`（Apache-2.0）、
`D:/IDM/oh-my-rime-main`（仓库 LICENSE = GPL-3.0）、`D:/IDM/dyyRime-master`（仓库**无 LICENSE**）；
另按**文件名**与 dyyRime 对照，区分「原样复制」与「同名但已改写」。

| 分类 | 个数 | 说明 |
|---|---|---|
| 与安卓数据根字节相同 | 17 | 主人已在安卓 1.10.1 分发同一份文件，来源责任与安卓一致 |
| 与 dyyRime 同名字节相同 | 29 | ⚠ 上游无 LICENSE（保留所有权利）|
| dyyRime 有同名但内容已改 | 13 | 衍生作品，主体版权仍归上游 |
| 四组参照与 dyyRime 都没有 | 16 | 本项目自写，或来自未在本机留档的上游 |
| 合计 | 65 | |

## 1) 全量对账表

| 文件 | 字节 | md5 | 命中 |
|---|---|---|---|
| `Custom_phrase.txt` | 1,657 | `a11524cf8fe85669` | dyy同名已改(dyyRime-master/Custom_phrase.txt，行级相似 46%) |
| `README.md` | 7,433 | `7293c1f84445f1a9` | dyy同名已改(dyyRime-master/README.md，行级相似 6%) |
| `cn_pinyin_wp.dict.yaml` | 1,450,889 | `bd7b3aecefcff3ce` | — |
| `default.yaml` | 4,830 | `cb578f49b8362f3f` | — |
| `en2zh_v2.dict.yaml` | 475,430 | `96284f0e69a4421b` | 安卓:en2zh_v2.dict.yaml |
| `en2zh_v2_wp.dict.yaml` | 2,234,473 | `9463ef0767f01ee5` | — |
| `lua-files.txt` | 1,092 | `cd59388ca5f67192` | — |
| `pinyin_simp.dict.yaml` | 1,266,106 | `2ca4eeef8cf1455a` | — |
| `pinyin_simp.schema.yaml` | 1,840 | `b0d7948559334d74` | 安卓:pinyin_simp.schema.yaml；jidian:pinyin_simp.schema.yaml |
| `rime.lua` | 6,853 | `ba1df220e405a4ba` | dyy同名已改(dyyRime-master/rime.lua，行级相似 0%) |
| `sansheng_t9.schema.yaml` | 4,023 | `c0d57f1743956858` | — |
| `wubi86.dict.yaml` | 2,289,631 | `449bbe2adbd952b3` | — |
| `wubi_pinyin.custom.yaml` | 5,910 | `3274e000423aecb3` | dyy同名已改(dyyRime-master/wubi_pinyin.custom.yaml，行级相似 42%) |
| `wubi_pinyin.schema.yaml` | 4,506 | `0c9d783879372bf1` | — |
| `zh2en_pinyin.dict.yaml` | 2,253,148 | `fd20cc6a591e2226` | — |
| `zh2en_pinyin_wp.dict.yaml` | 2,346,140 | `12dcdcec4d5ff0b7` | — |
| `zh2en_wubi.dict.yaml` | 1,907,702 | `b72c3fca1a7ba249` | — |
| `zh2en_wubi_wp.dict.yaml` | 2,046,267 | `be8f6a98a689163a` | — |
| `lua/GUID.lua` | 1,468 | `0131a155b3737960` | dyy原样(仅行尾差异):dyyRime-master/lua/GUID.lua |
| `lua/Upper_Filter.lua` | 1,875 | `a0f58a5eb0baa3bf` | dyy同名已改(dyyRime-master/lua/Upper_Filter.lua，行级相似 97%) |
| `lua/abbrGloss_Filter.lua` | 7,495 | `f10f12b38cf0c7b4` | 安卓:lua/abbrGloss_Filter.lua |
| `lua/abbr_en.txt` | 17,146 | `2500936430cdd596` | 安卓:lua/abbr_en.txt |
| `lua/abbr_num.txt` | 3,636 | `6adbdfb79c3c4805` | 安卓:lua/abbr_num.txt |
| `lua/codeLookup_Filter.lua` | 21,408 | `d098a3fea97542ae` | — |
| `lua/dateTimeModule.lua` | 16,151 | `cbf4dda9a7e33dff` | dyy原样(仅行尾差异):dyyRime-master/lua/dateTimeModule.lua |
| `lua/dateTime_filter.lua` | 20,353 | `ed9e108e5ef0d0c1` | dyy原样(仅行尾差异):dyyRime-master/lua/dateTime_filter.lua |
| `lua/dic_4w.lua` | 1,812 | `91139a71572ed14b` | dyy原样(仅行尾差异):dyyRime-master/lua/dic_4w.lua |
| `lua/dic_4w_Filter.lua` | 2,842 | `007142ba814066f4` | dyy同名已改(dyyRime-master/lua/dic_4w_Filter.lua，行级相似 79%) |
| `lua/dic_4w_cn.txt` | 888,075 | `76bde539be5882a0` | dyy原样:dyyRime-master/lua/dic_4w_cn.txt |
| `lua/dic_4w_en.txt` | 2,022,029 | `b4d234a21adb9108` | 安卓:lua/dic_4w_en.txt；dyy原样:dyyRime-master/lua/dic_4w_en.txt |
| `lua/dynamicPhrase_Filter.lua` | 6,522 | `ba83389cbf475f48` | dyy原样(仅行尾差异):dyyRime-master/lua/dynamicPhrase_Filter.lua |
| `lua/eventsList.txt` | 12,440 | `f8fcf39c8486f552` | 安卓:lua/eventsList.txt；dyy原样:dyyRime-master/lua/eventsList.txt |
| `lua/eventsListModule.lua` | 31,592 | `e4290148fff42367` | dyy原样(仅行尾差异):dyyRime-master/lua/eventsListModule.lua |
| `lua/help.lua` | 1,868 | `af5aa74c82a3b287` | dyy原样(仅行尾差异):dyyRime-master/lua/help.lua |
| `lua/inputShow.lua` | 2,919 | `f762a3e45e9e1271` | dyy同名已改(dyyRime-master/lua/inputShow.lua，行级相似 98%) |
| `lua/inputShow_Filter.lua` | 7,813 | `0b493515f3035570` | dyy同名已改(dyyRime-master/lua/inputShow_Filter.lua，行级相似 95%) |
| `lua/laneChangeAndSpace_Filter.lua` | 3,946 | `e0a92e251a5d5782` | dyy原样(仅行尾差异):dyyRime-master/lua/laneChangeAndSpace_Filter.lua |
| `lua/lunarModule.lua` | 18,127 | `708728567fc195db` | dyy原样(仅行尾差异):dyyRime-master/lua/lunarModule.lua |
| `lua/lunarjieQiModule.lua` | 44,399 | `1f28f48d0776cc06` | dyy原样(仅行尾差异):dyyRime-master/lua/lunarjieQiModule.lua |
| `lua/phoneComment_Filter.lua` | 2,397 | `3cd9b776895346b3` | 安卓:lua/phoneComment_Filter.lua |
| `lua/phraseComment chemicalElement.txt` | 35,279 | `f2dba39a96f9b795` | 安卓:lua/phraseComment chemicalElement.txt；dyy原样:dyyRime-master/lua/phraseComment chemicalElement.txt |
| `lua/phraseComment commonPhrase.txt` | 20,537 | `1b30b7885e89f278` | 安卓:lua/phraseComment commonPhrase.txt；dyy原样:dyyRime-master/lua/phraseComment commonPhrase.txt |
| `lua/phraseComment personal.txt` | 98 | `66d306c3e263c98d` | dyy同名已改(dyyRime-master/lua/phraseComment personal.txt，行级相似 10%) |
| `lua/phraseComment_Filter.lua` | 1,529 | `1e7d1650b4b2a34a` | dyy原样(仅行尾差异):dyyRime-master/lua/phraseComment_Filter.lua |
| `lua/phraseComment_Module.lua` | 2,599 | `829ada8458255e12` | dyy原样(仅行尾差异):dyyRime-master/lua/phraseComment_Module.lua |
| `lua/phraseExt commonPhrase.txt` | 7,277 | `6a40fa05093a284b` | 安卓:lua/phraseExt commonPhrase.txt；dyy原样:dyyRime-master/lua/phraseExt commonPhrase.txt |
| `lua/phraseExt esAppEmoji.txt` | 12,802 | `f6403751bee54a5d` | 安卓:lua/phraseExt esAppEmoji.txt；dyy原样:dyyRime-master/lua/phraseExt esAppEmoji.txt |
| `lua/phraseExt esUnicode.txt` | 16,276 | `7d55f13a3578cd3c` | 安卓:lua/phraseExt esUnicode.txt；dyy原样:dyyRime-master/lua/phraseExt esUnicode.txt |
| `lua/phraseExt personal.txt` | 121 | `dbfa85ac6b9f67c3` | 安卓:lua/phraseExt personal.txt；dyy同名已改(dyyRime-master/lua/phraseExt personal.txt，行级相似 11%) |
| `lua/phraseExt_Filter.lua` | 5,171 | `e9ad1826a4ca2a59` | dyy原样(仅行尾差异):dyyRime-master/lua/phraseExt_Filter.lua |
| `lua/phraseExt_Module.lua` | 3,446 | `101d5881c5a4f193` | dyy原样(仅行尾差异):dyyRime-master/lua/phraseExt_Module.lua |
| `lua/phraseReplace.txt` | 949 | `75d6424190879f80` | 安卓:lua/phraseReplace.txt；dyy原样:dyyRime-master/lua/phraseReplace.txt |
| `lua/phraseReplaceModule.lua` | 2,402 | `a60a87a482c984b6` | dyy原样(仅行尾差异):dyyRime-master/lua/phraseReplaceModule.lua |
| `lua/phraseReplace_Filter.lua` | 2,144 | `4b3af3d009ad2125` | dyy原样(仅行尾差异):dyyRime-master/lua/phraseReplace_Filter.lua |
| `lua/pinyinAdding.txt` | 4,531 | `9eee4745e1799dcc` | 安卓:lua/pinyinAdding.txt；dyy原样:dyyRime-master/lua/pinyinAdding.txt |
| `lua/pinyinAddingModule.lua` | 3,462 | `b01e6953c62e0d09` | dyy原样(仅行尾差异):dyyRime-master/lua/pinyinAddingModule.lua |
| `lua/pinyinAdding_Filter.lua` | 2,096 | `d231f12475728bb4` | dyy原样(仅行尾差异):dyyRime-master/lua/pinyinAdding_Filter.lua |
| `lua/rawEcho_translator.lua` | 5,395 | `c0cf6412e2df5e3a` | 安卓:lua/rawEcho_translator.lua |
| `lua/runLog.lua` | 2,939 | `a7eb73294b4577a8` | dyy同名已改(dyyRime-master/lua/runLog.lua，行级相似 22%) |
| `lua/socket.lua` | 1,680 | `b2608e26ad1b815b` | dyy同名已改(dyyRime-master/lua/socket.lua，行级相似 15%) |
| `lua/sysInfo.lua` | 4,686 | `0e071110fe09d1a1` | dyy同名已改(dyyRime-master/lua/sysInfo.lua，行级相似 38%) |
| `lua/utf8String.lua` | 8,121 | `18bfe003cbb3615d` | dyy原样(仅行尾差异):dyyRime-master/lua/utf8String.lua |
| `opencc/STCharacters.ocd2` | 45,310 | `cb009d723fb69938` | — |
| `opencc/STPhrases.ocd2` | 925,143 | `f97081a674cd8e5c` | — |
| `opencc/s2t.json` | 428 | `ab8511f45523464c` | — |

## 2) 与无授权上游 `happyDom/dyyRime` 的关系清单

（本表口径：字节命中 = 原样复制；同名不同字节 = 改写衍生；其余 = 与 dyy 无关）

| 关系 | 个数 | 合计字节 | 文件 |
|---|---|---|---|
| 原样复制 | 29 | 3,197,403 | `lua/GUID.lua`, `lua/dateTimeModule.lua`, `lua/dateTime_filter.lua`, `lua/dic_4w.lua`, `lua/dic_4w_cn.txt`, `lua/dic_4w_en.txt`, `lua/dynamicPhrase_Filter.lua`, `lua/eventsList.txt`, `lua/eventsListModule.lua`, `lua/help.lua`, `lua/laneChangeAndSpace_Filter.lua`, `lua/lunarModule.lua`, `lua/lunarjieQiModule.lua`, `lua/phraseComment chemicalElement.txt`, `lua/phraseComment commonPhrase.txt`, `lua/phraseComment_Filter.lua`, `lua/phraseComment_Module.lua`, `lua/phraseExt commonPhrase.txt`, `lua/phraseExt esAppEmoji.txt`, `lua/phraseExt esUnicode.txt`, `lua/phraseExt_Filter.lua`, `lua/phraseExt_Module.lua`, `lua/phraseReplace.txt`, `lua/phraseReplaceModule.lua`, `lua/phraseReplace_Filter.lua`, `lua/pinyinAdding.txt`, `lua/pinyinAddingModule.lua`, `lua/pinyinAdding_Filter.lua`, `lua/utf8String.lua` |
| 同名但已改写 | 13 | 46,826 | `Custom_phrase.txt`, `README.md`, `rime.lua`, `wubi_pinyin.custom.yaml`, `lua/Upper_Filter.lua`, `lua/dic_4w_Filter.lua`, `lua/inputShow.lua`, `lua/inputShow_Filter.lua`, `lua/phraseComment personal.txt`, `lua/phraseExt personal.txt`, `lua/runLog.lua`, `lua/socket.lua`, `lua/sysInfo.lua` |
| 无 dyy 同名文件 | 23 | 17,314,435 | `cn_pinyin_wp.dict.yaml`, `default.yaml`, `en2zh_v2.dict.yaml`, `en2zh_v2_wp.dict.yaml`, `lua-files.txt`, `pinyin_simp.dict.yaml`, `pinyin_simp.schema.yaml`, `sansheng_t9.schema.yaml`, `wubi86.dict.yaml`, `wubi_pinyin.schema.yaml`, `zh2en_pinyin.dict.yaml`, `zh2en_pinyin_wp.dict.yaml`, `zh2en_wubi.dict.yaml`, `zh2en_wubi_wp.dict.yaml`, `lua/abbrGloss_Filter.lua`, `lua/abbr_en.txt`, `lua/abbr_num.txt`, `lua/codeLookup_Filter.lua`, `lua/phoneComment_Filter.lua`, `lua/rawEcho_translator.lua`, `opencc/STCharacters.ocd2`, `opencc/STPhrases.ocd2`, `opencc/s2t.json` |


## 3) 关键文件文件头（看署名头是否到位）

### `wubi86.dict.yaml`
```
# Rime dictionary: wubi86
# encoding: utf-8
#
# Changelog
# Gong Chen <chen.sst@gmail.com>
#     - Convert to Rime dictionary format.
# Yu Yuwei <acevery@gmail.com>
#     - Use original level 1 and 2 JianMa.
```

### `symbols.yaml`
```
(不存在)
```

### `symbols.custom.yaml`
```
(不存在)
```

### `pinyin_simp.dict.yaml`
```
# Rime dictionary
# encoding: utf-8
#
# A minimal Pinyin dictionary for simplified Chinese script
#
# Derived from android open source project:
# http://android.git.kernel.org/?p=platform/packages/inputmethods/PinyinIME.git
#
```

### `cn_pinyin_wp.dict.yaml`
```
# Generated by DSH · 2026-10-13
# 中文拼音词条（供拼音混输：与英文同通道同字典竞争）
---
name: cn_pinyin_wp
version: "2026.10.13"
sort: by_weight
...
鼥	ba	0
```

### `lua/abbrGloss_Filter.lua`
```
-- abbrGloss_Filter.lua
-- 三生输入法（sansheng-ime）自研滤镜 · 2026-10-20
-- 作用：中文态打「流行固定英文缩写」的码（cpu / ppt / github / kpi …），
--       在第一条中文候选之后插入该缩写本体，并把中文释义放进 comment。
--       只插候选、只写自己的 comment，不动词库、不动别人插进来的候选、不删任何候选。
-- 数据：同目录 abbr_en.txt（码<TAB>词面<TAB>释义），由 rime-config/dicts/abbr-en-seed.txt 生成。
-- 开关：abbrEn（F4 / Ctrl+Shift 自选），关闭时本滤镜完全透明直通。
-- 铁律自检：候选条数只许多不许少；第 1 位仍是中文原候选；全程 pcall，出错直通不崩 coroutine。
```

### `lua/phoneComment_Filter.lua`
```
-- phoneComment_Filter.lua
-- 安卓版专用，由 build-android-qoder.py 生成（桌面版没有这个文件，也不该有）。
-- 取代桌面链尾的 laneChangeAndSpace_Filter：那个的上限是 150 字符且把 <br> 转成真实换行，
-- 是给电脑宽气泡设计的；手机上会把一个候选撑成 3 行，一屏只剩 4 个候选。
--
-- 为什么截断不会伤到反查：codeLookup_Filter 把反查码【前置】写入 comment，
--   本滤镜从右边截，所以 [vbrq] / 拼音 永远先保住，被砍掉的只是末尾的词典释义。
-- 为什么截断不会伤到互译：打 good 出「善行 / 好的」这些候选本身来自 wubi86 主词库表
```
