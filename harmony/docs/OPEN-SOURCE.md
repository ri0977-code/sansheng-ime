# 开源复用规则与候选清单

> 原则：**能用开源就不从零写**，但必须过许可证、安全、可维护性三道门。
> 本文件由 Qoder 定稿；CodeArts 可追加候选，追加时写清来源与许可证证据。

## 1. 复用顺序

1. **官方 Sample / 官方组件**（DevEco `Import Sample`、OpenHarmony 仓库）——优先，API 对齐最好。
2. **Apache-2.0 / MIT / BSD 的社区项目**——可复制代码，保留版权头。
3. **GPL / AGPL / 无 LICENSE 的项目**——只看交互思路，**不复制代码、不引入依赖**。
4. 都没有，才自己写。

## 2. 三道门

### 许可证门

- 根目录必须有 `LICENSE`，且与 `README`、`oh-package.json5` 的声明一致。
- Apache-2.0：保留 `LICENSE`、`NOTICE` 和源文件版权头；修改过的文件要注明。
- MIT/BSD：保留版权声明与许可文本。
- GPL/AGPL：不进入本工程；如需参考，只记录“交互/布局思路”，不复制实现。
- 许可证不明或双许可无法判断：按**禁止复制**处理。

### 安全门

- 只从源码构建，不用来源不明的预编译 `.so` / `.har`。
- 不引入带遥测、联网上报、动态下发代码的库。
- 引入前读一遍关键文件；不整包照搬，只取需要的组件。

### 质量门

- 必须能在 API 22 目标下编译，并在 M1/M2 验收里通过。
- 记录上游 commit；不跟随 `main` 自动更新；本地快照放 `F:\qoderwork\_ref_*`。
- 社区代码风格不统一的，先适配本项目接口，再提交。

## 3. 当前候选清单

| 项目 | 用途 | 许可证 | 本地位置 / 来源 | 状态 |
|---|---|---|---|---|
| **hMixedKeyboard** | IME 服务、面板生命周期、键盘面板、候选栏、按键路由 | **Apache-2.0**（GitHub API `license.spdx_id` 实测；本机副本 `LICENSE` 是未填写的 Apache-2.0 模板，README §License 自述 Apache-2.0） | `F:\qoderwork\_ref_hMixedKeyboard`；`https://github.com/nanaseyuu/hMixedKeyboard` | **M1 首选移植对象** |
| OpenHarmony KikaInputMethod（官方输入法 Sample） | IME Kit 接入的标准做法、面板/输入客户端范式 | Apache-2.0（以导入时 LICENSE 为准） | DevEco `Import Sample` 搜 `InputMethod` | 备用参考 |
| `chuanis/harmonyos-next-rime-har` | librime/OpenCC/Lua 预编译静态库与 NAPI 示例 | **MIT**（GitHub API 实测；本机副本 `LICENSE` 实测 "Copyright (c) 2026 Lucas Y.C. Wang"）。包内 `oh-package.json5` 标 Apache-2.0 属上游标注不一致，**H-007 已按 D-005 裁定**：本仓库统一 Apache-2.0，MIT 上游代码以 MIT 条款保留声明（`LICENSES/MIT-harmonyos-next-rime-har.txt`），两者兼容 | `F:\codeartswork\_ref_harmonyos-rime\` | 已使用；许可结论见根 `NOTICE` 第二节 |
| Trime / Fcitx5-Android | Rime 安卓前端交互参考 | GPL-3.0 | 仅网络资料 | **只看思路，不复制代码** |
| **fcitx-contrib/fcitx5-harmony** | 鸿蒙版 fcitx5（键盘 UI 在 WebView 里，非 ArkTS） | **GPL-3.0**（根 `LICENSE` 原文已核） | `F:\qoderwork\_ref_fcitx5_harmony`，commit `19d6129`（sha 已对 `ls-remote`） | **只读思路，禁止复制代码/引依赖**；ArkTS 侧仅 `model/KeyboardController.ets`（16,936 B）值得当状态机校验读物。**不作为候选栏 v2 的代码参考**，见 `DECISIONS.md` D-002 |
| **fcitx-contrib/fcitx5-prebuilder** | 为 macOS/Windows/iOS/**Harmony** 构建 fcitx5 静态库与资源 | **MIT**（GitHub API 返回 spdx `MIT`，用前再核一次根 `LICENSE`） | 仅网络资料（未克隆） | **待评估**：M4 的 librime/OpenCC/Lua 静态库沙箱化可能能省工序；评估结论写进 `DECISIONS.md` 再决定引不引入 |
| FlorisBoard | 键盘布局、手势、主题结构参考 | Apache-2.0 | 仅网络资料 | 可参考，不直接移植（Android） |

> 皮肤/主题：目前没有核实到可直接商用的 HarmonyOS 开源皮肤仓库。先做**自有主题格式**（颜色/圆角/背景/字体），色板可取自 MIT/Apache 项目；不得扒商业输入法皮肤资源。

## 4. 移植 hMixedKeyboard 的边界（M1）

**可以直接借鉴/改写：**

- `HMixedService.ets`：`InputMethodExtensionAbility` 生命周期。
- `model/MixedController.ets`：panel 创建、`setUiContent` 后 `resize`、输入事件路由、屏幕尺寸计算。
- `pages/KeyboardIndex.ets`：候选栏 + QWERTY 布局 + 按键样式。
- 资源与主题结构（颜色、圆角、行高）。

**必须替换：**

- `model/DictEngine.ets`（`.ms2` 字典）→ 本项目 `EngineProvider.get()` / `RimeEngine`。
- 包名、应用名、图标、签名。

**不要带进来：**

- 它的字典数据、预置词库、与 Rime 无关的网络/统计逻辑。
- 任何 GPL 代码或来源不明的二进制。

## 5. 记录模板

新增复用项时，在清单表追加一行，并另起一段写：

```markdown
### <项目名> @ <commit>

