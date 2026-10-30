# 应用内「关于 / 第三方声明」页内容源（2026-10-22，Qoder）

用途：M-043 / H-049 ④ 那个页面的**唯一文案来源**。CodeArts 只负责渲染，不要自创许可结论；
每一行都能回溯到 `NOTICE` 第二/三节与 `docs/release/legal/third-party-audit-2026-10-22.md`。

写法约定（给页面）：

- 页尾必须有「许可原文」一节，指向随包文本（`LICENSES/` 下的 11 个文件），不要只写缩写。
- **禁止**把整包写成「Apache-2.0」；本项目代码是 Apache-2.0，数据与 Lua 各自不同许可。
- 「授权申请中」这条要如实显示，不要美化成「已获授权」；对外如实披露本身就是减责。
- 联系方式用公开邮箱 `ri0977@qq.com`（备用 `ri0977@gmail.com`），与隐私政策、AGC 后台一致。

---

## 一、引擎与依赖库（随包二进制）

| 组件 | 用途 | 许可 | 上游 | 原文 |
|---|---|---|---|---|
| librime | 输入引擎核心（词库编译、方案、候选） | BSD-3-Clause | rime/librime | `LICENSES/BSD-3-Clause-librime.txt` |
| LevelDB | 词库存储 | BSD-3-Clause | Google/leveldb | `LICENSES/BSD-3-Clause-Google.txt` |
| glog | 日志 | BSD-3-Clause | google/glog | 同上（BSD-3） |
| marisa-trie | 前缀树词典 | BSD-2-Clause | s-yata/marisa-trie | `LICENSES/BSD-2-Clause-marisa.txt` |
| yaml-cpp | 方案/词库 YAML 解析 | MIT | jbeder/yaml-cpp | `LICENSES/MIT-yaml-cpp.txt` |
| Lua 5.4 | 滤镜脚本运行时 | MIT | lua.org | `LICENSES/MIT-Lua.txt` |
| OpenCC | 简繁转换（含随包 `.ocd2` 数据） | Apache-2.0 | BYVoid/OpenCC | `LICENSES/Apache-2.0.txt` |
| rime-har（HarmonyOS NEXT librime 移植） | 让 librime 能在鸿蒙编译 | MIT | chuanis/harmonyos-next-rime-har | `LICENSES/MIT-harmonyos-next-rime-har.txt` |
| LLVM libc++（`libc++_shared.so`） | C++ 标准库运行时，由 DevEco / OHOS NDK 工具链随原生构建注入 | Apache-2.0 WITH LLVM-exception | llvm/llvm-project | 无随包抄本（见下方说明） |

**实际入包的是两个 `.so`，上面这些库不单独进包**（2026-10-23 逐字节核对 `entry-default-unsigned.hap`，细节与依据见 `NOTICE` 第二节）：

- `libs/arm64-v8a/libfanxing_rime.so`（5,549,616 B）= `fanxing_napi.cpp` ＋ 上表 7 个静态库现场链接、剥离符号后的产物；
- `libs/arm64-v8a/libc++_shared.so`（1,262,504 B）= LLVM libc++ 运行时，工具链注入。
  它的 LLVM 例外明确允许分发编译产物时不附带许可文本，所以 `LICENSES/` 里**不放**它的抄本 ——
  页面若在「许可原文」一节列它，请写成「Apache-2.0 WITH LLVM-exception；随包为编译产物，依例外不附原文」，
  不要指向一个不存在的文件。

## 二、界面与键盘壳的借鉴来源

| 项目 | 借鉴内容 | 许可 |
|---|---|---|
| hMixedKeyboard | 键盘壳结构（键位布局、控制器分层）；未带入其字典引擎 | Apache-2.0 |
| OpenHarmony KikaInputMethod | 候选栏布局思路（经 kanonIME 间接沿用） | Apache-2.0 |
| ysk0518/kanonIME | 单行候选条 + ▼ 展开网格布局 | MIT（`LICENSES/MIT-kanonIME.txt`） |
| yuetyam/jyutping-harmony | 键帽尺寸模型 | CC0-1.0（无署名义务，此处致谢） |
| fcitx5-android / Trime / fcitx5-harmony | **仅交互设计**（辅助信息行不吃候选宽度、comment 置于词上方），未复制源码 | LGPL-2.1 / GPL-3.0（仅说明，不构成链接或派生） |

