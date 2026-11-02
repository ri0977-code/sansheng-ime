# 下架 dyy 层预案（**当前状态：预案，未执行**）

*三生输入法 · 2026-10-20 起草 · 数字全部来自本机实测扫描，脚本口径写在第六节*

这是「dyy（happyDom / yaoyuan.dou）回一句『不允许』之后怎么在 24 小时内干净撤下」的操作预案。
**今天不做**。写出来的原因是主人 2026-10-20 定的口径：授权拿不到时不主动砍功能，但必须随时能砍。

---

## 一、触发条件（满足任一条才执行）

1. dyy 在 [Issue #9](https://github.com/happyDom/dyyRime/issues/9) 或邮件里明确回「不允许」；
2. dyy 提出我们无法执行的条件（例如要求停止分发且不可谈）；
3. 主人自己判断风险要主动避险。

他若回「同意 + 指定协议」，走另一条路：把协议文本放进 `LICENSES/`、表头补授权行、不删任何文件。

**不回复不构成触发条件。** 主人 2026-10-20 23:5x 定的口径是：等不到回复也照发 v1.10，本预案只是他一句「不允许」时的执行手册。

---

## 二、要撤走的东西（实测数字）

| 范围 | 数量 | 说明 |
|---|---|---|
| 桌面仓库归属 dyy 的文件 | **39 个** | `THIRD_PARTY_NOTICES.md` 第二节逐文件表实测：32 个在 `rime/lua/`，7 个在 `rime/` 与 `rime-config/`（4 个 yaml + `rime.lua` + 2 个 `Custom_phrase.txt`） |
| 其中一字未改的原样转发 | 30 个 | 删掉不需要判断，直接移走 |
| 其中我们改过的 | 9 个 | `dic_4w.lua`（懒加载开关）、`inputShow_Filter.lua`、`inputShow.lua`、`latexLettersInWubi.lua`、`rime.lua`（补注册）、`wubi_pinyin.custom.yaml`、`default.custom.yaml`、`weasel.custom.yaml`、`Custom_phrase.txt` |
| 大体积数据 | **2,922,544 B（2.8 MB）** | `dic_4w_cn.txt` 888,075 + `dic_4w_en.txt` 2,022,029 + `eventsList.txt` 12,440 |
| 安卓 `rime/lua/` | 40 个 `.lua` | 比桌面多 3 个自研（`codeLookup_Filter`、`phoneComment_Filter`、`Custom_phrase_Full`），dyy 部分同上 |
| 已经公开的分发事实 | 桌面 v1.9.10（2026-10-20 Release，带 exe）+ 安卓 1911 | 撤下动作只能对未来版本生效，收不回已下载的用户 |

撤走的代价 = 产品卖点：**中英互译注释、编码反查、智能日期/时间/农历/节气、节日提醒、候选注释、表情与 Unicode 扩展、敏感词替换、LaTeX 公式**。这些全部长在这 39 个文件上。

---

## 三、切割点（一处一处列，别漏）

1. **`rime-config/rime.lua`** —— 17 条注册（`help_translator`、`inputShow_translator`、`codeLookup_Filter` 这 3 条是自研，其余 14 条属 dyy 层）；**安卓 `rime/rime.lua`** 18 条。删函数定义但**保留自研 3 条**。这里历史上踩过雷：漏注册直接「打不出汉字」，改完必须整表核对。
2. **`rime-config/wubi_pinyin.custom.yaml`** —— `filters` / `speller` 里出现 12 个 lua 名，其中 10 个属 dyy（`Upper_Filter`、`dateTime_Filter`、`dic_4w_Filter`、`dynamicPhrase_Filter`、`inputShow_Filter`、`laneChangeAndSpace_Filter`、`phraseComment_Filter`、`phraseExt_Filter`、`phraseReplace_Filter`、`pinyinAdding_Filter`），2 个自研（`codeLookup_Filter`、`phoneComment_Filter`）。
3. **`rime-config/wubi_pinyin.schema.yaml`** —— 12 个 lua 名，同上口径处理。
4. **`wubi86_jidian_trad_pinyin.schema.yaml`** —— 只有 `date_translator`、`single_char_first_filter` 两条，来自**极点五笔**（Apache-2.0），与 dyy 无关，**不动**。
5. **`rime.lua` 之外**：`default.custom.yaml`、`weasel.custom.yaml` 的文件骨架源自 dyy 配置包，但内容早已被我们换成三生自己的方案清单和主题设置 → 保留文件、只在 notices 里把归属改成「结构承自 dyyRime，内容已重写」，不删。
6. **镜像与产物**：`packaging/stage/config`、`packaging/stage/patched`、`packaging/release/config` 三处是旧副本，`build-stage-workbuddy.py` 取料自正在运行的 `D:\Program Files\Rime`、`build-android-qoder.py` 取料自 `packaging/release/config` → 只删仓库不生效，四个位置 + 两个运行目录都要同步。
7. **英文缩写流行词（1.10 新增）不受影响**：`abbrGloss_Filter.lua` + `abbr_en.txt` 是我们自研，数据表也是自采，不在 39 个里。

---

## 四、一个降低风险的实测结论：整条链是 `pcall(require, ...)`

抽查全部 `rime/lua/*.lua` 的 `require` 写法，dyy 的 32 个文件**无一处裸 `require`**，统一是：

```lua
local logEnable, log = pcall(require, "runLog")
local utf8StringEnable, utf8String = pcall(require, 'utf8String')
```

意味着**把 dyy 的 .lua 删掉不会让输入法崩溃，也不会让部署失败**，只会让对应功能静默失效。
但有两个连带点必须处理：

- `runLog.lua`、`sysInfo.lua`、`utf8String.lua` 是**基础库**，被 dyy 的几乎每个文件和我们的 `codeLookup_Filter.lua`、`Custom_phrase_Full.lua` 依赖。
  删掉后自研模块会走进 `pcall` 失败分支（少日志、少 UTF-8 辅助，功能可用但退化）。
  两条路：① 这三个基础库留下（它们同样属 dyy 版权，等于没撤干净）；② 自研替换，估 30–60 行，半天工作量。**建议 ②**。
- 反过来，这条结论也说明「用户自己装 dyyRime 当作可选扩展包」技术上可行（缺文件不崩），只是体验差。

---

## 五、执行流程（24 小时版，每步都可回退）

| 步 | 动作 | 回退 |
|---|---|---|
| 0 | 全量快照：仓库 `git stash` 前先建分支 `dyy-remove`；两个运行目录整目录复制到 `_sansheng_backup/<日期>-dyy-remove/` | 快照本身即回退点 |
| 1 | 移出 32 个 `rime/lua/*.lua` + 2 个 `rime/lua/dic_4w_*.txt` + `eventsList.txt` + 7 个 yaml/txt（用 `shutil.move`，不 delete） | 从备份目录原路 copy 回来 |
| 2 | 清 `rime.lua` 注册表：删 dyy 14 条，保留自研 3 条 | 备份的 `rime.lua` 覆盖 |
| 3 | 清两个 schema / custom.yaml 的 filters 与 key_binder 引用 | 同上 |
| 4 | 自研替换 `runLog` / `sysInfo` / `utf8String` 的最小实现，接到 `codeLookup_Filter`、`Custom_phrase_Full` | 保留旧文件在备份，改回 require 名即可 |
| 5 | 同步 4 个镜像位置 + 2 个运行目录，跑「重新部署」，看 `rime.log` 无 error | 部署回旧目录快照 |
| 6 | 回归清单：打汉字、中英互译（应无）、日期 `date`、LaTeX、表情、敏感词（应无）、编码反查（应有）、自定义短语（应有）、简繁切换、方案切换 | 任一项异常 → 整目录回退 |
| 7 | 发版口径：`v1.11-lite`（或直接 1.10 不带 dyy 层），Release 说明写「应原作者要求移除其 lua 功能层，中英互译/日期/表情/LaTeX 等功能下线」+ 保留 `THIRD_PARTY_NOTICES.md` 的 dyy 段落作为历史与署名 | 文案改动无关功能 |

**不做的事**：不卸载用户已装的输入法、不动用户词库与 `sync/`、不改用户已选方案（中州韵仍是默认）。

---

## 六、数字怎么复现

- 39 个文件与 30/9 的原样/改版拆分：`THIRD_PARTY_NOTICES.md` 第二节逐文件表（逐文件字节比对本机 `D:\IDM\dyyRime-master`）。
- 数据体积、`rime/lua` 文件数、各 yaml 里的 lua 名、`rime.lua` 注册条数、`pcall(require` 结论：
  本机只读扫描脚本 `C:\temp\dyy_scan.py`，输出 `C:\temp\dyy_scan.json`（2026-10-20 23:23）。
- 未验证项：`pcall` 降级后的**真实手感**（注释消失、快捷键是否留空转）——真要执行前必须在沙盒部署一次实测，别只看代码。

---

*本预案存在的原因：上游 `happyDom/dyyRime` 没有 LICENSE 文件（GitHub API `license` 字段为 null）= 默认保留所有权利。请求已公开挂在 Issue #9，等回复。*
