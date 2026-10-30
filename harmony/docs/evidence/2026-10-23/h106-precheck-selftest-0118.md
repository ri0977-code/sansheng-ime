# H-106 交付前自检工具 `scripts/h106_precheck.py` —— 三向自测证据

时间：2026-10-23 01:18（Mate 80 未装机，全程只读，未点屏、未构建）
作者：Qoder（审核验收侧；`entry/src/**` 不由我改）

## 为什么要这个工具

H-106（底栏常驻收起键）已经返工三四轮，失败模式每次同一个：**改了但没改全**。
以前我只能等产物装机后用眼睛看，等于每轮消耗一次真机安装（主人明确说过不要反复装机）。
现在把判据前移到「源码结构 + 交付形式」，一条命令判完，CodeArts 自己先跑，我验收跑同一份 —— 判据一致，不再互相猜。

## 判据与分级

只有 BLOCK 级决定退出码。这是刻意设计：历史上 `check_app_content.py` 曾把 ⑨b/⑩ 写成 WARN，
结果 `.app` 带着模板启动图照样打印 `RELEASE OK`（H-115）；反过来若把提示级算进阻断，
夜间值守会永远「不可测」，闸门同样失效。所以两条都要防。

- BLOCK：`BottomBar()` 里**每一个并列 Row** 都要有 `hideKeyboard`（这一条就等价于「symbol 分支和字母分支都要加」）
- BLOCK：功能键 `sym123 / lang / space / dot / enter` 不能被删（主人铁律：宽度不够只许减 margin/字号）
- BLOCK：底栏不得直接调 `hidePanel/destroyPanel/setUiContent/panel.show/panel.hide`（面板 API 归控制器）
- BLOCK：交付形式 —— mtime 静置 ≥120s、已 checkpoint 提交、WIP/MAILBOX 有记账行且带 unsigned 字节数
- WARN：候选栏 ▼（`chevron_down`）是否仍在 —— 版本结构不同，只提示

## 三向自测（证明判据既能放行也能抓错，不是恒 PASS/恒 FAIL）

### A) 已知好样本 = `git show HEAD:` 的 `KeyboardIndex.ets`（H-085 那版）

```
  [OK  ] 结构:找到 BottomBar()        L1793..L1959
  [OK  ] 结构:底栏 Row 解析             并列 Row 1 个：单栏
  [OK  ] 底栏[单栏]有收起键               调用 keyboardController.hideKeyboard()；layoutWeight 求和 9.9 / 7 个键
  [OK  ] 功能键未丢失:sym123 / lang / space / dot / enter
  [OK  ] 底栏未直接操作面板 API            只通过 hideKeyboard()
  [OK  ] 候选栏 ▼ 仍在                 全文 chevron_down 3 处 / hideKeyboard 1 处
结论：BLOCK 全过，可以进入独立构建（阻断 0 项 / 提示 0 项）
exit=0
```

HEAD 那版是**单栏**（还没拆 symbol/字母分支），含收起键共 7 键、权重求和 9.9 —— 这就是「加一个 0.7 权重键放得下」的实测基准。

### B) 已知坏样本 = 当前工作树（2026-10-23 01:08:50 版）

```
  [OK  ] 结构:找到 BottomBar()        L1959..L2210
  [OK  ] 结构:底栏 Row 解析             并列 Row 2 个：symbol, else
  [FAIL] 底栏[symbol]有收起键           当前求和 9.4 / 6 个键
  [FAIL] 底栏[else]有收起键             当前求和 8.8 / 5 个键
  [OK  ] 功能键未丢失 ×5
  [OK  ] 底栏未直接操作面板 API
  [OK  ] 代码已静置 >=120s             mtime 距今 199s
  [FAIL] 已做 checkpoint 提交         工作区状态: M entry/src/main/ets/pages/KeyboardIndex.ets
  [OK  ] WIP/MAILBOX 有记账行         （最新仍是我自己 01:07 的 W-146/M-107，不是他的交付行）
  [FAIL] 记账行含 unsigned 字节数
结论：先补齐再报交付，不要装机（阻断 4 项 / 提示 0 项）
exit=2
```

⇒ 结论：**CodeArts 01:08 的编辑不是 H-106 交付**（两栏都没有收起键、没提交、没报字节数），我没有构建也没有装机。

### C) 半对样本 = 只在字母分支注入 `hideKeyboard`（夹具在仓库外 `_audit_tmp`，没进工作树）

```
  [FAIL] 底栏[symbol]有收起键           ← 只有这一栏报错
  [OK  ] 底栏[else]有收起键             调用 keyboardController.hideKeyboard()
结论：先补齐再报交付，不要装机（阻断 1 项）
exit=2
```

⇒ 判据是**逐栏**生效的，不是全文 grep 一刀切；这正是主人描述的「一会儿能折叠一会儿不能」在源码里的形状。

## 顺带纠正我自己一句会害他返工的断言

我 01:06 写进 H-106 的「`kbHidden` 只写不读 ⇒ 第三拍必然失败，需要接读侧」**不成立**，已作废：

- `KeyboardController.ets:135-144` —— `ability.on('inputStart')` 里**无条件**调 `this.showPanel()`；
- `:232-241` —— `showPanel()` 就是 `this.panel.show()`（面板不存在才 `createPanel()`），中间**没有任何 `kbHidden` 判断**；
- `:291-300` —— `hideKeyboard()` 用 `panel.hide()` 不销毁面板，`:290` 的注释本身就写着「光标变化时自动弹回」。

所以 `kbHidden`（`:74`，4 处赋值 0 处读）是**死状态**，属于清理项而不是缺陷成因。第三拍「收起后点同一输入框键盘回来」
成不成立取决于**平台是否在同域同焦点的重爱上再次派发 `inputStart`**，这是真机行为 —— 我上机实拍，
不拿它当静态判据逼 CodeArts 改控制器。M-108 已明写「这轮 `KeyboardController.ets` 一行都不要碰」。

## 交付判据（下一次我构建/装机的唯一入口）

`python scripts/h106_precheck.py` 退出码 0 + mtime 静置 ≥120s ⇒ 我才跑独立构建，
再拿他的 unsigned 字节数逐字节比对，一致才 `sign.ps1` + `install.ps1 -Target 7GL0226408083897`，
装机后跑 16 项内容检查（裸 HAP 期望 14 PASS / 阻断 0），然后才是真机 6 项。
详见 `docs/release/h106-collapse-key-acceptance.md`。
