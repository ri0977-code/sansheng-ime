# 三生输入法 · 鸿蒙版 Rime 数据集（M3）

本目录是打进 HAP 的**只读**数据，运行首帧由 `entry/src/main/ets/engine/RimeDataInstaller.ets`
释放到应用沙箱（shared 目录 `filesDir/rime`，user 目录 `filesDir/rime_user`）。
**不要手工编辑本目录**（唯一例外：文件头的许可/署名注释，由 Qoder 按 H-049 统一维护）；
重新生成请用

```
python scripts/port_rime_data.py
```

该脚本从桌面端三个数据根里按「逐文件优先级」挑选，产出的来源清单与 md5 在
`docs/evidence/2026-10-21/m3-data-manifest.json`。

## 文件与来源

| 文件 | 作用 | 来源（本机） | 上游与许可 |
|---|---|---|---|
| `default.yaml` | 方案列表、页大小、翻页键、中文标点 | 本项目自写（鸿蒙版） | Apache-2.0 |
| `wubi_pinyin.schema.yaml` | 主方案：五笔·拼音·英文混输 | `F:/workbuddywork/三生输入法/rime-config/` | 方案结构源自 rime-wubi86（Apache-2.0）；三生改动见文件内 DSH 注释 |
| `wubi_pinyin.custom.yaml` | 三生滤镜/开关补丁（落地时删掉小狼毫气泡图标 3 行、`import_preset: symbols`→`default`） | `D:/Program Files/Rime/`（当前运行目录，含 abbrGloss 一行） | 同上 |
| `pinyin_simp.schema.yaml`、`pinyin_simp.dict.yaml` | 拼音底座（反查 + 智能九键的词库） | rime 官方 `pinyin_simp`（rime/rime-pinyin-simp） | Apache-2.0（源自 Android PinyinIME） |
| `wubi86.dict.yaml` | 五笔 86 主词库 | `F:/.../rime/` | 主要来自 rime/rime-wubi（LGPL-3.0，2026-10-22 更正）；KyleBing/rime-wubi86-jidian（Apache-2.0）只贡献极点权重与补充词条 |
| `cn_pinyin_wp.dict.yaml` | 中文拼音词（拼音混输通道） | `F:/.../rime/` | 由 CC-CEDICT 生成，CC BY-SA 4.0 |
| `zh2en_pinyin_wp`、`zh2en_wubi_wp`、`en2zh_v2_wp` | 五笔词库的 `import_tables`（缺一个就整类候选消失） | `F:/.../rime/` | CC-CEDICT（CC BY-SA 4.0）/ ECDICT（MIT） |
| `zh2en_pinyin.dict.yaml`、`zh2en_wubi.dict.yaml`、`en2zh_v2.dict.yaml` | 三个中英互译 translator 的词库 | `D:/Program Files/Rime/` | 同上 |
| `Custom_phrase.txt` | 自造词/自定义短语（stabledb，运行期可写） | `F:/.../rime/` | 主人自用模板；含 Rime 官方模板行，与 dyy 同名文件行级相似 46%（见下注） |
| `sansheng_t9.schema.yaml` | 智能九键方案（数字入、拼音出，H-028 ①） | 本项目新写（Qoder） | Apache-2.0 |
| `opencc/s2t.json`、`opencc/STCharacters.ocd2`、`opencc/STPhrases.ocd2` | 简→繁转换（`zh_trad` 开关） | `F:/workbuddywork/三生输入法/opencc/` | OpenCC（Apache-2.0）；`.ocd2` 是预编译二进制，设备上不需要 opencc CLI |

## 许可与署名（2026-10-21 已按 H-049 处理）

- **CC-CEDICT 派生词库是 CC BY-SA 4.0**：`zh2en_*`、`cn_pinyin_wp` 都来自它。BY-SA 是带传染性
  的署名-相同方式共享许可，意味着**这几份词库必须以 CC BY-SA 4.0 继续分发并署名**，
  不能并进 Apache-2.0 的整体许可里。
  **当前状态**：每个 `.dict.yaml` 文件头都写了来源、许可与署名（CC-CEDICT project），
  许可全文随包提供 `LICENSES/CC-BY-SA-4.0.txt`，整体署名说明见仓库根 `NOTICE`。
  义务**只约束词库数据本身**，不要求公开 ArkTS / C++ 代码。
- **ECDICT（`en2zh_v2*`）是 MIT**：`en2zh_v2.dict.yaml` 头部已带 `© Linwei (skywind3000)`
  版权行，许可全文见 `LICENSES/MIT-ECDICT.txt`。
