# UI ↔ 引擎接口契约（v0.1.8）

> 归属：Qoder。CodeArts 只 import，不修改。
> 目的：让键盘壳（CodeArts）和 Rime 引擎（Qoder）可以分开开发，最后只换一个实现。

## 1. 文件

| 文件 | 归属 | 作用 |
|---|---|---|
| `entry/src/main/ets/engine/RimeEngine.ets` | Qoder | 接口与数据类型 |
| `entry/src/main/ets/engine/MockRimeEngine.ets` | Qoder | M1 用的假引擎 |
| `entry/src/main/ets/engine/RealRimeEngine.ets` | Qoder | M2 真引擎（包 `libfanxing_rime.so`） |
| `entry/src/main/ets/engine/RimeDataInstaller.ets` | Qoder | M2 把 rawfile 里的方案文件释放到沙箱 |
| `entry/src/main/ets/engine/EngineProvider.ets` | Qoder | 单例入口；M2 已换成真实现 |
| `entry/src/main/ets/inputmethod/**` | CodeArts | IME 服务、面板、键盘 UI |
| `entry/src/main/ets/pages/**` | CodeArts | 应用内设置/引导页 |

## 2. 契约

```ts
export interface RimeCandidate {
  text: string;       // 候选词
  comment?: string;   // 三向反查注解；没有就不显示
}

export interface RimeContext {
  preedit: string;             // 当前编码，如 "ni"
  candidates: RimeCandidate[]; // 当前页候选
  page: number;                // 从 0 开始
  hasNext: boolean;            // 是否还有下一页
  commitText?: string;         // 需要立刻上屏的文本（空格/回车等）
}

export interface RimeEngine {
  init(sharedPath: string, context?: common.Context): Promise<void>; // v0.1.5 起可带 IME 扩展上下文
  processKey(key: string): RimeContext;
  selectCandidate(index: number): string;
  deleteBackward(): RimeContext;
  flipPage(direction: number): RimeContext;
  clear(): RimeContext;
  getContext(): RimeContext;
  setOption(name: string, value: boolean): void;
  getOption(name: string): boolean;      // v0.1.8，见 §4
  setPageSize(size: number): RimeContext; // v0.1.5，见 §4
  selectSchema(id: string): boolean;     // v0.1.7，见 §4
}
```

## 3. 用法

```ts
import { EngineProvider } from '../engine/EngineProvider';
import { RimeContext } from '../engine/RimeEngine';

const engine = EngineProvider.get();
await engine.init(getContext(this).filesDir + '/rime');

// 按键
const ctx: RimeContext = engine.processKey('n');
// 渲染 ctx.preedit、ctx.candidates（text + comment）、ctx.page
// 如果 ctx.commitText 非空，立刻 inputClient.insertText(ctx.commitText)

// 选词：返回要上屏的文本，由 IME 调 inputClient.insertText()
const committed: string = engine.selectCandidate(0);

// 删除 / 翻页 / 清空
engine.deleteBackward();
engine.flipPage(1);
engine.clear();

// 选项：zh_trad = 简繁，ascii_mode = 中文/英文
engine.setOption('zh_trad', true);
```

## 4. 语义约定

- `init`：幂等；首次可能较慢（引擎部署）；失败要 throw `Error`，UI 捕获并显示。**v0.1.5：第二个参数传 `InputMethodExtensionContext`**——真机 11:22 实证，IME 扩展进程里全局 `getContext()` 返回空，`resourceManager` 拿不到，rawfile 数据无法释放；控制器（`KeyboardController`）本来就持有该 context，直接透传即可。mock 忽略该参数。
- `processKey`：
  - 字母 `a-z` / `A-Z`：进入编码（v0.1.2：大写也算字母，见下）。
  - `Backspace`：删除一个编码；编码为空时由 UI 决定是否交给系统删除。
  - `Space`：选第一个候选或上屏。
  - `Enter`：上屏当前编码原文。
  - `Escape`：清空编码。
  - **v0.1.1 手机语义**：`0-9`、标点、`-`、`=`、`'` 不进入编码；引擎若没有消费该键，应通过 `commitText` 原样交回 UI 上屏。
  - **v0.1.2 大写与翻页**：⇧ Shift **是面板本地状态，引擎永远不会收到 `'Shift'` 这个键**——UI 自己决定大小写，再把单个字母（可能是大写）送进 `processKey`；因此字母判定必须同时接受 `a-z` 与 `A-Z`，否则按 ⇧ 打出的首字母会被当成标点直接上屏。翻页**只由候选栏手势调用 `flipPage()`**（v0.1.3 起候选栏为「左滑 `flipPage(1)` / 右滑 `flipPage(-1)`」；`‹` `›` 按钮已删除，v0.1.2 曾定的上滑/下滑经真机验证无效且方向不符合手机习惯，已废弃），任何符号键都不承载翻页语义。
  - 其他键：返回可直接上屏的 `commitText`，或保持原 context 交给 UI 处理。