## 三、词库与数据

| 数据 | 许可 | 说明 |
|---|---|---|
| `wubi86.dict.yaml`（86 五笔主码表） | **LGPL-3.0** | 属 `rime/rime-wubi` 一脉（`LICENSES/LGPL-3.0.txt`）；极点权重与补充词条来自 KyleBing/rime-wubi86-jidian（Apache-2.0）。文件头保留贡献者署名：Gong Chen、Yu Yuwei、Chen Xing，原始码表作者 Wozy。 |
| `zh2en_pinyin*.yaml`、`zh2en_wubi*.yaml` | **CC BY-SA 4.0** | 由 CC-CEDICT 转换/加权生成，属改编作品，依 SA 条款继续以 CC BY-SA 4.0 分发；署名 © CC-CEDICT project。义务只覆盖这些数据本身。 |
| `en2zh_v2*.dict.yaml` | MIT | 来自 ECDICT，© Linwei (skywind3000)，按行筛选的子集（`LICENSES/MIT-ECDICT.txt`）。 |
| `pinyin_simp.dict.yaml` / `.schema.yaml` | Apache-2.0 | rime/rime-pinyin-simp（上游为 Android PinyinIME）。 |
| `cn_pinyin_wp.dict.yaml` | Apache-2.0 | 由 `pinyin_simp.dict.yaml` 重新整理生成（65,114 个词条与拼音标注逐一对应），不含 CC-CEDICT 内容，许可随上游 `pinyin_simp`。 |
| `opencc/STCharacters.ocd2`、`STPhrases.ocd2`、`s2t.json` | Apache-2.0 | OpenCC 预编译简繁数据，未修改。 |
| `Custom_phrase.txt` | 用户数据 | 自造词/自定义短语模板，运行期写入沙箱，不属第三方许可范围。 |

## 四、Lua 滤镜与符号表（含未闭环项，如实显示）

| 内容 | 来源 | 许可 | 页面文案 |
|---|---|---|---|
| `rime/lua/**` 中 29 个文件（3,197,403 B：释义、日期/节气、4 字词、phraseExt/phraseComment 等 `.lua` 与配套 `.txt` 数据表） | `happyDom/dyyRime` | **上游仓库未附许可证（法律上保留所有权利），本项目正在申请授权** | 「本节 Lua 滤镜与数据表参考/取自 happyDom/dyyRime，其仓库未附带开源许可证；我们已向上游作者提出许可请求（<https://github.com/happyDom/dyyRime>），在获得书面许可前，该部分版权归上游作者所有，本项目仅在本应用内以现有形态使用并如实披露。」 |
| `symbols.custom.yaml`、`Upper_Filter.lua`、`dic_4w_Filter.lua`、`inputShow*.lua`、`runLog.lua`、`socket.lua`、`sysInfo.lua`、`rime.lua` 等 12 个 | 在上行文件基础上的改写 | 同上；本项目只主张自己改动部分 | 追加一句：「其中若干文件由本项目在上游实现基础上修改，修改部分版权归本项目。」 |
| `symbols.yaml`（`/xx` 斜杠符号预设，28,473 B） | rime 官方数据（`Rime's punctuation and symbols`）的部署副本，与安卓版 1.10.1 内副本字节相同 | 上游无可指认许可证文本 ⇒ **D-020 已决定 1.0.0 不再打包该文件**（工作区已删，需重出签名包才落到包里） | 该行不再出现在页面上；若历史版本被问及，文案为「1.0.0 起不再包含该符号预设文件。」 |
| `symbols/symbols.json`（34,984 B，116 组 / 2,093 项） | 本项目脚本 `scripts/build_symbol_data.py` 生成，其中 105 个 `r_` 组（1,236 项，占 59%）**派生自上行 dyy 血脉的 `symbols.custom.yaml`**：104 组成员集合与该表逐项相同（实测 2026-10-22 15:5x，`docs/evidence/2026-10-22/d-020-landing-audit.md` §5） | 许可归入本节 dyy「申请授权中」条目；本项目只主张整理与生成脚本部分。**原写「本项目原创」属高估，已更正** | 「符号面板数据整理自 Rime 社区公开的符号表（happyDom/dyyRime 一脉），整理与生成脚本为本项目所作，该部分上游许可申请中。」 |
| `default.yaml` 内的 `punctuator/symbols` 9 组（117 项）与 `half_shape` 10 个多义标点键（28 项）＝合计 145 项（该文件其余部分仍是本项目自写） | 2026-10-22 16:04 起从 `symbols.custom.yaml` 逐字符并入；逐组逐项比对实测见 `docs/evidence/2026-10-22/d-020-merge-recheck.md` §八（9 组全部逐字符相同；并入时保留了 2 处上游怪值） | 承 dyy 档（授权申请中，随 2026-10-22 14:22 已发出的请求一并披露）；`default.yaml` 已从「100% 自写」改列为「自写 + 含派生片段」，行内亦有来源标注 | 用户可见口径：1.0.0 保留这 9 组斜杠符号，是否保留待开发方最终确认 |
| `abbrGloss_Filter.lua`、`codeLookup_Filter.lua`、`phoneComment_Filter.lua`、`rawEcho_translator.lua`、`sansheng_t9.schema.yaml`、`abbr_en.txt`、`abbr_num.txt` | 本项目 | Apache-2.0 | 「三向反查、释义、注释截断、智能九键与英文缩写数据为本项目原创实现。」 |

