# 五笔词通 · 安装说明

**五笔拼音中英混输自造词**

一套基于 Rime（小狼毫）的中文输入法方案：五笔字型 + 汉语拼音混输 + 中英双向翻译 + 自动造词。

---

## 一、这是什么

| 能力 | 说明 |
|---|---|
| 五笔 · 拼音混输 | 打五笔码或拼音都能出词，同一方案内自由切换 |
| 中 → 英 | 打 `vb`（好）候选出 good / good-looking；打 `agjs`（苹果）出Apple |
| 英 → 中 | 打 `good` 出「好 / 好处 / 好的」；10.6 万条英中词条 |
| 自动造词 | 打「刚」再打「需」上屏后，下次直接打 `mqfd` 出「刚需」 |
| 词频自适应 | 常用词会随使用自动上移 |
| 自造词继承 | 可选导入万能五笔的自造词（附在包里，默认不启用） |

**不支持**：整句翻译。词库是**词级**的（ECDICT 词典），打整句只会逐词匹配，没有句子级翻译。

---

## 二、安装（Windows）

### 前提
已安装**小狼毫（Weasel）0.17.4 或更新版本**。若未装：https://github.com/rime/weasel/releases

### 步骤

1. **完整解压**本包（得到 `wubi-citong-v1.0.2` 文件夹）。不要在压缩包里直接双击。

2. **双击 `install.bat`**

   脚本会自动：
   - 先跑一次完整性自检（显示 `[OK] 全部检查通过，可以安装` 才继续）
   - 扫描 C/D/E/F/G 盘 + 注册表，找到小狼毫安装目录
   - 备份你原来的配置到 `_wbcitong_backup`
   - 复制全部词库、方案、lua 滤镜
   - **自动触发小狼毫重新部署**（不用再手动托盘右键）

   窗口不会闪退：开头有一次 `pause`，结束时也有。出问题看同目录 `install-log.txt`。

3. **等编译完成**（首次约 1-2 分钟，`build` 目录文件数不再增加即完成）

4. 按 `F4` 切换方案，会看到三个：
   - **五笔·拼音**（主推，功能最全）
   - 拼音混输
   - 拼音混输·繁体

### 如果 install.bat 报错

| 提示 | 处理 |
|---|---|
| 「没找到小狼毫安装目录」 | 确认已装官方小狼毫；或照本文「手动安装」做 |
| 「无法创建备份目录」 | 用**管理员身份**运行 `install.bat` |
| 复制后没生效 | 看 `install-log.txt` 确认部署有没有触发；没有就手动：托盘右键 → 重新部署 |
| 双击窗口一闪而过 | 同目录 `install-log.txt` 里会有启动时间戳，说明是系统在拦 .bat；改用下面的手动安装 |

### 手动安装（备选）

**完整图文步骤见 [`手动安装指南.md`](./手动安装指南.md)** —— bat 双击闪退、显示乱码、报错时直接看这份。

速览：

1. 找 Rime 目录：托盘右键小狼毫 → **用户文件夹**（该目录必有 `installation.yaml` 和 `build`）
2. 备份原配置到 `_wbcitong_backup`
3. 把 `rime` 文件夹里**所有 .yaml 文件** + **`lua` 子目录**复制到 Rime 目录（覆盖）
4. 退出小狼毫 → 重开 → 托盘右键 **重新部署**
5. `F4` 选「五笔·拼音」

### 关于万能五笔自造词（2026-10-20 已下架）

以前 `wubi86.dict.yaml` 的 `import_tables` 里挂着 4 个 `wnwb_*` 词表（从万能五笔导出的自造词与学习词），
**现已全部移除**：那批词里 87 行其实是万能五笔出厂自带的符号模板和颜文字，不该由我们转发；
剩下的个人学习词质量参差、还夹着切词碎片，公开出去对你没有好处。

因此现在的安装包不再包含任何 `wnwb_*` 文件，`import_tables` 只剩 `cn_pinyin_wp` / `zh2en_pinyin_wp` /
`zh2en_wubi_wp` / `en2zh_v2_wp` 四张公共词表。**如果你手上还有旧版安装目录里留下的 `wnwb_*.dict.yaml`，
直接删掉即可**——新版词表已经不再引用它们，留着不影响使用，只是占地方。
符号、表情输入不受影响：它们走的是 `wubi_pinyin.custom.yaml` 里 `import_preset: symbols` 引入的
小狼毫自带 `symbols` 预设（`weasel-0.17.4/data/symbols.yaml`），`/fh` 符号、`/jt` 简单字、`/bq` 表情
都来自那里，跟 `wnwb_*` 没有关系；`lua/help_translator.lua` 的帮助行也是同一套前缀。

---

## 三、验证是否装好

切换到「五笔·拼音」方案，测试：

| 输入 | 期望 |
|---|---|
| `vb` | 第1「好」，附近有 good |
| `hao` | 第1「好」，附近有 good |
| `pingguo` | 苹果 |
| `agjs` | 苹果 + Apple |
| `good` | 好 / 好处 / 好的 |
| 打「刚」「需」上屏 → `mqfd` | 「刚需」（自动造词） |