- `selectCandidate`：返回要插入编辑框的文本；调用后编码清空。返回空字符串表示没有可选项。
- `commitText`：`processKey` 的返回值里如果带这个字段，UI 必须立即 `insertText`；典型是空格选首选、回车原样上屏。
- `flipPage`：`1` 下一页，`-1` 上一页；越界时保持原页（**不循环**）。返回的 context 里 `candidates` 必须是**该页的切片**、`page` 是当前页码、`hasNext` 反映是否还有下一页——UI 靠这个判断「到底」，真机也靠候选变化确认手势生效。编码发生变化（新字母、退格、选词、清空）时页码回到 0。
- `clear`：清空编码，不删除已上屏文本。
- `setOption`：目前支持 `zh_trad`、`ascii_mode`；未知选项忽略。
- `getOption`（**v0.1.8**）：读回引擎当前开关状态，返回布尔；未知选项返回 `false`。存在理由：开关的**唯一真相在 Rime 会话里**（`simplifier` 的 `option_name`、方案自带的 `switches`、`selectSchema` 都会改它），UI 自己记一份必然和引擎漂移——尤其 `selectSchema` 切方案（26 键↔九键）会重置开关。所以 H-043 的「中/英」键与「简/繁」长按态**必须用 `getOption('ascii_mode')` / `getOption('zh_trad')` 渲染，不要在 UI 里存本地布尔**。引擎未就绪时返回 `false`，不抛错。
- `setPageSize`（v0.1.5，语义在 **v0.1.6** 改为「UI 主导」）：`1..50`，越界钳到边界；改变后页码回到 0，返回新 context。**v0.1.6：UI 应当调用它**——候选栏自己量可用宽度（`onAreaChange`）算出「按当前字号能完整放下几条」再调 `setPageSize(n)`；引擎一旦被 UI 显式调用就置 `uiPinned`，**之后转屏不再自动覆盖**，所以面板必须在每次宽度变化后重量重调。取向硬编码的 5/9 只在 UI 从没调用过时作为兜底。起因是 H-042：竖屏 5 条 + 长预编辑把「你好吗」压成了「你…」，而横屏 9 条反而显示得下——定死档位满足不了两种屏，必须弹性。引擎内部把该值作为「候选栏一页条数」，与 Rime 自身的 `menu/page_size`（50）解耦：桥要负责翻 Rime 的分页再切片，见 §4 `flipPage`。
- `comment`：三向反查注解，UI 必须显示在候选词旁边（有才显示）。
- `selectSchema`（**v0.1.7**）：`wubi_pinyin` = 26 键主方案（五笔·拼音·英文混输），`sansheng_t9` = 九宫格数字方案。九宫格面板按下去的是数字，只有切到 T9 方案才会被拼写代数解释成拼音；26 键字母面板必须切回 `wubi_pinyin`。**这个决定只能 UI 做，引擎不猜**——猜了 `?123` 的数字直出语义就废了（H-024 铁律）。返回是否切换成功；成功后编码清空、页码回 0，且开关状态可能被方案重置，UI 要重新 `getOption` 取态。

## 5. M1 的 mock 行为

