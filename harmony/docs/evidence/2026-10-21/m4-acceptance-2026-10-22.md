# M4 三生能力 · 真机验收纪要（2026-10-22 00:25）

> 设备 Mate 80 `7GL0226408083897`，HarmonyOS NEXT，横屏 2832×1280。
> 装机包：`entry-default-signed.hap` **27,965,945 B**（unsigned 27,852,654 B），构建日志 `docs/evidence/2026-10-22-build-h061.txt`。
> 结论：**M4 引擎侧目标全部达成**；符号页交互阻断 H-061 已修复并复验；候选页边界 H-058/H-059/H-060 仍是 CodeArts M-047 的 UI 尾项，不阻塞 M4 能力验收。

## 1. 九宫格：一键进布局 + 64426 → 你好

| 项 | 结果 | 证据 |
|---|---|---|
| 26 键点底栏最左「九键」一键进 3×3 | 通过，无二次选择 | `m4-t9-00-mode.jpeg`、`m4-a1-07-t9-grid.png` |
| `64426` 出「你好」 | 通过：预编辑 `64 426 · ni hao`，首候「你好」 | `m4-final-t9-64426.jpeg`、`m4-t9-01-64426.jpeg` |
| 空格/点选上屏 | 通过：输入框落到「你好」 | `m4-final-t9-commit.jpeg`、`m4-t9-03-space-commit.jpeg` |
| T9 下数字进编码而非直出 | 通过（H-028 ① 无回归） | `m4-t9-01-64426.jpeg` |

最终包内同屏还验证了「符号 + emoji + 数字 + T9 中文」连续上屏：输入框最终为 **「，🚹5你好」**（`m4-final-t9-commit.jpeg`）。

## 2. 自造词 / 自调频：真落盘、跨会话、跨升级

数据源为 `[SSM3Probe]` 自检行（已过滤的 hilog 见同目录 `hilog-m4-v14..v18-*.txt`）。

| 能力 | 判据 | 结果 | 证据 |
|---|---|---|---|
| 自造词（跨会话） | 连续上屏「刚」「需」造出 `mqjfdm → 刚需`，杀进程重开后仍命中 | **PASS**（v14-run2、v15、v16、v17 两轮均 PASS） | `hilog-m4-v14-run2.txt` 等 |
| 自造词（再造一组，跨会话） | v18-run3 造 `qqqiiiu → 鑫淼`，v18-run4 重启后命中 | **PASS** | `hilog-m4-v18-run3/4.txt` |
| 自调频（跨会话） | `hello` 提交后升至 `nihao` 首位，重开后仍在首位 | **PASS**（v17-run2、v18-run3/4） | 同上 |
| LevelDB 落盘 | `<user>/user.userdb/` 有非空数据，且随提交增长（876 B → 1157 B → 1434/1745 B → 1184 B） | **PASS** | v17/v18 日志 `PASS userdb[...]` |
| HAP 覆盖安装后学习状态不丢 | 极 被选一次后从第 11 位升到第 2 位；force-stop 重开仍在第 2 位；覆盖安装后仍第 2 位 | **通过** | `m4-persist-00/01/02.jpeg`、`m4-h061-04-ji-after-update.jpeg` |

说明：`grumble` 是移植数据里已有的学习词条，只能证明旧词典被正确加载，**不作为本轮自造词证据**；本轮自造词的干净证据是上面的 `刚需` 与 `鑫淼`。

根因与方案见 `docs/DECISIONS.md` D-010（`tabledb` 纯内存、只在析构落盘 → 改 `userdb`/LevelDB 每次提交写 WAL），接口见 `docs/INTERFACE.md` §8.4/§8.5。

## 3. 符号 / emoji 数据与上屏（H-057 / H-061）

- 数据：`rawfile/symbols/symbols.json` **116 组 / 2093 项 / 660 emoji / 约 35 KB**，启动日志 `SSKeyboardIndex symbols.json loaded: 116 groups`（`m4-cold-final-hilog.txt`）。
- 渲染：常用、表情等分组可切；emoji 按 2 格宽排版（`m4-sym-00-page1.jpeg`、`m4-sym-01-emoji.jpeg`）。
- **H-061 根因**：`fanxing_napi.cpp` 的 `ProcessKey` 只处理单字节 key；符号页送来的「，」是 3 字节 UTF-8、emoji 是 4 字节，全部落到函数末尾 `commit` 为空 —— 页面能看不能点。
- **修复**：`key.size() > 1` 视为字面字符，直接作为 `commitText` 返回，不进 Rime；单字节标点/数字路径不变（`INTERFACE.md` §8.8）。UI 零改动。
- 复验：点「，」→ 输入框「，」（`m4-h061-01-comma.jpeg`）；点 emoji 🚹 → 「，🚹」（`m4-h061-02`）；点数字 5 → 「，🚹5」（`m4-h061-03`）；随后 T9 `64426` → 你好（`m4-final-t9-commit.jpeg`）。数字直出（H-024）与 T9 数字进编码（H-028）均无回归。

