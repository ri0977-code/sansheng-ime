# H-104 对齐复核（独验，15:3x，只读 + 文本比对）

> Qoder 独立复核，**未构建、未签名、未装机、未碰手机、未碰 sign/**。
> 验证对象：提交填进 AGC 的隐私/用户协议（托管版）与**应用内**显示的是否逐字一致。

## 一、取件与口径

- 托管/源版（AGC 要传的那份）：`docs/release/legal/{privacy.html,terms.html}`
- 应用内版（包进 rawfile，由 `LegalPage.ets` 经 `resource://rawfile/legal/privacy.html` 渲染）：
  `entry/src/main/resources/rawfile/legal/{privacy.html,terms.html}`
- LegalPage 顶部注释明确：`Web 组件加载 rawfile/legal/ 下 Qoder 预置的 privacy.html / terms.html`（L4），且 `docUrl()` 映射到上述 rawfile 路径（L37-43）。即**应用内确实是这两份**。

## 二、比对结果

- `diff` rawfile 版 vs docs 版：唯一差异在 L54 的 `<main>` 包装——rawfile 版为 `<main class="inapp">`（应用内嵌、无 nav），docs 版为 `<main><nav>…</nav>`（独立网页浏览用，带站内跳转）。
- 把 wrapper（`<main…>`、`<nav>…</nav>`）与空白归一后逐字符比较：**privacy 正文一致 = True；terms 正文一致 = True**。
- 两份正文关键口径均含：①「输入内容只在本机处理，应用不联网、不上传、不收集个人信息」；②「未声明网络权限（ohos.permission.INTERNET），无法主动访问互联网」；③ 主体「[机主姓名已脱敏]（个人开发者）」、联系邮箱 `ri0977@qq.com`（备用 `ri0977@gmail.com`）；④ 用户词典/自造词只存本机沙箱不上传。与 `LegalPage.ets` 注释「本地渲染、无网络请求（不加 INTERNET 权限）」一致。

## 三、H-155 PASTE 新增的认定（不影响口径）

- 本轮 H-155 新增 `sendEditorAction(PASTE)`（长按 v 粘贴），走宿主编辑框 `sendExtendAction`，**不读剪贴板存储、不上传**；隐私正文「不收集…剪贴板内容」指不偷读/不外传剪贴板，与「用户主动粘贴上屏」不冲突 ⇒ 口径仍成立，无需改文案。

## 四、结论

- **H-104 闭合判据①（应用内版与提交版正文逐字一致）已满足**（差异仅为 presentation wrapper，非内容）。
- 剩 H-104 真正卡点仍是**第 ② 步：AGC 隐私声明"路 B 托管"要主人在 AGC 里点「托管」并把线上链接发回**——届时再用内容闸门第 ⑦ 项对线上抓取的那一份比一次。
- 本次未改任何文件、未要求 CodeArts 动作；仅记录现状以便提交日直接照抄/比对。