- `init` 立即 resolve。
- 输入字母时 `preedit` 累积；候选固定 15 条，按每页 5 条切成 **3 页**：第 1 页仍是「你 / 尼 / 泥 / 呢 / 你好」（与 `v0.2.x` 真机记录一致，便于对比），第 2 页「你的 / 你们 / 拟 / 逆 / 匿」，第 3 页「泥巴 / 逆风 / 匿名 / 呢喃 / 尼龙」，均带 comment。
- **mock 必须分页**（v0.1.4）：若只有一页，`flipPage` 无论有没有被调用，候选栏都不变，真机会把「手势没生效」和「引擎没内容」混成同一个现象——翻页就无法验收。这与 v0.1.2 让 mock 接受大写是同一类「先让效果可见」的配套修正。
- 数字、标点、`-`、`=`、`'` 不进入 mock 编码，直接作为 `commitText` 上屏；翻页由候选栏手势调用 `flipPage()`（v0.1.3 起为左/右滑，`‹` / `›` 按钮已删除）。
- `selectCandidate` 返回**当前页**对应文本并清空编码，页码回到 0。
- `flipPage` 改变页码并返回新页切片；到第 3 页再左滑保持不动（不循环），右滑回上一页。编码变化时回到第 1 页。
- `setPageSize(n)` 改每页条数后重新分页并回到第 1 页（v0.1.5，mock 同样实现，便于 UI 在没有 native 时也能验证 H-035）。
- 目的：让 UI 能完整跑通「按键 → 候选栏 → 翻页 → 选词上屏」，不依赖 native。

## 6. 变更规则

- 任何破坏性变更（改方法名/参数/返回）必须升版本号，并在 `HANDOFF.md` 写变更请求。
- CodeArts 不得在 UI 里直接 `import ... from 'libfanxing_rime.so'`；只能通过本契约。
- M2 时 Qoder 只改 `EngineProvider` 的返回值，UI 代码不动。
- **v0.1.2（2026-10-20，Qoder）**：方法签名**未变**，只补两条语义——① 字母判定接受 `A-Z`；② Shift 归面板本地，引擎不收 `'Shift'`；翻页入口从 `‹ ›` 按钮改为候选栏滑动手势。起因是 M1.2 把 Shift 改成 UI 本地状态后，mock 仍只认小写会让大写首字母直接上屏，真机看不出 Shift 是否生效。
- **v0.1.3（2026-10-20，Qoder）**：签名与引擎行为**依旧未变**，只把候选栏翻页手势的方向定稿——**左滑 `flipPage(1)` / 右滑 `flipPage(-1)`**。起因是真机第二轮：上滑在 Mate 80 上完全收不到事件（手势挂候选栏 `Row`，被子节点横向 `List` 吃掉），且主人判定手机候选只有一行，翻页的自然方向是水平。实现约束写给 UI：用 `priorityGesture` 或把翻页绑到 `List` 自身滚动，普通 `.gesture` 压不住子节点滚动。M2 换真引擎时这条不受影响。
- **v0.1.4（2026-10-20，Qoder）**：签名依旧不变，两处补强——① `flipPage` 的返回语义写清：候选必须是**该页切片**、`page`/`hasNext` 要真实反映状态、编码变化回到第 0 页、到边界不循环；② mock 从「固定 5 条候选」改成 **15 条分 3 页**。起因是 M1.3 复核时发现：mock 只有一页，`flipPage` 调不调候选栏都不变，真机把「手势没触发」和「引擎没内容」渲染成同一个现象，H-029 根本没法验收。**M2 的真 Rime 桥必须满足 ①**，否则翻页又退化成不可测。
- **v0.1.8（2026-10-21 15:45，Qoder，M3 / H-041、H-043）**：**新增一个方法** `getOption(name: string): boolean`（`RimeNativeApi` 侧对应新 NAPI 入口 `getOption`，mock 用 `Map` 同步实现）。起因是 run10 的 ascii_mode 断言 FAIL：探针打了 `zhongguo` 没清编码，`processKey('x')` 变成往编码里追加，预编辑 `zhongguox`——librime 的 `ascii_composer` 在编码非空时**故意**不直出，这是正确行为，不是引擎缺陷。同时 H-043（中/英键 + 简繁长按收口）需要 UI 显示开关态：让 UI 自查引擎，别自己记一份。UI 侧改动见 §4 `getOption`；方法签名新增，旧调用点不受影响。
- **v0.1.7（2026-10-21，Qoder，H-028 ① 智能九键）**：**新增一个方法** `selectSchema(id: string): boolean`。九宫格按的是数字，只有 `sansheng_t9` 方案把数字写进了 `speller/alphabet`；26 键方案 `wubi_pinyin` 里数字必须直出（H-024 铁律）。两者互斥，只能由面板在切键盘形态时显式切方案。语义见 §4。
- **v0.1.6（2026-10-21 13:20，Qoder，H-042）**：签名不变，只改 `setPageSize` 的**主导权**——由「引擎按取向定 5/9、UI 不必调」改成「UI 按实测宽度定条数、调过之后引擎不再覆盖」（`RealRimeEngine.uiPinned` + `KeyboardController.setPageSize()` 透传）。UI 侧要配套：量宽 → 算可完整放下的条数 → 调 `setPageSize(n)` → **候选词本体永不截断**（放不下先舍 comment，再舍可见条数）。
- **v0.1.5（2026-10-21，Qoder，M2）**：**新增一个方法** `setPageSize(size: number): RimeContext`，其余签名不变。起因是 H-035：横屏一页 5 条只占半行，主人要求 8–10 条。实现分两层——Rime 的 `menu/page_size` 固定 50（一次拿满，掉页开销小），桥按 UI 页大小切片，并用 `Page_Down`/`Page_Up` 翻 Rime 自己的页；`RealRimeEngine` 监听 `display` 变化自动切 5/9，UI 无需改动。`RimeEngine` 接口因此多出这一条；实现了 `RimeEngine` 的地方（mock）同步补齐。另：`init` 增加可选第二参数 `context`，`KeyboardController` 的一行调用随之透传（Qoder 于 11:25 做的最小改动，原因见 §4；不影响其他 UI 逻辑）。

