# 给 dyy 的催授权文本（已按主人 10-20 定稿措辞，待主人点头后由 Qoder 在他的 Chrome 里发出）

> **2026-10-22 14:22 已发出（Qoder 在主人已登录的 Chrome 里操作）**
>
> - **邮件**：Gmail 账号 `ri0977@gmail.com` → `douyaoyuan@126.com`，主题
>   「dyyRime 文件授权请求 · 三生输入法（免费五笔输入法）」，正文即本文 §一（含 §一 里那处
>   「鸿蒙 NEXT 一并请示」增补与逐功能文件清单）。页面提示「邮件已发送」，
>   并已核对「已发邮件」列表出现该件（14:22）。截图留痕（仓库外）：
>   `F:\workbuddywork\三生输入法\_sansheng_backup\20261022-dyy-email\04-ready.png`（发送前全貌）、
>   `05-sent-list.png`（已发邮件列表）。
> - **Issue #9 追评**：已发（`ri0977-code commented on Oct 22, 2026`），内容即本文 §二。
> - **Issue #8**：已按 §三 发说明评论并**关闭**（Close as completed），页面上该评论唯一、无重复。
> - 本文下方的 §四 处置表仍然有效：**等回复，不阻塞发版**；主人 10-22 定的路线 A（保留 + 标注）不变。
> - 待办：dyy 若回复，按其 §四 对应行执行；3 日无回复则维持现状继续。
>
> ---

> 2026-10-22 13:3x · Qoder 整理
> 主人 10-22 指令：「issue 你处理，dyy 邮件你发，用谷歌邮箱」。
> 我只在**他定稿的措辞**上做了两处必要增补，都单独标出，其余一字未改：
> ① 补上「鸿蒙 NEXT 版」这个新平台（10-20 发 Issue 时只有桌面版+安卓版，授权范围必须覆盖现在要上架的鸿蒙包，否则等于没批）；
> ② 把「具体文件清单」真的列出来（原邮件说「可以整理成表格发给您」，一次给全，省一轮往返）。

---

## 一、邮件（Gmail → `douyaoyuan@126.com`）

**收件人**：douyaoyuan@126.com
**主题**：`dyyRime 文件授权请求 · 三生输入法（免费五笔输入法）`

**正文**：

```
dyy 您好：

我在维护一个免费开源项目「三生输入法」（Windows 小狼毫 + 安卓 fcitx5），中英互译、智能日期农历、
节日提醒、候选注释、LaTeX 这些功能直接用您 dyyRime 里的 54 个文件（44 个原样、10 个为手机屏幕和
懒加载做了小改），您的 Copyright 注释都保留了。

您的仓库没有 LICENSE，所以发 GitHub 之前想跟您要一句授权：是否允许继续携带并修改？我会在
THIRD_PARTY_NOTICES.md 和「关于」页逐项署名，项目免费不盈利。

条件您定：CC-BY、CC-BY-SA、GPL-3 我都可以照办；如果不允许，回一句我就把这部分功能整体下掉再发。

【增补】最近我们在做 HarmonyOS NEXT（鸿蒙）版，携带的是同一批文件、同样免费，所以一并请示；
如果您只愿意授权其中某几个平台或某几个文件，也请直接说明，我按您的范围来。

附：文件清单（按功能分组，括号内是字节数）

  中英互译        dic_4w.lua / dic_4w_Filter.lua / dic_4w_cn.txt(888KB) / dic_4w_en.txt(2.0MB)
  日期·时间·农历·节气  dateTimeModule.lua(16KB) / dateTime_filter.lua(20KB) /
                  lunarModule.lua(18KB) / lunarjieQiModule.lua(44KB)
  节日事件提醒     eventsListModule.lua(32KB) / eventsList.txt(12KB)
  候选注释        phraseComment_*(4 个文件)
  表情与 Unicode 扩展  phraseExt_*(5 个文件)
  敏感词替换       phraseReplace_*(3 个文件)
  拼音加词/自造词   pinyinAdding_*(3 个文件)
  LaTeX 公式      latex_translator.lua / latexHelp_translator.lua / latexLettersInWubi.lua
  输入环境识别与日志  sysInfo.lua / runLog.lua / socket.lua / luaSocket/
  其它            inputShow_Filter.lua、symbols.custom.yaml、rime.lua（注册表补条目）、
                  wubi_pinyin.custom.yaml（手机端注释长度截断）

  其中 Custom_phrase.txt 与两个 personal.txt、default.custom.yaml 我们已清空成给用户的空白模板，
  不携带您的内容。

具体到每一个文件的比对结果，我可以再发一份逐文件的 md5 对照表给您。

打扰了，谢谢您写出这套配置，我的用户这几年真正受益的是这些功能。

—— 三生输入法 唯一的维护者（GitHub：@ri0977-code，Issue 见
   https://github.com/happyDom/dyyRime/issues/9 ）
```

**发送后必做**：把「已发送」页截图 + 邮件原文另存到
`F:\workbuddywork\三生输入法\_sansheng_backup\20261022-dyy-email\`（仓库外留痕）。

---

## 二、Issue #9 追评（`happyDom/dyyRime`，用主人已登录的 `ri0977-code`）

```
补充一条（2026-10-22）：

1. 我们最近在做 HarmonyOS NEXT（鸿蒙）版，携带的是同一批文件，所以授权范围希望把「桌面 / 安卓 / 鸿蒙」
   三个平台一起算进去；如果只想授权其中一部分，请直接说明，我按您的范围执行。
2. 逐文件清单：44 个字节完全相同、一字未改；10 个有改动（dic_4w.lua 改懒加载、inputShow_Filter.lua、
   latexLettersInWubi.lua、rime.lua 注册表补条目、wubi_pinyin.custom.yaml 手机端注释截断、
   symbols.custom.yaml），另外 Custom_phrase.txt / 两个 personal.txt / default.custom.yaml 已清空成空白模板。
   您的 Copyright (C) 2023 yaoyuan.dou 注释全部保留。
3. 我们已经在 THIRD_PARTY_NOTICES.md 与应用内「第三方声明」页逐项署名并标注「授权申请中」。
   在您回复之前，如果这给您带来任何不便，说一句我就把这些文件整体下掉，不会有任何异议。

（同一封邮件也已发到 douyaoyuan@126.com，两边任一处回复都算。）
```

## 三、Issue #8 处理（误发的空壳）

在 #8 里发一条评论，然后关闭：

```
这条是我 2026-10-20 探测表单时误提交的占位 Issue（正文只有 line1/line2），不是真实请求，请忽略。
正式请求见 #9。抱歉打扰。
```

---

## 四、发出去之后

| 结果 | 我做 |
|---|---|
| 他指定协议 | 协议文本进 `LICENSES/`，`THIRD_PARTY_NOTICES.md` 去掉「授权申请中」，改为「已授权（条件：xxx，回复日期 2026-xx-xx）」，回复截图存仓库外备份 |
| 他泛泛同意 | 按「署名 + 非商业 + 不可再授权」最保守口径写清，标注回复原文与日期 |
| 继续不回复 | 维持主人 10-20 终定口径：**不阻塞发版**，标注「授权申请中」继续分发，剥离预案（`dyy-strip-plan-2026-10-22.md`）随时可执行 |
| 他拒绝 | 执行剥离（P1~P11），并按 `dyy-selfbuild-estimate-2026-10-22.md` §4 的中间态方案补回日期/农历/节气 |

主人 10-22 已定：**路线 A（保留 + 标注）**，所以本轮**不删任何 rawfile**。
