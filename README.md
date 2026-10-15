# 五笔词通 · Rime 编码反查滤镜（codeLookup_Filter）

为 [Rime](https://rime.im/) 五笔拼音（`wubi_pinyin`）输入法增加**候选词编码反查**与**多音字注释**的独立 Lua 滤镜。

> 反查出来的是**真正能打出的五笔词组码**（遵循五笔标准组词取码规则），不是逐字裸拼的假码。

## 功能

- **五笔编码反查**：每个中文候选下方显示其五笔码。
  - 单字：显示最短码（如 `电 [jn]`）。
  - 多字词：**整词优先查词库**（词库本就有正确词组码，如 `春夏秋冬 [ddtt]`、`你好 [wqvb]`）；查不到时按五笔标准组词规则现算：
    - 二字词：各取前两码（`你好` = 你`wq` + 好`vb` = `wqvb`）
    - 三字词：前两字各取首码 + 第三字前两码
    - 四字词：各取首码（`海洋生物` = 海`i` 洋`i` 生`t` 物`t` = `iitt`）
    - ≥五字词：前三字首码 + 末字首码（`中华人民共和国` = `kwwl`）
- **拼音注释**：显示候选读音，多音字收集全部读音（如 `长 [ta] zhang/chang`）。
- **开关可控**：复用 Rime 的 `phraseComment` 选项（默认开），关闭后本滤镜不输出任何注释。
- **安全无副作用**：只改候选 `comment`，不改候选顺序与身份 → **词频调整 / 自造词完全不受影响**。

## 设计原则（踩坑后确立）

本滤镜由 dsh 起头、doubao 与 WorkBuddy 接手完善。关键教训：

1. **独立文件**，绝不整文件替换 `inputShow_Filter.lua`，避免「修一个坏一个」。
2. **全程 `pcall` 保护**，任何候选处理出错都不阻断 `yield`，绝不导致候选中断。
3. `comment` 一律用 `cand:get_genuine().comment` 赋值，且先 `or ''` 防 `nil` 崩溃（旧版在 `comment` 为 `nil` 时崩 coroutine，导致调频/自造词全废）。
4. 索引**一次性构建**（`M._built` 守卫），不随每次按键重建。

## 安装

1. 把 `codeLookup_Filter.lua` 复制到 Rime 用户/程序目录的 `lua/` 下（与 `wubi86.dict.yaml` 同级）。
2. 在 `rime.lua` 末尾增加一行：
   ```lua
   codeLookup_Filter = require("codeLookup_Filter")
   ```
3. 在 `wubi_pinyin.custom.yaml` 的 `engine/filters` 中，`pinyinAdding_Filter` 之后插入：
   ```yaml
   filters:
     - lua_filter@pinyinAdding_Filter
     - lua_filter@codeLookup_Filter   # ← 新增，放在 pinyinAdding 之后
     - lua_filter@laneChangeAndSpace_Filter
     ...
   ```
4. 部署所需字典：`wubi86.dict.yaml`（主五笔词库）、`cn_pinyin_wp.dict.yaml`（拼音，含多音字）；
   可选：`wnwb_wubi_custom_wp.dict.yaml`、`wnwb_wubi_user_wp.dict.yaml`、`user.txt`（自造词兜底反查）。
5. **Rime 托盘 → 重新部署**，使新滤镜与 schema 生效。

> 反查依赖上述字典文件与 `wubi_pinyin` schema，本仓库**不打包**字典（它们属于对应 Rime 方案）。

## 配置

- 开关注释：`phraseComment` 选项。可在 `wubi_pinyin.schema.yaml` 的 `switches` 中暴露该选项，或用 `Ctrl+\`` 方案菜单切换；默认开启。

## 版本

- **v2.0**（2026-10-15）：修复「多字词编码为逐字裸拼」的遗留坏问题（dsh 旧逻辑），改为「整词查库 + 五笔标准组词规则现算」，反查码可真实打出；新增 `M._built` 一次性构建守卫。
- **v1.0**（2026-10-15）：首版实现编码反查 + 多音字注释，独立滤镜、pcall 保护、不改候选顺序。

## 兼容性

- Rime / Weasel（Windows）实测；依赖 `wubi_pinyin` schema 及其字典。
- 需要 Rime 的 Lua 扩展（ librime-lua ）支持。

## License

MIT —— 见 [LICENSE](./LICENSE)。
