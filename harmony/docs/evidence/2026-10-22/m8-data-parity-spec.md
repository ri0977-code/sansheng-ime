# M8 数据对等任务书：照抄安卓版三生自己的 Rime 数据

> 撰写：Qoder · 2026-10-22 09:34
> 执行人：**CodeArts**（M-059）
> 主人指令原话：「安卓版三生比较适合我们，里面好多功能是其他输入法没有了，所以你就以他为参照来做，每一项功能都来参考一下，就不走冤枉路了」「要不直接让他去看nova6手机吧，都抄过去」
> **本文件里的每一个数字都是 Qoder 用命令行实测出来的，不是推测。实测方法写在 §5，你自己能复现。**

---

## 1. 基准在哪（三个源，别找错）

| 源 | 路径 | 说明 |
|---|---|---|
| **安卓版数据（基准，优先级最高）** | `F:/dshdesktopwork/sansheng-ime-android/rime/` | 74 个文件，全部 mtime `2026-10-21 21:57` = 打进 1.10.1 APK 的那版，主人手机上天天在用的就是它 |
| 上游 rime 预设（运行必需） | `F:/dshdesktopwork/sansheng-ime-android/APK/org.fcitx.fcitx5.android.plugin.rime-0.1.3-0-g048f581c-arm64-v8a-release.apk` 内 `assets/usr/share/rime-data/` | 实测有 `default.yaml` 1301B、**`symbols.yaml` 28473B**、`punctuation.yaml` 2107B、`key_bindings.yaml` 3117B、`pinyin.yaml` 4895B、`essay.txt` 5887417B、`luna_pinyin.*`、`stroke.*` |
| 鸿蒙现状 | `F:/qoderwork/sansheng-ime-harmony/entry/src/main/resources/rawfile/rime/` | 64 个文件，由 `scripts/port_rime_data.py` 从**桌面端**根目录挑出来 |

**根因**：`port_rime_data.py` 的 `ROOTS` 只有 4 个桌面根（`F:/workbuddywork/三生输入法/rime`、`.../rime-config`、`D:/Program Files/Rime`、`%APPDATA%/Rime`），**没有安卓版那个根**。所以安卓版 10-21 21:57 之后改的齿轮，鸿蒙一份都没拿到。

实测举例（同一文件三处对比，安卓最新）：

| 文件 | 安卓版 | 桌面 rime-config | D: 运行目录 | 鸿蒙现有 |
|---|---|---|---|---|
| `wubi_pinyin.schema.yaml` | 4628B / 10-21 21:57 | 4436B / 10-16 14:38 | 4436B / 10-16 | 4669B（移植改写） |
| `wubi_pinyin.custom.yaml` | 5890B / 10-21 21:57 | 5167B / 10-21 14:38 | 5167B | 6042B（移植改写） |
| `lua/dic_4w.lua` | 2235B / 10-21 21:57 | 1812B / 10-18 | 1891B / 08-09 | **1812B（旧版）** |

## 2. 已经坐实的功能缺口（按收益排序）

### 2.1 【最高优先】`/xx` 斜杠符号直出在鸿蒙上大概率全灭

实测证据链，四条都在：

1. 安卓 `wubi_pinyin.custom.yaml:70` → `punctuator:` 下面是 **`import_preset: symbols`**。
2. 鸿蒙同一位置（`wubi_pinyin.custom.yaml:76` 附近）→ `punctuator:` 下面是 **`import_preset: default`**。
3. 鸿蒙 `rawfile/rime/` 里**既没有 `symbols.yaml`，也没有 `symbols.custom.yaml`**（`find` 实测 64 个文件清单里没有）；`symbols.yaml` 只在 rime 插件 APK 的 `rime-data/` 里（28473B）。
4. 两边 `custom.yaml` 里都带着同一句作者注释：「没这一行，`symbols.custom.yaml` 里那 **107 组 `/xx` 符号**一个都出不来（2026-10-21 沙箱实测）」。

安卓 `symbols.custom.yaml` 里的 `/xx` 是这类（`head -40` 实测）：`/zt`→➖✔❌❓、`/tj`→★☆评级、`/jd`→进度条方块、`/dc`→☐☑☒✅❌✓✕、`/lm`→ⅰⅱⅲ罗马数字小写、`/lmd`→ⅠⅡⅢ大写、`/szd`→⒈⒉⒊、`/szk`→⑴⑵⑶、`/szm`→〡〢〣苏州码子，加上 `half_shape` 里 `[`→［【〔、`'`→‘’「」、`#`→№╬ 等多选一标点。

