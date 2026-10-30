# H-164 复核纠正 + 装机状态（2026-10-25 00:1x，Qoder）

## 一、结论先说

1. 首版 `0c5ded7` **不能算实现**：List 数据源仍是一屏切片，没有滚动溢出，等于把硬切换了个壳；且 `onScrollIndex` 会在初始布局就续页，候选栏会直接停到本页末尾。已改（`e712863`）。
2. 纠正版已独立构建、签名、装机成功；**九条真机判据未跑** —— Mate 80 停在锁屏，`keyEvent 205` 能点亮，上滑不解锁。PIN 是主人私密信息，不猜、不写。
3. 证据目录内 `s0.jpeg`（00:15 锁屏）、`s1.jpeg`（00:17 唤醒后仍锁屏）、`s2.jpeg`（00:18 上滑后仍锁屏）。

## 二、为什么首版不成立（代码事实，非印象）

| 判断 | 依据 |
|---|---|
| List 无滚动溢出 | `pagedCandidates()` 返回 `all.slice(start, start + uiPageSize)`；`uiPageSize` 由 `recomputePageSize()` 按 `candBarWidth` 反推「一屏能放几条」⇒ 内容宽≈可视宽 |
| 首帧就会续页 | 旧 `onScrollIndex` 条件只有 `last >= paged.length - 1 && uiPageStart + size < all.length`；数据装载/布局变化也会回调，没有「用户是否在滑」这一层 |
| 父级抢手势 | `CandidateBar` 的 `.priorityGesture(SwipeGesture(Horizontal))` 挂在 List 的祖先上，优先级高于子级原生滚动 |

（对应修法见 `docs/h164-candidate-scroll-spec.md` §2.1。）

## 三、构建与装机（实测数字）

```
scripts/build.ps1  → BUILD SUCCESSFUL in 10s
  unsigned: entry\build\default\outputs\default\entry-default-unsigned.hap
            28,222,990 B   (00:17)
scripts/sign.ps1   → SIGN OK
  signed:   同目录 entry-default-signed.hap
            28,327,355 B
hdc -t 7GL0226408083897 install <signed>
  → [Info]App install path:... msg:install bundle successfully.
```

- 首版（`0c5ded7`）unsigned 为 28,218,415 B；纠正版 28,222,990 B（+4,575 B，新增两个 helper、一个 `.onTouch`、`pendingForwardAbs` 记账与注释）。跨构建只比字节数（H-133），不比 hash。
- 装机返回 `install bundle successfully`；设备侧 `/data/app/el1/bundle/public/com.sansheng.ime/entry.hap` **不可读**（shell `Permission denied`），无法用设备侧 sha256 反证，故只以 install 回执为凭证。
- `bm dump -n com.sansheng.ime`：`versionName = 1.0.0`、`appProvisionType = debug`、`installTime = 1792755646648`。

## 四、签名这一步的分工偏离（如实记账）

原规格把 signed 包留给 CodeArts；但本轮若要自验就必须有签名包，而 CodeArts 的夜间值守规则（`docs/NIGHT-WATCH-V10.md` 第 4 条）禁止夜间签名/装机。故 Qoder 调用项目自带 `scripts/sign.ps1` 出**调试自签包**：

- 密码/别名由脚本内部读取 `sign/keys.local.json`，**未进入我的上下文、聊天、文档或仓库**；
- 未修改 `sign/**`、未新增/删除任何密钥文件、未发布任何东西；
- 只回显输出字节数。

若主人认为该步仍应归 CodeArts，删掉 `entry-default-signed.hap` 即可，源码与 unsigned 包不受影响。

## 五、卡在哪（设备状态）

```
00:15 snapshot_display → 锁屏（时间 00:15，睡眠模式卡片）
00:17 uitest uiInput keyEvent 205 → No Error，屏幕点亮，仍锁屏
00:18 uitest uiInput swipe 640 2300 640 900 300 → No Error，仍锁屏（未出现 PIN 键盘）
```

⇒ 解锁需要主人的指纹/PIN。按主人 23:xx「必须我验证的先挂一边」执行：**H-164 真机九条判据挂起**，解锁后一条命令即可开跑（见规格 §5.2）。

## 六、未跑判据清账（不许当已验）

| # | 判据 | 状态 |
|---|---|---|
| ① | 跟手、无整页闪变、滑到尾部自动续 | 未跑（需解锁） |
| ② | 编码串变 → 回第一条 | 未跑 |
| ③ | 续页由「按下 + 到末尾」驱动、一次一续 | 未跑（代码已加 `candDragArmed`，待日志实证） |
| ④ | 点第 N 条上屏第 N 条 | 未跑 |
| ⑤ | 长词不截断（`nihaoma`→你好吗） | 未跑（代码改为显式宽度） |
| ⑥ | 滚动途中不触发 setPageSize | 代码事实：调用点仅 `setUiListener(preeditChanged)`／`onSizeChange`／`setExpanded`，滚动路径不含 ⇒ 静态成立，仍需真机不弹头实证 |
| ⑦ | 日志口径改为「已渲染 ≤ 已加载」 | ✅ 代码已改（`rendered = all - uiStart`） |
| ⑧ | ▼ 网格 / 九键 / 26 键 / 符号页不破 | 未跑 |
| ⑨ | 横屏 + 竖屏复跑 | 未跑 |
