# M8 数据对等交付报告（M-059：H-079 + H-080）

> 执行人：CodeArts · 2026-10-22
> 规格：`docs/evidence/2026-10-22/m8-data-parity-spec.md`
> 基准：安卓版 `F:/dshdesktopwork/sansheng-ime-android/rime/`（1.10.1 打包版，mtime 2026-10-21 21:57）
> 构建产物：unsigned 28,043,916 B
> dry-run：`docs/evidence/2026-10-22/m8-port-dry.txt`（files=19, missing=0, diverged=11, PASS 齿轮完备性）

---

## H-079：/xx 斜杠符号直出

| # | 文件 | 动作 | 依据 | 真机怎么验 |
|---|---|---|---|---|
| 1 | `rawfile/rime/symbols.yaml`（28473B） | **新增** | 从 APK `rime-data/symbols.yaml` 取（spec §2.1）；`import_preset: symbols` 需要此预设文件在 `shared_data_dir` | 打 `/szd`→⒈⒉⒊、`/jd`→进度条方块、`/dc`→☐☑☒✅、`/lm`→ⅰⅱⅲ、`/fh`→箭头符号，候选出现并可上屏 |
| 2 | `rawfile/rime/symbols.custom.yaml`（138行/107组） | **新增** | 安卓版 `rime/symbols.custom.yaml`（spec §2.1）；107 组 `/xx` 符号定义在此 | 同上，`/xx` 编码出候选即为生效 |
| 3 | `rawfile/rime/wubi_pinyin.custom.yaml` `punctuator/import_preset` | **覆盖** | `default`→`symbols`（spec §2.1）；安卓版同位置就是 `symbols`，作者注释明确「没这一行 107 组 /xx 一个都出不来」 | 输入 `/` 后跟字母出符号候选 |
| 4 | `engine/RimeDataInstaller.ets` `SHARED_FILES` | **覆盖** | 加 `symbols.yaml`、`symbols.custom.yaml`（spec §2.1）；预设文件必须释放到 `shared_data_dir` 才能被 `import_preset` 找到 | 全新安装后 `/xx` 即可用，无需手动拷文件 |
| 5 | `scripts/port_rime_data.py` | **覆盖** | `REPLACE_LINE` 清空（不再替换 import_preset）；`FILES` 加 `symbols.yaml`/`symbols.custom.yaml` | `python scripts/port_rime_data.py --dry` 输出 PASS |

## H-080：数据对等（手机版注释截断 + encnDic + 移植脚本）

| # | 文件 | 动作 | 依据 | 真机怎么验 |
|---|---|---|---|---|
| 1 | `rawfile/rime/lua/phoneComment_Filter.lua`（59行） | **新增** | 安卓版 `rime/lua/phoneComment_Filter.lua`（spec §2.2）；注释折单行+按显示宽度截断（MAX_WIDTH=20），替代桌面版 `laneChangeAndSpace_Filter` | 候选注释单行显示、不撑高成 3 行；长释义被截断 |
| 2 | `rawfile/rime/rime.lua` | **覆盖** | 注册 `phoneComment_Filter`（spec §2.4）；安卓 `rime.lua` 已注册，鸿蒙缺失 | 齿轮完备性检查 PASS（yaml 引用 ↔ 模块 ↔ rime.lua 全局） |
| 3 | `rawfile/rime/wubi_pinyin.custom.yaml` 滤镜链尾 | **覆盖** | `laneChangeAndSpace_Filter`→`phoneComment_Filter`（spec §2.2）；安卓链尾就是 phoneComment_Filter | 候选注释折行行为与安卓一致 |
| 4 | `rawfile/rime/wubi_pinyin.custom.yaml` `encnDic reset` | **覆盖** | `1`→`0`（spec §2.2）；安卓 `reset: 0`（默认关长释义，手机上占屏） | 长释义默认不展开，开关仍可手动开 |
| 5 | `rawfile/rime/lua-files.txt` | **覆盖** | 加 `phoneComment_Filter.lua` | 安装时该 lua 文件被正确释放 |
| 6 | `scripts/port_rime_data.py` `ROOTS` | **覆盖** | 加安卓版根 `F:/dshdesktopwork/sansheng-ime-android/rime`（spec §1）；原只有 4 个桌面根，安卓版改的齿轮鸿蒙拿不到 | dry-run 输出中 `symbols.custom.yaml` 来源指向安卓根 |
| 7 | `scripts/port_rime_data.py` `LUA_MODULES` | **覆盖** | 加 `phoneComment_Filter` | dry-run 齿轮完备性 PASS |
| 8 | `engine/RimeDataInstaller.ets` `DATA_VERSION` | **覆盖** | `m5-pinyin-v18`→`m8-parity-v19`；数据变更触发重新释放 | 全新安装或升级后新数据生效 |
| 9 | 死代码（7个 lua 模块） | **保留鸿蒙（不搬）** | `latex_translator`/`latexHelp_translator`/`pinyin_translator`/`pinyin_Filter`/`Custom_phrase_Full`/`force_gc`/`wubi86_jidian_*` 在安卓所有 yaml 中无引用（spec §2.3）；搬了多一个齿轮多一分抛错风险（H-044 教训） | 不验（不存在于鸿蒙） |

## 鸿蒙保留项（不许被覆盖）

| 文件 | 原因 |
|---|---|
| `rawfile/rime/lua/runLog.lua` | 鸿蒙沙箱版（1191B vs 安卓 2939B），去 Windows 专用逻辑 |
| `rawfile/rime/lua/sysInfo.lua` | 鸿蒙沙箱版（4578B vs 安卓 4686B），去 Windows 专用逻辑 |
| `wubi_pinyin.custom.yaml` `script_translator@pinyin` | D-012 自加（M5 拼音候选补强），安卓没有 |

## 待真机验收（Qoder 在 Mate 80 执行）

1. `/szd`、`/jd`、`/dc`、`/lm`、`/fh` 出候选并上屏（竖屏+横屏各一遍）
2. `[`→［【〔、`'`→‘’「」多选一标点
3. 候选注释单行不撑高
4. `encnDic` 长释义默认关
5. H-058/059/060/A1–A9 无回归