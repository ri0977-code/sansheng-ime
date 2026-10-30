# 00:09 clean 构建 + 包内 16 项闸门（Qoder 独立验收）

- 时间：2026-10-23 00:08–00:09
- 目的：CodeArts H-106 尚未交付（`git log` 仍止于 `bbb2229`，`KeyboardIndex.ets` mtime 23:36 未变），
  先对**当前未提交工作区**做一次“从零”编译验证，防止 23:48 的产物只是增量缓存假绿；
  同时把 H-110/H-111/H-112/H-090 从“源码侧发现”升级为“包内实测”。
- 约束遵守：源码 mtime 23:36（距构建 >120 s）；构建期间 `wmic` 未发现任何 hvigor/assembleHap 进程；
  仅构建，未 sign、未 install、未动 `entry/src/**`。

## 1. 过程与结果

| 步骤 | 命令 | 结果 |
|---|---|---|
| 快照旧产物 | `cp …/entry-default-unsigned.hap %TEMP%/ss-hap-archive/prev-2348-codearts.hap` | 28,178,736 B，md5 `53194cdd8f23…` |
| 官方 clean | `node hvigorw.js clean --no-daemon` | BUILD SUCCESSFUL，3 tasks executed |
| 全量构建 | `scripts/build.ps1 -Product default -BuildMode debug` | BUILD SUCCESSFUL in 10 s 360 ms，**32 executed / 1 up-to-date** |
| 产物 | `entry/build/default/outputs/default/entry-default-unsigned.hap` | **28,178,736 B**，md5 `b65d29ea5bd5…` |

注：clean 只清了 `entry/build` 与模块产物，`entry/.cxx` 的 CMake 缓存仍在，
所以原生库是复用、ArkTS/资源/打包是真跑（32/33 个任务 executed）；足以验证 ArkTS 全量编译。

## 2. 字节数一致、md5 不一致的原因（重要，别误判）

与 23:48 产物相比：83 个 zip 条目名完全一致、字节数一致，仅 5 个条目 CRC 不同：
`module.json`、`resources.index`、`resources/base/media/layered_image.json`、
`resources/base/profile/input_method_config.json`、`ets/sourceMaps.map`。

逐字 diff 证明差异只是**资源 ID 重新编号**（clean 构建的枚举顺序不同），不是源码变化：

```
module.json            iconId 16777223 → 16777224
layered_image.json     background/foreground 16777221/16777222 → 16777222/16777223
input_method_config    subtype icon 16777225 → 16777226
```

结论：**验收口径只能用“字节数 + 包内内容检查”，不能用 md5 比两个 agent 的产物**。
同源同参数构建字节数稳定（两次均 28,178,736 B），md5 会因资源 ID 重排而变。

## 3. 包内 16 项闸门

```
python scripts/check_app_content.py entry/build/default/outputs/default/entry-default-unsigned.hap
结果: 14/16 通过；阻断项未过 0 个
结论: 阻断项全部通过。
WARN 9b app_icon.png 48x48/182B 全不透明=True ⇒ DevEco 模板（H-105）
WARN 10 main_pages 仍注册探针页（H-098）
```

## 4. 包内实测（源码侧三项发现的包级确认）

| 项 | 包内事实 | 结论 |
|---|---|---|
| H-111 | `resources/rawfile/rime/lua/phoneComment_Filter.lua` 在包内，**2,397 B**；但 `wubi_pinyin.custom.yaml` 与 `wubi_pinyin.schema.yaml` 的过滤链尾都是 `- lua_filter@laneChangeAndSpace_Filter` | 手机注释截断**仍未生效**；不是“文件没打进包”，是“打进包但没接线” |
| H-112 | `input_method_config.json` 两个子类型 `id` 都是 `"InputMethodService"` | 与 HEAD 的两个不同 id、官方样例不一致 |
| H-090 / H-098 | `main_pages.json` 仍是 8 条：`Index, KeyboardIndex, LandscapeProbe, M3Probe, AboutPage, LegalPage, SettingsPage, SettingsCategoryPage` | 设置两页虽无入口仍会打进 `.app`；探针页同样 |

## 5. 对下一轮的意义

- CodeArts H-106 交付后，我按同一口径验收：clean 构建 → 字节数比对 → sign+install → 16 项闸门 → 真机 6 条。
- H-111 的两行链尾替换、H-110 的三个文件登记、H-112 的 id、H-090 的两条路由，**都必须出现在同一个本地 commit 里**，
  否则下一次出包还是这份“包内有滤镜、链上没有”的状态。

## 6. 设备侧只读核对（00:12，不唤醒屏幕、不碰锁屏）

```
hdc list targets                     → 7GL0226408083897
bm dump -n com.sansheng.ime          → versionName 1.0.0 / debug=true / appProvisionType=debug
firstInstallTime                     → 2026-10-19 22:52:52
installTime                          → 2026-10-22 22:19:40
updateTime                           → 2026-10-23 00:05:03
```

解读（推断，非字节级证明）：00:04:40 出现过一份 signed 产物，23 秒后设备 `updateTime` 刷新
⇒ 手机当前跑的应是 23:48 unsigned 的签字版（资源 ID 与本轮 00:09 clean 版不同、内容等价）。
因此**本轮不重复装机**（同一份源码，只差资源编号）；H-086 状态不变：默认输入法仍不是三生，面板不可测。
`updateTime` 只能证明“某次 debug 包在 00:05 装过”，不能证明装的就是哪一份字节；真要确认须等下次装机前先量包内哈希。
