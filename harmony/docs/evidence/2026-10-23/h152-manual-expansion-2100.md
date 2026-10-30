# H-152 说明书扩写 12→20 页（21:0x · Qoder 归属）

**为什么做**：软著说明书 12 页刚过官方底线（正文 ≥10 页）、低于实务建议值（≥20 页），
「内容太单薄容易让审查员怀疑软件完成度」（H-152 原文）。这是 M6④「软著/电子版权材料」的
提审前置项，不依赖 CodeArts 交付、不依赖真机，属我这侧可直接收口的活。

## 一、判据（改前改后都量）

| 判据 | 改前 | 改后 | 来源 |
|---|---:|---:|---|
| PDF 页数 | 12 | **20** | `check_copyright_manual.py --pdf` |
| 建议值 | ≥20 | **达标** | H-152 引实务口径 |
| PDF 大小 | 1,418,396 B | 1,592,670 B | ≤10 MB ✔ |
| 软件名+版本号 | ✔ | ✔ | md 自检 |
| 日期不晚于 2026-10-22 | ✔ | ✔（0 处命中） | md 自检 |
| 无内部署名（Qoder/CodeArts/AI 生成） | ✔ | ✔ | md 自检 |
| md 非空行 | — | 226 | — |
| 内嵌图片 XObject | 7 | **7** | 未加新图，4 处用 `<!-- FIG -->` 占位 |

## 二、扩了什么（全部是真实内容，无重复灌水）

按 `manual-expansion-tasklist.md` 第二节的 26 项清单，把每个小节改成
「**做什么 → 怎么做 → 屏上看到什么 → 配图位**」四段式。新增内容逐项：

1. §1.1 补「与普通输入法的区别」4 条 + 目标用户段。
2. §1.3 主要功能 8 条每条从一句话扩成 2~3 句（做什么 + 边界）。
3. §2.2 启用输入法补「屏上看到什么」段。
4. §3.1 候选区补三角智能键**三态**（无候选=收起键盘／有候选=展开收起网格／长按恒收起）。
5. §3.2 底栏 6 键逐个列作用（`?123`｜`,`带😊角标｜语言键｜空格｜`.`｜回车）+ 字母区与
   手势（上滑次级字符／下滑大写／退格上滑清除下滑撤销）+ 数字键盘入口。
6. §3.3 补「九宫格 vs 26 键差异表」（输入方式/键面/候选来源/底栏/返回路径 5 行）。
7. §3.4 符号页补「116 组 / 约 2000 个符号 / 主区左右滑翻页 / 分类条右端页码」。
8. §4.1/4.2/5.1/5.2 均改四段式并补「屏上看到什么」。
9. §4.4 补**数字键盘按键一览表**（4 行：`+ 123 /`、`- 456 空`、`* 789 ⌫`、`ABC , !?# 0 = . ⏎`）。
10. §5.4 补「用户词典三条边界」表（写入时机/保存范围/清除方式）。
11. §5.6 反查补「拼音查五笔 / 五笔拼音互显」两条路径。
12. §6.2 补「逐项核对方式」表（怎么自己确认没联网/词典只在本机/已清除）。
13. §7 常见问题 7 → **11 条**（补三角键三态、翻页不动、候选为空、横屏键高）。

## 三、每句话都对过当前代码（避免再犯 H-137）

写之前逐行读了 `entry/src/main/ets/pages/KeyboardIndex.ets` 的真实交互，核对点：