> 注：`abbr_en.txt`（17,146 B）与 `abbr_num.txt`（3,636 B）原列「来源待确认」，2026-10-22 14:0x 复测判定为本项目自有整理数据（与安卓版数据根逐字节相同、三组第三方参照均无同名文件），已并入上行，页面不再单列。

## 五、本项目代码

`entry/src/main/ets/**`、`entry/src/main/cpp/**`（NAPI 桥、IME 服务、页面与引擎封装）：
Apache-2.0，© 2026 三生输入法 contributors；许可原文见仓库根 `LICENSE`（页面可内嵌要点）。
注：本项目不使用任何 GPL 血脉的源码或数据（`oh-my-rime` 等 GPL-3.0 仓库的文件未进入包内，
已在审计里逐字节排除）。

## 六、提审闸门（这一节是给流程看的，不进页面）

| 项 | 状态 | 卡点 |
|---|---|---|
| `NOTICE` 与本页内容一致 | 已收口（2026-10-22，f19a3fc；14:0x 补 abbr 表判定） | — |
| 应用内声明页可见 | **未做** | 等 CodeArts M-043 渲染本页 |
| dyyRime 授权 | **未取得；主人已定路线 A（D-016）** | 保留全部文件并对外如实标注「授权申请中」；剥离方案封存为备胎（`dyy-strip-plan-2026-10-22.md`），Issue #9 截至 12:5x 仍 0 回复 |
| `abbr_en.txt` / `abbr_num.txt` 来源 | **已判定：本项目自有** | 无卡点（与安卓数据根逐字节相同，三组第三方参照无同名文件；见 `NOTICE` 第三节） |
| 发布 Profile（`.p7b`）+ `.app` 构建 | **已到位**（2026-10-22 13:45 核验：release HAP 27,822,532 B、`.app` 11,791,326 B，sha256 见 `docs/release/SIGNING.md` §8） | 当前 `.app` 出自**脏工作树**，不可提审；等工作树干净后由 Qoder 重建。**2026-10-23 08:4x：13:25 那份已不在盘上（00:08 我执行的 `hvigorw clean` 清空了 `entry/build`，机器上无第三处副本（H-144）），盘上只剩 01:17 的 debug 包，不能用来提审** |
| 隐私政策 / AGC 隐私表单 | 文案已备（`docs/release/legal/agc-privacy-form.md`） | 主人登录 AGC 填表 |
| 工信部 APP 备案 | **免办（D-018：单机应用）** | 提审时按「单机应用」勾选；硬约束：任何版本不得新增网络权限，否则申报口径不符 |
| 软著 / 电子版权 | 材料已备（`docs/release/copyright/`） | 主人选路线（D-006 未答）并提交 |
| 商店素材 | 文案已备（`docs/release/store/listing.md`） | 截图待主人解锁 Mate 80 后重拍（H-081/082/084 已 VERIFIED） |
| ~~开发者激励计划（D-019）~~ **已放弃本次时间窗（D-027）** | 个人账号可参与，无需注册公司（评估留档） | 无需动作；12-31 截止与商户服务随之作废 |
