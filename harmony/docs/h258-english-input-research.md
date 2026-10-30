# H-258 英文直接输入+联想功能调研报告

> 整理：CodeArts（鸿蒙开发 agent）
> 日期：2026-10-28
> 状态：调研完成，待 Qoder/主人拍板方案后进入实现

## 一、需求描述（主人原话）

打英文单词（如 apple）时候选栏应出现 **apple 本身**（而非只有中文翻译"苹果"），空格可上屏英文，有英文联想功能，候选注释跟五笔和拼音反查码。跨平台需求（Windows/Android/鸿蒙）。

## 二、当前系统英文处理机制（逐项实证）

### 2.1 ascii_mode 开关

- `wubi_pinyin.schema.yaml:16-18`：`ascii_mode` 开关控制中/西文模式（中文=0，西文=1）
- **中文模式下**：英文字母被当作五笔/拼音编码处理，不会直接出现英文候选
- **西文模式下**：字母直接上屏为 ASCII 字符，不走候选流程
- 主人要的是**中文模式下打英文单词时候选栏出现英文本身**——这是当前做不到的

### 2.2 现有英文相关 translator（3 个中英互译）

| translator | 词典 | 条目数 | 格式 | 行为 | initial_quality |
|---|---|---|---|---|---|
| `en2zh_v2` | `en2zh_v2.dict.yaml` | 20,567 | `中文释义\t英文\t权重` | 打英文→候选出**中文释义**（apple→苹果） | -5 |
| `zh2en_wubi` | `zh2en_wubi.dict.yaml` | ~80,000 | `英文\t五笔码\t权重` | 打五笔码→候选出英文翻译 | -5 |
| `zh2en_pinyin` | `zh2en_pinyin.dict.yaml` | 89,747 | `英文\t拼音\t权重` | 打拼音→候选出英文翻译 | -5 |

**关键问题**：打 `apple` 时候选栏只有 `苹果`（中文释义），**没有 `apple` 本身**。想上屏 `apple` 只能敲回车（直接上屏编码），不能敲空格（空格上屏第一候选=中文）。

### 2.3 现有 Lua 滤镜/translator 相关英文处理

| 组件 | 文件 | 行为 |
|---|---|---|
| `abbrGloss_Filter` | `abbrGloss_Filter.lua` | 中文态打缩写码（cpu/ppt/github）→ 在第一条中文候选后插入缩写本体+释义。**最接近主人需求**，但只覆盖少量缩写，不是通用英文单词 |
| `rawEcho_translator` | `rawEcho_translator.lua` | `/5g` `/ri0977` 这类含数字的原文串→候选出原文。只接管 `/` 开头含数字的串 |
| `codeLookup_Filter` | `codeLookup_Filter.lua` | 编码反查+多音字注释。英文输入时（mode='both'）给中文候选追加拼音+五笔码注释。**只处理含 CJK 的候选**（`has_cjk(txt)` 判定），英文候选不经过反查 |
| `dic_4w_Filter` | `dic_4w_Filter.lua` | 中英对照注释。查到释义时追加到候选 comment |

### 2.4 en2zh_v2_wp 词典（已打包但未接入 translator）

- `en2zh_v2_wp.dict.yaml`：106,013 条，2,234,473 B
- 格式与 `en2zh_v2` 相同（`中文释义\t英文\t权重`），但条目更多
- 数据来源：ECDICT (MIT 许可)
- **当前 schema 里没有引用这个词典的 translator**——它被打包进来了但没有生效

### 2.5 enable_completion 状态

- 主 translator (`wubi86`)：`enable_completion: false`（关闭前缀联想，避免挤占候选）
- `en2zh_v2`：`enable_completion: false`
- `pinyin`（custom.yaml 里新增的拼音 translator）：`enable_completion: true`（开启前缀联想）
- **要实现英文联想，新 translator 必须 `enable_completion: true`**

## 三、实现方案

### 方案 A（推荐）：添加 `en_words` table_translator

**核心思路**：创建一个英文单词词典，编码=单词本身，添加 `table_translator@en_words` 到 schema，开启 `enable_completion` 实现联想。

#### 3.1 词典文件 `en_words.dict.yaml`

**格式**：
```yaml
---
name: en_words
version: "2026.10.28"
sort: by_weight
...
apple	apple	100
application	application	80
apply	apply	75
app	app	60
banana	banana	100
...
```

- 第一列（text）：英文单词本身
- 第二列（code）：英文单词本身（编码=词面，打什么出什么）
- 第三列（weight）：词频权重，常用词高权重排前面

**数据来源**（按优先级）：

