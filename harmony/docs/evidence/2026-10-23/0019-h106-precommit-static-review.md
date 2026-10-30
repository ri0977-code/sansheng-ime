# 0019 · H-106 开工前静态预审（工作区 vs HEAD，00:30）

- 只读审查，不改 `entry/src/**`；对象是 CodeArts 工作区里尚未 commit 的 9 个改动 + 1 个未跟踪文件。
- 目的：让他**一次 commit 就带对**，避免装完机才发现方向反了。

## 结论表

| # | 级别 | 发现 | 证据 | 要求 |
|---|---|---|---|---|
| 1 | **P1 方向反了** | `input_method_config.json` 工作区把两个子类型 id 从 HEAD 的不同值统一成了 `InputMethodService`。上游参考工程与 HEAD 都是两个不同 id。子类型 id 不要求等于 extensionAbility 名（参考工程的 ability 也叫 `InputMethodService`，但 id 仍是 `InputMethodExtAbility1`/`InputMethodExtAbility`） | `git diff HEAD -- entry/src/main/resources/base/profile/input_method_config.json`；`F:\codeartswork\_ref_harmonyos-rime\harmonyos-next-rime-har-main\entry\src\main\resources\base\profile\input_method_config.json:4,10`；参考工程 `module.json5` 的 ability 名 `InputMethodService`；本仓 `module.json5` 同样只有 `InputMethodService` | 改回两个不同 id；除非拿得出官方样例/文档证明可重复，并在 commit message 附链接 |
| 2 | **P1 文件不在 git** | `rawfile/rime/lua/phoneComment_Filter.lua`（2,397 B）未被跟踪，`git ls-files` 报 pathspec 不存在；但 `lua-files.txt:20` 已列它 ⇒ clean checkout 缺文件 | `git ls-files --error-unmatch …`；`git status` | 随 H-106 同一 commit `git add` |
| 3 | **P1 没接线** | `phoneComment_Filter` 只在 `rime.lua:102` 注册、`lua-files.txt` 列出；两份 schema 的链尾仍是 `laneChangeAndSpace_Filter`（custom.yaml:60、schema.yaml:66）。全仓 grep `lua_filter@phoneComment_Filter` = 0 | `grep -c` 全部 yaml 均为 0 | 改两处链尾 + `DATA_VERSION` bump **v21**（设备已装 v20） |
| 4 | **P1 HEAD 编不过** | 工作区 `KeyboardController.ets` 的 `hideKeyboard()`（`:291-300`，含 `panel.hide()` 与 `engine.clear()`）未入库；HEAD 的 `KeyboardIndex.ets:1807` 却调用它（工作区已挪到 `:1019`） | H-114 / M-102 | 随 H-106 commit，不许 revert；自测 `git grep -n hideKeyboard HEAD -- entry/src/main/ets` 同时命中调用与定义 |
| 5 | P3 死代码 | `Index.ets:79` 新增 `private openSettings()`，全文件 0 处调用；`:166` 多一个空行。H-090 已定案 1.0.0 摘掉设置入口 | `grep -n openSettings Index.ets` 只有定义 | 同一 commit 顺手删掉，别把入口接回来 |
| 6 | **P2 验收缺口** | `hideKeyboard()` 只把 `kbHidden` 置 true，全仓**没有任何地方读它**；`showPanel()` 只在 `inputStart` 触发 ⇒ 收起后再点同一个输入框，键盘可能不回来 | `KeyboardController.ets:74/149/233/293`；`ability.on('inputStart')` 在 `:135` 调 `showPanel()` | H-106 的 ① 判定加半步：收起 → 再点同一输入框 → 键盘应重新出现；不复现就在本轮补 show 路径（属 H-106 完成度，不另开项） |

## 静态复核通过、无需改动的部分

- 改过的 yaml 注释是**准确的**：包内确实没有 `punctuator`/`symbols.custom.yaml`（`ls rawfile/rime | grep symbol` = 0），符号输入走 `rawfile/symbols/symbols.json`（34,984 B，存在，`KeyboardIndex.ets:28` 起的数据驱动注释也指向它）。
- `phoneComment_Filter.lua` 的截断逻辑静态看是对的：按 UTF-8 首字节定长切、汉字算 2 格、右侧截断并补 `…`，反查码前置所以先保住；`MAX_WIDTH=20`。真正是否生效只能等接线后真机看注释长度。
- `hideKeyboard()` 调 `panel.hide()`（不是 destroy），符合「收起不销毁」的设计。

## 复现命令（只读）

```bash
git diff HEAD -- entry/src/main/resources/base/profile/input_method_config.json
git ls-files --error-unmatch entry/src/main/resources/rawfile/rime/lua/phoneComment_Filter.lua
grep -rc "lua_filter@phoneComment_Filter" entry/src/main/resources/rawfile/rime/*.yaml
grep -rn "kbHidden" entry/src/main/ets --include=*.ets
grep -n "openSettings" entry/src/main/ets/pages/Index.ets
```
