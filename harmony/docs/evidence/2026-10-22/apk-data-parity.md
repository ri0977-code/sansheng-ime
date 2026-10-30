# 安卓发布 APK rime-data 与鸿蒙随包数据逐文件对账（2026-10-22）

- 只读比对；摘要统一用 **md5 前 16 位**（此前散在记录里的 `6d089695…`、`ea929515…` 是 sha256 前 16 位，两套值不能互比）。
- 安卓基准包：`2-Rime插件-0.1.3-arm64.apk`（发布 1.10.1，内含 `assets/usr/share/rime-data/`）。
- 鸿蒙随包：`entry/src/main/resources/rawfile/rime/`（工作区未提交状态，CodeArts 12:10 记录在案）。

## 1) 与安卓 APK 字节相同：1 个
  - `symbols.yaml` 28,473 B

## 2) 同名但内容不同：1 个
| 文件 | 安卓 B / md5 | 鸿蒙 B / md5 |
|---|---|---|
| `default.yaml` | 1,301 / `0b153bbcb765f0e6` | 3,957 / `91de9d650f6ff691` |

## 3) 只在鸿蒙随包里出现：65 个
  - `Custom_phrase.txt` 1,657 B `a11524cf8fe85669`
  - `README.md` 4,848 B `fac47b031c42cd27`
  - `cn_pinyin_wp.dict.yaml` 1,450,889 B `bd7b3aecefcff3ce`
  - `en2zh_v2.dict.yaml` 475,430 B `96284f0e69a4421b`
  - `en2zh_v2_wp.dict.yaml` 2,234,473 B `9463ef0767f01ee5`
  - `lua-files.txt` 1,092 B `cd59388ca5f67192`
  - `lua/GUID.lua` 1,468 B `0131a155b3737960`
  - `lua/Upper_Filter.lua` 1,875 B `a0f58a5eb0baa3bf`
  - `lua/abbrGloss_Filter.lua` 7,495 B `f10f12b38cf0c7b4`
  - `lua/abbr_en.txt` 17,146 B `2500936430cdd596`
  - `lua/abbr_num.txt` 3,636 B `6adbdfb79c3c4805`
  - `lua/codeLookup_Filter.lua` 21,408 B `d098a3fea97542ae`
  - `lua/dateTimeModule.lua` 16,151 B `cbf4dda9a7e33dff`
  - `lua/dateTime_filter.lua` 20,353 B `ed9e108e5ef0d0c1`
  - `lua/dic_4w.lua` 1,812 B `91139a71572ed14b`
  - `lua/dic_4w_Filter.lua` 2,842 B `007142ba814066f4`
  - `lua/dic_4w_cn.txt` 888,075 B `76bde539be5882a0`
  - `lua/dic_4w_en.txt` 2,022,029 B `b4d234a21adb9108`
  - `lua/dynamicPhrase_Filter.lua` 6,522 B `ba83389cbf475f48`
  - `lua/eventsList.txt` 12,440 B `f8fcf39c8486f552`
  - `lua/eventsListModule.lua` 31,592 B `e4290148fff42367`
  - `lua/help.lua` 1,868 B `af5aa74c82a3b287`
  - `lua/inputShow.lua` 2,919 B `f762a3e45e9e1271`
  - `lua/inputShow_Filter.lua` 7,813 B `0b493515f3035570`
  - `lua/laneChangeAndSpace_Filter.lua` 3,946 B `e0a92e251a5d5782`
  - `lua/lunarModule.lua` 18,127 B `708728567fc195db`
  - `lua/lunarjieQiModule.lua` 44,399 B `1f28f48d0776cc06`
  - `lua/phoneComment_Filter.lua` 2,397 B `3cd9b776895346b3`
  - `lua/phraseComment chemicalElement.txt` 35,279 B `f2dba39a96f9b795`
  - `lua/phraseComment commonPhrase.txt` 20,537 B `1b30b7885e89f278`
  - `lua/phraseComment personal.txt` 98 B `66d306c3e263c98d`
  - `lua/phraseComment_Filter.lua` 1,529 B `1e7d1650b4b2a34a`
  - `lua/phraseComment_Module.lua` 2,599 B `829ada8458255e12`
  - `lua/phraseExt commonPhrase.txt` 7,277 B `6a40fa05093a284b`
  - `lua/phraseExt esAppEmoji.txt` 12,802 B `f6403751bee54a5d`
  - `lua/phraseExt esUnicode.txt` 16,276 B `7d55f13a3578cd3c`
  - `lua/phraseExt personal.txt` 121 B `dbfa85ac6b9f67c3`
  - `lua/phraseExt_Filter.lua` 5,171 B `e9ad1826a4ca2a59`
  - `lua/phraseExt_Module.lua` 3,446 B `101d5881c5a4f193`
  - `lua/phraseReplace.txt` 949 B `75d6424190879f80`
  - `lua/phraseReplaceModule.lua` 2,402 B `a60a87a482c984b6`
  - `lua/phraseReplace_Filter.lua` 2,144 B `4b3af3d009ad2125`
  - `lua/pinyinAdding.txt` 4,531 B `9eee4745e1799dcc`
  - `lua/pinyinAddingModule.lua` 3,462 B `b01e6953c62e0d09`
  - `lua/pinyinAdding_Filter.lua` 2,096 B `d231f12475728bb4`
  - `lua/rawEcho_translator.lua` 5,395 B `c0cf6412e2df5e3a`
  - `lua/runLog.lua` 2,939 B `a7eb73294b4577a8`
  - `lua/socket.lua` 1,680 B `b2608e26ad1b815b`
  - `lua/sysInfo.lua` 4,686 B `0e071110fe09d1a1`
  - `lua/utf8String.lua` 8,121 B `18bfe003cbb3615d`
  - `opencc/STCharacters.ocd2` 45,310 B `cb009d723fb69938`
  - `opencc/STPhrases.ocd2` 925,143 B `f97081a674cd8e5c`
  - `opencc/s2t.json` 428 B `ab8511f45523464c`
  - `pinyin_simp.dict.yaml` 1,266,106 B `2ca4eeef8cf1455a`
  - `pinyin_simp.schema.yaml` 1,840 B `b0d7948559334d74`
  - `rime.lua` 6,853 B `69a26747aa20cbc0`
  - `sansheng_t9.schema.yaml` 4,023 B `c0d57f1743956858`
  - `symbols.custom.yaml` 11,696 B `b1e28d38ede993a7`
  - `wubi86.dict.yaml` 2,289,631 B `449bbe2adbd952b3`
  - `wubi_pinyin.custom.yaml` 6,253 B `307af610cf5b090e`
  - `wubi_pinyin.schema.yaml` 4,669 B `a2a5cd26ba852190`
  - `zh2en_pinyin.dict.yaml` 2,253,148 B `fd20cc6a591e2226`
  - `zh2en_pinyin_wp.dict.yaml` 2,346,140 B `12dcdcec4d5ff0b7`
  - `zh2en_wubi.dict.yaml` 1,907,702 B `b72c3fca1a7ba249`
  - `zh2en_wubi_wp.dict.yaml` 2,046,267 B `be8f6a98a689163a`

