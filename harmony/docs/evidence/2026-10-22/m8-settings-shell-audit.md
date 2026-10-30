# M8 在飞改动实测复核（Qoder，2026-10-22 14:5x）

对象：CodeArts `M-070-re`（14:45）声明 + 当前工作树。全部为只读测量，未改任何代码。

## 1. 构建产物核对：M-070-re 报的字节数对不上任何文件

`entry/build` 下现存产物（`stat -c %s`，单位 B）：

| 文件 | 大小 | mtime |
|---|---|---|
| `default/outputs/default/entry-default-m053-signed.hap` | 28,049,332 | 10-22 04:37 |
| `default/outputs/default/entry-default-m066-signed.hap` | 28,175,592 | 10-22 12:55 |
| `default/outputs/default/entry-default-m067-cr01-signed.hap` | 28,174,855 | 10-22 13:06 |
| `default/outputs/default/entry-default-release-signed.hap` | 27,822,532 | 10-22 13:25 |
| `default/outputs/default/entry-default-unsigned.hap` | **28,178,584** | **10-22 14:43** |
| `release-stage/entry-default.hap` | 27,822,532 | 13:2x |
| `default/outputs/default/sansheng-ime-1.0.0-release.app` | 11,791,326 | 13:2x |

- 全仓 `find -size 28175674c` **0 命中** ⇒ M-070-re 里「构建绿 28,175,674 B」不是磁盘上任何一个产物。
- 14:43 那个是 **unsigned**，本轮**没有** `entry-default-m070-signed.hap` 之类的新签名包 ⇒ 无法装机，真机结论一律不成立。

## 2. 声明页第三节：PASS

`entry/src/main/ets/pages/AboutPage.ets`（mtime 14:33）词库来源表现在有 10 行，与根 `NOTICE` 第三节逐条对齐：

`CC-CEDICT/CC BY-SA 4.0`（说明已改成「中英互译词库（zh2en 系列）」，不再含 `cn_pinyin_wp`）、
`cn_pinyin_wp/Apache-2.0`（说明「拼音词库（由 pinyin_simp 重新整理生成）」）、
`ECDICT/MIT`、`rime-wubi86-jidian/Apache-2.0`、`rime-pinyin-simp/Apache-2.0`、`OpenCC/Apache-2.0`、
`librime/BSD-3-Clause`、`harmonyos-next-rime-har/MIT`、`hMixedKeyboard/Apache-2.0`、`kanonIME/MIT`。
⇒ M-070 ②③ 要求的更正已落地。

## 3. 数据侧改动的记账：正确

`RimeDataInstaller.ets`：`DATA_VERSION` `m5-pinyin-v18` → **`m8-parity-v19`**，
`SHARED_FILES` 新增 `symbols.yaml`、`symbols.custom.yaml` ⇒ 新数据会真正下发，v18 老机器会重装。
`rime.lua` 新增 `phoneComment_Filter`，`lua-files.txt` 同步登记（插在 `laneChangeAndSpace_Filter` 与 `lunarModule` 之间，破坏字母序，纯排版瑕疵）。

## 4. 设置页是空壳，且文案与隐私申报冲突（H-087）

未跟踪新文件：`common/SettingsModels.ets`(445) + `pages/SettingsPage.ets`(112) + `pages/SettingsCategoryPage.ets`(455)，
`main_pages.json` 已注册，`Index.ets:81` 有入口 ⇒ 首页可进。

对每个 prefKey 在 `entry/src/main/ets` 全库检索，命中文件数 **恒为 1（只有定义处）**：

| prefKey | 命中文件 |
|---|---|
| `clip_enable` / `clip_listening` / `clip_limit` | 仅 `SettingsModels.ets` |
| `emoji_skin_tone` | 仅 `SettingsModels.ets` |
| `adv_verbose_log` | 仅 `SettingsModels.ets` |

其中 `getClipboardSettings()` 提供「启用剪贴板 / **记录剪贴板历史** / 历史上限 / 隐藏敏感信息 / **清空剪贴板数据库**」，
`getPluginSettings()` 提供「插件列表」，`getAdvancedSettings()` 提供「导入/导出用户数据」。
⇒ 与已定稿的 `docs/release/legal/privacy-policy.md`、`agc-privacy-form.md`「不读取剪贴板、无插件、无云端」口径**正面冲突**，
属华为隐私驳回 TOP 类（申报与实际不一致 / 虚假功能）。

## 5. 新入包数据文件的许可归属（H-088）

