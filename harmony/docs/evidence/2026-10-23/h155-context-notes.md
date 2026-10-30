# H-155 上下文备注（context-notes）

## 项目
- 三生输入法鸿蒙版，包名 `com.sansheng.ime`，ArkTS + ArkUI，IME 扩展工程。
- 工程根：`F:\qoderwork\sansheng-ime-harmony`
- 构建：`powershell -Command "$env:SS_WHO='CodeArts'; & 'F:\qoderwork\sansheng-ime-harmony\scripts\build.ps1'"`
- 签名：`powershell -Command "& 'F:\qoderwork\sansheng-ime-harmony\scripts\sign.ps1'"`
- 装机：`hdc -t 7GL0226408083897 install -r <signed.hap>`（hdc 路径 `D:/DevTools/DevEco/DevEco Studio/sdk/default/openharmony/toolchains/hdc.exe`）；装机后 `hdc -t 7GL0226408083897 shell ime -s com.sansheng.ime` 切回输入法（干净重装默认弹回小艺）。
- 验证设备：Mate80（`7GL0226408083897`），**人工真机滑键验证，不做设备自动测试**。

## 关键 API（已确认，来自 @ohos.inputMethodEngine，API 10+）
- `inputClient.sendExtendAction(action: ExtendAction)`：
  - SELECT_ALL=0, CUT=3, COPY=4, PASTE=5
- **PASTE 限制**：需宿主 app 申请 `ohos.permission.READ_PASTEBOARD`，非输入法权限；个别 app 静默失败属正常。

## 现有代码结构（H-154 已合入 commit b5fda68）
- `entry/src/main/ets/inputmethod/KeyboardController.ets`：
  - 已 import `inputMethodEngine`；私有 `inputClient`（`inputStart` 回调赋值）。
  - 已有撤销栈 `undoStack` / `UndoRecord` / `pushUndo` / `clearAllAndRecord` / `undoLastAction`；`insertText` 已入栈。
  - 需新增：`sendEditorAction(action)` 封装 `this.inputClient?.sendExtendAction(action)`，及 `HIDDEN_SYMBOLS` 常量（或表放 KeyboardIndex）。
- `entry/src/main/ets/pages/KeyboardIndex.ets`：
  - `LetterKey(ch)` @Builder：`.onTouch` 短按发送（Down press、Up 发 `sendLetter` 除非 `swipeAltDone`）；`.priorityGesture(PanGesture {direction: Vertical, distance:12})` 上滑 ALT/下滑大写并置 `swipeAltDone`。
  - `getAltChar(ch)` 已存在（ALT_CHARS 表）。
  - 需新增：`getHiddenSymbols(ch)`、`@State` 气泡显隐 + 高亮索引、`LongPress` 分支（a/s/v/c→editorAction；其余→气泡）、气泡 Stack。
  - L1005 注释与代码相反（写"短按展开"实际单击折叠）——顺手修正，不强制本批。

## 约束
- 源码编辑由 logic-coder 子 agent 执行；构建/签名/装机/提交由主协调执行。
- 不新增页面，不动 `main_pages.json`、不动 `module.json5` metadata。
- 不参照安卓 nova6（用户拍板纯通用符号集）。
- 不改动 Qoder 归属的 `scripts/owner_*.py`。

## 文件归属
- `entry/src/main/ets/{pages,inputmethod}/**`、`docs/**`、`scripts/**` 归 CodeArts。
- `module.json5` 的 `ohos.entry.mainability` metadata 归 Qoder（本批不动）。