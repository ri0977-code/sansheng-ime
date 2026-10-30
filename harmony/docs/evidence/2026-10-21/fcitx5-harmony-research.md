# fcitx5-harmony 研究总结

> 2026-10-21 CodeArts 调研记录，供后续参考。

## 仓库信息

- **仓库**：`github.com/fcitx-contrib/fcitx5-harmony`（Qoder 已用 GitHub API + `git ls-remote` 核实 owner 是 `fcitx-contrib`，不是 `fcitx5-android`；本机浅克隆 `F:/qoderwork/_ref_fcitx5_harmony`，commit `19d61297e6313014bff8b15a488d843ffbcfc1bd`，最后推送 2026-06-10）
- **类型**：HarmonyOS NEXT 原生 ArkTS 移植（非 Android 版在鸿蒙上跑）
- **许可证**：GPL-3.0（`LICENSE` 第 1 行：`GNU GENERAL PUBLIC LICENSE Version 3`）
- **获取方式**：`git clone` 失败（GitHub 连接超时），用 `curl.exe` 从 `raw.githubusercontent.com` 下载关键文件

## 关键发现

### 1. UI 渲染方式：WebView，非纯 ArkTS

`VirtualKeyboard.ets` 只有一个 `Web()` 组件——键盘 UI 用 **WebView + HTML/CSS/JS** 渲染，不是纯 ArkTS。

这意味着：
- UI 代码（HTML/CSS/JS）不能直接搬到我们的纯 ArkTS 项目中
- 渲染性能取决于 WebView，不如原生 ArkTS
- 但交互设计和事件处理模式有参考价值

### 2. 有参考价值的文件

| 文件 | 内容 | 参考价值 |
|---|---|---|
| `KeyboardController.ets` | 事件处理、退格滑动选择、预编辑处理 | 交互模式可借鉴 |
| `FcitxEvent.ets` | 事件类型定义 | 事件分类思路 |
| `keycode.ets` | 键码映射 | 键码定义参考 |
| `TextOperation.ets` | 文本操作 | 文本处理思路 |
| `module.json5` | 模块配置 | IME 配置参考 |

### 3. 许可证限制

**GPL-3.0** 是强 copyleft 许可证：
- 不能直接搬代码到我们的闭源分发中
- 只能借设计思路和交互模式
- 与 kanonIME（MIT）和 hMixedKeyboard（Apache-2.0）不同，GPL-3.0 代码无法安全复用

## 结论

| 维度 | fcitx5-harmony | kanonIME（主参考） |
|---|---|---|
| 许可证 | GPL-3.0（不能搬代码） | MIT（可改写） |
| UI 方案 | WebView + HTML/CSS/JS | 纯 ArkTS |
| 候选栏 | **ArkTS 侧没有候选栏**：`grep -i candidate` 全项目只有 5 处原生事件转发（`hasCandidates`/`askCandidateActions`/`activateCandidateAction`/`selectCandidate`），词是 WebView 里画的 | 171 行成熟 ArkTS 双行实现 |
| 适配我们项目 | 不适配（WebView 方案） | 直接适配（纯 ArkTS） |

**维持 kanonIME 作为主参考**。fcitx5-harmony 的交互设计思路（退格滑动选择、预编辑处理）可在 M5+ 阶段借鉴，但代码层面无复用可能。