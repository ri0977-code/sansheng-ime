# dyy 同名文件逐行复核：7 个改写 / 6 个独立重写（2026-10-24 00:0x · Qoder）

## 为什么做这一轮

`scripts/third_party_audit.py` 的「dyy同名已改」是**按文件名**判的启发式：
只要 `dyyRime-master` 里有同名文件、字节又不同，就记成「改写衍生」。
本轮它数出 **13 个**（`total=65 same_android=17 dyy_same=29 dyy_modified=13 orphan=16`），
但 13 里混进了 `README.md`、`rime.lua` 这类**同名却零重合**的本项目自写文件。
把它们写进 NOTICE 的「在其基础之上改写」，等于凭空承认上游对我们自己的代码享有权利 ——
这对本项目不利，也不符合事实。所以逐个用 `difflib` 做行级比对，按实测分级披露。

## 复核命令（可复现）

```bash
python scripts/third_party_audit.py 2026-10-24     # 全量 65 文件，逐文件 md5
# 行级相似度：difflib.SequenceMatcher(None, ours.splitlines(), dyy.splitlines()).ratio()
```

参照树：`D:/IDM/dyyRime-master/dyyRime-master/`（仓库无 LICENSE 文件）。
另核对：29 个原样文件合计 **3,197,403 B** 与上一轮一致；`symbols.custom.yaml` 已不在包内。

## 逐文件实测

| 文件 | 我方行 | dyy 行 | 命中行 | 行级相似 | 归类 |
|---|---:|---:|---:|---:|---|
| `lua/inputShow.lua` | 154 | 153 | — | **98.4%** | ① 改写 |
| `lua/Upper_Filter.lua` | 75 | 73 | — | **97.3%** | ① 改写 |
| `lua/inputShow_Filter.lua` | 268 | 253 | — | **94.8%** | ① 改写 |
| `lua/dic_4w_Filter.lua` | 78 | 54 | — | **78.8%** | ① 改写 |
| `Custom_phrase.txt` | 47 | 22 | — | **46.4%** | ① 改写（共用 `@ at`、latex、换行词条等实体行） |
| `wubi_pinyin.custom.yaml` | 96 | 58 | — | **41.6%** | ① 改写 |
| `lua/sysInfo.lua` | 146 | 189 | 64 | **38.2%** | ① 改写（`currentDir()` 等函数体原样保留，文件头自述） |
| `lua/runLog.lua` | 93 | 54 | 16 | 21.8% | ② 同名重写（命中行几乎全是 `end`/空行，仅 1 行实体 `local current_path=…`） |
| `lua/socket.lua` | 47 | 58 | 8 | 15.2% | ② 同名重写（安全桩；命中行是空行 / `local M = {}` / `end` / `return M`） |
| `lua/phraseExt personal.txt` | 3 | 15 | 1 | 11.1% | ② 同名重写（唯一命中是空行；我方是自写模板） |
| `lua/phraseComment personal.txt` | 3 | 17 | 1 | 10.0% | ② 同名重写（同上） |
| `rime.lua` | 106 | 16 | **0** | **0.0%** | ② 同名重写（我方是 pcall 容错加载器，与上游逐行无交） |
| `README.md` | 73 | 241 | **0** | **0.0%** | ② 同名重写（我方是鸿蒙数据说明，与上游文档无关） |

合计 **13 = 7（① 改写）+ 6（② 独立重写）**。

## 口径

- **① 改写**：保留上游代码片段 ⇒ 主体版权归上游，本项目只主张自己那部分改动；
  授权申请覆盖这 7 个 + 29 个原样文件。
- **② 同名重写**：只沿用模块名/文件名与调用契约（`M.xxx` 函数名、返回形态），
  无逐行复制 ⇒ 按 Apache-2.0 归本项目；在 NOTICE 与 README 中列出**仅为对照**，
  避免审核方在包里看到同名文件却找不到说明。
- 若上游回复中对某个 ② 类文件主张权利，以逐行比对表为起点重谈，不在本次预判。

## 同步改动

- `NOTICE`：dyy 条目改为两级披露（7 改写 / 6 同名重写），新增「第三轮核查（2026-10-24）」。
- `entry/src/main/resources/rawfile/rime/README.md`：许可表按两级更新；
  顺带修正 `wubi86.dict.yaml` 行残留的「Apache-2.0」旧口径（同文件第 41 行早已更正为 LGPL-3.0）。
- `entry/src/main/resources/rawfile/legal/notice.html` 与 `docs/release/legal/notice.html`：
  由 `python scripts/build_notice_html.py --public` 重新生成，两份逐字节相同（77,255 B）。