- **`wubi86.dict.yaml` 是 LGPL-3.0，不是 Apache-2.0**（2026-10-22 逐文件核更正）：本文件属
  `rime/rime-wubi` 一脉（该仓库 LICENSE = LGPL-3.0，全文见仓库 `LICENSES/LGPL-3.0.txt`），
  KyleBing/rime-wubi86-jidian（Apache-2.0）只贡献极点权重与补充词条，不能据此把整份文件记成
  Apache-2.0。文件头的 changelog 署名（Gong Chen / Yu Yuwei / Chen Xing / Wozy）须保留。
- **rime/rime-pinyin-simp（pinyin_simp）、OpenCC（简繁数据）是 Apache-2.0**：文件头已注明来源与许可，
  全文见 `LICENSES/Apache-2.0.txt`。
- **2026-10-22 第二轮逐文件核查（Qoder）**：本目录 65 个文件（含 `lua/**` 44 个）已逐个做字节级来源
  比对，结论在 `docs/release/legal/third-party-audit-2026-10-22.md`，逐文件表在
  `docs/evidence/2026-10-22/third-party-audit-data.md`。上面的表原来**漏了**下表几类，补在这里
  （2026-10-24 第三轮按行级相似度复核，同名文件拆成「改写 / 独立重写」两级）：

  | 文件 | 作用 | 来源 | 许可状态 |
  |---|---|---|---|
  | `lua/**` 里的 29 个 | 释义/注释/日期/节气/4 字词等滤镜与数据表（3,197,403 B） | `happyDom/dyyRime` 原样复制（仅行尾差异） | ⚠ 上游无 LICENSE，授权申请中；完整清单见根 `NOTICE` |
  | 由 dyy 同名文件**改写**的 7 个 | `lua/Upper_Filter.lua` 97%、`lua/inputShow.lua` 98%、`lua/inputShow_Filter.lua` 95%、`lua/dic_4w_Filter.lua` 79%、`Custom_phrase.txt` 46%、`wubi_pinyin.custom.yaml` 42%、`lua/sysInfo.lua` 38%（行级相似度） | `happyDom/dyyRime` 同名文件改写 | ⚠ 同上，逐文件见根 `NOTICE`「授权申请中」条 |
  | 与 dyy **同名但独立重写**的 6 个 | `rime.lua`、`README.md`（相似度均 0%）、`lua/runLog.lua`、`lua/socket.lua`（安全桩）、`lua/phraseComment personal.txt`、`lua/phraseExt personal.txt`（本项目模板） | 本项目（仅沿用模块名/文件名与调用契约，无逐行复制） | Apache-2.0（列出仅为对照，不含上游代码） |
  | `lua/abbrGloss_Filter.lua`、`codeLookup_Filter.lua`、`phoneComment_Filter.lua`、`rawEcho_translator.lua`、`lua-files.txt` | 三生三向反查与释义链路的自写实现 | 本项目 | Apache-2.0 |
  | `symbols.yaml`、`symbols.custom.yaml` | `/xx` 斜杠符号预设的早期副本 | 安卓 1.10.1 插件 APK / `happyDom/dyyRime` 改版 | **1.0.0 已移除、不随包**（只存在于 m066 / m067-cr01 / release 三个旧签名包，那三个包不得提审；见根 `NOTICE`「许可敞口已于 1.0.0 移除」条） |
- 随包引擎二进制的第三方库许可（librime/LevelDB/glog/marisa/yaml-cpp/Lua）见根 `NOTICE`
  第二节与 `LICENSES/`。
- 应用内「关于 / 第三方声明」页已落地（H-052）：关于页可打开「完整许可声明」，
  内容即根 `NOTICE` + `LICENSES/*.txt` 的全文（H-099）。

## 已知边界（M3 阶段）

1. **Lua 滤镜已接入，个别模块受限**：`rime.lua` 已为鸿蒙重写——用 `pcall(require, ...)`
   逐个加载，失败则回落到恒等放行桩（保主链路出词不被打断）。`lua/` 目录随包发布，
   `wubi_pinyin.custom.yaml` 里 12 个 `lua_filter@*` 均已注册。绝大多数滤镜（inputShow、
   dateTime、dic_4w、abbrGloss、codeLookup、laneChangeAndSpace 等）在设备上正常工作。
   仅 `socket.lua`（依赖 luaSocket DLL）和 `sysInfo.lua`（读 Windows 环境变量）两个
   非滤镜模块在鸿蒙上 pcall 失败、走桩放行，不影响输入主链路。
2. **`punctuator/import_preset`**：桌面端指向 `symbols` 预设（在小狼毫公共目录里），鸿蒙
   没打包那份文件，已改成本目录 `default.yaml` 自带常用中文标点；符号/emoji 页由键盘 UI
   提供（`rawfile/symbols/symbols.json`）。
3. **首次启动要现编译词库**：约 17 MB 的 YAML 词库在设备上第一次编译成 `.bin`
   （`filesDir/rime_user/build/`），耗时体现在 M3 自检页的 `init` 行里；
   若慢到影响上手，M4 做预置 `build/*.bin` 快路径。