要你做的：
- 把 `symbols.custom.yaml`（安卓那份）+ `symbols.yaml`（从插件 APK 的 `rime-data/` 取出）纳入移植清单；确认 `RimeDataInstaller` 会把预设文件释放到 librime 的 **`shared_data_dir`**（不是 user_data_dir），`import_preset: symbols` 才找得到。这一步**必须先读 `entry/src/main/ets/**` 的安装逻辑确认目录，不改 UI 代码**。
- 把 `wubi_pinyin.custom.yaml` 的 `punctuator/import_preset` 从 `default` 改成 `symbols`（或确认 `default.yaml` 已含 `punctuator` 且能被 symbols 覆盖，二者取其一，别双份）。
- **`recognizer/patterns/punct` 那行鸿蒙已经有了**（`"^/([0-9]0?|[A-Za-z]+)$"`），所以缺的只是预设数据，不是接线。

### 2.2 手机版注释截断滤镜 `phoneComment_Filter`

安卓滤镜链尾部实测（`wubi_pinyin.custom.yaml:53`）：

```
- lua_filter@phoneComment_Filter   # 安卓版：注释折成单行并按显示宽度截断（桌面版上限 150 字符，手机上会撑成 3 行）
```

安卓文件头注释写明它替代 `laneChangeAndSpace_Filter` 的链尾位置；鸿蒙链尾还是 `laneChangeAndSpace_Filter`，且 `rime.lua` 没注册 `phoneComment_Filter`。另外 `encnDic` 开关：安卓 `reset: 0`（默认关长释义，注释说「长释义手机上占屏，开关仍在可开」），鸿蒙 `reset: 1`。

⇒ 这两条和主人现在骂的「候选栏拥挤、后半截空的」**直接相关**，属于「数据侧的密度修复」，和 CodeArts 自己手上的 H-077（UI 侧密度）是两条腿，都要做。

### 2.3 16 个「安卓有 / 鸿蒙没有」的文件，先分类再抄

清单（`comm -23` 实测）：`_包版本.txt`、`_必读_使用方法.txt`、`default.custom.yaml`、`symbols.custom.yaml`、`lua/Custom_phrase_Full.lua`、`lua/force_gc.lua`、`lua/help_translator.lua`、`lua/inputShow_translator.lua`、`lua/latexHelp_translator.lua`、`lua/latexLettersInWubi.lua`、`lua/latex_translator.lua`、`lua/phoneComment_Filter.lua`、`lua/pinyin_Filter.lua`、`lua/pinyin_translator.lua`、`lua/wubi86_jidian_date_translator.lua`、`lua/wubi86_jidian_single_char_first_filter.lua`、`lua/wubi86_jidian_single_char_only.lua`。

**重要，别当任务清单直接抄**：Qoder 已 grep 过 `latex_translator`、`latexHelp_translator`、`pinyin_translator`、`pinyin_Filter`、`Custom_phrase_Full`、`force_gc`、`wubi86_jidian_*` 在安卓 `rime/*.yaml` 里的引用，**一条引用都没找到**（只在词库正文里撞见 `latex`、`jidian` 这种无关词条）。它们只在安卓 `rime.lua` 里被 `require` 过，属于**注册了但没接线的死代码**。
你的活：逐个复核（含 `default.custom.yaml`、`symbols.custom.yaml`、`pinyin_simp.schema.yaml`），分成三类写进清单，只把「真被 yaml 引用」和「运行必需预设」搬过来；死代码**不要**搬（搬了多一个齿轮就多一分抛错打断候选链的风险，见 H-044 教训）。

### 2.4 齿轮注册数：安卓 20 / 鸿蒙 15

安卓 `rime.lua` 全文实测注册的齿轮里，鸿蒙 `need(...)` 缺 5 个：`pinyin_translator`、`pinyin_Filter`、`latex_translator`、`latexHelp_translator`、`phoneComment_Filter`。前 4 个按 §2.3 判定（大概率不补），**只有 `phoneComment_Filter` 是真被链引用的**，必须补。

### 2.5 两边都有但内容不同：鸿蒙普遍比安卓旧

`cmp` 实测有差异的共享文件 54 个（不算文件名带空格的那 8 个 `phraseComment*/phraseExt*` 数据表，它们需要单独处理：路径含空格，shell 一定要加引号）。Lua 齿轮普遍「安卓大、鸿蒙小」约 7%（例：`dic_4w.lua` 2235 vs 1812、`codeLookup_Filter.lua` 20987 vs 21408 反例）。
你的活：**逐文件 diff 判断差异性质**，输出三选一结论：
- 安卓更新，鸿蒙落后 → 覆盖（但要保留鸿蒙的移植改写：去 Windows 专用逻辑、BOM、`need()` 桩等）；
- 鸿蒙更新（例如 `runLog.lua` 1191 vs 2939、`sysInfo.lua` 4578 vs 4686、`wubi_pinyin.custom.yaml` 里我们自加的 `script_translator@pinyin` M5/D-012）→ **保留鸿蒙**，不许覆盖回去；
- 纯移植改写（注释/缩进/编码）→ 保留鸿蒙，记录一行说明。
**词典类**（`wubi86.dict.yaml`、`cn_pinyin_wp`、`zh2en_*_wp` 等）体积双向都有大小差异，必须按 mtime + 内容判断，取最新最全那份；`zh2en_pinyin.dict.yaml` 只差 1 字节这种，也要写清是什么差异，别留悬案。