---

## 四、词库来源与许可（2026-10-20 实测修正）

之前这一节把 `zh2en_*` 写成「ECDICT / MIT」，不准确。下面是把仓库里 75 个配置 / 词库文件
逐个与上游原包做字节比对后的结果。完整版（含引擎二进制与安卓随包 76 个文件）见
[`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md)，许可证全文在 [`LICENSES/`](../LICENSES/)。

| 词库 / 文件 | 来源 | 许可 | 分发时要做什么 |
|---|---|---|---|
| `wubi86.dict.yaml`（主力五笔码表） | [rime/rime-wubi](https://github.com/rime/rime-wubi) | **LGPL-3.0** | 保留文件头部上游 changelog 署名（Gong Chen / acevery / Chen Xing / Wozy），2026-10-20 已贴回 |
| `wubi86_jidian*`、`pinyin_simp.*`、`cn_pinyin_*` | [KyleBing/rime-wubi86-jidian](https://github.com/KyleBing/rime-wubi86-jidian)、[rime/rime-pinyin-simp](https://github.com/rime/rime-pinyin-simp) | Apache-2.0 | 附上游 LICENSE；极点码表源头 `wubi-jidan-dict` 本身无许可证声明，风险记在 THIRD_PARTY_NOTICES |
| `zh2en_pinyin_wp` / `zh2en_wubi_wp`（汉→英） | [CC-CEDICT](https://cc-cedict.org/wiki/) | **CC-BY-SA-4.0（具传染性）** | 必须署名 + 说明改编；这两张表要以 CC-BY-SA-4.0 提供，**不能并进 MIT**。署名 2026-10-20 已写进各文件表头，卡片全文见仓库 `README.md`「CC-CEDICT 署名」 |
| `en2zh_v2_*`（英→汉） | [skywind3000/ECDICT](https://github.com/skywind3000/ECDICT) | MIT | 保留 ECDICT 的 MIT 版权声明 |
| `lua/` 下 39 个功能脚本（中英互译、编码反查、日期农历、节日、LaTeX、敏感词） | [happyDom/dyyRime](https://github.com/happyDom/dyyRime) | **上游没有 LICENSE = 保留所有权利** | 授权请求中 → [dyyRime Issue #9](https://github.com/happyDom/dyyRime/issues/9)（2026-10-20 发出，尚无回复）。这一层是三生的核心功能；若原作者明确要求下架，我们会在下个版本移除并提前公告 |
| ~~`wnwb_*`（万能五笔导出层）~~ | 万能五笔出厂模板 + 个人学习词 | 已下架 | 2026-10-20 全部移除，不再随包发布，理由见第二节末 |
| `opencc/*` 繁简转换数据 | [BYVoid/OpenCC](https://github.com/BYVoid/OpenCC) | Apache-2.0 | 附上游 LICENSE |
| 引擎 weasel 0.17.4 | [rime/weasel](https://github.com/rime/weasel) | GPL-3.0 | 安装器已附 `LICENSE.txt` 与官方源码地址 |
| 三生自研（`codeLookup_Filter.lua`、`inputShow_translator.lua`、`help_translator.lua`、图标与主题、构建脚本） | 我们自己写的 | MIT | 顶层 `LICENSE` 现在只覆盖这部分 |

一句话：**发布 / 分发时不能只写一句「MIT」**，各组件按上表分别署名。

---

## 五、文件清单

```
wubi-citong-v1.0.0/
├─ install.bat                 ← 双击这个安装
├─ rime/                      ← 安装源（脚本会复制这些）
│  ├─ wubi_pinyin.schema.yaml       五笔·拼音（主推）
│  ├─ wubi_pinyin.custom.yaml
│  ├─ wubi86_jidian_pinyin.schema.yaml      拼音混输
│  ├─ wubi86_jidian_trad_pinyin.schema.yaml 拼音混输·繁体
│  ├─ default.custom.yaml            方案清单（只留 3 个）
│  ├─ cn_pinyin_wp.dict.yaml         中文拼音码 65114 条
│  ├─ zh2en_pinyin_wp.dict.yaml      中→英（拼音）89737 条
│  ├─ zh2en_wubi_wp.dict.yaml        中→英（五笔）89841 条
│  ├─ en2zh_v2_wp.dict.yaml          英→中 106004 条
│  ├─ wubi86.dict.yaml 等基础字典
│  ├─ *_py.dict.yaml（别名）
│  └─ lua/                          滤镜（含关键修复）
└─ 使用说明/                本文档
```

> v1.9.11 / v1.10 起，包里不再有 `我的自造词_可选\`（万能五笔导出的 `wnwb_*` 层已下架，
> 详见仓库 `THIRD_PARTY_NOTICES.md` 第三节末）。老安装目录里若还留有 `wnwb_*.dict.yaml`，
> 新配置不再引用，删不删都不影响使用。

---

*五笔词通 · 五笔拼音中英混输自造词*