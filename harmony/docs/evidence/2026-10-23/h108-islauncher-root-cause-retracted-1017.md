# H-108 根因撤回：`isLauncherApp=false` 不是「桌面没有入口」的判据（10:1x 实测）

> 谁：Qoder · 何时：2026-10-23 10:1x · 触发：CodeArts 的 W-193（09:12）把 H-108 的根因写成
> 「`bm dump` 显示 `isLauncherApp=false`／`isLauncherAbility=false` ⇒ 桌面根本不渲染该图标」，
> 我在 09:2x 的 W-194／H-108／`OWNER-ACTIONS`／`ROADMAP` 里**照抄了这个结论并讲给了主人**。
> 本轮做同级对照后：**该结论不成立，是我没核就转述**。下面全部是实测量，不是推断。

## 一、对照实验（只读 `hdc shell bm dump`，没碰屏幕、没装机）

对照组选 `com.huawei.hmos.notepad` —— 华为自带记事本，桌面上一定有图标，是「有 launcher 入口」的正面样本。

| `bm dump` 字段 | com.sansheng.ime（我们的包） | com.huawei.hmos.notepad（桌面确有图标） | 判读 |
|---|---|---|---|
| `isLauncherApp` | **false** | **false** | 两台相同 ⇒ 这个字段**不能**区分「桌面有没有入口」，W-193 的因果不成立 |
| `isLauncherAbility` | **false** | **false** | 同上 |
| `bundleType` | 0 | 0 | 同类（普通应用，非原子服务） |
| `isSystemApp` | false | true | 唯一实质差别是「系统预装」，与桌面入口无关 |
| `appDistributionType` | `"none"` | `"os_integration"` | 预装渠道差异 |
| `installSource` | `"unknown"` | `"pre-installed"` | 我们是 hdc 侧装 |
| EntryAbility `skills` | `entities=[entity.system.home]`、`actions=[action.system.home]` | **同一写法**（另多一条 business_and_privacy_statement） | ⇒ `action.system.home` 这个串**不是**问题（我上一轮列的「低置信度候选：应改成 `ohos.want.action.home`」也一并撤回，记事本用的就是 `action.system.home`） |

⇒ **H-108 回到「只有一条观测：桌面上没拍到它」，根因未定。** 之前所有「根因已确定」的写法（含我给主人的那句）都要作废。

## 二、桌面到底有没有，目前唯一的实拍是什么

`docs/evidence/2026-10-23/q-0024-home.jpeg`（00:23 实拍，HOME 后落到的真实桌面第 1 页）：
本页**只有 4 个文件夹**（工具／社交与生活服务／出行与工具／生活服务与社交）＋ 底部 dock 5 个，
页码指示器显示共 **6 页**，**第 2–6 页从没拍过、4 个文件夹从没展开**。
⇒ 这张图只能证明「第 1 页没有单独的三生 tile」，**不能**证明「应用没有桌面入口」——
华为桌面会把新装应用自动归进分类文件夹，「在文件夹里」和「没有图标」在这张图里长得一模一样。
这一格是 H-108 至今真正的证据缺口，只能靠**主人解锁后翻完 6 页／展开文件夹**（或授权我逐页 dump）补上。

## 三、10:00 那份交付改的是哪一层图标（解包实测，不是看提交说明）

包里有**两条互不相同的图标通道**，这次只动了第二条：

| 通道 | 来源 | 10:00 包里的实际内容 | 谁在用 |
|---|---|---|---|
| 应用级图标 | `AppScope/app.json5:7` `icon = $media:layered_image` | `background.png` 6,034 B（蓝底，主色 RGB 30,80,192）＋ `foreground.png` 8,884 B（白键帽）⇒ **还是蓝底三条键帽** | 清单语义上的「应用图标」＝桌面 tile 与 AGC 比对的那一层（**这句是规范判读，不是实拍**） |
| 能力级图标 | `entry/src/main/module.json5` EntryAbility `icon`／`startWindowIcon` = `$media:app_icon` | `app_icon.png` **32,629 B／512×512／黑底金**（sha256 前 12 位 `57f4e3e559c4`，主色黑 0,0,0 ＋ 金 255,223,114） | Ability 自身与启动窗那一层 |