- 来源：
- 许可证：<LICENSE 文件路径/链接，核对日期>
- 复用文件：
- 改动说明：
- 保留的版权头：
- 验收：构建结果 / 真机结果
```

## 5.1 CodeArts 调研补充（2026-10-20，M-002 / H-022）

- **方法**：用 `webfetch` 检索 GitHub（仓库搜索 API + 网页搜索）与 Gitee 搜索页，关键词 `harmonyos keyboard` / `harmonyos inputmethod` / `鸿蒙 输入法`。
- **结果**：
  - GitHub 仓库搜索 API 返回空或 `socket closed`（网络受限）；
  - Gitee / GitHub 搜索页为前端渲染，`webfetch` 取不回结果列表。
- **结论**：**无新增候选**；沿用第 3 节清单，`hMixedKeyboard` 仍为 M1 首选移植对象。
- **已采用并落地**（源文件版权头见各文件顶部）：
  - `entry/src/main/ets/inputmethod/InputMethodService.ets` — IME 生命周期
  - `entry/src/main/ets/inputmethod/KeyboardController.ets` — 面板生命周期 + 横竖屏重算
  - `entry/src/main/ets/pages/KeyboardIndex.ets` — 候选栏 + QWERTY/九宫格 + 分类符号页
  - 保留版权头：各文件头注明 `nanaseyuu/hMixedKeyboard (Apache-2.0)`。
- **皮肤/主题**：与第 3 节一致——无可直接商用的 HarmonyOS 开源皮肤；本工程用自有配色常量（`BG_*` / `FG_*`）。

## 6. M1 壳复用审计（2026-10-21，M-023 / H-036）

> 以 `F:\qoderwork\_ref_hMixedKeyboard`（Apache-2.0）为基准，逐文件对照三生输入法的 `InputMethodService.ets`、`KeyboardController.ets`、`KeyboardIndex.ets`。
> 审计范围：M1 键盘壳（`v0.2.7-shell`），不含引擎/NAPI/词库。

### 6.1 已复用清单

| 三生文件 | 参考壳文件 | 复用内容 | 参考壳行号 |
|---|---|---|---|
| `InputMethodService.ets` | `HMixedService.ets` | 整体结构：`InputMethodExtensionAbility` → `onCreate(want)` 转调 controller → `onDestroy` 转调；TAG 常量；`want.abilityName` 日志 | 全文 17 行 |
| `KeyboardController.ets` | `MixedController.ets` | ① 面板生命周期顺序 `createPanel → setUiContent → resize(px) → show`（关键坑：setUiContent 必须先于 resize） | `executeTransition():724-728` |
| | | ② `inputStart`/`inputStop` 事件路由 + `inputClient` 缓存 | `registerListener():877-912` |
| | | ③ `display.on('change')` + 300ms 防抖 `scheduleRelayout()` | `registerListener():909`、`scheduleRelayout():915-929` |
| | | ④ `display.getDefaultDisplaySync().rotation`（1/3=横屏）判取向 | `applyLayout():403` |
| | | ⑤ `resize` 传 **px**（`heightVp * densityPixels`）而非 vp | `applyLayout():431` |
| | | ⑥ 退格用 `deleteForward`（方向命名反转） | `deleteBeforeCursor():1229-1233` |
| | | ⑦ `inputClient.insertText()` 上屏 | `commitText():1270+` |
| | | ⑧ `setUiListener` 推送状态到面板 | `setUiListener():1025-1031` |
| | | ⑨ 面板尺寸计算 `computePanelSize()` 依取向区分 bar/row vp | `applyLayout():391-435` |
| `KeyboardIndex.ets` | `inputmethod/pages/KeyboardIndex.ets` | ① QWERTY 三行字母 `LETTER_ROW_1/2/3` 完全相同 | `:8-10` |
| | | ② 配色常量 `BG_PANEL/BG_BAR/BG_KEY/BG_FUNC/BG_FUNC_ON/FG_TEXT` 值相同 | `:20-26` |
| | | ③ 候选栏 + 按键区 + 底栏的三段式 `build()` 布局 | `build():679-738` |
| | | ④ `?123` 切换数字/符号模式 | `ModeKey():560-576` |
| | | ⑤ Shift + 第三行字母 + 退格的行布局 | `LetterRows():649-677` |
| | | ⑥ `layoutWeight` 分配按键宽度 | 全文 |
| | | ⑦ `keyH()` = `rowHeight - margin` 的键高计算 | `:506` |

### 6.2 可复用但未用清单

| # | 参考壳能力 | 参考壳文件/行号 | 能解决什么问题 | 最小改法 | 归属阶段 |
|---|---|---|---|---|---|
| 1 | **`onTouch` + `startPress` 按键触摸体系**：按下高亮（`BG_PRESSED`）、长按 1s 后每 100ms 重复（退格连续删除）、20ms 触感反馈（`vibrator`） | `KeyboardIndex.ets:226-262`（`startPress`/`cancelRepeat`/`vibrate`/`keyBg`） | 按键无视觉反馈、无长按重复、无触感——三大体验缺陷 | `KeyboardIndex.ets`：加 `@State pressedKey`、`startPress()`/`cancelRepeat()`/`vibrate()` 函数，`LetterKey`/`BackKey` 等改 `onClick` → `onTouch` | M5 皮肤/体验 |
| 2 | **`onEnter` 用 `getEditorAttribute` + `sendKeyFunction`**：搜索框回车触发搜索而非换行，单行字段不插无效 `\n` | `MixedController.ets:1151-1190`（`onEnter`） | 搜索框/聊天发送框里回车不触发对应动作 | `KeyboardController.ets`：`onKey('Enter')` 分支加 `getEditorAttribute` 判断 `enterKeyType`，≥2 调 `sendKeyFunction`，否则 `insertText('\n')` | M2 引擎接入 |
| 3 | **`resizeWithRetry` 重试机制**：resize 失败后最多 6 次重试 + 300ms 退避 | `MixedController.ets:826-853` | resize 偶发失败（系统竞态）时面板尺寸不对 | `KeyboardController.ets`：`createPanel`/`applyPanelSize` 的 `resize` 调用包装 retry | M2 稳定性 |
| 4 | **`onContentArea` 自校准回路**：页面 `onAreaChange` 回报实际渲染尺寸，controller 据此校准（3 次预算） | `MixedController.ets:566-630`；`KeyboardIndex.ets:729-736` | 系统 clamp 后面板尺寸与预期不符 | `KeyboardIndex.ets` `build()` 加 `onAreaChange` → 回报 `KeyboardController` → 比对并重算 | M2 稳定性 |
| 5 | **`foldDisplayModeChange` 事件**：折叠屏展开/收起的第三种 display 事件 | `MixedController.ets:911` | 折叠屏展开/收起时面板不更新 | `KeyboardController.ets` `registerDisplayListener` 加 `display.on('foldDisplayModeChange', ...)` | M2 折叠屏 |
| 6 | **`notifyUi` 去重推送**：状态签名比对，相同则不推送，减少 ArkUI 重渲染 | `MixedController.ets:1037-1048`（`lastPushSig`） | 不必要的重渲染导致性能浪费 | `KeyboardController.ets` `notify()` 加签名比对 | M2 性能优化 |
| 7 | **`panel.on('show'/'hide')` 回调**：跟踪面板实际可见性 | `MixedController.ets:807-823` | 面板可见性状态不准确（`showPanel` 只调 `show()` 不确认） | `KeyboardController.ets` `createPanel` 后加 `p.on('show'/'hide')` | M2 稳定性 |
| 8 | **Jyutping 尺寸模型**（CC0）：`key(pt) = phone-landscape ? 36 : min(53 + floor((widthPt-300)/20), 58)` | `MixedController.ets:25-28`、`applyLayout():408-413` | 不同屏幕宽度下键高不自适应（我们用固定 48/34vp） | `KeyboardController.ets` `computePanelSize` 改用此公式 | M5 适配 |
| 9 | **`onPunctuation` 标点组合上屏**：打标点时先 flush 编码再上屏标点；Shift+标点切换半/全角 | `MixedController.ets:1246-1268` | 打字中途打逗号不会先上屏已打内容 | `KeyboardController.ets` `onKey` 里对标点做特殊处理 | M2 引擎接入 |
| 10 | **`puncLabel` 半/全角键面提示**：Shift 状态下 `,` `.` 键面显示 `，` `。` | `KeyboardIndex.ets:618-629` | 用户不知道 Shift+标点可以输入全角 | `KeyboardIndex.ets` 底栏标点键的键面文字随 Shift 状态变化 | M5 体验 |
| 11 | **`Blank().height(bottomInset)` dock 避让**：面板底部留透明 spacer 避开 taskbar/导航指示器 | `KeyboardIndex.ets:722` | 2-in-1 设备上键盘遮住 dock | `KeyboardIndex.ets` `build()` 底部加 `Blank().height(bottomInset)` | M5 平板适配 |
| 12 | **物理键盘支持**：`inputDevice` 检测、`KeyboardDelegate.on('keyEvent')`、漢/EN 切换、浮动候选栏（`FLG_FLOATING`） | `MixedController.ets:937-1011`、`executeTransition():684-805` | 物理键盘场景完全没有支持 | 大规模新增，需独立 milestone | M3+ 物理键盘 |

### 6.3 许可证不兼容或不可直接用

| 项目 | 许可证 | 结论 |
|---|---|---|
| `DictEngine.ets`（hMixedKeyboard 自带字典引擎） | Apache-2.0（许可证兼容） | **不直接用**：它是 `.ms2` 格式字典引擎，本项目用 `EngineProvider` / `RimeEngine` 替代。许可证本身无障碍，是架构选择不用它 |
| `chuanis/harmonyos-next-rime-har` | 根 **MIT**（GitHub API 实测） | **已使用预编译库**；H-007 标注不一致已按 D-005 收口：本仓库 Apache-2.0 + 保留 MIT 声明（`LICENSES/MIT-harmonyos-next-rime-har.txt`），随包静态库的逐项许可见根 `NOTICE` 第二节 |
| Trime / Fcitx5-Android | GPL-3.0 | **只看交互思路，不复制代码** |
| `yuetyam/jyutping-harmony`（Jyutping 尺寸模型来源） | CC0 | **可自由使用**，无需署名。尺寸公式可直接采用 |

### 6.4 三条按性价比排序的最小改动建议

1. **（最高性价比）`onTouch` + `startPress` 按键触摸体系** — 一次改动同时解决按键无高亮、无长按重复、无触感三大体验缺陷。只改 `KeyboardIndex.ets` 一个文件，参考壳的 `startPress`/`cancelRepeat`/`vibrate`/`keyBg` 代码可直接适配（Apache-2.0），约 80 行新增。**建议在 M5 皮肤阶段优先实施。**

2. **（次高性价比）`onEnter` 用 `getEditorAttribute` + `sendKeyFunction`** — 解决搜索框/发送框回车不触发对应动作的功能缺陷。只改 `KeyboardController.ets` 的 `onKey('Enter')` 分支，约 20 行新增。**建议在 M2 引擎接入时一并实施**，因为真引擎的 `processKey('Enter')` 语义需要与此协调。

3. **（第三）`resizeWithRetry` + `onContentArea` 自校准回路** — 解决 resize 偶发失败和系统 clamp 后尺寸不对的稳定性问题。改 `KeyboardController.ets` + `KeyboardIndex.ets` 两个文件，约 60 行新增。**建议在 M2 稳定性阶段实施**，需真机回归验证。

> **总结**：M1 壳的核心架构（面板生命周期、输入路由、横竖屏重算、QWERTY 布局、配色）已从 hMixedKeyboard 充分复用；主要差距在按键交互体验（触摸反馈/长按重复/触感）和边缘稳定性（resize 重试/自校准），这些可在 M2/M5 阶段按优先级逐步吸收，不需要推翻现有实现。

## 7. 发布前

- 生成 `THIRD-PARTY-NOTICES`，列出所有复用项目、许可证、版权人。
- 确认没有 GPL/AGPL 代码进入产物。
- 确认 `sign/`、密钥、内部路径没有进入公开仓库。