## 7. M2 真引擎落地说明（2026-10-21，签名未变，仍是 v0.1.5）

- **comment 的数据来源**：`rawfile/rime/pinyin_simp.schema.yaml` 的 `engine.filters` 加了 `reverse_lookup_filter`，并配 `reverse_lookup: { tags: [abc], dictionary: pinyin_simp }`。反查库 `pinyin_simp.reverse.bin` 由 librime 编译词库时自动生成，**不需要额外数据文件**，M3 换三生词库时同样成立。真机效果：`n` → 「嗯 `en n ng`」「唔 `en n ng wu`」；横屏 `j` → 9 条候选每条带拼音（`m2-41` / `m2-48`）。
- **数据版本与升级路径**：`RimeDataInstaller.DATA_VERSION` 现为 `m2-pinyin-simp-v2`；改词库/改 schema **必须同时升这个号**，否则真机仍用旧沙盒数据。升号时注意 H-039：沙盒目录已存在时 `fs.mkdirSync(path, true)` 在鸿蒙会抛 `File exists`，必须先 `accessSync` 探测再建（已修，别改回去）。
- **真机已按本契约验证的能力**（Mate 80，`v0.3.0-engine`）：候选、`selectCandidate` 上屏、`Space` 选首选、`Backspace` 只删编码（编码为空才交回 UI 删编辑器）、`flipPage` 一滑一页且越界不循环、`setPageSize` 5/9 自动切换、`comment` 显示。**未验证**：`setOption('ascii_mode' / 'zh_trad')` 的真机效果（H-041）。
- **测试脚手架**（不改变契约，仅调试启动参数）：`aa start -b com.sansheng.ime -a EntryAbility --ps m2_landscape 1` → 横屏探针页；`--ps m2_probe 1` → 竖屏探针页；不带参数 → 日常 `pages/Index`。

## 8. v0.2.0（2026-10-22，Qoder，M4）——分页/收尾/沙箱契约

v0.2.0 **新增字段与方法，旧调用点不受影响**，但 UI 侧新增两条硬约束（H-060）：

### 8.1 `RimeContext` 新字段

| 字段 | 类型 | 语义 |
|---|---|---|
| `allCandidates` | `RimeCandidate[]` | **当前 Rime 菜单页的全部候选**（Rime `menu/page_size=50` 时最多 50 条）。UI 按「全量候选」估算一页放几条，不能用当页切片反推（否则棘轮，H-055）。 |
| `baseIndex` | `number` | `allCandidates[0]` 的**全局绝对下标**。跨 Rime 菜单页时它会跳（= `rimePageNo * 50`），UI 选词要用 `baseIndex + 光标下标`。 |

`candidates` 仍是「当前 UI 页切片」，`take` 不单独暴露（= `candidates.length`）；`hasNext` 表示本切片之后是否还有候选（含跨 Rime 页）。

### 8.2 新方法 `selectCandidateAbs(absIndex: number): string`