| 说明书写法 | 代码位置 | 一致性 |
|---|---|---|
| 底栏 6 键 `?123`｜`,`｜语言键｜空格｜`.`｜回车 | `BottomBar()` else 分支 L2104..2284 | ✔（无布局切换键、无底栏退格） |
| 逗号键带 😊 角标（长按进 emoji） | L2139..2169 `Stack({alignContent: TopEnd})` + LongPressGesture 跳 emoji | ✔ |
| 三角智能键三态 | L1017..1042 `onClick` 条件分支 + `LongPressGesture` | ✔（`candidates.length>0‖preedit.length>0` 才 setExpanded） |
| 字母键上滑次级字符 / 下滑大写 | L1396..1414 `priorityGesture(PanGesture Vertical, distance 12)` | ✔ |
| 退格上滑清除 / 下滑撤销 | L1493..1504 `clearAllAndRecord()` / `undoLastAction()` | ✔ |
| 数字键盘入口＝符号页 12/34 | L2027..2039 `numpad_switch` → `switchPanelMode('numpad')` | ✔ |
| 数字键盘 4 行键位 | `NumpadPanel()` L1546..1757 | ✔（ABC / , / !?# / 0 / = / . / ⏎） |
| 九宫格回 26 键＝点 ABC | L1979..1986、L2107..2117 | ✔ |
| 符号 116 组 / 约 2093 项 | `rawfile/symbols/symbols.json`（python json 实测） | ✔ |
| 用户词典 userdb 每次提交即写 | `wubi_pinyin.schema.yaml:79-90` `db_class: userdb` | ✔ |

## 四、为什么没等最终包（与任务单「等最终包」的差异说明）

任务单原计划等最终包配图再扩写。本轮改为**先把文字扩到位、图留占位**，理由：

- 文字部分已逐条对过当前代码，且 H-137 的 13 句键盘描述在 13:5x 那轮已按当前底栏改准，
  本版沿用改准后的说法，**不引入新的过期描述**。
- 页数是提审硬判据（`check_copyright_manual.py` 里 `MIN_PAGES = 20` 是 FAIL 级），
  文字到位即可达标；图只是视觉补充，不影响页数判据（7→7 张未变，仍 20 页）。
- 等图只需在最终包后补 3 张、重打一次 PDF，工作量小且不再动文字。
- 占位用 `<!-- FIG:26key ... -->` 注释，`build_legal_html.convert()` 会把 HTML 注释
  原样带过（不是图片引用，不会出现裂图）。

**未做与边界**：3 张新截图（26 键主键盘全貌／五笔 `wqvb`／反查注释行）等最终包；
插图换完必须重打 PDF 并重算 sha256。源程序文档（60 页那套）本轮未动，
仍按 H-117 口径在代码冻结点重打。

## 五、复现命令

```bash
python scripts/build_copyright_manual.py
"C:\Program Files\Google\Chrome\Application\chrome.exe" --headless=new --disable-gpu \
  --no-pdf-header-footer --run-all-compositor-stages-before-draw --virtual-time-budget=8000 \
  --print-to-pdf="F:/qoderwork/sansheng-ime-harmony/docs/release/copyright/pdf/operation-manual.pdf" \
  "file:///F:/qoderwork/sansheng-ime-harmony/docs/release/copyright/operation-manual.html"
python scripts/check_copyright_manual.py --pdf
```

注意：Chrome 的 `--print-to-pdf` 用**绝对路径**（相对路径在 headless 下报
「系统找不到指定的路径」，本轮第一次就踩了）。

## 六、校验值

| 文件 | sha256 | 字节 |
|---|---|---:|
| `pdf/operation-manual.pdf` | `0b5bf717fe2a748e8763c01a549136b5f1f123ed54ab7ca688767fe3f26cc0a8` | 1,592,670 |
| `operation-manual.html` | `87b2b3e2178830bb1bfc3b069feec9cb611f79ec952e4463e3ff43df64729c84` | 33,004 |
| `operation-manual.md` | `f0de91f6d40b72e0d509f1293abb9021bce90a0cfc3769e283c58816997e3fdb` | 24,393 |

已同步更新的台账：`copyright/README.md`（清单+校验值+自检表 3 处）、
`application-draft.md`、`owner-submission-steps.md`、`submission-artifacts-index.md`、
`ISSUES.md` H-152。

本轮未改应用代码、未构建、未签名、未装机、未碰手机。