## 3. 明确不许动

- `entry/src/main/ets/pages/KeyboardIndex.ets` —— 你自己在 M-058 里正在改的文件，本任务**先不碰**，等 M-058 收口后再统一构建，避免两个任务互相覆盖。
- NAPI / `fanxing_napi.cpp` / librime 桥：本任务不动（真要动先在 MAILBOX 说一声）。
- `build-profile.json5`、`module.json5`、`sign/**`：不动。
- `rawfile/symbols/symbols.json`（面板符号数据，116 组 / 2093 条）：格式与内容都不动 —— 那是 H-078 UI 的数据源。

**鸿蒙侧代码归你全权改**（主人 2026-10-22 明确：ArkTS/鸿蒙 SDK 你是主力，不要绕回来等我动手）。所以 §2.1 里那句「先读 `RimeDataInstaller` 确认 `shared_data_dir`/`user_data_dir` 释放逻辑」不是限制，是**你的实现步骤**：如果预设文件（`symbols.yaml` 等）现在只释放到 user_data_dir 导致 `import_preset: symbols` 找不到，就改安装逻辑 / 调整释放目标目录 / 必要时确认 `rime_set_logging_level`、`std::shared_ptr<rime::RimeTraits>` 那侧 traits 的 `shared_data_dir` 配置（在 NAPI 里的话按上一条先报备）。改完在 `m8-parity-result.md` 写清楚「为什么必须动这处、动了哪一行」。

允许改：`entry/src/main/resources/rawfile/rime/**`、`entry/src/main/ets/**`（IME 数据安装与配置部分）、`scripts/port_rime_data.py`、`docs/**`、必要时 `entry/src/main/cpp/**`（先 MAILBOX 报备）。

## 4. 交付要求

1. 先改 `port_rime_data.py`（加安卓版根、补 FILES 清单、补死代码判定逻辑），再跑 `python scripts/port_rime_data.py --dry`，把 dry-run 输出留档到 `docs/evidence/2026-10-22/m8-port-dry.txt`；确认无误再正式跑一次，manifest 落到 `docs/evidence/2026-10-22/m8-data-manifest.json`（**别覆盖 M3 那份**）。
2. 齿轮完备性检查必须过（脚本里已有：yaml 引用 ↔ 模块 ↔ `rime.lua` 全局，缺一个非 0 退出）。
3. 构建出包，报告 HAP 字节数。装真机由 **Qoder** 做，你不要装。
4. 在 `docs/evidence/2026-10-22/m8-parity-result.md` 写：每个缺口一条，格式「文件 / 动作（新增·覆盖·保留鸿蒙）/ 依据 / 真机怎么验」。
5. `python scripts/wip.py log --who CodeArts --milestone M8 --status WIP|READY --files ... --doing ... --impact ...`。
6. **构建绿不算过**：`/szd`、`/jd`、`/dc`、`/lm`、`/fh`、多选一标点（`[` 出 ［【〔）、`'` 出 ‘’「」这些，必须真机打出来才算；Qoder 会在 Mate 80 竖屏+横屏各验一遍才写 VERIFIED。

## 5. Qoder 的实测方法（你复现用）

```bash
A=F:/dshdesktopwork/sansheng-ime-android/rime
H=F:/qoderwork/sansheng-ime-harmony/entry/src/main/resources/rawfile/rime
find $A -type f | sed "s|$A/||" | sort > a.txt      # 74
find $H -type f | sed "s|$H/||" | sort > h.txt      # 64
comm -23 a.txt h.txt   # 安卓独有 16 条
comm -12 a.txt h.txt | while read f; do cmp -s "$A/$f" "$H/$f" || echo "DIFF $f"; done
grep -nE "translator|filter|switches" $A/wubi_pinyin.custom.yaml
grep -n "need(" $H/rime.lua
unzip -l <插件APK> | grep rime-data
```
控制台是 GBK，中文 `print` 会乱码 —— 一律写 UTF-8 文件再用 Read 读回。

## 6. 分工（主人 2026-10-22 09:38 最终定调：**活全给 CodeArts，含真机自验；Qoder 只做验收评估与核对**）