| 文件 | 大小 | md5 | 实测来源 |
|---|---|---|---|
| `rawfile/rime/symbols.yaml` | 28,473 | `b4fe9b1fb5419b6cf4ebc4193b121560` | = 桌面 `F:/dshdesktopwork/rimetest/symbols.yaml`（md5 `aa4227956f4a00afdcf146f92d81e80f`，与 `weasel-0.17.4/data/symbols.yaml` 同 md5）+ **3 行差异**：多一行注释「#結構、偏旁、康熙（部首）、筆畫、標點」，`/pp`、`/kx` 两行由普通汉字改写成**康熙部首码位**（⼀⼁⼂…）。319 行 vs 318 行 |
| `rawfile/rime/symbols.custom.yaml` | 11,696 | `b1e28d38ede993a7403b8087c55bc194` | 与安卓根 `sansheng-ime-android/rime/symbols.custom.yaml` **逐字节相同**（`diff` 0 行差异）⇒ 自有整理 |
| `rawfile/rime/lua/phoneComment_Filter.lua` | 2,397 | `3cd9b776895346b3ea0e2864a7810271` | 安卓根 `rime/lua/` 存在同名文件（且 4 个历史备份里都有）⇒ 自有 |

⇒ 只有 `symbols.yaml` 需要许可判定（上游 Weasel/rime 共享数据派生），且它落在 10-22 许可审计收口（`bd5d920`/H-083）之后，属新增缺口。

## 6. 26 键拼音翻译器被删（H-089）

`git diff` `rawfile/rime/wubi_pinyin.custom.yaml` 两个 hunk：

1. **删除** `engine/translators/+` 里的 `- script_translator@pinyin` 与整块 `pinyin:`（14 行，注释写明 M5/D-012/H-066：26 键 `nihao` 从 1 条升级为逐字/词组/整句）。
2. `punctuator/import_preset: default` → `symbols`（标点多义的实现方向，配合 §5 的 symbols.yaml）。

基础 `wubi_pinyin.schema.yaml` 的 `engine/translators` 实测只有：
`punct_translator`、`table_translator`、`reverse_lookup_translator`、`lua_translator@inputShow_translator`、`lua_translator@help_translator`
⇒ 没有任何 `script_translator@pinyin` 兜底，删 patch 即回退。全库检索 `script_translator@pinyin` 在工作树 **0 命中**（HEAD 命中 1 处）。

## 7. 设备状态

14:47 截图 `r3-chk.jpeg`（135,470 B）：屏幕已解锁，但主人正在「国家网络身份认证公共服务」页输入 8 位凭证口令（系统安全键盘，状态栏 14:47 / 中国工商）
⇒ **本轮不触碰设备**（不点按、不注入、不猜口令），补测三条与 H-085 重拍继续等设备空闲。

## 8. `symbols.yaml` 上游追查（H-088 判定过程，14:5x）

| 尝试 | 结果 |
|---|---|
| 文件自身 | 只有 4 行注释（`# Rime's punctuation and symbols` / `# encoding: utf-8` / `# Usage: patch your Rime schema to enable /X symbols`），**无许可、无作者、无仓库地址**；`config_version: '1.6'`，319 行 |
| 分发渠道 | `weasel-0.17.4/README.txt`：「授權條款：**GPLv3**」；其第三方清单只列 Boost/curl/glog/googletest/LevelDB/**librime(BSD-3)**/marisa-trie/OpenCC(Apache-2.0)/plum(LGPLv3)/WinSparkle(MIT) —— **没有为 `data/` 目录里的配置文件声明许可** |
| librime `data/minimal/symbols.yaml` | HTTP 200，但**不是同一份**：139 行 / 11,024 B / `config_version: "0.8.1"`；与我们这份差 **217 行**（我们多出 `patch:` 头、`⟨ ` 等条目、`/pp` `/kx` `/bz` 分节） |
| iDvel/rime-ice | 根目录文件清单实测：只有 `symbols_caps_v.yaml`、`symbols_v.yaml`，**无 `symbols.yaml`**；`v1.0.0`/`v1.4.0`/`v1.6.0`/`v2.0.0` tag 下的 `symbols.yaml` 全 404 |
| sgalal/rime-symbolic、sgalal/rime-symbolic-simp | `main`/`master` 下 `symbols.yaml` 全 404 |

**结论**：来源链能证到「小狼毫 0.17.4 附带 `data/symbols.yaml`（与桌面 `rimetest/` 同 md5）+ 我们改 3 行」，
但**上游仓库与许可钉不到** ⇒ 不能凭猜测写进 NOTICE。
该文件在 1.0.0 包里换到的只有 `/pp`（偏旁）、`/kx`（康熙部首）、`/bz`（笔画）等 `/` 模式符号输入，不在宣传口径内
⇒ 处置建议见 `docs/DECISIONS.md` **D-020**（推荐 A：不用该文件，标点增补并入自有 `default.yaml`）。