1. **从 ECDICT 提取**（MIT 许可，已在包内）—— `en2zh_v2_wp.dict.yaml` 有 106,013 条英文单词，可直接提取英文列作为词典数据。这是最快且许可无争议的方案。
2. **SCOWL** (Spell Checker Oriented Word Lists, MIT 许可) —— 按词频分级，可控制词典大小
3. **WordNet** (open license) —— 学术级英文词汇

**推荐**：从 ECDICT 提取，按词频筛选常用词 10,000-20,000 条（覆盖日常英文输入需求），包体增加约 150-300 KB。

#### 3.2 Schema 配置

在 `wubi_pinyin.custom.yaml` 的 `engine/translators/+` 添加：

```yaml
- table_translator@en_words
```

新增 `en_words` translator 配置：

```yaml
en_words:
  dictionary: en_words
  enable_charset_filter: false
  enable_completion: true      # ★ 开启前缀联想：打 app → apple/application/apply
  enable_sentence: false       # 英文不需要整句
  enable_user_dict: false      # 不需要用户词典（英文词不自造）
  enable_encoder: false
  initial_quality: -3          # ★ 排在中文候选之后、中英互译(-5)之前
  comment_format:
    - xform/.+//                # 清掉自动生成的编码注释（码=词面，注释无意义）
```

**`initial_quality` 排序策略**：
- 中文候选（五笔/拼音）：默认 quality 0~580
- 英文单词（en_words）：-3（排在中文之后、中英互译之前）
- 中英互译（en2zh_v2 等）：-5（排在最后）

这样打 `apple` 时候选顺序：`苹果 [中文] → apple [英文] → 苹果 [中英互译释义]`

#### 3.3 空格上屏行为

- Rime 默认行为：空格上屏第一候选
- 当前中文模式下：打 `apple` → 第一候选是中文释义 → 空格上屏中文
- 加入 en_words 后：打 `apple` → 第一候选仍是中文（quality 更高）→ 空格仍上屏中文
- **要让空格上屏英文**：需要把 en_words 的 `initial_quality` 设为 **正值**（如 1），让英文排在中文之前
- **但这样会破坏中文输入体验**：打 `nihao` 时候选栏会先出英文再出中文

**解决方案**（二选一）：
- **方案 A1**：保持 `initial_quality: -3`，英文排在中文之后。主人打英文时用**回车上屏编码**（当前已有行为），或者选第二候选（英文）。空格仍上屏中文。
- **方案 A2**：利用 `laneChangeAndSpace_Filter` 或新 Lua filter 实现**智能空格**：当第一候选是英文单词时，空格上屏英文；当第一候选是中文时，空格上屏中文。这需要 Lua filter 介入空格行为，复杂度较高。

**推荐 A1**：先让英文单词出现在候选栏（核心需求），空格上屏英文作为后续优化。主人可以：
- 打 `apple` → 候选栏出现 `苹果 | apple | ...` → 选 `apple` 上屏
- 或者打 `apple` → 回车直接上屏编码 `apple`（当前已可用）

#### 3.4 候选注释（反查码）

主人要求候选注释跟五笔和拼音反查码。当前 `codeLookup_Filter` 只处理含 CJK 的候选（`has_cjk(txt)` 判定），英文候选不会经过反查。

**解决方案**：扩展 `codeLookup_Filter` 或创建新 Lua filter `enComment_Filter`：

- 英文候选 `apple` → 查 `en2zh_v2` 词典得到中文释义 `苹果` → 对 `苹果` 查五笔码和拼音 → 注释显示 `[vbrq] píngguǒ`
- 或者更简单：英文候选 `apple` → 注释直接显示中文释义 `苹果`（从 en2zh_v2 词典查）

**推荐**：先实现简单版（注释=中文释义），反查码作为后续增强。因为：
1. 英文单词→中文释义→五笔码→拼音，这条链需要两次查表，性能开销大
2. 主人最需要的是"看到英文单词本身能上屏"，注释是附加价值
3. 可以复用 `dic_4w_Filter` 的中英对照能力——它已经能给候选追加中英对照注释

#### 3.5 包体影响

| 项 | 大小 | 说明 |
|---|---|---|
| `en_words.dict.yaml`（10,000 词） | ~150 KB | 常用英文单词 |
| `en_words.dict.yaml`（20,000 词） | ~300 KB | 更全面覆盖 |
| 编译后 `.table.bin` | ~100-200 KB | Rime 编译后的二进制词典 |

当前 rawfile/rime 总大小约 20 MB，增加 150-300 KB 影响可忽略。

### 方案 B：Lua translator 实现英文联想

