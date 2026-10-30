# nova 6 键路径实测记录（H-081 前置 · CodeArts）

> 实测人：CodeArts · 2026-10-22 12:10–12:35
> 设备：nova 6（`HBX4C19C02009787`，1080×2400 竖屏）
> 被测：安卓版三生 `com.sansheng.ime` 1.10.1（fcitx5 内核，`FcitxInputMethodService`）
> 结论先行：**拿到了 `/` 入口的 UI 硬证据（26 键 `h` 键下挂次级字符 `/`），但 adb 无法模拟「用户在软键盘上点/上滑」（华为挡触摸注入），按派单预案改用已知 fcitx5 行为定位修法。**
> 还原状态：实测完已 `ime set com.baidu.input/.ImeService` 并 `settings get secure default_input_method` 复核通过（12:35）。

## 一、实测过程

1. `am start` 打开三生 MainActivity（主题页），`input tap 540 1200` 后 `uiautomator dump`（`w01.xml`）。
   注意：该页 dump 出的「键盘」实为 MainActivity **内嵌键盘预览**（y 438–747，位于屏幕上部），
   但它**忠实渲染了 26 键键帽布局**（含主字符 + 次级字符双层文字节点），与真实软键盘同布局源（fcitx5 主题渲染）。
2. 系统设置 → 搜索页（AutoCompleteTextView）拉起三生软键盘，`dumpsys input_method` 确认 `mIsInputViewShown=true`。
3. 前后帧差分定位软键盘区域：**y ≈ 1780–2400**（候选栏 1780–1830、q 行 ~1840、a 行 ~1955、z 行 ~2145、底栏 ~2310）。
   ASCII 深度图确认 QWERTY 结构（10+9+7+底栏）与次级字符双层标注。
4. 触摸注入测试：`input tap 198/600/653 1955`、`input swipe 600 1960→1650`（多次）——**键盘区像素零变化**（连按压高亮都没有）。
5. 硬件按键通道测试：`input keyevent KEYCODE_H` 键盘区有响应（按压高亮 + 候选栏变化）；但 `KEYCODE_A` 单步复测时**只有 EditText 直接收字**（diff bbox 172,88–1080,443，键盘区零变化）——硬件按键走系统直通路径，不经过软键盘的按键处理逻辑，无法模拟「软键盘按键进引擎」。
6. 结论：**nova 6 上 adb 无法完成「用户打出 /szd」的端到端模拟**。华为对 IME 窗口的触摸注入有防护（防远程劫持输入法），keyevent 又绕开软键盘路径。

## 二、拿到的硬证据（可复核）

### 2.1 `/` 的 UI 入口 = 26 键 `h` 键次级字符（`w01.xml`）

26 键三行键帽均双层标注（主字符 + 次级字符），`h` 键：

```
text='h'  bounds 中心 cx=594 cy=523   ← 主字符（键帽上层）
text='/'  bounds 中心 cx=594 cy=553   ← 次级字符（键帽下缘小字）
```

完整次级字符表（dump 提取，与鸿蒙 M-058 抄的表一致）：

| 行 | 键→次级 |
|---|---|
| q 行 | q→1 w→2 e→3 r→4 t→5 y→6 u→7 i→8 o→9 p→0 |
| a 行 | a→@ s→* d→+ f→- g→= h→**/** j→# k→( l→) |
| z 行 | z→' x→: c→? v→! b→~ n→\ m→\*（m 为 `\`，见 dump） |

> 修正：dump 实测 z 行次级为 `z→' x→: c→? v→! b→~ n→\ m→\`（m 键次级字符是 `\`，与鸿蒙 M-058 的 `z' x: v?...` 表一致）。

### 2.2 fcitx5 候选栏是自绘 View

候选区（软键盘 y 348–408 对应内嵌预览）在 uiautomator dump 中**无任何 text 节点**（Canvas 自绘），候选词无法用 accessibility 读取。

### 2.3 已知 fcitx5 行为（修法依据，Qoder 派单口径）

fcitx5 Android（开源）对「次级字符上滑」的实现：`onSwipeUp` → 以该 hint 字符构造 `KeyEvent` → **走与真实按键完全相同的 `processKey` 路径进输入法引擎**。因此安卓版用户打出 `/szd` 的真实键路径是：

```
上滑 h 键（次级字符 /）→ '/' 作为按键进 fcitx5 引擎 → punctuator/symbols preset 接管
→ 依次点 s、z、d（普通字母键，进编码）→ 候选栏出现 /szd 对应词条 → 点候选上屏
```

这正是 Qoder M-059-review §5.3 定的修法方向：**鸿蒙侧同位置（符号面板按键 + 26 键上滑次级字符）在非 ascii_mode 时改走 `inputKey()` 进 Rime**，让 `symbols.yaml` 的 punctuator/symbols preset 生效。`[`、`'` 多义标点同理。

## 三、对 H-081 修法的直接结论

1. `/` 不需要新增面板分组——安卓版的日常入口就是 **26 键 `h` 上滑**；但符号面板 `()` 组也必须可达（Qoder 追加验收：翻页第 2 页取 `/` 与 `\`）。
2. 修法定稿（与派单一致）：非 ascii_mode 时上滑次级字符与面板键都走 `inputKey()`；英文模式保持 commitText 直出。
3. 翻页口径按 M-059-review2：主区 3 行 + PanGesture 左右滑翻页，一滑一页；`english` 组第 1 页 19 项 + 第 2 页 9 项；不恢复纵向滚动。

## 四、遗留（不阻塞）

- 「上滑 h 出候选」的安卓版**屏上截图**因触摸注入被挡无法采集；若需像素级对照，建议主人在 nova 6 上手工上滑 `h` 打一次 `/szd`（肉眼 5 秒可验）。
- 本轮未动 nova 6 任何输入法设置与用户数据；唯一的交互痕迹是设置搜索页输入了测试字符并已全部删除（DEL×6 + 返回），默认输入法已还原 `com.baidu.input/.ImeService`。

## 附：文件清单

- `w01.xml`：26 键布局 dump（含次级字符表，核心证据）
- `w02-swipe-h.xml`、`w03-main.xml`、`w04-settings.xml`、`w05-kb.xml`、`w06-kb.xml`、`w07.xml`、`w08.xml`、`w09-swipe-h.xml`、`w10.xml`：过程 dump
- `nova-szd-01..08*.png`、`chk.png`、`f1/f2.png`、`frameA/frameB.png`、`pre-h/post-h.png`：截屏序列（触摸/按键通道有效性判定用）