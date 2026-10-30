# 「单机应用 / 本机处理不联网」独立实测复核（M6 ③ · 提审口径的证据）

> 2026-10-22 14:3x · Qoder · 触发：CodeArts 在 `M-068-re` 里代主人承诺「当前代码已满足无网络权限/无网络请求」。
> 按验收回路，**对方结论我自己量一遍**。本轮全部是静态实测，不需要真机，不涉及任何代码改动。
> 用途：AGC 提审时「单机应用免备案」（D-018）与应用内《隐私政策》第 3 节「未申请联网权限」这两处申报口径的支撑材料。

## 一、权限声明（逐 module.json5 解析，不是人眼扫）

| 文件 | `requestPermissions` | 实测内容 |
|---|---|---|
| `entry/src/main/module.json5` | 有 | **只有** `ohos.permission.VIBRATE` |
| `fanxing_rime_har/src/main/module.json5` | 无 | 0 条 |
| `fanxing_rime_har/src/ohosTest/module.json5` | 无 | 0 条（测试壳，不进包） |

⇒ 全工程 **0 处** `ohos.permission.INTERNET` / `GET_NETWORK_INFO`。没有网络权限时系统层面就建不了 socket，这是「不联网」最硬的一条证据。

## 二、ArkTS / C++ 侧网络调用

命令：在 `entry/src` 内按 `@ohos.net|createHttp|XMLHttpRequest|http.|socket.|WebSocket|url.URL|fetch(` 检索（`.ets/.ts/.cpp/.h`）。

结果：**1 处命中，且是注释文字** —— `entry/src/main/ets/engine/RimeDataInstaller.ets:145`，内容是解释「真模块（`socket.lua` 要加载 luaSocket DLL……）还在逐个去 Windows 化」。
⇒ ArkTS 与 native 侧 **无任何网络 API 调用**，CodeArts 的承诺成立。

## 三、rawfile 里的 `socket.lua`（唯一需要说清楚的点）

包里确实带了一个叫 `socket.lua` 的文件，也在 `rawfile/rime/lua-files.txt` 清单里（44 个 lua 文件之一），所以**必须给出它惰性的证据**，否则「全仓无网络」这句话不严谨：

1. `rawfile/rime/lua/socket.lua` 是 **M4 安全桩**（文件头自述：桌面版 `require 'socket.core'` 加载 Windows DLL；鸿蒙无 musl 版 luaSocket，且「本机处理、不联网」产品上就不该做）。第 22 行 `M.socketEnable = false`（注释「恒关」），`dns.*` 只返回 `nil`。
2. 唯一 `require` 它的是 `lua/dynamicPhrase_Filter.lua:16`（`pcall`），第 19–20 行立刻把开关读成 `socket.socketEnable` ⇒ 第 85 行 `if socketEnable then`（那条按公网 IP 出动态短语的路径）**永不进入**。
3. 即使误进：无 `INTERNET` 权限，系统拒绝建 socket。

⇒ 结论：`socket.lua` 是**从安卓数据目录带过来的惰性数据文件**，不是联网能力。三层（权限 / 恒关开关 / 唯一引用点被关）互锁。
**处置：不动它。** 删文件会牵动 `dynamicPhrase_Filter` 的 `pcall` 与 `lua-files.txt` 清单、要升 `DATA_VERSION` 重新出词库、重新签名 —— 收益为零、风险不为零。这条与「rawfile 冻结」（D-016 / M-067）一致。

## 四、应用内法律文本（Web 渲染，最容易被忽略的联网面）

`entry/src/main/resources/rawfile/legal/privacy.html`（8,073 B）与 `terms.html`（7,195 B）：

- 按 `(https?:)?//…` 检索外链：**0 命中**（唯一像 URL 的是 CSS `@media (max-width: 640px)`）。⇒ 页面自包含，`Web` 组件加载 `$rawfile` 不产生任何网络请求，也不会因无网权限而白屏。
- 内容一致性：`privacy.html` 第 109 行明写「未申请联网权限（`ohos.permission.INTERNET`），无法主动访问互联网，因此不存在把输入内容上传网络的路径」—— 与本文件 §一/§二 实测一致。
- 新鲜度：源 `docs/release/legal/privacy-policy.md` / `user-agreement.md` 时间戳 10:53，渲染出的 html 10:54 ⇒ **html 不比 md 旧，无漂移**。
- 联系方式：两文件均含 `ri0977@qq.com`（主）/ `ri0977@gmail.com`（备），无「草案」「待填」残留。