创建 `enWords_translator.lua`，类似 `rawEcho_translator` 但处理纯字母输入：

- 读取英文词表文件
- 判断输入是否为纯字母串
- 生成候选：精确匹配 + 前缀联想匹配
- 注释附带中文释义

**优点**：更灵活，可精确控制候选生成逻辑
**缺点**：Lua translator 性能不如原生 table_translator；维护复杂度更高；联想功能需自己实现（table_translator 的 `enable_completion` 是引擎原生支持的）

**不推荐**：方案 A 用 Rime 原生机制更稳定高效。

### 方案 C：扩展 abbrGloss_Filter

`abbrGloss_Filter` 已经实现了"打缩写码→插入缩写本体"的逻辑，可以扩展它覆盖更多英文单词。

**不推荐**：
1. Filter 只能插入候选到已有列表中，不能从零生成候选（如果词库里没有对应中文候选，英文候选也出不来）
2. 当前 `hitFor()` 闸门要求整串精确匹配缩写码，不支持前缀联想
3. 扩展成通用英文输入工具会破坏其"缩写专用"的简洁设计

## 四、跨平台兼容性

| 平台 | 兼容性 | 说明 |
|---|---|---|
| 鸿蒙 | ✅ | 只改 schema/词典/Lua，不改 C++ 引擎 |
| Android | ✅ | 同上，Rime 配置层改动三端通用 |
| Windows | ✅ | 同上 |

**关键**：方案 A 只涉及 Rime schema 配置和词典文件，不涉及任何平台特有代码，三端可同步生效。

## 五、实现步骤（方案 A）

1. **生成 `en_words.dict.yaml`**：从 ECDICT (`en2zh_v2_wp.dict.yaml`) 提取英文单词列，按词频筛选 10,000-20,000 常用词，格式 `word\tword\tweight`
2. **修改 `wubi_pinyin.custom.yaml`**：
   - `engine/translators/+` 添加 `- table_translator@en_words`
   - 新增 `en_words` translator 配置块
3. **（可选）扩展 `codeLookup_Filter`**：让英文候选也能查到中文释义和反查码
4. **构建装机验证**：
   - 打 `apple` → 候选栏出现 `apple`
   - 打 `app` → 候选栏出现 `apple/application/apply`（联想）
   - 选 `apple` → 上屏 `apple`
   - 候选注释显示中文释义或反查码

## 六、待 Qoder/主人拍板的决策点

| # | 决策点 | 选项 | 推荐 |
|---|---|---|---|
| 1 | 词典规模 | 10,000 词 / 20,000 词 / 全量 106,000 词 | 20,000 词（平衡覆盖与包体） |
| 2 | initial_quality | -3（中文优先）/ 1（英文优先）/ 0（同优先） | -3（不破坏中文输入体验） |
| 3 | 空格上屏英文 | A1 先不做 / A2 智能空格 | A1 先不做（回车可上屏编码） |
| 4 | 英文候选注释 | 中文释义 / 反查码 / 两者 | 先做中文释义，反查码后续增强 |
| 5 | 词典数据来源 | ECDICT提取 / SCOWL / WordNet | ECDICT提取（已在包内，MIT许可） |

## 七、风险与注意事项

1. **候选栏拥挤**：加入英文候选后，候选栏条目增多。当前 `page_size=50`，Rime 一次给 50 条，桥内按 UI 宽度切片。英文候选 `initial_quality: -3` 排在后面，不影响前几条中文候选的显示。
2. **`enable_completion` 性能**：开启前缀联想后，打 `a` 会匹配所有 `a` 开头的英文单词（数千条）。但 Rime 引擎内部有前缀索引，性能可接受。实测 `pinyin` translator 也开着 `enable_completion`，未报告性能问题。
3. **与 `abbrGloss_Filter` 的关系**：`abbrGloss_Filter` 处理缩写（cpu/ppt），`en_words` translator 处理通用英文单词。两者不冲突——缩写词在 `abbr_en.txt` 里，通用单词在 `en_words.dict.yaml` 里，命中不同数据源。
4. **与 `en2zh_v2` 的关系**：`en2zh_v2` 给中文释义候选，`en_words` 给英文本身候选。打 `apple` 后候选栏会有：`苹果 [en2zh_v2]` + `apple [en_words]` + `苹果 [en2zh_v2 释义]`。需要确认 `en2zh_v2` 和 `en_words` 的排序不冲突。
5. **九键模式**：`sansheng_t9.schema.yaml` 是独立的九键方案，`en_words` translator 只加到 `wubi_pinyin` 方案。九键下打英文走 `ascii_mode` 切换，不需要英文联想。