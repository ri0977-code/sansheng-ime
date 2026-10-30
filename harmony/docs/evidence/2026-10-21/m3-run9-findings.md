# M3 run9（2026-10-21 15:29，Mate 80 7GL0226408083897）—— H-044 根因锁定

装机：v0.4.0-m3 数据 v7（`m3-sansheng-v7`）+ 5 个 `zzd_*` 诊断方案。
init 3686 ms（17 MB 数据重放，marker 变了所以全量释放）。

## 1. 摘掉 lua_* 齿轮后，wubi_pinyin 全绿

| 用例 | 结果 |
|---|---|
| 拼音混输 `nihao` | PASS 你好 / hello |
| H-042 样本 `nihaoma` | PASS 你好吗（竖屏也出，见 §3） |
| 五笔词码 `wqvb` | PASS 你好 / 您好 / hello / 𠛈 |
| 英→中 `dog` | PASS 狗 / 跟踪 / 尾随 |
| 中→英 `haoma` | INFO 号码 / 好吗 / number / 好嘛（`_wp` 词库走 wubi86 主词典通道，不需要那三个没编译出来的 translator） |
| 简体基线 `zhongguo` | PASS 中国 / China |
| 繁体 `zh_trad` on | PASS 中国 → **中國**（OpenCC s2t 在真机生效，H-041 ① 收口） |
| 九宫格 T9 `64426` | PASS 你好[ni hao] / 你敢[ni gan] / 米高[mi gao]（H-028 ① 引擎侧收口） |
| 反查 `` `ni `` | PASS 你 / 拟 / 尼 / 呢 / 泥（comment 版要等真 Lua 滤镜） |
| `ascii_mode` + `x` | FAIL commit 空、候选 0 —— 桥里的键分发问题，不是数据问题 |

## 2. 诊断方案二分结论

| 方案 | 配置差异 | wqvb 候选 |
|---|---|---|
| zzd_min | 只有 table_translator(wubi86) | **4 条** ✅ |
| zzd_rvl | + reverse_lookup_translator + extra_tags | **4 条** ✅（还多出 `你好[nihao wqvb]`） |
| zzd_ud | + enable_user_dict/tabledb/encoder | **4 条** ✅ |
| zzd_lua | + 1 个 lua_translator 桩 + 1 个 lua_filter 桩 | **0 条** ❌ |
| zzd_full | 完整复刻（13 级滤镜全是桩） | **0 条** ❌ |
| wubi_pinyin（v7，摘掉全部 lua_*） | = full − lua | **4 条** ✅ |

→ **掐断候选链的就是 Lua 齿轮本身（桩也不行）**，与词库、prism、反查、用户词典、
simplifier/opencc、custom 补丁都无关。
wubi86 的三个 .bin 与桌面端逐字节同尺寸：
prism 2,826,556 / table 9,101,972（桌面 9,101,956，差 16 B 是 build 时间戳） / reverse 3,695,604。

## 3. 下一轮（run10）要问的最后一个问题

zzd_lua 里同时有一个 filter 和一个 translator，还没分开。run10 用 4 个单齿轮方案二分：
- 只有 filter 桩（恒等 `return input`）→ 是否归零
- filter 桩把 `type(input)` 打到 stderr → 看清 1.16.1 的 rime-lua 到底传进来什么类型
- filter 桩返回**重建的普通 Lua table** → 验证「必须返回真 table」假设
- 只有 translator 桩（`return nil`）；再加一个返回 `{{"诊断词","zz"}}` 的 translator → 验证 Lua 翻译器能否注入候选

结论决定 M4 移植真滤镜时是「直接用桌面端 Lua 源码」还是「按鸿蒙这版 rime-lua 的契约改适配器」。
