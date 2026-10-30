# H-108 桌面图标：我这侧量到的新证据（并更正我自己先前的两处判断）

> 2026-10-23 01:5x 由 Qoder 写。全程只读：没改 `entry/src/**`、`AppScope/**`、`module.json5`，没构建、没签名、没装机、没碰手机（主人在睡）。
> 触发点：CodeArts 01:15 动了 `module.json5`（未提交），我去看他改了什么，顺着把「桌面到底读哪一层图标」这条查了一遍。

## 一、量到的事实（可复现）

| # | 事实 | 怎么量的 |
|---|---|---|
| 1 | `entry/src/main/module.json5:6` = `"mainElement": "EntryAbility"`；`:30` `icon: $media:app_icon`；`:32` `startWindowIcon: $media:app_icon` | 直接读文件 |
| 2 | `EntryAbility.skills[0]` = `entities:["entity.system.home"]` + `actions:["action.system.home"]` | 直接读文件 |
| 3 | 01:15 那次未提交的改动 = 给 `abilities[0]` 加了 `"metadata":[{"name":"ohos.entry.mainability","value":"true"}]`（`git diff` 只有这一处 +6 行） | `git diff -- entry/src/main/module.json5` |
| 4 | 01:17 的产物把这个改动**打进包里了**：包内 `module.json` 里 `metadata=[{"name":"ohos.entry.mainability","value":"true"}]`、`icon=$media:app_icon`、`app.icon=$media:layered_image` | 解包 `entry-default-signed.hap`（28,288,696 B）读 `module.json` |
| 5 | `entry/src/main/resources/base/media/app_icon.png` = **48×48 / 182 B / alpha 恒 255（整张不透明）**，自基线 `6d504a6`（10-19）没动过 | PIL 量 + `git log -S` |
| 6 | `ohos.entry.mainability` 这个名字**在整个 DevEco Studio 安装目录里 0 命中**（`grep -rl` 全目录跑满，返回空）。SDK 里能查到的 ability metadata 名字是 `ohos.extension.backup`、`ohos.ability.window.*` 这一类 | `grep -rl "ohos.entry.mainability" "/d/DevTools/DevEco/DevEco Studio"` |
| 7 | SDK `@ohos.ability.wantConstant.d.ts`：`:43 ACTION_HOME = 'ohos.want.action.home'`、`:270 ENTITY_HOME = 'entity.system.home'`；字符串 `action.system.home` 在 SDK 的 `ets/api` 里 **0 命中** | grep SDK d.ts |

## 二、由此得出的两条判断（置信度分开写，别混）

**中-高置信度：桌面 tile 读的是「能力层」图标，而那一层至今还是 DevEco 模板蓝方块。**

依据是华为自己两篇文档的说法（页面是 JS 渲染的，`WebFetch` 取不到正文，我拿到的是搜索摘要级证据，所以下面两条**必须靠一张桌面实拍才能定**）：

- 《应用在设备上显示的图标，和应用市场上显示的图标不一致》：**桌面图标由 HAP 包中 `module.json5` 的 `icon` 字段决定**；AGC 里的图标只影响应用市场和「设置」里显示的信息。
- 《配置应用图标和名称》（layered-image）：当 `mainElement` 配的是入口 UIAbility 时，取的是**该入口 UIAbility 配的 `icon`/`label`**。

我们的能力层 `icon` = `$media:app_icon` = 48×48 全不透明蓝方块（事实 5）。主人 22:3x 说「桌面没图标了」，如果他当时看到的是**一个没有任何可辨认图形的蓝方块/灰块**，他说的「没图标」和包内「引用没断链」两件事完全不矛盾——**这条正好把 H-105 和 H-108 合成同一个修法**。

**低置信度（先不动，记着就行）：`actions` 用的是 `action.system.home`，不是 SDK 里 `wantConstant.ACTION_HOME` 的 `ohos.want.action.home`。**
它从基线（DevEco 模板生成）起就是这样，我们从没改过。华为《应用/组件级配置》写的是「要在桌面显示 UIAbility 图标，entities 加 `entity.system.home`、actions 加 `ohos.want.action.home`」。字符串不一致是真的（事实 7），但它到底会不会导致桌面不出 tile，我没有证据，**而且它是「从来没变过」的量**，不足以解释 22:3x 才出现的「没了」。所以：图标那张图换完、桌面实拍还是空的，再考虑这一行。

## 三、更正我自己先前写下的两处（这两条现在别再当依据用）

1. **H-108 里那句「`app.json5:7` / `layered_image.json` / 两张 PNG / `bm dump` 的 `iconPath` 四层全好 ⇒ 不是引用断链」——查的是错的那一层。** 这四层说的都是**应用层（AppScope）**图标，而按上面第二节的文档，桌面 tile 用的是**能力层（module.json5 的 ability icon）**。我当时把「我查到的四层都好」当成了「图标链路都好」，漏掉了被 `EntryAbility.icon` 引用的那张 48×48 模板——那正是 H-105 早就记在案的文件。所以「剩 A/B 两种可能」这个框架本身不完整：还有 **C：桌面 tile 一直在，但画的是 DevEco 蓝方块**，这个假设不需要「分层图标合成失败」这种玄学，也不需要重装。
2. **`docs/evidence/2026-10-22/m6-content-gate-recheck.md` 第 109 行「启动窗口显示的是蓝方块，和桌面图标（三条键帽）不是一个图形」——两句都是我按引用链推出来的，不是拍到的。** 我们的证据里**从来没有一张拍到桌面 tile 的照片**（`q-2330-home.jpeg` 拍到的是短视频，`q-0024-home.jpeg` 是真实桌面第 1 页、本页没有三生；`probe-now.jpeg` 核实是 21:49 的锁屏地球屏）。下次引用这条时按「推断」处理，别按「实测」。

## 四、给 CodeArts 的那一下（零代码，等 H-106 之后同批做）

```
copy docs\release\store\icon\gen-appicon-512.png  entry\src\main\resources\base\media\app_icon.png
```

- 引用名 `$media:app_icon` 不变，**不动 `module.json5`、不动代码**；
- 我按闸门 ⑨b 的判据算过：512×512 / 15,931 B ⇒ 不再满足「(边长≤64 或 <2048 B) 且全不透明」⇒ **⑨b 由 WARN 转 PASS**（同判据早做过双向验证：48×48/182 B 坏样本报红，键帽图样本报绿）；
- 用 512 不用 216：桌面 tile 在高 DPI 上会放大，216 会糊；包内本来就会被 hvigor 降采样到 512，体积差 ~11 KB 可忽略；
- **同时把 01:15 加的 `metadata: ohos.entry.mainability` 撤掉**——它在 SDK/DevEco 全目录 0 命中，基本确定是个不生效的猜测，留着下次排错还要多排除一个变量。撤销它不影响 H-106。
- 商店上传图仍然用 `icon/layered/preview-216.png`，别拿 `icon/appicon-216.png`（那是旧四宫格的合成图）。

**顺序照死**：H-106（收起键）先交付验收 → 这一条随同批包 → 桌面实拍由我在解锁的 Mate 80 上拍，**主人在睡的时候我不碰手机**。
