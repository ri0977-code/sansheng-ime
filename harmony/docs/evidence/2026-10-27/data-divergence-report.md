# 词库三端差异清单 (H-080/H-111)

> 整理：(CodeArts) 2026-10-27，port_rime_data.py --check + manifest.diverged

## 概况
- 总文件：19，分叉：9，缺失：0
- 三端根：W=F:/workbuddywork/三生输入法/rime, D=D:/Program Files/Rime, A=%APPDATA%/Rime, Android=F:/dshdesktopwork/sansheng-ime-android/rime

## 9个分叉文件

| # | 文件 | 选中源 | 选中字节 | D端字节 | 差异 |
|---|---|---|---|---|---|
| 1 | wubi_pinyin.schema.yaml | W-config | 5,029 | 8,867 | D多3.8KB（含wubi86_jidian/cn_pinyin_jidian_wp导入） |
| 2 | wubi_pinyin.custom.yaml | D | 5,862 | 5,862 | W-config=5,472, W=3,168 |
| 3 | wubi86.dict.yaml | W | 2,289,631 | 2,352,069 | D大62KB；安卓=2,488,821（大199KB） |
| 4 | cn_pinyin_wp.dict.yaml | W | 1,450,889 | 1,516,010 | D大65KB |
| 5 | zh2en_pinyin_wp.dict.yaml | W | 2,346,140 | 2,227,191 | D小119KB |
| 6 | zh2en_wubi_wp.dict.yaml | W | 2,046,267 | 1,933,964 | D小112KB |
| 7 | en2zh_v2_wp.dict.yaml | W | 2,234,473 | 2,340,486 | D大106KB |
| 8 | pinyin_simp.dict.yaml | W | 1,266,106 | 1,331,241 | D大65KB |
| 9 | Custom_phrase.txt | W | 1,657 | 1,636 | D小21B；三端互不相同 |

## 关键差异
1. schema：D端多wubi86_jidian/cn_pinyin_jidian_wp两个导入，鸿蒙缺⇒对应候选不出现
2. 词库：4个D>W，2个W>D；安卓端wubi86比鸿蒙大199KB
3. 安卓端未纳入脚本ROOTS（H-080已知问题）
4. 对齐方向待Qoder/主人定
