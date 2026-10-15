# 五笔词通（Rime 五笔·拼音 增强）

在 Rime「五笔·拼音」输入法里，**给每个中文候选自动加注五笔编码 + 拼音（含多音字全读音）** 的独立 Lua 滤镜，并附带一个补充词典让常用拼音多字词也能按正确五笔组词码单码打出。

> 设计原则：独立滤镜，**绝不改动** `inputShow_Filter.lua`；全程 `pcall` 保护；只改注释、不动候选顺序与身份 → **调频 / 自造词不受影响**。

---

## 功能一览

- ✅ 中文候选反查五笔编码（单字最短码 / 整词实码 / 非词典词按标准组词规则现算）
- ✅ 多音字注释（全部读音，如 长→`zhang/chang`）
- ✅ 候选词拼音注释
- ✅ 常用拼音多字词可单码打出（如 海洋生物→`iitt`）
- ✅ `phraseComment` 开关：托盘右键「commentOn」可一键关闭注释
- ✅ 健壮：独立文件、pcall 保护、`get_genuine().comment` 防 nil 崩溃、索引一次性构建

完整能力清单见 [功能清单.md](功能清单.md)。

---

## 文件说明

| 文件 | 作用 |
|------|------|
| `codeLookup_Filter.lua` | **核心滤镜**，放到 Rime 的 `lua/` 目录 |
| `wubi_citong.dict.yaml` | **补充词典**，放到 Rime 主目录，收录拼音多字词的正确五笔组词码 |
| `gen_supp_dict.py` | 补充词典的生成脚本（可重跑，见下） |
| `功能清单.md` | 能力清单（打勾表） |
| `LICENSE` | MIT |

---

## 安装 / 部署

1. 关闭 Rime 相关进程前**先备份**你的 Rime 目录（通常是 `D:\Program Files\Rime` 或 `%APPDATA%\Rime`）。
2. 复制文件：
   - `codeLookup_Filter.lua` → Rime 主目录的 `lua/` 子目录
   - `wubi_citong.dict.yaml` → Rime 主目录
3. 在 `rime.lua` 末尾追加一行（若已存在可跳过）：
   ```lua
   codeLookup_Filter = require("codeLookup_Filter")
   ```
4. 在 `wubi_pinyin.custom.yaml` 的 `engine/filters:` 中，`pinyinAdding_Filter` 之后插入：
   ```yaml
   - lua_filter@codeLookup_Filter
   ```
5. 在 `wubi86.dict.yaml` 的 `import_tables:` 末尾追加：
   ```yaml
   - wubi_citong
   ```
6. **重新部署**：Rime 托盘图标 →【重新部署】（会重编译方案并加载新 Lua 与词典）。

> 注：自动部署（`WeaselDeployer /deploy` 等）在本机实践中不可靠，请以托盘「重新部署」为准。

---

## 重生成补充词典（可选）

```bash
python gen_supp_dict.py
```

脚本从 `cn_pinyin_wp.dict.yaml` 中挑出「`wubi86` 未收录的多字词」，按标准五笔组词规则算出正确编码，写入 `wubi_citong.dict.yaml`（已做与 `wubi86` 的码碰撞检查，避免制造歧义；种子词 `海洋生物` 显式收录）。改完需重新部署生效。

---

## 回滚

- 删除 / 注释 `wubi_pinyin.custom.yaml` 里的 `- lua_filter@codeLookup_Filter` 与 `rime.lua` 里的 `require` 行，并移除 `wubi86.dict.yaml` 末尾的 `- wubi_citong` 一行，重新部署即可。原始文件均有备份。

---

## 版本历史

- **v2.1**（2026-10-15）：修复 dsh 遗留的「多字词五笔编码裸拼全码」坏逻辑（海洋生物 曾被拼成 `itxiutgtr` 打不出），改为标准组词规则 + 补充词典，使常用多字词可单码打出。
- **v2.0**（2026-10-15）：初版独立滤镜，实现编码反查 + 多音字注释，全程 pcall、不动原文件。

---

## 声明

本项目为输入法增强组件，仅做候选注释与词典补充，不修改任何原有候选逻辑。使用风险由使用者自担；部署前请备份 Rime 目录。
