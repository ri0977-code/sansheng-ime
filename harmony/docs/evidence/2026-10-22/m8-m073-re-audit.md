# M-073-re 复核（CodeArts 声称 H-087/H-089 已修）· 2026-10-22 15:1x · Qoder

复核方式：只读 `entry/src/**`，逐项量。工具输出全部留在本文，不引聊天。

## 1. 记账核对：本轮 PASS

| 产物 | 声称 | 实测 | 结论 |
|---|---|---|---|
| `entry/build/default/outputs/default/entry-default-unsigned.hap` | 28,175,230 B（`stat -c %s`） | `stat -c %s` = **28175230**，mtime 15:01 | **一致** |

上一轮（M-070-re）报的 28,175,674 B 磁盘上不存在，本轮对得上 ⇒ 记账规矩生效。
仍缺：**签名 debug HAP**（目录里最新的签名包是 13:06 的 `entry-default-m067-cr01-signed.hap`）。

## 2. H-089（26 键拼音翻译器）：源码已恢复，但**装机即失效**

- `entry/src/main/resources/rawfile/rime/wubi_pinyin.custom.yaml:31` 实测回到
  `- script_translator@pinyin  # M5/D-012：拼音逐字+整句候选（词典 pinyin_simp）；五笔 table 不动` ⇒ 源码层 FIXED。
- **新缺陷（H-091）**：`RimeDataInstaller.ets:101` 仍是 `const DATA_VERSION: string = 'm8-parity-v19';`
  而 `:177-179` 的逻辑是「shared 目录里 `.data-version` 文本 === DATA_VERSION ⇒ `console.info(... already present)` ⇒ `return`」，
  Mate 80 上 13:06 的 m067 包已把 marker 写成 v19 ⇒ **改过的 `wubi_pinyin.custom.yaml` 不会被重新铺到 shared 目录，装机后 `nihao` 仍是 1 条整词**。
  这个坑该文件自己的头注释第 10 行就写着：「14:36 真机实测就是这么踩的：本地改了，marker 还是 v2，文件根本没更新。」
- 另外 CodeArts 的解释「port_rime_data.py --check 脏改动导致的误删」我接受，但**结论要落成规矩**：
  脚本 `--check` 不许就地改写 rawfile 数据；改写数据必须同一次 bump `DATA_VERSION`。

## 3. H-087：三个分类确实从页面上摘了，但**「空壳」是这个页面的常态，不是三类的病**

先看摘干净没有（检索三个设置文件）：

| 词 | SettingsPage.ets | SettingsCategoryPage.ets | SettingsModels.ets |
|---|---|---|---|
| 剪贴板 | 2（都在注释：`:6` 过期文件头、`:17` 移除说明） | 2（`:428-429` 死代码分支） | 0 |
| 插件 | 2（`:6`/`:17` 注释） | 0 | 0 |
| 表情 | 2（`:6`/`:17` 注释） | 0 | 0 |
| 导入/导出 | 0 | 4（`:431/:434` 死代码分支） | 0 |

⇒ 页面可见项里三类已消失（这点 DONE）；残留是注释与不可达 `switch case`，属清理项，不是阻断项。

再看**我的判据 ① 本身错了**，必须更正：

- 页面读写偏好走的是动态取值 —— `SettingsCategoryPage.ets:59/63/77/108/203/274/300` 全是
  `const key = item.prefKey || item.id;` ⇒ **prefKey 字面量只会出现在定义文件里，命中数 >1 这条判据永远不满足，也与「是否生效」无关**。我原来用它当"最硬的一条"，是错仪器。
- 换成能量化的判据：**谁打开了 `sansheng_prefs`**。全库检索 `preferences` API 命中文件 = **3 个**：
  `common/PrivacyConsent.ets:18,40`、`pages/Index.ets:21,57`（只读 `PREF_KEY_AGREED` 隐私弹窗）、
  `pages/SettingsCategoryPage.ets:12,48`（设置页自己）。
  `inputmethod/`、`engine/`、`pages/KeyboardIndex.ets` **一个都没有**。
- 消费侧抽样验证：`k_haptic`（按键时振动）—— `KeyboardIndex.ets:773-775` 无条件
  `vibrator.startVibration({type:'time',duration:20}, {usage:'touch'})`，没读任何偏好 ⇒ 关了也照样振。
- 按上面的取值方式重抽 pref 承载项：**32 项**（27 switch + 4 slider/dropdown + 1 input），
  **被引擎/键盘消费的 = 0 项**。另有 `mkButton` 1 项、`mkNavigation` 8 项：
  `executeButtonAction`（`:424-442`）四个 case 全是 `console.info` 后 `break`；
  `navigateFromItem`（`:445-455`）只有 `case 'a_about'` 真跳 `pages/AboutPage`，
  `default` 的注释写着「其他导航项暂未实现子页面」⇒ `im_manage_table` / `im_pinyin_dict` / `im_quickphrase` /
  `addon_list` / `addon_configure` / `a_real_time_logs` / `a_crash_logs` **7 项点了没反应**。

⇒ **结论：H-087 不能按"砍掉三类"关闭。** 1.0.0 若带着这个入口上架，商店看到的是 8 个分类里 32 个拨了没用的开关 +
1 个只打日志的按钮 + 7 个点了没反应的行；而我们申报口径是「功能与描述一致」。这比原来那三类的文案冲突面更大。

## 4. 待 CodeArts 一并交付（不重复派单，见 M-077）

D-020 落地（`symbols.yaml` 出包 + `import_preset: default` + 标点并进自有 `default.yaml` + T9 `punct` 补齐）本轮未动，
`rawfile/rime/symbols.yaml` 28,473 B 仍在、`SHARED_FILES` 第 116 行仍列它、`wubi_pinyin.custom.yaml:77` 仍是 `import_preset: symbols`、
`DATA_VERSION` 仍是 v19 ⇒ 与主人 15:0x 的 D-020 选 A 决议不一致，属我 M-075/M-076 尚未消化的部分（时间线：CodeArts 15:05 回复早于我 15:0x/15:3x 两条）。