> 主人原话：「真机他也能看的吧，都连在电脑上，他怎么看不了，你就做验收评估，核对，不好吗，活都交给他，抄完自己验证，一气呵成，比来回核对不好吗，效率不高吗」
> ⇒ 鸿蒙侧从**抄安卓 → 写代码 → 装机 → 真机自验 → 落证据**由 CodeArts 一个人闭环，不再来回转手。两台手机都连在这台电脑上，你自己能开。

| 谁 | 干什么 |
|---|---|
| **CodeArts** | ① M-058（H-077 候选密度 + H-078 `?123` 面板照抄安卓）+ M-059（H-079 `/xx` 符号直出 + H-080 数据对等）+ 后续所有鸿蒙实现；② **自己开 nova 6 抄界面、自己装 Mate 80 自验**（命令见 §7）；③ 交付三件套：构建产物字节数 + 真机截图（竖屏/横屏各一套，存 `docs/evidence/2026-10-22/`）+ hilog 关键行；④ 需要主人拍板的（图标、邮箱、AGC 点击）才升级到 MAILBOX |
| **Qoder** | ① **验收评估与对抗核对**：你报的每个数字我独立复测一遍才写 VERIFIED，「构建绿不算过」由我把关；② 上架与合规：发布签名链路、隐私政策/用户协议、软著与备案、AGC 商店素材与提审字段、第三方许可声明（含本轮带入的上游 rime-data）；③ 基准资料定位（§1 三个源 + APK 内 rime 预设路径）与主人新需求的路由、优先级排序 |

**两台设备使用规则（防撞车）**：动手前在 `docs/MAILBOX.md` 写一行「占用 Mate80 / nova6 至 HH:MM」，完事写「已释放」；`wip.py log` 里带设备名。同一设备同一时刻只允许一方操作。
nova 6 是**参考机不是测试机**：只看不改，测完必须 `$ADB shell ime set com.baidu.input/.ImeService` 还原并用 `settings get secure default_input_method` 确认。Mate 80 是**我们的目标机**，装机回归都在它上面。

## 7. 你自己上设备的命令（Qoder 已实测可用）

```bash
# ---- Mate 80（VYG-AL30，1280x2832，竖屏面板约 360vp）----
cd /f/qoderwork/sansheng-ime-harmony && . scripts/dev_env.sh      # 提供 HDC / d_tap / d_swipe / dshot / d_start / d_stop
"$HDC" shell snapshot_display -f /data/local/tmp/s.png
"$HDC" file recv /data/local/tmp/s.png s.png        # recv 目标必须用相对路径，写 /f/... 会静默失败
"$HDC" hilog | grep -E "cand=|all=|page=|uiSize|rendered"    # H-077 判定就靠这几行
bash scripts/build.ps1 ; bash scripts/sign.ps1 ; "$HDC" app install <hap>

# ---- nova 6 参考机（WLZ-AN00，1080x2400，serial HBX4C19C02009787）----
ADB="G:/Android/Sdk/platform-tools/adb.exe"
$ADB shell ime set com.sansheng.ime/org.fcitx.fcitx5.android.input.FcitxInputMethodService
$ADB shell am start -n com.sansheng.ime/org.fcitx.fcitx5.android.ui.main.MainActivity
$ADB shell input tap 540 1200
$ADB exec-out screencap -p > ref.png
MSYS_NO_PATHCONV=1 $ADB shell uiautomator dump /sdcard/w.xml
MSYS_NO_PATHCONV=1 $ADB exec-out cat /sdcard/w.xml > w.xml
# ↑ 不加 MSYS_NO_PATHCONV=1，Git Bash 会把 /sdcard 翻译成 Windows 路径，dump 落不到设备上（我已踩过）
$ADB shell ime set com.baidu.input/.ImeService      # 用完还原
```

**安卓设置界面结构（Qoder 09:41 真机 uiautomator 实测）**：首页本身就是设置列表，**没有抽屉**；13 行自上而下：`三生输入法`（标题行，点不进）/ `Fcitx` / `全局选项` / `输入法` / `附加组件` / `Android` / `主题` / `虚拟键盘` / `候选窗口` / `剪贴板` / `表情和符号` / `插件` / `高级`。
坐标：`x=400`，`y` 依次 `178 375 504 665 826 1011 1140 1301 1462 1623 1784 1945 2106`（1080x2400）。
**遍历脚本已写好**：`tmp-androidwalk/walk2.sh`（每项：`am start` 回列表 → 点进去 → dump+截图 → 上滑两屏再 dump+截图；产物落 `tmp-androidwalk/walk2/`）。
**坑（我已踩过，别再踩）**：不要用 `KEYCODE_BACK`+侧滑去找"抽屉"，BACK 从列表页会直接退出 app；Qoder 这样误退到了主人的记事本 app，第一版清单全部作废。每项开头重新 `am start` 就是回到列表，最稳。