按**全局绝对下标**选词，返回上屏文本（空串 = 没选中）。UI 自己按实测宽度分页时用它，页内下标用 `selectCandidate(index)` 仍按**当页**解释。两者选完都会清编码、页码回 0。

### 8.3 分页一致性（H-060，必须）

- `setPageSize(n)` 返回的 context 必须被 UI 直接采用为屏上切片（`KeyboardController.setPageSize()` 已 `notify(ctx)`）；**禁止** UI 保留旧切片、只把 n 记在本地。
- `flipPage(±1)` 的起点是引擎维护的「上页起点 + 实际上页条数」；UI 若自行改过切片，必须保证页大小与切片同源。
- 验收：一次输入连翻 3 页，页首页尾无重复、无跳条，屏上条数恒等于最后一次 `setPageSize`。
- M-042 真机实测反例：屏上 16 条 / 日志 `setPageSize=13`，第 2 页首条与第 1 页第 13 条重复（`docs/ISSUES.md` H-060）。

### 8.4 新方法 `finalize(): void`

销毁 session + 引擎，释放 LevelDB/OpenCC/Lua 句柄；调用后 `g_ready=false`，需重新 `init` 才能用。IME 面板 `onDestroy` 调用（H-056），**不要**在 `onHide`/切输入法时调用。真机日志：`[Rime-Napi] finalize ok`。

### 8.5 用户词典落盘（D-010）

`schema` 的 `translator/user_dict` 用 `db_class: userdb`（LevelDB）。每次提交即写 WAL，不依赖进程收尾；文件位置 `<filesDir>/rime/user.userdb/`（**目录**，二进制，不是 `user.txt`）。真机已验证：上屏过的英文候选在 IME 进程重启后仍排第一。`tabledb` 会丢（只在内存，析构才写），不要再切回去。

### 8.6 数据版本与 Lua 释放

- `RimeDataInstaller.DATA_VERSION = 'm4-userdb-v17'`：改 `rawfile/rime/**` 必须升号，否则真机沿用旧沙盒。
- 桌面 Lua 模块按 `rawfile/rime/lua-files.txt` 清单释放到 `<filesDir>/rime/lua/`；`rime.lua` 用 `need()` 逐个挂载，缺一个会让 `LuaTranslation::Next` 抛错并**静默截断候选队列**（真机现象：预编辑正常、候选只剩 2 条）。`scripts/port_rime_data.py` 已加 yaml 引用 ↔ 模块 ↔ 全局符号的完备性检查，缺齿轮直接非 0 退出。
- 鸿蒙沙箱实现（Qoder）：`runLog.lua`（日志写到模块目录、默认关）、`sysInfo.lua`（Windows 环境变量一律返回「未知」、`currentDir()` 用模块路径）、`socket.lua`（`socketEnable=false`、dns 返回 nil，不联网）。桌面的 `os.getenv('APPDATA')` 依赖在这三处收口，不再需要 `installation.yaml`。

### 8.7 符号/emoji 数据（H-057）

`entry/src/main/resources/rawfile/symbols/symbols.json`，格式：

```json
{"version":"2026-10-22","groups":[{"id":"common","label":"常用","items":["，","。"]}]}
```

- 生成脚本：`scripts/build_symbol_data.py`（数据源：桌面 `symbols.custom.yaml` 107 组 + `phraseExt esUnicode.txt`/`esAppEmoji.txt`）。
- 当前 116 组 / 2093 项 / 660 emoji / 约 35 KB。前 5 组 id 与 UI fallback 对齐（`common/math/currency/arrow/english`），随后 `emoji`/`emoji_2`…/，再后 `r_<code>` 107 组。
- `id` 稳定，UI 状态只存 id；emoji/全角按 2 格宽排；读不到 JSON 必须回落 fallback，不许白屏。

### 8.8 符号键上屏契约（H-061）

`processKey(key)` 的 `key` 不保证是单字节：符号页会把「，」「？」「🚹」这类多字节 UTF-8 字符直接交给桥。桥的约定：

- `key.size() > 1`：视为**字面字符**，原样放进 `commitText` 上屏，**不进 Rime**（Rime 的 `process_key` 只吃 keycode，多字节传不进去）。
- 单字节 ASCII 标点：仍按 H-024 直提；数字先试引擎（九键 T9 要进编码），引擎不吃再直提。
- UI 侧不需要为符号/emoji 走特殊通道，统一 `keyboardController.onKey(ch)` 即可。
