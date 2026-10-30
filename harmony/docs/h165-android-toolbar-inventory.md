# H-165 安卓工具栏功能交叉核对

> 核对人：CodeArts（只读，不改代码）
> 口径：M-178 ③ + M-180 更新（Qoder 已做完清点，CodeArts 改为交叉核对）
> 日期：2026-10-25 01:1x
> 目的：逐枚确认 Qoder `h165-top-function-bar-spec.md` §七 的 `setOption` 键名与安卓磁贴一一对应，补差异/遗漏

## 一、安卓 trime.yaml preset_keys — Rime 状态开关

来源：`F:/dshdesktopwork/sansheng-ime-android/试装-Trime-20261022/stage/rime/trime.yaml` lines 962-966

| preset_key | toggle | send | states | 语义 |
|------------|--------|------|--------|------|
| `Mode_switch` | `ascii_mode` | `SWITCH_CHARSET` | [中文, 西文] | 中英切换 |
| `Zenkaku_Hankaku` | `full_shape` | `SWITCH_CHARSET` | [半角, 全角] | 半角↔全角 |
| `Henkan` | `simplification` | `SWITCH_CHARSET` | [漢字, 汉字] | 简繁切换 |
| `Charset_switch` | `extended_charset` | `SWITCH_CHARSET` | [常用, 增廣] | 常用↔增廣 |
| `Punct_switch` | `ascii_punct` | `SWITCH_CHARSET` | [。，, ．，] | 中英标点 |

## 二、鸿蒙端 schema switches — 逐方案对比

### wubi_pinyin.schema.yaml（26键主方案）

来源：`entry/src/main/resources/rawfile/rime/wubi_pinyin.schema.yaml` lines 16-30

| switch name | reset | states | 语义 |
|-------------|-------|--------|------|
| `ascii_mode` | 0 | [中文, 西文] | 中英切换 |
| `full_shape` | 0 | [半角, 全角] | 半角↔全角 |
| `extended_charset` | 0 | [常用, 增廣] | 常用↔增廣 |
| `ascii_punct` | 0 | [。，, ．，] | 中英标点 |
| `zh_trad` | 0 | [简体, 繁體] | 简繁切换 |
| `phraseComment` | 1 | [Off, commentOn] | 编码提示开关 |

### sansheng_t9.schema.yaml（九键方案）

来源：`entry/src/main/resources/rawfile/rime/sansheng_t9.schema.yaml` lines 34-41

| switch name | reset | states | 语义 |
|-------------|-------|--------|------|
| `ascii_mode` | 0 | [中文, 西文] | 中英切换 |
| `full_shape` | 0 | [半角, 全角] | 半角↔全角 |
| `ascii_punct` | 0 | [。，, ．，] | 中英标点 |
| `zh_trad` | 0 | [简体, 繁體] | 简繁切换 |

**九键缺少**：`extended_charset`、`phraseComment`

## 三、交叉核对 — Qoder §七 vs 安卓 vs 鸿蒙 schema

| 安卓磁贴 (README §360) | 安卓 toggle (trime.yaml) | 鸿蒙 schema switch | Qoder §七 setOption 键名 | 鸿蒙状态机 | 差异/遗漏 |
|------------------------|-------------------------|--------------------|-----------------------|------------|-----------|
| `繁體→简体` | `simplification` ⚠️ | `zh_trad` ✓ | `zh_trad` ✓ | `tradMode` ✓ | **⚠️ 安卓 trime.yaml toggle=`simplification`，但安卓/鸿蒙 schema switch=`zh_trad`。toggle 名不匹配 ⇒ 安卓 `Henkan` 按键可能不生效。鸿蒙端用 `zh_trad` 与 schema 一致，正确。** |
| `中英对照→Off` | `ascii_mode` ✓ | `ascii_mode` ✓ | `ascii_mode` ✓ | `asciiMode` ✓ | 无差异 |
| `commentOn` | (无 preset_key) | `phraseComment` ✓ | §七 原说"无引擎开关" ❌ | `commentLine()` 恒显 | **❌ Qoder §七 原判断错误**：鸿蒙 schema 有 `phraseComment` 开关（wubi_pinyin line 28-30，states: [Off, commentOn]）。ISSUES.md H-165 已更正为"comment 有引擎开关"。九键 schema 无此开关。 |
| `半角→全角` | `full_shape` ✓ | `full_shape` ✓ | `full_shape` ✓ | 无状态机 | **鸿蒙需新增 UI 状态机**（`setOption('full_shape')` 走通用接口 `fanxing_napi.cpp:1015`，但无 `fullShapeMode` 字段跟踪当前态） |
| `常用→增廣` | `extended_charset` ✓ | `extended_charset` ✓ (仅 wubi_pinyin) | `extended_charset` ✓ | 无状态机 | **九键 schema 无此开关** ⇒ 磁贴需按方案置灰。鸿蒙需新增 UI 状态机 |
| `Reload Config` | — | — | — | — | ❌ napi 无 `reloadConfig` 导出（`fanxing_napi.cpp:1070-1083`），不做 |
| **(遗漏) `。，↔．，`** | `ascii_punct` ✓ | `ascii_punct` ✓ | **§七 未提及** ❌ | 无状态机 | **❌ Qoder §七 遗漏了 `ascii_punct`（中英标点切换）**。安卓 trime.yaml 有 `Punct_switch`，鸿蒙两个 schema 都声明了 `ascii_punct`。这是第六枚可用开关。 |

