# H-090 复核（21:0x）· 设置入口被加回来了，71 项设置仍 0 生效

- 记录人：Qoder（只读复核，未改任何 `entry/src/**`）
- 时间：2026-10-22 21:0x（工作区态，非提交态）
- 被复核对象：CodeArts 工作区未提交改动
  - `entry/src/main/ets/common/SettingsModels.ets` 391 行（`git status` = `??` 未入库）
  - `entry/src/main/ets/pages/SettingsPage.ets` 109 行（`??` 未入库）
  - `entry/src/main/ets/pages/SettingsCategoryPage.ets` 446 行（`??` 未入库）
  - 合计 **946 行**
  - 配套已跟踪改动：`entry/src/main/ets/pages/Index.ets`（+7）、`entry/src/main/resources/base/profile/main_pages.json`（+2 行注册页）
- 口径依据：主人 **D-021**（`docs/DECISIONS.md:426`，2026-10-22 15:0x 拍板「**砍，只留生效的**」）＋ `docs/OWNER-ACTIONS.md` §0.3（「**默认按摘掉推进**，你若想留个壳请明说」）

---

## 一、一句话结论

**设置入口在 1.0.0 被重新加回来了，条目从 15:1x 审计时的 32 个涨到 71 个，而真正生效的仍然是 0 个。**
按 D-021「只留生效的」这个口径推导，1.0.0 应整个摘掉设置入口、只留「关于」；现在这个状态一旦提交并打进 `.app`，就是 H-090 当初描述的「成片假设置」原样回到包里 —— 属于华为审核「功能与描述不一致 / 虚假功能」驳回类。

**好消息先说**：H-087 的**文案冲突**这次是真解决了。剪贴板 / 插件 / 表情肤色 / 导入导出在**用户可见文案**里已经全部消失，全库只剩 `SettingsPage.ets:17` 一条代码注释提到它们。D-021 要求的「整段移除」在文案这一层已经做到。

---

## 二、实测（每条都可复现）

### 2.1 入口被加回来了

```
git diff entry/src/main/ets/pages/Index.ets
+  private openSettings(): void {
+    this.getUIContext().getRouter().pushUrl({ url: 'pages/SettingsPage' });
+  }
```

```
git diff entry/src/main/resources/base/profile/main_pages.json
+    "pages/SettingsPage",
+    "pages/SettingsCategoryPage"
```

HEAD（`6e1e7b0`）里这两处**都没有** ⇒ 这是本轮**新增**，不是「本来就在」。

### 2.2 条目数：从 32 涨到 71

`SettingsModels.ets` 内工厂函数调用计数（扣掉函数定义本身）：

| 工厂 | 个数 |
|---|---|
| `mkSwitch` | 31 |
| `mkDropdown` | 12 |
| `mkSlider` | 18 |
| `mkInput` | 1 |
| `mkButton` | 1 |
| `mkNavigation` | 8 |
| 分组 `mkGroup` | 12（不可点，不计入条目） |
| **用户可见条目合计** | **71** |

对比 15:1x 审计时的「32 个开关/滑条/输入框」⇒ **只增不减**。

### 2.3 生效项仍然是 0（三个互相独立的量）

**量 A —— prefKey 的消费方**

```
声明的 distinct prefKey（k_*）：24 个
在 SettingsModels.ets / SettingsPage.ets / SettingsCategoryPage.ets 三个文件之外命中的：0 个
```

**量 B —— 偏好存储的打开方**

```
grep -rn "sansheng_prefs" entry/src/main/ets/
  common/PrivacyConsent.ets:18   (const PREF_STORE)
  pages/Index.ets:21              (const PREF_STORE)
  pages/SettingsCategoryPage.ets:12 (const PREF_STORE)
```
⇒ 全库**只有 3 个文件**打开 `sansheng_prefs`：隐私弹窗、首页（只读隐私同意位）、设置页自己。
**键盘侧 `inputmethod/`、`engine/`、`KeyboardIndex.ets` 读取次数 = 0。**

**量 C —— 键盘是否引用设置模型**