## 4) APK rime-data 全清单（14 个）
  - `default.yaml` 1,301 B `0b153bbcb765f0e6`
  - `essay.txt` 5,887,417 B `876d335c27f73bd3`
  - `key_bindings.yaml` 3,117 B `1ce1d27f274c0d3f`
  - `luna_pinyin.dict.yaml` 889,896 B `8297ef9a67024e80`
  - `luna_pinyin.schema.yaml` 2,809 B `6d7ee0de0befd616`
  - `luna_pinyin_fluency.schema.yaml` 527 B `877d33bbec605fc2`
  - `luna_pinyin_simp.schema.yaml` 420 B `51662ea387a4f1e7`
  - `luna_pinyin_tw.schema.yaml` 423 B `ececa0c5d48bbe3c`
  - `luna_quanpin.schema.yaml` 398 B `9d0b7098ee5e8c05`
  - `pinyin.yaml` 4,895 B `1074801aefdce2ca`
  - `punctuation.yaml` 2,107 B `774a929c38a4ee10`
  - `stroke.dict.yaml` 3,396,347 B `b912c6b14a7a16c2`
  - `stroke.schema.yaml` 3,056 B `194e20d22dca34a8`
  - `symbols.yaml` 28,473 B `b4fe9b1fb5419b6c`