## 四、Qoder §九 安卓实物截图核实 — 交叉确认

Qoder §九 结论：
- `>`/`▼` 展开的是**图标工具栏**（‹/撤销/重做/光标/剪贴板/`…`/▼），不是磁贴行
- 六枚磁贴在 `…` 打开的**开关菜单**里
- 截图证据：`docs/evidence/2026-10-25/h165-android-toolbar/k1_toolbar.png`（展开态）、`s_toolbar.png`（折叠态）

**CodeArts 确认**：安卓 README 第 360 行描述的"磁贴"确实是 `…` 菜单里的条目，不是工具栏上的一排图标。Qoder §九 的修正正确。

**图标行逐枚可行性**（Qoder §十 已做，CodeArts 确认）：
- `‹`/`▼`：纯 UI 收起按钮，可做 ✓
- 撤销/重做：鸿蒙 `undoLastAction()` 零调用点（`7ba71d7` 删了唯一触发点），不可做 ❌
- 移动光标：API 齐（`KeyboardIndex.ets:1336/1371/1428`）但 0 调用，可做 ✓
- 剪贴板历史：需 `READ_PASTEBOARD` 权限，撞内容闸门 ⑧；"粘贴当前内容"长按 v 已有
- `…`：打开开关菜单覆盖层，可做 ✓

## 五、总结

### Qoder §七 需更正的两处

1. **`commentOn` 有引擎开关**：鸿蒙 wubi_pinyin schema 有 `phraseComment`（states: [Off, commentOn]），不是"无引擎开关、纯显示"。九键 schema 无此开关。ISSUES.md H-165 已更正。

2. **遗漏 `ascii_punct`（中英标点）**：安卓 trime.yaml 有 `Punct_switch`，鸿蒙两个 schema 都声明了 `ascii_punct`。这是第六枚可用 `setOption` 开关，Qoder §七 未列出。

### 可用开关汇总（修正后）

| 开关 | setOption 键名 | wubi_pinyin | sansheng_t9 | 鸿蒙状态机 | 需新增 |
|------|----------------|-------------|-------------|------------|--------|
| 中英 | `ascii_mode` | ✓ | ✓ | `asciiMode` ✓ | 无 |
| 简繁 | `zh_trad` | ✓ | ✓ | `tradMode` ✓ | 无 |
| 半角全角 | `full_shape` | ✓ | ✓ | 无 | UI 状态机 |
| 常用增廣 | `extended_charset` | ✓ | ✗ | 无 | UI 状态机 + 九键置灰 |
| 编码提示 | `phraseComment` | ✓ | ✗ | `commentLine()` 恒显 | UI 状态机 + 九键置灰 |
| 中英标点 | `ascii_punct` | ✓ | ✓ | 无 | UI 状态机 |
| Reload | — | — | — | — | 引擎侧加 API |

**结论**：安卓六枚磁贴中，**5 枚现有 API 可做**（`ascii_mode`/`zh_trad`/`full_shape`/`extended_charset`/`phraseComment`），加上遗漏的 `ascii_punct` 共 **6 枚**。Reload 需引擎侧加 API。九键方案只有 4 个开关（缺 `extended_charset`/`phraseComment`），磁贴需按方案置灰。

### 安卓 trime.yaml `Henkan` toggle 不匹配问题

安卓 trime.yaml 的 `Henkan: {toggle: simplification}` 与 schema 的 `zh_trad` switch 不匹配。这意味着安卓端的 `Henkan` 按键在当前配置下可能不生效（toggle `simplification` 不是 schema 声明的 switch）。鸿蒙端直接用 `zh_trad`，与 schema 一致，不受此问题影响。**这是安卓端的配置 bug，鸿蒙端无需处理**。

### 证据路径

- 安卓 trime.yaml preset_keys：`F:/dshdesktopwork/sansheng-ime-android/试装-Trime-20261022/stage/rime/trime.yaml` lines 962-966
- 安卓 schema switches：`F:/dshdesktopwork/sansheng-ime-android/rime/wubi_pinyin.schema.yaml` lines 20-29
- 鸿蒙 wubi_pinyin schema：`entry/src/main/resources/rawfile/rime/wubi_pinyin.schema.yaml` lines 16-30
- 鸿蒙 sansheng_t9 schema：`entry/src/main/resources/rawfile/rime/sansheng_t9.schema.yaml` lines 34-41
- 安卓实物截图：`docs/evidence/2026-10-25/h165-android-toolbar/k1_toolbar.png`、`s_toolbar.png`
- Qoder §七/§九/§十：`docs/h165-top-function-bar-spec.md`