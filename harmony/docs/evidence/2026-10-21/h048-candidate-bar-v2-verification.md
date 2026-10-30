# H-048 候选栏 v2 真机验收（Qoder，2026-10-21 18:47–19:01）

设备：Mate 80 `7GL0226408083897`。构建 24,380,923 B → 签名 24,506,694 B → 装机。
宿主全程用我们自己的 `pages/LandscapeProbe`（`--ps m2_probe 1` / `--ps m2_landscape 1`），**未动主人备忘录正文**。
引擎侧日志确认 `SSRealRimeEngine setPageSize=8 (UI pinned)` + `[Rime-Napi] pageSize=8`。

## 结论：不通过，退回返工（2 条必修 + 3 条次要）

主目标（密度）达成，但把主人已经否掉过的老毛病带回来了，并且弄丢了 H-046。

## 通过项

| 项 | 证据 | 实测 |
|---|---|---|
| 双行候选密度 | `h048-03-eight-candidates.png`、`h048-06-t9-64426-8cands.png` | 竖屏一页 **8 条**（4 列 × 2 行）；v0.4.1 同宽只放得下 3 条（对比 `m4-panel-09-restart-nihao.png`）。`shangxian` → 上线/upper bound、上限/上线、上线/上限 全部同屏 |
| 反查独立整宽行 | 同上 | 候选条下方整宽一行显示 `shangxian` / `ni hao`，不再内联挤占候选宽度 |
| ▼ 展开网格 | `h048-02-expanded-grid.png` | 展开后覆盖键盘区，每格「码上词下」（`nihao wqvb` / 你好），底部「取消 / 收起」在位，收起后回双行条 |
| H-047 九宫格无回归 | `h048-06`、`h048-07-t9-nihao-commit.png` | `64426` → 你好/你敢/米高/嗯/米/迷/拟 8 条，点「你好」→ 输入框与「已上屏：你好」同时出现 |
| H-037 横屏首帧无回归 | `h048-08-landscape-firstframe.png` | 横屏面板首帧完整，无裁切；候选栏 44vp = 单行 + 反查行 |
| H-035 横屏条数无回归 | `h048-09-landscape-ni-11cands.png` | `ni` 单行可见 **11 条**（你 拟 尼 呢 泥 妳 you doubtful parapet girl distressed familiar） |
| H-024 数字直出无回归 | `h048-10-digit-direct-56.png` | 26 键下 `?123` 数字行点 5、6 → 正文 `56` 直出 |

## 必修 F1：候选条被手指横向拖动，首列裁在左边缘，偏移跨输入残留（H-034 回归）

`h048-04-FAIL-list-scrolled-clipped.png`：在候选条上左滑一次，**内容整体左移约 70px**——第一列变成半截的「线好的 / oper bound」，而候选集合没换页。
`h048-05-FAIL-derstanding-clipped.png`：再滑一次，条上显示「derstanding and enjoying」，仍是半截词；此时偏移跨输入残留（下一条编码进来仍然是滚动态）。

根因：v2 把候选容器从**非滚动 `Row`**（H-034 专门为「一滑一页」改的）换成了横向 `List`（`KeyboardIndex.ets:288`），`List` 自带的横向滚动交互和候选栏的 `priorityGesture(SwipeGesture)` 抢手势。主人 2026-10-21 已明确否过滚动候选栏（「翻页是候选栏左右滑，不是上下」「一滑一页」）。

修法（任选，推荐 ①）：
① `List(...).enableScrollInteraction(false)` —— 关掉手指滚动，保留 `stripScroller` 做程序滚动与「选中项跟随可见」；
② 或换回非滚动容器（`Row`/`Flex` 包双行列）。
改完必须复验：连续左/右滑各一次，每次**恰好换一页**且首列不被裁。

## 必修 F2：预编辑列 44vp 把长编码截断（H-046 回归）

`h048-03`：`shangxian` 显示成「sha…」；`h048-06`：`64 426` 显示成「64 …」。
H-046 上一轮刚收口成「10 字符预编辑整条显示、无省略号」（`m4-panel-05-long-preedit-no-ellipsis.png`），本轮被 44vp 左侧列重新截断。

修法：预编辑不再占候选行左侧列。两条候选行保持整宽，预编辑与反查合并到下面那条整宽行（例：`shangxian · zhongguo`），或预编辑单独一行。`recomputePageSize()` 里扣的 44vp 一并还给候选区。

## 次要（不阻塞，下一轮）

S1 空态浪费：无编码无候选时整条 82vp 空白只剩一个 ▼（`h048-14`、`h048-20`），建议空态收回单行高度。
S2 反查行信息量为 0：`nihao` 时候选 0 的 comment 就是 `nihao`，与预编辑重复；建议优先显示与预编辑不同的那条（五笔码 `wqvb`）。
S3 符号页第四行疑似被裁（`h048-10-digit-direct-56.png` 底部），需与 v0.4.1 对比确认是否本轮新引入。

## 参考实现核对

kanonIME（MIT，`F:/qoderwork/_ref_kanon`）的 `CandidateBar.ets` 里横向 `List` 是**它自己翻页的载体**（滑 List = 翻页，没有引擎分页手势）。我们是「引擎分页 + 手势翻页」，所以**这一处不能照抄**，必须关掉手指滚动。