## 五、顺带查出我自己两处记账错误

1. **H-053 其实 10:55 就 CLOSED 了**（主人 09:5x 给了对外邮箱，`4b7d196` 落地并同步 4 处文档 + 4 个 html）。我在 13:45 与 14:2x 的 `PROGRESS.md` 抬头和 `OWNER-ACTIONS.md` 第 3 条里仍写「等主人回 H-053」，等于**向主人重复索取一个他三小时前就答过的东西**。已在本轮全部划掉。教训：**每次写「等主人 X」之前先 grep `docs/ISSUES.md` 看 X 是不是已经 CLOSED**，别凭本轮记忆。
2. **「锁屏判据 = JPEG 字节数」不可靠**。13:50 我拿 `snapshot_display` 的 164,092 B 判「已解锁」，14:34 同一台锁屏实测 157,398 B（历史锁屏基线 156,411 B）——两个数只差 4%，锁屏与解锁态**根本分不开**。已改为：判状态必须**把截图读出来看**，字节数只当旁证。

## 六、验收结论

M6 ③ 的「本机处理、不联网」申报口径，**静态证据链完整**：权限 0 网络、ArkTS/native 0 网络调用、rawfile 唯一网络相关文件恒关且无引用生效、应用内法律页 0 外链。
**仍未闭合的是运行时证据**：需要真机抓一次「输入法工作全程无网络请求」的旁证（`hilog` 无 socket 报错 / 无网络权限弹窗），以及商店截图重拍 —— 两项都卡在 Mate 80：**14:34 又回到锁屏**，且 14:2x 实测**当前默认输入法是百度输入法**（见 `docs/ISSUES.md` H-086）。

**本轮改动文件**：只新增本文件 + 更新 `docs/ISSUES.md`（H-086）、`docs/MAILBOX.md`（M-071）、`docs/PROGRESS.md`、`docs/OWNER-ACTIONS.md`、`docs/RELEASE-READINESS.md`。**未动 `entry/src/**`、未动 rawfile、未动签名。**

---

## 七、2026-10-22 19:2x 复测（CodeArts 新增设置页之后）

**为什么要复测**：14:3x 那次审计之后，工作树新增了 `SettingsModels.ets`（16,500 B）、`SettingsPage.ets`、
`SettingsCategoryPage.ets`（12,505 B），首页也改过。**新增代码是"不联网"声明最容易被动摇的地方** —— 加个
"检查更新"或"词库在线更新"的念头就会引入网络面。所以按同一口径重跑一遍。

| 检查项 | 方法 | 结果 |
|---|---|---|
| 三个 `module.json5` 的权限 | 逐个解析 `requestPermissions` | `entry` 只有 `VIBRATE`；`fanxing_rime_har` 与其 `ohosTest` **无任何权限** ⇒ 仍只有 `VIBRATE` |
| 包内 `module.json` 实测 | 解包 16:50 的 unsigned HAP 读字段 | `['ohos.permission.VIBRATE']`，**`INTERNET` 0 命中、`GET_NETWORK_INFO` 0 命中** |
| 新增 5 个文件的网络 API | 检索 `http` / `fetch` / `@kit.NetworkKit` / `request` / `Web(` / `socket` | **5 个文件全部 0 命中** |
| 敏感能力 API | 检索 `pasteboard`（剪贴板）/ `contacts` / `geoLocation` / `camera` / `@kit.SensorServiceKit` | **只有 `KeyboardIndex.ets:112` 的 `vibrator`（对应唯一权限 VIBRATE）**；剪贴板/通讯录/定位/相机 **0 命中** |
| `entry/src/main/cpp` 与 HAR | 检索 `socket(` / `connect(` / `curl` / `http` | 只有 OpenCC 头文件里的 Apache 许可证 URL 注释与一处 GitHub issue 链接注释，**无网络调用** |

⇒ **结论不变：单机、不联网、不收集**。新增的设置页三件套**没有**引入任何网络或敏感能力。
本结论与包内实测（权限字段）一致，可作为 AGC「隐私标签：全部不收集」与「单机应用免备案」的依据。

**这一项以后放在哪**：每次出提审包前，除了 `check_app_content.py` 的 11 项，**再跑一次本表的检索**（可以脚本化），
因为"新增了代码"是唯一会让这条声明失效的路径。

