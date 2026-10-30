# H-222 证据包：port_rime_data.py 非只读运行把桌面端词库配置盖进了鸿蒙包

整理：(Qoder) 2026-10-27 15:4x。本目录里的文件**全部是覆盖发生后（15:27 状态）的原样留存**，
不是我改过的版本 —— 目的是：① 证据可复核；② 若主人/CodeArts 认可这次对齐，一条命令就能重新应用；
③ 未获认可前，鸿蒙包保持 HEAD 状态。

## 这份目录里有什么

| 文件 | 是什么 |
|---|---|
| `wubi_pinyin.custom.yaml`（5,862 B） | 15:27 被写进 rawfile 的**桌面板**（对照 HEAD 鸿蒙版 6,264 B） |
| `wubi_pinyin.schema.yaml`（5,029 B） | 15:27 被写进 rawfile 的**桌面板**（对照 HEAD 鸿蒙版，`db_class` 被改回 `tabledb`） |
| `zh2en_pinyin.dict.yaml`（440 B） | 15:27 的 import_tables 壳（对照 HEAD 全量表 2,163,401 B） |
| `symbols.yaml`（28,473 B）/ `symbols.custom.yaml`（11,696 B） | 15:27 被放进 rawfile 的上游符号表 —— D-020 提审阻断项，已从 rawfile 请出，存放在 `quarantine-from-rawfile/` |
| `m3-data-manifest.json`（15:27 版） | 那次运行的清单：`generated_at: 2026-10-27 15:27:18`，`total_bytes: 15,049,369`（HEAD 版是 `2026-10-21 22:30:55` / `20,528,604`） |
| `m3-port.log` | 同一次运行写的移植日志（该文件被 `.gitignore` 的 `*.log` 忽略，所以 git status 里看不到它被改） |
| `rime-overwrite.diff`（2,274,646 B） | 覆盖发生时的 `git diff`（rawfile/rime + manifest），**重新应用＝`git apply` 这个文件** |

## 覆盖发生的时间点（怎么证明是「非只读运行」）

`scripts/port_rime_data.py` 只在 `dry` 为假时才写 `rawfile/**`、`m3-data-manifest.json` 和
`m3-port.log`（源码 `:633` `if not dry:`、`:657`、`:678`）。实际落盘时间：

```
entry/.../rawfile/rime/wubi_pinyin.custom.yaml   2026-10-27 15:27:17.901
entry/.../rawfile/rime/symbols.yaml              2026-10-27 15:27:17.908
docs/evidence/2026-10-21/m3-data-manifest.json   2026-10-27 15:27:18.159
docs/evidence/2026-10-21/m3-port.log             2026-10-27 15:27:18.159
```

⇒ 15:27:17~18 有一次**写盘**运行。CodeArts 的信（M-259）说他跑的是 `--check`，而脚本 2026-10-22
之后 `--check` 确实等于只读（`check_only = "--check" in sys.argv; dry = dry or check_only`）
—— 所以要么另外还跑了一次不带旗标的，要么旗标没生效。**这一条我没法从他信里判定，留给他自己核对命令历史。**

## 这次覆盖拿掉了什么（四条鸿蒙专用口径）

1. `engine/translators` 里的 `script_translator@pinyin`（M5/D-012/H-089）被桌面的
   `lua_translator@slash_translator` 顶掉 ⇒ 26 键拼音逐字/词组/整句候选没了。
2. `punctuator/import_preset` 从 `default` 回到 `symbols`，且 `symbols*.yaml` 进包 ⇒ D-020 阻断。
3. `lua_filter@phoneComment_Filter`（M-235 主人拍板：手机版显示宽度 20、从右截）被换回桌面
   `laneChangeAndSpace_Filter`（150 字符 + `<br>` 真换行，手机上把一个候选撑成 3 行）。
4. `translator/db_class` 从 `userdb` 回到 `tabledb`（M4：鸿蒙 IME 进程常驻、没有 finalize 回调 ⇒
   `user.txt` 永远只有表头，自造词/自调频跨会话全丢，run16 实测）。

发布闸门 `scripts/check_app_content.py` 当场 13/16（3 条阻断红），unsigned HAP
28,443,643 → 26,235,679 B（少 2,207,964 B，主因是第 5 条：zh2en_pinyin 全量表变成 440 B 壳）。
第 3、4 条**闸门拦不住**（闸门只查 1、2、5 那三类）⇒ 新增开发期守卫
`scripts/rime_harmony_overrides_check.py`（9 条阻断判据 + 1 条 WARN，`--selftest` 用本目录这份真实坏数据验过：阻断命中 5/5、WARN 触发）。

## 处置（15:4x，已做）

- 先留证据（本目录），**再**恢复：`git restore --source=HEAD` 还原
  `wubi_pinyin.custom.yaml` / `wubi_pinyin.schema.yaml` / `zh2en_pinyin.dict.yaml` / `m3-data-manifest.json`；
  `symbols.yaml` / `symbols.custom.yaml` 移入 `quarantine-from-rawfile/`（**没删**）。
- 重建后闸门 16/16、三条守卫全绿（29/29、54/54、9/9），包内 rawfile 与源码树**逐文件逐字节相等**
  （69 个文件 / 20,598,287 B 两边一致）⇒ 词库层零丢失。signed **28,479,875 B**，15:44:29 已装机。
- 未追的账：HAP 容器字节比 r4 少 85,599 B（0.3%）。因为 rawfile 内容层已证明与源码树相等，
  差额只可能出在 zip 容器的压缩/排列上，**不影响数据**；我没有 r4 的原包可比，故不下结论。

## 入库口径（为什么这目录里有东西故意不进 git）

`symbols.yaml` / `symbols.custom.yaml` 与 `quarantine-from-rawfile/`（同一份的两个副本）**留在本地、不入 git**：
它们是 rime 上游符号表，D-020 的结论就是「许可不允许我们再分发」——**提审包不能带，仓库也不该带**，
留在本地只为「主人若点头要用它做桌面端合并，文件还在手边」。
和它同类的 2026-10-26 那批 `trime-*.yaml` 上游转储，历史上也一律未入库（约定＝上游原始配置只当草稿）。
其余（3 个被盖文件的 15:27 原样、`rime-overwrite.diff`、15:27 清单）随本轮提交；
`m3-port.log` 被 `.gitignore:36` 的 `*.log` 规则忽略，所以它在 git 里看不见——内容已抄进本 README 的时间戳链。

## 如果主人要「对齐桌面端」，正确的做法是什么


不是整包替换。逐条决定、逐条合并，且每条要保留鸿蒙侧口径的理由：
`wubi86_jidian` / `cn_pinyin_jidian_wp` 两个导入（桌面 schema 多出 3.8 KB）可以单独加；
`symbols*.yaml` 属于许可问题，**加不进来**（D-020）；`laneChangeAndSpace_Filter`、`db_class: tabledb`
属于桌面专用，**鸿蒙不能用**。跑数请用 `--dry` 或 `--check`，跑完必过
`scripts/rime_harmony_overrides_check.py`。