⇒ **结论：这次换图不会把桌面 tile 变成黑底金。** 若主人要的是「桌面与商店都换成黑底金」，必须连应用级 `AppScope` 那两层一起换（`AppScope/**` 与 `module.json5` 按分工表都在 CodeArts 名下），然后我这边重出 AGC 上传件 `icon/layered/preview-216.png`；
若只换能力层，包内会出现**两套品牌图**，AGC「上传图标与包内一致」这一条反而更容易被挑。
在主人点头之前，商店上传件**继续按现状（蓝底键帽）准备**，因为它对得上现在包里的应用级图标。

## 四、这一轮的构建与闸门（独立复现，不是复用他的产物）

| 项 | 实测 |
|---|---|
| 他的交付（W-197） | unsigned **28,218,991 B**／signed **28,322,730 B**，未标模式 |
| 我第一次跑 `scripts/build.ps1` | **不算独立构建**：hvigor 报「15 executed／**18 up-to-date**」，产物 mtime 仍是他的 10:00:53 ⇒ 只是把他那份文件又确认了一遍。发现后作废重来（这条写下来是因为它是个会反复踩的坑：**增量构建「绿」不等于我构建过**） |
| 强制全量重建 | 先把 `entry/build` 整棵移到 `F:\qoderwork\_audit_tmp\2026-10-23\build-tree-1000`（没删，可回退），再 `build.ps1` ⇒ **32 executed／1 up-to-date**，产物 mtime 10:12:50、83 条 ZIP 条目时间戳 10:12:48–50 |
| 字节数比对 | 我的 debug unsigned **28,218,991 B ＝ 他报的 unsigned**（只比字节数，不比 hash） |
| 内容闸门 | `check_app_content.py` 对该 HAP：**15/16 通过、阻断 0**；唯一 `[WARN] 10` 是探针页（H-098，装进 `.app` 时仍是阻断） |
| 设备侧（只读） | `bm dump` 的 `updateTime` = 1792720874228 ⇒ **10:01:14**，与 signed 产物 10:00:58 相差 16 秒 ⇒ 是他自己签并装的；我**没有再装**（同一个 HAP 不重复安装）、没签名、没点屏幕 |

## 五、顺带量到的两件（都归 CodeArts 的文件）

1. **H-145 仍未闭，且 HEAD 依旧编不过**：`73d7d07` 只提交了 1 个文件（`app_icon.png` 15,931→32,629 B）。
   `git show HEAD:.../KeyboardIndex.ets` 里 `hideKeyboard()` 调用 **1 处**，`git show HEAD:.../KeyboardController.ets` 里定义 **0 处**
   （工作区那份有 2 处，即 +17 行仍未提交）⇒ 检出 HEAD 仍然构建失败，交付字节仍然指不回任何提交。
   工作区现在 **9 改 + 4 新 = 13 项**未提交（09:4x 我记的 15 项里，`app_icon.png` 与 `KeyboardIndex.ets` 已被 d5fbada／73d7d07 收走）。
2. **H-090 一行没摘**：`main_pages.json` 仍是 8 项（含 `pages/SettingsPage`、`pages/SettingsCategoryPage`），
   `Index.ets:79` 的 `openSettings()` 全文只有这 1 处出现＝**定义存在、0 个调用者**，三个 Settings 文件（16,500／12,505／3,948 B）还在树里。
   这条是 1.0.0 的既定裁决，不是新需求。
3. **候选栏那个 ▼ 的注释与代码相反**（`KeyboardIndex.ets:1005` 注释写「短按展开/收起候选网格，长按折叠键盘」，
   代码是 `onClick → hideKeyboard()`、`LongPressGesture → setExpanded(!expanded)`，与 d5fbada 提交说明「单击折叠」一致）。
   ⇒ 行为按提交说明是故意的，注释是旧的；改注释一行即可，别改行为（行为要不要这样，是主人和你在布局那条线上定的事）。

## 六、我这一轮错在哪（写下来是为了下次不再犯）

- **把 W-193 的 `isLauncherApp=false` 当结论转述**，还写进了给主人的那一节。它的错法很典型：
  一个字段看着像因果、又只有「我们这一侧」的数，**没有对照组**。以后凡是「系统字段 ⇒ 系统行为」的说法，
  必须同时量一个「行为正常」的对照包（这次是记事本，一条命令就够）。
- **第一次构建差点当成独立构建**：日志里 `18 up-to-date` 已经提示了，是我先看「BUILD OK + 字节数一致」而没看 mtime。
  以后独立验收一律先移走 `entry/build`（或核对产物 mtime 晚于源码 mtime），否则「字节对上」这句话不成立。