## 4. 首启 / 冷启动耗时

最终包冷启动（`aa force-stop` 后重新拉起并点输入框），完整过滤日志 `m4-cold-final-hilog.txt`：

| 节点 | 时间戳 | 耗时 |
|---|---|---|
| `inputStart` | 00:25:57.805 | — |
| `[Rime-Napi] init start` | 00:25:57.789 | — |
| `librime 1.16.1`（数据/共享库装载完成） | 00:25:58.693 | **904 ms** |
| `prebuild=1 (65 ms) files=10 \| deploy=1 (65 ms) files=10` | 00:25:58.824 | **130 ms** |
| `deploy ... files=10` + `init ok` | 00:25:59.234 | 410 ms |
| `SSRealRimeEngine ready` / `SSKeyboardController engine ready` | 00:25:59.235 | **总计 1.430 s**（init start → init ok 为 1.445 s） |

- **没有运行时词库编译**：`build/` 随包携带预生成的 `*.table.bin / *.reverse.bin / *.prism.bin`（日志 `build dir now: ... table.bin, reverse.bin, prism.bin ...`），`prebuild` 只是 65 ms 的拷贝/校验。
- 对照：M3 首次全新安装（需要释放 17 MB 数据）初始化 **4,120 ms**（`v0.4.0-data`）；本轮为已装数据下的冷进程启动，**1.43 s**。H-061 包新增 symbols.json 与 userdb 逻辑后未回退。
- **口径声明**：`bm clean -n com.sansheng.ime -d` 报成功，但日志仍打印 `SSRimeData data m4-userdb-v17 already present`，说明 `files/` 未被清空。**本轮数字是「冷进程启动」，不是「首次安装」**；首次安装耗时以 M3 run15 的 4,120 ms 为准，后续 M5 若要压首装时间，应从数据释放（20.5 MB / 19 files + lua tree）下手。

## 5. 本轮复核的 CodeArts 交付

| 项 | 结果 | 证据 |
|---|---|---|
| H-047 九宫格接 `sansheng_t9` | 通过（`selectSchema` 生效，64426 出中文） | `m4-t9-*`、`v0.4.1-t9-panel` |
| H-045 中英切换先清码 | 通过（A9） | `m4-a9-01-switch-clears-preedit.png` |
| H-046 预编辑放宽 | 通过（10 字符无省略号） | `m4-panel-05-long-preedit-no-ellipsis.png` |

## 6. 未闭合项（不阻塞 M4 能力验收）

| 编号 | 状态 | 说明 |
|---|---|---|
| H-058 | OPEN（CodeArts M-047） | 符号页内容区第二排被底栏压住；数据侧已就绪，纯 UI 高度/末端 padding |
| H-059 | OPEN（CodeArts M-047） | 展开网格「下一页」跳过当页第 7–13 条 |
| H-060 | OPEN（CodeArts M-047） | 屏上候选条数与 `setPageSize` 不一致、翻页首条重复 |
| H-056 | FIXED（未触发） | `onDestroy → finalize()` 已接；本轮用返回键/force-stop 只能把 ability 冻结，未产生 `finalize ok` 日志，需系统真正销毁时再看 |
| H-053 | OPEN | `NOTICE` 许可联系邮箱待主人给 |

## 7. 复现路径（下轮直接用）

```bash
# 构建/签名/安装
powershell -ExecutionPolicy Bypass -File scripts/build.ps1
powershell -ExecutionPolicy Bypass -File scripts/sign.ps1
powershell -ExecutionPolicy Bypass -File scripts/install.ps1

# 冷启动日志
hdc shell aa force-stop com.sansheng.ime
hdc shell hilog -r && hdc shell hilog -b I
hdc shell aa start -b com.sansheng.ime -a EntryAbility --ps m2_landscape 1
# 点输入框后
hdc shell "hilog -x | grep -E 'RIME_NAPI|JSAPP'"
```