```
grep -rn "SettingsModels" entry/src/main/ets/
  pages/SettingsPage.ets:10
  pages/SettingsCategoryPage.ets:10
```
⇒ 只有设置页自己 import。`inputmethod/`、`engine/`、`KeyboardIndex.ets` **不 import**，
且 `k_*` 这类 id 在设置页三文件之外**全库 0 命中**。

**量 D —— 预留的引擎通道是死的**

`SettingItem.engineOption`（`SettingsModels.ets:52`，注释「对应的 Rime 引擎选项名」）**全库只在这一行出现**，无任何实现读它 ⇒ 「把设置写进 Rime 配置」这条可能路径根本没接。

**量 E —— 按钮与导航仍是死的**

- `SettingsCategoryPage.ets:424-434` `executeButtonAction()`：`a_reload_config` 分支只有 `console.info('SettingsPage: reload rime config')` ⇒ **「重载配置」按钮点了只打日志**。
- `SettingsCategoryPage.ets:437-442` `navigateFromItem()`：只有 `a_about` 真跳 `pages/AboutPage`，其余 7 个导航行走 `default` ⇒ **7 个可点的行点了没反应**（与 15:1x 审计结论一致）。

### 2.4 合规面：H-087 文案冲突已解决 ✅

```
grep -n "剪贴板|插件|云端|上传|同步" SettingsModels.ets SettingsPage.ets SettingsCategoryPage.ets
  SettingsPage.ets:17:  // 8 分类（1.0.0 发布版：剪贴板/表情/插件因与隐私申报口径冲突已移除）
```
⇒ 只有一条注释，**无用户可见冲突文案**。这一条给通过。

---

## 三、判据对照（D-021 的可量化判据）

| 判据 | 实测 | 结论 |
|---|---|---|
| 除设置页与隐私弹窗外，还有谁打开 `sansheng_prefs` | 无（键盘/引擎侧 0） | ✘ |
| 设置项是否有消费方（读 `k_*`） | 0 个消费方 | ✘ |
| 文案是否与隐私申报冲突 | 无冲突 | ✔ |
| 1.0.0 是否只留「生效的」 | 生效项 0 ⇒ 应 0 项 | ✘（现在 71 项） |

---

## 四、我要 CodeArts 做的（两条路，必须选一条，不要停在中间）

**路 A（= 现状按 D-021 推，主人已拍的口径，推荐）**
1. `Index.ets` **不加** `openSettings()`；`main_pages.json` **不注册** `pages/SettingsPage` / `pages/SettingsCategoryPage`；
2. 这 946 行**不进 1.0.0 发布分支**（可以留在本地分支 / M7 里程碑做）；
3. 1.0.0 首页只留「隐私政策」「用户协议」「关于」。

**路 B（= 主人改主意要留设置页）**
按 D-021 字面「只留**真实生效**的」，那至少要有一批设置**真生效**才允许存在。最省事的做法：
- 挑 8–12 项**键盘侧本来就有行为**的（如振动开关与时长、按键边框样式、横屏候选条数、跟随系统深色），让 `KeyboardIndex.ets` / `KeyboardController.ets` 在初始化时**读** `sansheng_prefs` 里对应的 `k_*`，并对变更做一次即时应用；
- 其余 59 项全部**从页面上删掉**（不是隐藏、不是置灰，删掉才不承诺）；
- 「重载配置」要么真调 Rime 重载，要么删掉；
- 7 个无子页面的导航行，要么真做子页面，要么删掉。
⇒ 做完这两条，验收仪器就是本文 §2.3 的量 A/B/C：至少要能看到**键盘侧打开了 `sansheng_prefs`** 且**有 `k_*` 的消费点**。

**在主人回话之前**：按 §0.3 的默认（摘掉）推进，别把 71 项空壳提交进来。

---

## 五、我这轮明确没做的

- 未构建、未签名、未装机（`KeyboardIndex.ets` 20:46 仍在写，布局未定稿）；
- 未改任何 `entry/src/**`、`AppScope/**`；
- 未推远端；
- 未碰 `sign/**`、未问任何密码；
- 未对手机做任何操作（H-086 仍堵着：Mate 80 默认输入法不是三生）。
