/*
 * 三生输入法 · 键盘面板（M-044 九宫格一级入口 + 候选页大小棘轮修复）
 * 归属：CodeArts（鸿蒙 UI）。
 * 布局与配色借鉴自 nanaseyuu/hMixedKeyboard (Apache-2.0) 的 pages/KeyboardIndex.ets。
 * 候选栏借鉴自 kanonIME (MIT) 的 components/CandidateBar.ets——▼ 展开网格。
 *
 * M-037/M-038 候选区结构（照 fcitx5 层结构，两层从上到下）：
 *   L1 预编辑行：整宽 12fp 灰字，**只显示 preedit（原始编码）**，约 16vp；H-190 起不再混入候选注释
 *     （主人 2026-10-26 原话「字母行应该是干净的，比如 gavc 开始，字母行就应该只是 gavc」）；
 *   L2 候选行：整宽单行一格一词，comment 跟在该词后面同一条目内（灰小字，安卓 CandidateItemUi
 *     `buildSpannedString { color(fg){text} color(commentColor){comment} }` 同构），最右 ▼ 约 28vp。
 *   ▼ 展开面板：Scroll + Flex(wrap) 覆盖键盘区，每格「码上词下」，点格上屏并自动收起；
 *   展开态有「上一页/下一页」按钮补密度（单行一页只有 4~5 条）。
 *   收起态候选行是原生横向 List 连续滚动（H-164），滑到本页尾才由引擎翻页；
 *   非 List 区域（内边距/展开键）保留 gesture 左右滑翻页（H-034）；展开态禁用手势避免冲突。
 *
 * M-044 改动（H-054 + H-055）：
 *   H-054: 九宫格一级入口——底栏最左新增布局切换键（26键显示「九键」/九键显示「26键」），
 *     点一下直接切布局；?123/ABC 回归本职（字母页↔符号页），从符号页返回时回到 prevPanelMode；
 *     删掉符号页的「九宫格」标签（SYMBOL_TABS 6→5）；切布局前先 clear()。
 *   H-055: 候选页大小棘轮——recomputePageSize 改用全量候选 allCandidates 估宽（不用当前页切片），
 *     只在编码串变化时重算 setPageSize（翻页不重算，避免棘轮）。
 *
 * H-034：候选栏翻页——SwipeGesture(Horizontal)，一次滑动只翻一页，500ms 防抖。
 *   H-164：L2 改原生横向 List 后，List 区域内的左右滑交给 List 连续滚动（H-034 硬切不再参与），
 *   手势只接管非 List 区域；priorityGesture 已降为普通 gesture，否则父级会抢走 List 的滚动。
 * H-043：简繁合并到中英键——点击切换中/英，长按切换简/繁；底栏删独立简繁键，空格加宽。
 * H-047：九宫格面板接 T9 引擎——进入九宫格时 selectSchema('sansheng_t9')，
 *   退出时切回 wubi_pinyin；切方案后用 getOption 回填中英/简繁键面状态。
 * H-045：中英切换前先 clear() 清挂起编码，防止旧编码和新键拼在一起。
 * H-052：关于/第三方声明页——长按 ?123 键弹出关于面板，覆盖键盘区；
 *   独立 pages/AboutPage.ets 供应用主界面 router 访问。
 * H-057（M-046）：符号页数据驱动——分类表改读 rawfile/symbols/symbols.json（Qoder 数据，
 *   格式冻结 groups[{id,label,items[]}]），读不到/解析失败回落写死表 FALLBACK_SYMBOL_GROUPS（不白屏）；
 *   当前分组用 id 记（activeSymbolGroupId，不存下标——数据更新后分组数/顺序可能变）；
 *   标签栏横向 Scroll 可滑（107 组也放得下，不再 layoutWeight 均分）；符号键按显示宽度排格——
 *   emoji（astral 码点）/CJK/全角 2 格宽、ASCII 等 1 格宽；内容区纵向 Scroll + Flex(wrap)。
 *
 * M-047 改动（H-058 + H-059 + H-060）：
 *   H-058: 符号页内容区裁切——数字行/分组标签改显式高度（不再三层 layoutWeight 竞争），
 *     内容区 layoutWeight(1) 独吃剩余高度并 clip(true)，被严格约束在底栏之上；
 *     滚到底最后一排完整可见（竖/横屏通用）。
 *   H-059: 展开网格「下一页」跳条——网格在本页切片内 6 格一屏翻（gridScreenOffset），
 *     翻到本页末屏按钮置灰显示「本页末」，翻引擎页交给候选栏手势（展开态已放开），
 *     引擎页/新候选到达后 gridScreenOffset 自动复位第 1 屏。
 *   H-060: 页边界一致性——渲染切片改由 UI 单一记账：allCandidates + baseIndex + uiPageStart
 *     + uiPageSize（=最后一次 setPageSize 的值），屏上条数恒等于 setPageSize；
 *     翻页起点 = 屏上末条 + 1（uiPageStart 步进绝对接续，跨 Rime 菜单页才调引擎 flipPage）；
 *     点词一律 chooseCandidateAbs(baseIndex + uiPageStart + 页内下标)，不与引擎切片错位。
 *
 * M-049 改动（H-062，M5 体验打磨第一批）：
 *   按键触摸体系——① 所有字母/数字/符号/功能键 TouchType.Down 换按下色 BG_PRESSED（比激活色
 *   更深的灰蓝），Up/Cancel 复原；onTouch 只做按下态+振动，按键功能仍走原 onClick（不重复触发）。
 *   ② 退格两处（qwerty 行内 + 底栏）长按连删：按住 500ms 后每 100ms 删一次，抬手/滑出立即停；
 *   短按（未触发连删）仍只删 1 个；删除逻辑全部迁到 onTouch（退格键不再挂 onClick 防双删）；
 *   定时器在 aboutToDisappear 统一清理，无泄漏。
 *   ③ 按下时 vibrator 20ms 轻振（usage 'touch'，50ms 节流）；无 ohos.permission.VIBRATE /
 *   设备不支持 / 任何失败都 try/catch + .catch 静默降级。
 *   （H-120 更正：此处原写「module.json5 不加权限，Qoder 决定」，与实况相反——`2fea788`
 *   （2026-10-22）起 module.json5 **已声明** ohos.permission.VIBRATE，内容闸门第 8 项断言的
 *   正是「权限恰好为 ['VIBRATE']」。留这条更正，免得下一个人照着旧注释把权限删了。）
 *
 * M-050 改动（H-063 + H-065，M5 视觉/布局收敛）：
 *   H-063 ①: 功能键图标化——⌫/⏎/⇧/▼▲ 从 Unicode 字形换 SymbolGlyph（delete_left /
 *     return_down_left / arrow_up / chevron_down|up；资源名均已对 SDK sysResource.js 核对），
 *     图标色/尺寸统一走 TEXT_FUNC + FUNC_ICON_SIZE；空格/?123/ABC/九键·26键保持文字键面。
 *     onClick/onTouch/keyId（含退格连删状态机）全部原样保留，只换键面内容。
 *   H-063 ②: 视觉 token 收敛——BG_FUNC_ON→BG_ACTIVE 更名；新增 TEXT_KEY/TEXT_FUNC/RADIUS/
 *     RADIUS_SM/KEY_MARGIN/KEY_MARGIN_SM/CAND_PAD_H；散落 borderRadius 6|8 与 margin 3|2 收口
 *     到常量（数值不变，仅收敛不改观感）。
 *   H-063 ③: 底栏收纳——删底栏中英键，中/英·简/繁收进布局键长按小菜单（LangMenu，浮底栏上方，
 *     半透明遮罩点外关闭）；A7 语义不变——H-045 clear() 前置 + setOption('ascii_mode'/'zh_trad')
 *     逻辑原样迁移，仅入口位置变了；空格 layoutWeight 4→5 吃掉腾出的权重（底栏总权重不变）。
 *   H-065 ④: 展开网格列数自适应——gridCols()=max(3, floor(面板宽/90))，竖屏 360vp 仍 4 列
 *     （与原 25% 观感一致），横屏不再右侧半屏空白；GRID_PAGE_SIZE 常量改 gridPageSize()=cols*2，
 *     gridCandidates()/gridScreen()/gridScreenCount() 切片边界与工具行翻屏步进同步适配；
 *     H-059 翻屏语义不变（仍两行一屏、本页内切片步进、翻引擎页走候选栏手势）。
 *   H-065 ⑤: 候选条 L1/L2 统一 CAND_PAD_H=8 左右内边距（真机 x≈4px 贴边修复）；
 *     recomputePageSize 的 availW 同步扣 2*CAND_PAD_H，估宽与实际渲染保持一致。
 *
 * M-058 改动（H-077 + H-078，D-014：键盘密度以本机安卓版实测面板为唯一基准）：
 *   H-077 候选行密度四修——① estimateCandWidth 只返回纯文字宽（渲染端 Text 无 padding，
 *     估算与渲染同源，去掉每条 20vp 的幽灵 padH）；② 单条计入宽度封顶 availW*0.30
 *     （长英文词不再吞行，格子上屏仍走 Ellipsis）；③ 字号三档（>=620→18 / >=460→20 /
 *     其余→18，竖屏 304vp 落 18fp）替换 availW>360（竖屏恒 false 的根因）；④ 展开网格
 *     解耦——setExpanded 统一入口：展开 setPageSize(gridCols()*2) 向引擎要大页（8 格喂满），
 *     收起 recomputePageSize() 恢复行页大小；H-060 记账（uiPageStart/baseIndex/
 *     pagedCandidates/flipCandidates）语义一行不动。
 *   H-078 ?123 面板照安卓版重做——顶部分类条 8 项（7 个组映射 +「更多」进完整分组列表，
 *     Row 均分不横滑）；主区 3 行×10 列（第 1 行数字 1-9 0 常驻、第 2/3 行随分类换前 19 个、
 *     第 20 格固定 ⌫）；键 layoutWeight 均分 + margin 归零；底栏删「九键」键（撤销 D-009）：
 *     布局切换改长按 ?123/ABC 弹 LayoutMenu（26键/九键），LangMenu 迁长按空格；
 *     26 键字母键挂次级字符（数字/常用符号）上滑直接上屏（PanGesture Up 20vp，
 *     swipeAltDone 防与 onTouch(Up) 双上屏）。AboutPanel 入口废弃（关于页走 Index 首页入口 H-072）。
 *     symbols.json 数据不动（116 组保持），一级分类只是 UI 映射表。
 *
 * H-081（M-059-review/re2，CodeArts 本轮）：
 *   ① UI 侧链路收口——符号面板键与 26 键上滑次级字符统一走 onKey() 送引擎
 *      （review §5.2 实测的「直出」发生在 C++ 桥标点分支，不在 UI；UI 侧已无 commitText 调用点，
 *      桥侧标点分支的变更请求已写 HANDOFF.md，等 Qoder 批）；
 *   ② 翻页口径（M-059-review2 勘误后修正，含 12:45 并发改动合流）——主区仍 3 行、行高按
 *      H-082 修完的值不动；主区 Swiper 只做分类的程序化定位（「更多」/分类条点选后 changeIndex
 *      跳转），disableSwipe(true) 禁手势滑动保住「分类切换零横滑」；组内翻页用
 *      priorityGesture(SwipeGesture Horizontal)（与候选栏同款，一滑一页+500ms 防抖）挂在 Swiper 上，
 *      english 组 = 第 1 页 19 项 + 第 2 页 9 项（不重排数据），`/`（第 27 项）与 `\`（第 21 项）
 *      翻到第 2 页可达；页码指示放分类条右端（第 3 行末位已被 ⌫ 固定占用），>1 页才显示；
 *      不恢复纵向滚动。
 *
 * H-082（M-059-review）：符号面板第 3 行裁切修复——
 *   分类条高度从 max(28, rowHeight-12)=36vp 压到固定 28vp；
 *   3 行（数字+符号2+符号3）各 layoutWeight(1) 均分剩余空间，键高度从 keyH()=42vp 改 100% 填满行高。
 *   竖屏：每行 (144-28)/3≈38.7vp，横屏：(102-28)/3≈24.7vp。
 *   基线靠下的字形（_ ` ，）加下内边距防贴底裁切（review §四建议）。
 *
 * H-096（M-085，布局重做）：
 *   ① 键帽间距——KEY_MARGIN 水平 3→4vp，键帽间留更多呼吸空间，观感不再拥挤。
 *   ② 底栏比例——layoutWeight 重新平衡：空格 3.5→4.5（占 45% 宽度），功能键收窄
 *      （hide 0.8→0.7、?123 1.2→1.0、emoji 1→0.8、lang 1→0.8、dot 1→0.8），
 *      底栏与主键区视觉比例更协调。
 *   ③ 横屏候选区——barHeight<40 时隐藏 L1 预编辑行 + candBarHeight() 压缩 6vp，
 *      给主键区更多垂直空间，横屏键高不再被压到偏薄。
 *   ④ 展开网格分隔——ExpandedPanel 顶部加 Divider(0.5vp, BG_FUNC)，
 *      与候选栏之间有清晰视觉分隔。
 *   ⑤ 符号键圆角——RADIUS_SM(6) 全部统一为 RADIUS(8)，与字母键一致。
 *
 * 状态来自 KeyboardController.setUiListener，按键事件回传 KeyboardController。
 */
import { KeyboardState, keyboardController } from '../inputmethod/KeyboardController';
import { RimeCandidate } from '../engine/RimeEngine';
import { inputMethodEngine } from '@kit.IMEKit';
import { TextEditPad, ClipboardPad } from '../components/ToolPanels';   // H-194（CodeArts M-221 交付）→ H-218(Qoder)：CursorPad 换全量 TextEditPad（主人点单）
import { common } from '@kit.AbilityKit';
import { vibrator } from '@kit.SensorServiceKit';
// H-176：工具栏未接地图标（重做/移动光标/剪贴板）的明确反馈用——不做静默假按钮。
// promptAction 声明在 @kit.ArkUI（DevEco SDK ets/kits/@kit.ArkUI.d.ts 实测，不是 ArkKit）。
import { promptAction } from '@kit.ArkUI';
import display from '@ohos.display';   // H-215：气泡边缘夹取用屏幕真实 vp 宽
// H-241（Qoder 2026-10-28）：设置页——存储层（输入法进程独立沙箱的 preferences）＋面板内覆盖层 UI。
// 为什么画在面板里而不是拉起 App 的 SettingsPage：官方「输入法安全模式」写明基础模式**不能**
// 从 InputMethodExtensionAbility 拉起别的 UIAbility，且面板**不支持** window.createWindow
//（依据与逐条文档链接见 docs/SETTINGS-CONTRACT.md §1）。
import { SettingsStore, SETTINGS_REV_KEY } from '../common/SettingsStore';
import { SettingsPanel } from './SettingsPanel';

const TAG: string = 'SSKeyboardIndex';

const LETTER_ROW_1: string[] = ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p'];
const LETTER_ROW_2: string[] = ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l'];
const LETTER_ROW_3: string[] = ['z', 'x', 'c', 'v', 'b', 'n', 'm'];

// 数字行：1-9 + 0
const DIGIT_ROW: string[] = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'];

// 九宫格：数字 + 字母组标注
const T9_NUM: string[] = ['1', '2', '3', '4', '5', '6', '7', '8', '9'];
const T9_LABEL: string[] = ['', 'ABC', 'DEF', 'GHI', 'JKL', 'MNO', 'PQRS', 'TUV', 'WXYZ'];
// H-227（Qoder 2026-10-28 08:0x）：**只在 wubi_pinyin 里声明**的引擎开关——
// `sansheng_t9.schema.yaml:33` 的 switches 只有 ascii_mode/full_shape/ascii_punct/zh_trad，
// 九键方案下点这些没有任何反应＝假按钮（H-090/D-021 口径）⇒ 统一在这里置灰，别再各处硬写名字。
const WUBI_ONLY_OPTIONS: string[] =
  ['extended_charset', 'phraseComment', 'encnDic', 'phraseExt', 'phraseReplace', 'abbrEn', 'pinyin'];

// H-057（M-046）：符号分类数据契约（格式冻结，与 Qoder 约定）——
// rawfile/symbols/symbols.json：{"version":"...","groups":[{"id":"common","label":"常用","items":["，","。"]}]}
// items 只有字符串（一个按钮一个字符/emoji）；id 稳定不变，UI 状态按 id 记（不存下标）。
interface SymbolGroup {
  id: string;
  label: string;
  items: string[];
}

interface FlatPage {
  groupId: string;
  page: number;
}

// H-057 fallback：rawfile/symbols/symbols.json 缺失/损坏/不合法时回落到这张写死表（不许白屏）。
// 内容即 H-054 前的写死表（5 组）；id 与 Qoder 契约示例对齐，数据到位后不改代码直接生效。
const FALLBACK_SYMBOL_GROUPS: SymbolGroup[] = [
  { id: 'common', label: '常用', items: ['，', '。', '？', '！', '、', '；', '：', '“', '”', '‘', '’', '（', '）', '【', '】', '《', '》', '…', '—', '·'] },
  { id: 'math', label: '数学', items: ['＋', '－', '×', '÷', '＝', '≠', '≈', '±', '％', '‰', '°', '√', '∞', '∑', '∫', 'π', '²', '³', '≤', '≥'] },
  { id: 'currency', label: '货币', items: ['¥', '$', '€', '£', '₩', '₹', '℃', '℉', '㎏', '㎝', '㎜', '㎡', '㎞', 'μ', 'Ω', '§', '©', '®', '™', '№'] },
  { id: 'arrow', label: '箭头', items: ['←', '→', '↑', '↓', '↔', '①', '②', '③', '④', '⑤', '⑥', '⑦', '⑧', '⑨', '⑩', '☆', '★', '※', '§', '¶'] },
  { id: 'english', label: '英文', items: ['~', '`', '!', '@', '#', '^', '&', '*', '(', ')', '-', '_', '=', '+', '[', ']', '{', '}', '\\', '|', ';', ':', '\'', '"', ',', '.', '<', '>', '/', '?'] },
];

// H-078（M-058，D-014）：26 键字母键次级字符（安卓版 a2 实测同款）——上滑直接上屏。
// 并行数组按字母查表（c 键无次级字符，与安卓版键面一致）。
const ALT_LETTERS: string[] = [
  'q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p',
  'a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l',
  'z', 'x', 'c', 'v', 'b', 'n', 'm'
];
const ALT_CHARS: string[] = [
  '1', '2', '3', '4', '5', '6', '7', '8', '9', '0',
  '@', '*', '+', '-', '=', '/', '#', '(', ')',
  '\'', ':', '"', '?', '!', '~', '\\'
];

// H-078（M-058）：符号页一级分类条——8 项映射 116 组中的 7 个 +「更多」（groupId 空串 =
// 特殊项，点开完整分组列表）；标签取短字/单符号（照安卓版 a3 分类条图标位）。
interface SymbolCategory {
  label: string;
  groupId: string;
}
const SYMBOL_CATEGORIES: SymbolCategory[] = [
  { label: '1?#', groupId: 'common' },
  { label: '()', groupId: 'english' },
  { label: '→', groupId: 'arrow' },
  { label: '±', groupId: 'math' },
  { label: '①', groupId: 'r_szq' },
  { label: '￥', groupId: 'currency' },
  { label: '😊', groupId: 'emoji' },
  { label: '全', groupId: '' }
];

const SYMBOL_SWIPER_GROUPS: string[] = ['common', 'english', 'arrow', 'math', 'r_szq', 'currency', 'emoji'];

// H-065 ④ re2（M-050-review）：展开网格 Grid 列间/行间 gap（vp），与两侧 CAND_PAD_H 对齐。
const GRID_GAP: number = 4;
// H-168：展开网格向引擎要的候选条数＝整菜单页（对齐 rawfile/rime/default.yaml page_size:50），
// 这样网格里才有「多屏」可上下滑翻；之前 setExpanded 只 setPageSize(gridCols*2≈8)，窗口恒 8 条＝永远一屏。
const GRID_FULL_PAGE: number = 50;
// H-165（形态 B）：顶部功能三角宽度。
// 真机返工（Qoder 2026-10-25 14:4x）：删掉 FUNC_TRI_HEIGHT=20 / FUNC_TILE_ROW_HEIGHT=34 ——
// 这两个高度曾各自撑起一行塞进候选栏，而候选栏容器恒为 candBarHeight()=44vp、
// 且 44vp 已被 L1(16vp)+候选行(28vp) 占满、键区与底栏实测零余量 ⇒ 加任何一行都会溢出压到主键区。
// 现在三角内联进候选行（0 额外高度），磁贴行与 L1/候选行互斥（同占 44vp），不再需要独立高度常量。
// H-221（Qoder 2026-10-27 15:3x，主人「hjkl 长按不撒手，他应该继续他的动作，连续执行，直到撒手」）：
// 字母键长按触发后的方向连发间隔，与 ⇆ 面板四向格（ToolPanels.CURSOR_REPEAT_MS）同值同手感。
const LETTER_DIR_REPEAT_MS: number = 120;
const FUNC_TRI_WIDTH: number = 36;
// H-188：收起态候选行最左 `›` 的宽度。24vp ⇒ 中心 = CAND_PAD_H(8) + 12 = 20vp（屏宽 5.5%），
// 与展开后工具栏第一枚 `‹` 的中心重合（工具栏 padding 2 + 36/2 = 20vp）。
const FUNC_TRI_LEFT_W: number = 24;

// H-063（M-050）：视觉 token 收敛——颜色/圆角/间距统一取自此处；数值不变（8 仍 8、3 仍 3），
// 只收口命名，散落在各键的 .borderRadius(6|8) 与 margin 3|2 全部改为引用常量。
const BG_PANEL: string = '#E4E7EC';
const BG_BAR: string = '#F2F3F5';
const BG_POP: string = '#3A3F47';       // H-155：长按气泡浮层底色（深色浮起，高于键面）
const BG_KEY: string = '#FFFFFF';      // 键面底色（字母/数字/符号/空格）
const BG_FUNC: string = '#C9CEDA';     // 功能键底色
const BG_ACTIVE: string = '#B8C6E8';   // 功能键激活底色（原 BG_FUNC_ON 更名，语义不变）
// M-049（H-062）：按键按下色——比 BG_ACTIVE 更深的灰蓝，Down 换 Up/Cancel 复原
const BG_PRESSED: string = '#A8B4CE';
const BG_ENTER: string = '#B8860B';     // H-086：回车键金色/棕色（照安卓版）
const FG_TEXT: string = '#1A1C1E';     // 通用文字色（候选词/关于面板/展开网格词面）
const FG_HINT: string = '#8A8F99';
const FG_ACCENT: string = '#2B5FBF';
// H-179：工具栏图标色。真机安卓截图 `k1_toolbar.png` 量得墨色 rgb(23,32,58)=#17203A（深藏青），
// 七枚（‹/撤销/重做/光标/剪贴/···/▼）同色。此前我们用了蓝色 FG_ACCENT，与安卓对不上（主人「顶栏做的有问题」）。
const FG_TOOLBAR: string = '#17203A';
const TEXT_KEY: string = '#1A1C1E';    // 键面字色（字母/数字/符号/空格，原 FG_TEXT 键面用法）
const TEXT_FUNC: string = '#1A1C1E';   // 功能键字色/图标色（⌫/⏎/⇧/九键·26键/?123 等）
const RADIUS: number = 8;              // 行内/底栏键圆角
const RADIUS_SM: number = 6;           // 小键圆角（符号页数字键 / 展开网格格）
const KEY_MARGIN: Margin = { left: 4, right: 4, top: 3, bottom: 3 };    // 行内/底栏键外距

// H-155：字母键长按气泡符号表——**对齐 nova6 安卓三生真机**（实测自三生 APK 的
// org.fcitx.fcitx5.android.input.popup.PopupPreset，基于 fcitx5-android）：
// 每键长按弹 [数字/符号, shift 大写, ...该键变音]。与 ALT_LETTERS 同序并行。
// a/x/c/v 留空——它们长按走编辑框动作（全选/剪切/复制/粘贴），不弹气泡。
// H-215(Qoder 2026-10-27)：主人点名「里面的特殊符号也还没加上」。口径采纳 CodeArts
// 对照表（h210-40key-layout-facts.md §七，源＝Trime 40 键 trime.yaml:797-803）：
// q~p 数字/大写/变音**保留**（我们无数字行，数字是刚需），尾部追加 Trime 编程符号
// `_ - + = | \ [ ] { }`；b 补 `~`（Trime 同款，z 的反引号原已在）；s/d 死数据清空。
const HIDDEN_SYMS: string[][] = [
  ['1', 'Q', '_'],                                          // q
  ['2', 'W', '-'],                                          // w
  ['3', 'E', '+', 'ê', 'ë', 'ē', 'é', 'ě', 'è', 'ė', 'ę', 'ȩ', 'ḝ', 'ə'], // e
  ['4', 'R', '='],                                          // r
  ['5', 'T', '|'],                                          // t
  ['6', 'Y', '\\', 'ÿ', 'ұ', 'ү', 'ӯ', 'ў'],                       // y
  ['7', 'U', '[', 'û', 'ü', 'ū', 'ú', 'ǔ', 'ù'],                  // u
  ['8', 'I', ']', 'î', 'ï', 'ī', 'í', 'ǐ', 'ì', 'į', 'ı'],        // i
  ['9', 'O', '{', 'ô', 'ö', 'ō', 'ó', 'ǒ', 'ò', 'œ', 'ø', 'õ'],   // o
  ['0', 'P', '}'],                                          // p
  [],                                                       // a -> 全选
  [],                                                       // s -> 行首（H-220r3 更正：主人「不是全首全尾，是行」；长按走 moveCursorToLineStart，不弹泡）
  [],                                                       // d -> 行尾（同上，走 moveCursorToLineEnd；全文首尾留在 ⇆ 面板「全首」「全尾」格）
  // H-210(CodeArts) M-247(Qoder) 拍板：f/g/n 不挂长按、h/j/k/l/m 长按做编辑动作。
  // 这五组置空（与 a/x/c/v 同款），符号挪到 ?123 页。
  // H-226(Qoder 2026-10-27 16:5x)：f/g 已由主人改口径派了活（长按=文首/文末）⇒ 仍置空、不弹泡，
  // 但不再算「不做」（M-247③ 对 f/g 的那句作废，见 funcLabel 与长按分派处的注释）。
  [],                                                       // f -> 文首（H-226；鸿蒙无「页」概念）
  [],                                                       // g -> 文末（H-226）
  [],                                                       // h -> 光标左移（M-247②）
  [],                                                       // j -> 光标上移（H-220r3 主人「下移上移，互换位置」，与 k 对调）
  [],                                                       // k -> 光标下移（H-220r3 与 j 对调）
  [],                                                       // l -> 光标右移（M-247②）
  ['Z', "'", '`', 'ž', 'ź', 'ż'],                            // z  H-216(CodeArts): 大写Z移首位=默认选中
  [],                                                       // x -> 剪切
  [],                                                       // c -> 复制
  [],                                                       // v -> 粘贴
  ['B', '!', '~', '¡'],                                     // b  H-216(CodeArts): 大写B移首位=默认选中
  [],                                                       // n -> 不做（M-247③），回普通字母键
  [],                                                       // m -> 删除光标后1字（H-220r3：原来删前文＝和退格重复，主人点名改掉）
];

// H-215(Qoder)：长按气泡的面板局部几何（vp）
interface BubbleGeom {
  left: number;
  top: number;
  width: number;
  // 单格宽 = width / 格数（>10 格时缩格，保证 e(14)/i(11)/o(12) 不超屏宽）
  cell: number;
}

// H-065（M-050）：候选条 L1/L2 统一左右内边距（真机 x≈4px 贴边修复）；估宽 availW 同步扣减
const CAND_PAD_H: number = 8;
// H-063（M-050）：功能键 SymbolGlyph 统一图标尺寸（跟随原键面字号档 20）
const FUNC_ICON_SIZE: number = 20;
// H-180：空格键左右滑移光标的步长（vp）。
// 口径已按安卓实物源码核准（2026-10-26，fcitx5-android 即三生安卓的内核，LGPL-2.1：
// 只取参数与语义，代码独立实现）：`BaseKeyboard.kt` 里空格键 `swipeThresholdX = dp(10f)`，
// 竖向阈值 `dp(800f)`＝禁用；每累计 10dp 发一次方向键（count 可 >1），默认开关
// `spaceSwipeMoveCursor = true`；抬手不 commit 空格（swipeRepeatTriggered 吃掉 click）。
// displayX 单位是 vp（`common.d.ts` 注明 Unit: vp）⇒ dp 与 vp 同值，直接用 10。
const SPACE_CURSOR_STEP: number = 10;

// 面板模式：qwerty = 26键字母，symbol = ?123符号页，t9 = 九宫格
type PanelMode = 'qwerty' | 'symbol' | 't9' | 'numpad';

// H-179：工具栏图标的按压反馈。安卓实物那排图标**没有常态底色**（纯图标浮在条上），
// 我们此前给每枚套了白底圆角框，和安卓/主人要的「简洁」都对不上 ⇒ 常态透明，按下才浮一层浅灰。
// H-238（Qoder 2026-10-28 01:2x）：这层浅灰的**色值**保留，但顶栏图标行（FuncIcon）不再走
// `stateStyles` 这条通道——实机量到抬手不恢复，见下面 FuncIcon 的注释再照抄那条通路。
// H-254（Qoder 2026-10-28 08:5x）：同一根因在 `···` 菜单行上第二次落地（点过的行停在 #DCE2EC
// 直到关菜单重开）⇒ 这里原来那个 `@Styles funcIconPressed()` 已**删掉**，不留给下一个人再挂回去；
// 全仓应只剩 `FUNC_ICON_PRESSED` 这个色值被 `.backgroundColor(...)` 显式使用。
const FUNC_ICON_PRESSED: string = '#DCE2EC';

// H-241（主人 2026-10-28 01:4x 原话「让长按空格，或者回车键，调出设置页面」）：
// 长按触发时长（ms）。比字母键出泡（450ms）长一档——空格/回车日常按得久一点也常见，
// 600ms 才认，避免正常打字误开设置页。安卓**没有**这个入口（契约 §0 已写明是主人的设计）。
const SETTINGS_HOLD_MS: number = 600;

// H-255（Qoder 2026-10-28 09:0x，主人原话「二选一，都给做成出设置了，把回车设置成长按到 github 主页吧」）：
// **长按空格＝设置页（保留）**；**长按回车＝打开项目开源主页**（二选一，不再重复同一入口）。
// 系统硬约束（先量再写，别当成能开）：基础模式（IME 安全模式，本机现值 `ime -g` = BASIC_MODE）
// 下输入法扩展进程**不能拉起任何 UIAbility**（官方 ime-kit-security 原文；`startAbility` 会抛 16000069
// "The extension cannot start the third party application"）⇒ 浏览器也拉不起来。
// 所以这条入口做成两态：完整体验模式 ⇒ 真开浏览器；基础模式 ⇒ 画一张卡片把地址与开关位置写清楚，
// **不许留「按了没反应」的键**（H-207 同族）。判定与调用在 `KeyboardController.openExternalUrl()`。
const GITHUB_HOME: string = 'https://github.com/ri0977-code/sansheng-ime';


@Entry
@Component
struct KeyboardIndex {
  @State preedit: string = '';
  @State candidates: RimeCandidate[] = [];
  @State rowHeight: number = 48;
  @State barHeight: number = 44;
  @State asciiMode: boolean = false;
  @State tradMode: boolean = false;
  // H-165（形态 B）：顶部功能磁贴展开态（左上 `>` 三角点开）。现有右上 chevron 仍管候选网格，语义不冲突
  @State showFuncBar: boolean = false;
  // H-189：候选栏「内容」透明度，只给展开/收起工具栏时做淡出→换→淡入（栏底色/高度不动）。
  @State barAlpha: number = 1;
  // H-184（主人 2026-10-26 13:2x「照安卓抄」＝拍板：做安卓式弹层菜单）：`···` 弹出的
  // 开关菜单是否打开。菜单是临时面板：点外面/再点一次关闭；打字自动关（H-180 同理）。
  @State funcMenuOpen: boolean = false;
  // H-194（CodeArts M-221 交付 / Qoder 集成）：工具栏图标行当前显示的**子面板**。
  //  '' = 图标行本身；'cursor' = 四向光标移动面板；'clipboard' = 剪贴板面板（粘贴当前内容）。
  //  点 cursor/clipboard 图标 → 整行换成对应面板（安卓 toolbar→sub-panel 同义）；
  //  点 ‹ / ▼ 收起时一并清回 ''（语义同收起，不保留子面板态）。
  //  H-234（Qoder 2026-10-28 00:4x，主人 2026-10-27 深夜「文本编辑折叠后，还显示灰色选中状态，
  //  没变回来」）：加 @Watch ⇒ **不论从哪一条路折叠 ⇆ 面板**（再点图标 / ‹ / ▼ / 展开候选网格 /
  //  打字自动收），都顺手退出「选择」模式。用 @Watch 而不是在每个赋值点补一行，是因为
  //  `funcSubPanel = ''` 在文件里有十处赋值点，漏一处就是主人这次看到的「没变回来」——
  //  同类教训（H-129 之后）：第二次发生的事故说明第一次的修法只是散文 ⇒ 必须有强制的单一出口。
  @State @Watch('onFuncSubPanelWatch') funcSubPanel: string = '';
  // H-234：@Watch 回调拿不到旧值，自己记一份；只用来判「从 textedit 折到关闭」这一条。
  private prevFuncSubPanel: string = '';
  // H-220（Qoder，主人「安卓里面有个选择键，可以按方向选择文本」）：控制器「选择」扩展
  // 选区模式的镜像态（真源在 KeyboardController，键盘 n 键与 ⇆ 面板「选择」格共用一个态）。
  @State selMode: boolean = false;
  // H-187：用户是否**手动展开**了工具栏（安卓 fcitx5-android `isToolbarManuallyToggled` 同义）。
  // Android 的工具栏是 Idle 态的子态：打字（有 preedit＋候选）整栏让给 Candidate，commit 回 Idle
  // 后又显示用户展开的工具栏。我们此前「收起就不再回来」，与安卓不一致（M-217 两问之一）。
  // pinned 只在用户点 › / ‹▼ 时改，打字不碰它。
  private funcBarPinned: boolean = false;
  // H-199（CodeArts M-223 C①）：动画中的**目标态**。展开动画 220ms 内 showFuncBar 还是旧值，
  // 去重若读旧值，打字触发的「收起」会被当成同向重复吞掉，随后在途回调又把栏弹开。
  private funcBarTarget: boolean = false;
  // H-199：动画**代次**。任何非动画调用（打字即收起、连点反向）都 ++，在途 onFinish 见到代次不符就自我作废。
  private funcBarGen: number = 0;
  // H-165：四枚引擎开关态（安卓磁贴大字＝当前状态、小字＝再点切到的目标）
  @State fullShape: boolean = false;      // 半角/全角
  @State extendedCharset: boolean = false; // 常用/增廣
  @State phraseComment: boolean = false;   // 反查注释（phraseComment，管候选注释）
  @State asciiPunct: boolean = false;     // 中英标点
  // H-227（Qoder 2026-10-28 08:0x，主人点单「完善设置菜单·参考安卓」）：`···` 菜单补的 5 枚滤镜开关镜像。
  // M-271 逐项核过的结论＝**滤镜与数据都在包里，缺的只是入口**（不是新造功能）：
  //   encnDic        -> lua/dic_4w_Filter.lua:42（数据 lua/dic_4w_cn.txt / dic_4w_en.txt）
  //   phraseExt      -> lua/phraseExt_Filter.lua:29（数据 lua/phraseExt commonPhrase.txt 等）
  //   phraseReplace  -> lua/phraseReplace_Filter.lua:18（数据 lua/phraseReplace.txt，schema 里默认关）
  //   abbrEn         -> lua/abbrGloss_Filter.lua:156（数据 lua/abbr_en.txt）
  //   pinyin         -> lua/pinyinAdding_Filter.lua:19（数据 lua/pinyinAdding.txt）
  // 五个都在 `wubi_pinyin.custom.yaml` 的 `switches/+` 里声明（第 6-27 行），
  // **`sansheng_t9.schema.yaml` 只有 ascii_mode/full_shape/ascii_punct/zh_trad** ⇒ 九键下必须置灰（假按钮＝H-090 教训）。
  @State encnDic: boolean = false;         // 中英对照（候选注释换成字典释义）
  @State phraseExtOn: boolean = false;     // 短语扩展
  @State phraseReplaceOn: boolean = false; // 敏感词替换
  @State abbrEn: boolean = false;          // 英文缩写
  @State pinyinAnnot: boolean = false;     // 拼音注音
  @State panelMode: PanelMode = 'qwerty';
  // H-278（Qoder 2026-10-30，主人 2026-10-30「突然想起单手模式还没做，做完再发包吧」）：
  // 单手模式＝键面整体缩到屏宽 80%，贴左或贴右，另一侧留空并放两枚手柄（⇄ 换边／✕ 退出）。
  // 只改外层容器宽度，**不动键高/键距**：面板窗口尺寸由 KeyboardController.computePanelSize()
  // 按行数/行高算（与宽度无关），键面各行本来就走百分比宽度 ⇒ 缩容器即整排等比收窄。
  // 状态**不落盘**：SettingsStore 契约表只有那 12 项（D-021「只留真实生效的项」＋ §6 变更记录规矩），
  // 表外键不许出现 ⇒ 输入法进程被系统回收后回满宽；同一进程内反复唤起键盘会记住（≥ H-278 真机口径）。
  @State oneHandOn: boolean = false;
  @State oneHandSide: string = 'right';   // 'left' | 'right'（右手持机为默认，拇指够得着右侧）
  // H-057：符号页数据驱动——分组数据 + 当前分组 id（禁存下标：Qoder 数据更新后分组数/顺序可能变）
  @State symbolGroups: SymbolGroup[] = FALLBACK_SYMBOL_GROUPS;
  @State activeSymbolGroupId: string = 'common';
  // Shift 本地状态：shiftOn = 单击大写（下一个字母后复位）；shiftLocked = 双击锁定大写
  @State shiftOn: boolean = false;
  @State shiftLocked: boolean = false;
  // M-034：候选栏 v2 状态
  @State candBarWidth: number = 0;
  // H-278（Qoder 2026-10-30）：面板**窗口**宽度（根 Stack onAreaChange 回填）。
  // 单手模式把候选栏收到 80% 后，`candBarWidth` 不再等于窗口宽——而 H-215 气泡定锚/夹取
  // 的 `winW/contentLeft` 必须按窗口算（否则右手贴边那几列的长按气泡会被往左夹 ~77vp，
  // 不在键上方）。所以另记一份根宽，气泡只认它；未量到时才退回 candBarWidth。
  @State rootWinW: number = 0;
  @State compactMode: boolean = false;
  @State expanded: boolean = false;       // ▼ 展开面板是否打开
  // H-078（M-058）：符号页「更多」完整分组列表是否打开（分类条第 8 项进入）
  @State showSymbolAll: boolean = false;
  @State symbolPage: number = 0;
  // H-078（M-058，D-014）：长按 ?123/ABC 弹出的布局切换菜单（26键/九键）是否打开
  @State showLayoutMenu: boolean = false;
  // H-054：记住进入符号页之前的布局（qwerty 或 t9），从符号页返回时回到此布局
  @State prevPanelMode: PanelMode = 'qwerty';
  // H-055：全量候选（引擎 v0.2.0），用于估宽算页大小，避免当前页切片导致棘轮
  @State allCandidates: RimeCandidate[] = [];
  // H-060（M-047）：UI 单一记账分页——allCandidates[0] 的全局绝对下标（引擎 v0.2.0）
  @State baseIndex: number = 0;
  // H-060：UI 页大小（恒等于最后一次 setPageSize 传给引擎的值；0 = 尚未计算，渲染退全量）
  @State uiPageSize: number = 0;
  // H-060：当前 UI 屏在 allCandidates 内的起始偏移（翻页起点 = 屏上末条 + 1 的绝对接续）
  @State uiPageStart: number = 0;
  // H-059（M-047）：展开网格当前屏偏移（本页切片内按 gridPageSize() 步进，H-065 动态列数）
  @State gridScreenOffset: number = 0;
  // H-168：网格翻屏过渡动画态——整屏翻页时旧屏淡出+轻移、新屏淡入归位（不硬翻）
  @State gridOpacity: number = 1;
  @State gridOffsetY: number = 0;
  // M-049（H-062）：当前按下键标识（'' = 无）——按下高亮与触感共用，Down 置 Up/Cancel 清
  @State pressedKey: string = '';
  // H-238（Qoder 2026-10-28 01:2x，主人「顶栏的文本编辑，折叠后还是灰底选中状态」）：
  // 顶栏图标行的按下态从框架的 stateStyles(pressed) 挪到这里显式持有（同 pressedKey 一套通路）。
  @State pressedFuncIcon: string = '';
  // H-254（Qoder 2026-10-28 08:5x，H-227 真机验收时量到的同族第二次落地）：
  // `···` 菜单每一行点过之后都停在按压色 #DCE2EC，直到把菜单关掉重开——
  // 与 H-238 同一根因（框架 pressed 状态抬手不复位），只是这次落在 FuncMenuItem（12 行）＋设置行上。
  // 同一条修法：显式 @State 持有，Down 上色、Up/Cancel 清色、onClick 再兜一次底。
  // 键＝Rime 开关名（如 'encnDic'）或 'settings'（设置行）。
  @State pressedMenuItem: string = '';
  // H-063（M-050）：布局键长按弹出的「中/英 · 简/繁」小菜单（原底栏中英键 H-043 逻辑迁入）
  @State showLangMenu: boolean = false;
  @State langLongPressed: boolean = false;  // 长按语言键标志——防止长按后 onClick 重复触发
  // 语言键上滑识别：Down 记录起始 windowY，Up 判断上滑量（>30vp 判定为上滑切繁）
  @State langTouchDownY: number = -1;
  @State showAbout: boolean = false;
  @State candFs: number = 18;

  @State symbolPages: FlatPage[] = [];
  @State pendingFlatIndex: number = 0;


  private lastFlipTime: number = 0;

  private lastPageSize: number = 0;
  private lastPreedit: string = '';       // H-055：上次编码串，只在变化时重算页大小
  private lastBaseIndex: number = 0;      // H-060：上次菜单页基址，判断引擎页边界与翻页方向
  private stripScroller: Scroller = new Scroller();
  // M-049（H-062）：触感节流时间戳（50ms 内不重复振）
  private lastVibrateTime: number = 0;
  // M-049（H-062）：退格连删状态机——bsDelay = 500ms 延迟定时器、bsTimer = 100ms 连删定时器（-1 = 无）
  private bsDelay: number = -1;
  private bsTimer: number = -1;
  private bsRepeatStarted: boolean = false;
  // H-221（Qoder 2026-10-27 15:3x，主人「hjkl 长按不撒手…连续执行，直到撒手」）：
  // 字母键方向连发定时器（-1=无）＋当前连发的键名（抬手时只停自己那把键，防串）。
  private dirRepeatTimer: number = -1;
  private dirRepeatCh: string = '';
  /**
   * H-206（Qoder 2026-10-26 真机，主人「退格下滑会多恢复一遍」）：本次按下是否已经
   * 被 500ms 长按触发过 clearAllContent。
   * 真机日志证据链：16:22:52.863 `bs_row longpress: clearAllContent`（删 120 字）
   * → 16:22:54.562 `bs_row swipe down: undoLastAction dy=83.7`（restore 120 字）
   * ——用户想撤销的是**上一次上屏**，结果下滑撤销的却是自己刚误触发的那次清空，
   * 净效果＝内容被清掉又原样回来，看起来就是「多恢复一遍」。
   * 两道防线：① Move 一超过滑动意图阈值就撤掉长按定时器（清空根本不该在滑动中发生）；
   * ② 万一清空已经发生（先按住不动、再下滑），手势动作前先把这次清空还原掉。
   */
  private bsClearAllFired: boolean = false;
  // H-078（M-058）：字母键上滑出次级字符标记——PanGesture onActionEnd 触发后置 true，
  // onTouch(Up) 里消费复位（Down 兜底复位），防上滑+点击双上屏。
  // H-154：语义扩展为「滑键完成」——上滑次级字符/下滑大写共用；字母键与退格键各自实例
  // 共享该标志，复位时序一致（手势 onActionEnd 置位、onTouch(Up) 消费复位），互不串。
  private swipeAltDone: boolean = false;
  private swipeDotDone: boolean = false;  // H-155：句号键上滑英文点标记（防与短按双上屏）
  // H-180：空格键左右滑移光标——按下横坐标/上一次横坐标/累计未满步长的位移/本次是否已滑出光标
  private spaceDownX: number = -1;
  private spaceLastX: number = -1;
  private spaceAccum: number = 0;
  private spaceSwipeDone: boolean = false;
  // H-154：滑动检测改用 onTouch 手写（PanGesture 在本 IME 面板内不触发——语言键 onTouch 上滑可用、
  // 字母键/退格键 PanGesture 不可用，真机实测）。记录按下时的 windowY，Up 时按位移判定上/下滑。
  private letterTouchDownY: number = -1;
  // H-165(Qoder)：本次按下过程中手指到达的最高点（displayY 最小值）。Up 时用「最高点」而不是
  // 「Up 时刻坐标」算位移——即使 Up 被重定向到别的组件，最高点仍然可信。
  private letterPeakY: number = -1;
  // H-165(Qoder)：本次按下到达的最低点（displayY 最大值），下滑（大写）用。
  private letterBottomY: number = -1;
  private dotTouchDownY: number = -1;  // H-155：句号键上滑英文点检测（onTouch 手写）
  // H-175：退格键上下滑——2026-10-24 23:53 `7ba71d7`（H-167）按当时口径删过一遍，
  // 主人 2026-10-25 16:0x 点名要回来：「退格，上下滑动还是没有」。语义照 H-166 真机验过的原样：
  // **上滑＝清除到上一个分隔符、下滑＝撤销最近一次上屏/清除**。
  // 注：这两个动作的实现在 `KeyboardController.ets`（clearToLastSeparator / undoLastAction）
  // 一直没删，删的只是键上的手势入口 ⇒ 本次是「接回入口」，不是重新发明。
  private bsTouchDownY: number = -1;
  private bsPeakY: number = -1;
  private bsBottomY: number = -1;
  private bsLastY: number = -1;
  // Up 阶段 event.touches/changedTouches 可能取不到窗口坐标 → Move 里持续记录 lastY 兜底
  private letterLastY: number = -1;
  private dotLastY: number = -1;
  private symbolScroller: ListScroller = new ListScroller();
  // H-164：候选行横向滚动 List 的 scroller（续页/复位滚动手势用；ArkUI 原生滚动，非 PanGesture）
  private candListScroller: ListScroller = new ListScroller();
  // H-257(CodeArts): 展开候选纵向连续滚动 List 的 scroller（丝滑滚动+按钮翻页）
  private expandedListScroller: ListScroller = new ListScroller();
  // H-164（Qoder 00:2x 修）：只有「用户手指按下过」才允许续页——初始布局/数据刷新触发的
  // onScrollIndex 不算用户滑动（否则首帧就连跳几屏、候选栏直接停在本页末尾）。
  private candDragArmed: boolean = false;
  // H-164（Qoder 00:3x 修）：本次触摸是否移动过。移动过的抬手不立刻撤许可，
  // 因为甩动的索引事件常在抬手后才到达（见 onScrollStop），白点/轻点则立即撤。
  private candDragMoved: boolean = false;
  // H-164：onScrollStop 没有索引参数，用最近一次 onScrollIndex 的可见末条兜底判「是否在尾部」
  private candLastVisible: number = 0;
  // H-164：续页后「新一屏首条」的绝对下标（跨 Rime 菜单页时据此对齐 uiPageStart，不跳条）
  private pendingForwardAbs: number = -1;
  // H-164：List 是否已挂载——setUiListener 可能早于首帧 UI 绑定就回调，
  // 此时调 scrollToIndex 属于「控制器未绑定」用法（可能抛异常），故统一走 candScrollToStart() 守卫。
  private candListReady: boolean = false;
  // H-155：字母键长按气泡——正在长按的字母键（'' 无）；气泡内高亮符号下标（-1 未指向）。
  // 仅对非 a/s/v/c 的字母键生效；气泡画在键内部（Stack 顶部，溢出键区域）。
  // H-215(Qoder 2026-10-27)：主人点名「长按气泡功能还没有」。真机铁证（h38）：
  // hilog 已打出 `longpress q -> bubble`（状态置位成功）但屏上无气泡——
  // 这两个字段从 4f14d27 落地那天起就是普通 private，**没有 @State**，
  // 赋值不触发重渲染 ⇒ 气泡分支永远画不出来。改 @State 即修。
  @State longPressLetter: string = '';
  @State longPressSymIdx: number = -1;
  // H-216(Qoder)：本次出泡手指是否进过泡范围——没进过则「松手=默认选中第 0 格（数字）」，
  // 进过则恢复 H-215 口径（泡外松手=取消）。
  private bubbleEntered: boolean = false;
  // H-216(CodeArts)：手指是否已滑进气泡区域——出泡后手指仍在键上时 ArkUI 会持续触发
  // 假 Move（windowX 没变），bubbleTouchMove 用距离门槛过滤；手指滑进气泡后置 true，
  // 后续 Move 直接选中不再过滤。
  private bubbleTouched: boolean = false;
  // H-215(Qoder)：字母键实测键宽（vp，onAreaChange 回填）——气泡夹取用。
  private keyWidthVp: number = 0;
  // H-215(Qoder)：各字母键全局坐标（vp，**窗口系**，onAreaChange 实测）——顶层气泡定锚用。
  private letterKeyGlobalPos: Map<string, Position> = new Map();
  // H-215(Qoder)：**探针实测标定（h38_v7diag）**：DIAG 置 position(150,200) ⇒ 渲染屏幕位
  // (150.0, 517.1)px→vp(150.9, 517.5)。⇒ 顶层 Stack 的 .position 与 globalPosition 同为
  // **窗口系**，且窗口左缘 = 屏幕左缘（x 恒等，无偏移）；窗口顶在屏幕 317vp
  // （= 屏高 809.14 − 窗口高 492.1，窗口含可见面板上方的透明区）。
  // 触摸映射直接用 TouchObject.windowX（与 globalPosition 同系，SDK common.d.ts:8607），
  // 不需要任何屏幕↔窗口换算 ⇒ screenOffXvp 废弃为 0（保留字段仅供日志）。
  private screenOffXvp: number = 0;
  private screenOffYvp: number = 0;
  private panelWindowHeightVp: number = 492;
  // H-155：a/s/v/c 长按编辑框动作标志——置位后 onTouch(Up) 不再发字母本身，防重复。
  private editorActionDone: boolean = false;
  // H-215(Qoder)：气泡已接管松手（上屏/取消）⇒ 键侧 Up 不再走点键/滑动分支，防重复输入。
  private bubbleUpSwallow: boolean = false;
  // H-215(Qoder)：出泡计时器——ArkUI 在手指滑出键面时会把触摸流**重定向**并给键发 Cancel
  // （真机 h38_v8_drag_q：450ms 内滑进气泡 ⇒ LongPressGesture 根本不触发 ⇒ 永远不出泡）。
  // 改按下起 setTimeout 计时，与手指后续位置无关；到点仍按住且未滑动才出泡。
  private bubbleTimer: number = -1;
  private letterTouchDownX: number = -1;
  // H-215：手指是否仍按住（Up 才置 false；重定向来的 Cancel 不置）——出泡计时器判据。
  private letterHeld: boolean = false;

  // ---- H-241（Qoder 2026-10-28）设置页：入口 + 契约 12 项的键盘侧读取点 ----
  // 唯一真相源＝SettingsStore（输入法进程自己的 preferences 沙箱）；渲染期**只同步读**镜像 @State，
  // 绝不在 .fontSize()/.height() 里 await（契约 §4）。写侧自增 settingsRev → 下面 @Watch 重取镜像 → 当场重绘。
  @State settingsOpen: boolean = false;
  /** H-255：长按回车在基础模式下拉不起浏览器时，画「开源主页」卡片（地址＋开关位置）。 */
  @State githubCardOpen: boolean = false;
  @StorageLink(SETTINGS_REV_KEY) @Watch('syncFromSettings') settingsRev: number = 0;
  /** §3-2 候选词字号；0＝用户没定过 ⇒ 沿用 H-077 宽度自适应档位。 */
  @State candFsUser: number = 0;
  /** §3-3 键面字母字号（LetterKey 与 T9Key 同一个值，两处读取点必须一致）。 */
  @State keyFs: number = 20;
  /** §3-6 长按触发时长（出泡计时器与兜底手势共用）。 */
  @State longPressDelayMs: number = 450;
  /** §3-7 按键时弹出字符（气泡总开关）。 */
  @State popupOnPress: boolean = true;
  /** §3-5 按键时振动。 */
  @State hapticOn: boolean = true;
  /** §3-12 显示编码行（L1）。 */
  @State preeditShown: boolean = true;
  /** §3-9 展开网格每页条数（原 GRID_FULL_PAGE=50）。 */
  @State gridPageN: number = 50;
  /** §3-10 空格划动移光标步长（原 SPACE_CURSOR_STEP=10vp）。 */
  @State spaceStepN: number = 10;
  /** §3-4 每页候选词数；0＝用户没定过 ⇒ 沿用按宽度自适应（H-077），横屏仍拿得到 H-035 的 9。 */
  @State pageSizePref: number = 0;
  /** §3-11 默认展开工具栏：只存镜像＋判「这次是不是真的翻转了」，翻转才动工具栏。 */
  @State expandDefaultOn: boolean = false;
  /** 长按空格/回车的计时器 id（-1＝没在计）。不用 LongPressGesture：H-215 真机铁证——
   *  手指滑出键面时 ArkUI 把触摸流重定向并给键发 Cancel，手势可能整个不触发 ⇒ 入口会「点了没反应」。 */
  private settingsHoldTimer: number = -1;
  private settingsHoldKey: string = '';
  private settingsHoldDownX: number = -1;
  private settingsHoldDownY: number = -1;
  /** 长按已触发 ⇒ 紧随其后的那一次同键 onClick 不再发空格/回车（主人口径「长按不得再补发一个空格」）。 */
  private settingsHoldFiredKey: string = '';

  // ---- M-037 候选栏 v2 单行版尺寸计算 ----

  /** H-077 ③：候选词字号——读 recomputePageSize 设的三档值（>=620→18 / >=460→20 / 其余→18）。
   *  H-241 契约 §3-2：用户在设置页定过「候选词字号」就用他的值（14–22vp），没定过沿用自适应档。
   *  注意**只换字面大小，不换行高**——见下面 candRowHeight 的注释（窗口预算 236vp 死线）。 */
  private candFontSize(): number {
    return this.candFsUser > 0 ? this.candFsUser : this.candFs;
  }

  /** 单行候选行高（vp）：参照 kanonIME candidateRowHeight 公式。
   *  H-241：继续用**自适应档** this.candFs 算，不跟用户字号走。
   *  原因（量过的，不是猜的）：栏容器高 = max(barHeight=44, L1 16 + 候选行)，
   *  窗口预算恒为 44 + 4×48 = 236vp（H-208 定稿，不再随状态伸缩）。若 22vp 字把行高顶到 33vp，
   *  容器就成 49vp ⇒ 超出 236 的部分把键区末行裁掉（H-213 那条死线）。
   *  而行高 28vp 装 22fp 的字是够的（ArkUI 默认行高≈1.2×字号＝26.4vp＜28vp），字不会被切。 */
  private candRowHeight(): number {
    return Math.max(28, Math.ceil(this.candFs * 1.2 + 6));
  }

  /** 反查行高度（vp）：12fp 文字 + padding。 */
  private commentRowHeight(): number {
    return 16;
  }

  /** H-096：候选栏自适应高度——横屏（barHeight<40）时压缩，给主键区更多空间。
   *  H-165 返工（Qoder 2026-10-25 14:5x）：**竖屏**容器高度必须 ≥ 同时可见行高之和。
   *  原来直接返回 barHeight(44)，而 L1(16)+候选行(candRowHeight) 在 candFs=20 档时是 46vp，
   *  差的 2vp 就是「候选行被主键区吃掉一截」的溢出（Mate80 走 18 档＝正好 44，真机看不出来，
   *  宽候选栏机型才会踩）。取 max 后这条不变式由构造保证，闸门 scripts/h165_bar_height_check.py 判全绿。
   *  横屏分支**一行不改**：那边 L1 本就隐藏、只剩候选行，实测预算 24vp 与行高 28vp 差 4vp
   *  是 H-096 遗留（已记 ISSUES），但横屏判据（H-164 ⑨）还挂在主人那儿没验过，
   *  不在能验的屏幕上动几何——宁缺勿改。 */
  /** H-203（主人 2026-10-26「在不输入的时候显得太宽了，安卓的窄，但在输入的时候有候选的
   *  时候字母自动上去一行」）：空闲态＝单行窄条。判据与安卓 ExpandButtonStateMachine 的
   *  Idle 同口径：无 preedit、无候选、工具栏也没展开。打字/有候选/工具栏展开时仍是
   *  barHeight(44) 的「L1 字母行 + L2 候选行」双行。 */
  private barIdle(): boolean {
    return !this.showFuncBar && !this.expanded &&
      this.candidates.length === 0 && this.preedit.length === 0;
  }

  private candBarHeight(): number {
    if (this.barHeight < 40) {
      return Math.max(24, this.barHeight - 6);
    }
    // H-208（Qoder 2026-10-26 20:5x）：**恒返 44vp**，不再因空闲而缩成 28。
    // 原因：控制器现在把窗口高度固定为「预算栏高 + 4 行键」，栏内若只画 28vp，
    // 剩下的 16vp 就成了键区与栏之间的缝；反过来让窗口跟栏缩又会让键盘蹦跳（主人骂的那条）。
    // 所以栏容器始终占满 44vp，**空闲时内容靠下画一行**（见 CandidateBar 的 alignItems），
    // 上方 16vp 是同色背景 ⇒ 视觉仍是窄条，键盘却永远不动。
    return Math.max(this.barHeight, this.commentRowHeight() + this.candRowHeight());
  }

  /**
   * H-203(Qoder)：把**实际栏高**报给控制器，面板窗口 = 栏高 + 4 行键高。
   * 主人原话「顶栏…在不输入的时候显得太宽了，安卓的窄，但在输入的时候有候选的时候
   * 字母自动上去一行」——只把栏画窄、窗口不变的话，16vp 空白还在，视觉没变；
   * 必须让窗口跟着缩，键区才随候选出现/消失整体上下移一行（安卓同口径）。
   * 调它不会造成抖动：控制器只在栏高真变时 resize。
   */
  private syncPanelBarHeight(): void {
    // H-220(CodeArts)：符号页时候选栏容器高度为0（UI层），但 applyBarHeightVp(0) 是空操作
    //（被 KeyboardController.ets:283 `if (!(barVp > 0)) return;` 吞掉）。
    // 符号页的"增大显示空间"靠 CandidateBar 容器 .height(0) 实现，不靠窗口伸缩。
    keyboardController.applyBarHeightVp(this.candBarHeight());
  }

  /**
   * H-241（契约 §1-③）：把 SettingsStore 的当前值读进渲染用的 @State 镜像。
   * 调用时机＝① 面板 `aboutToAppear` 里 `load()` 完成之后；② 设置页每次写值后 `settingsRev` 自增
   * 由 @Watch 触发。 ⇒ **改完屏上立刻变，不要求重启输入法**。
   * 同时把「键盘高度百分比」这种**窗口级**的变化推给控制器（只有真变才 resize，见 applySettingsChanged）。
   */
  syncFromSettings(_propName: string): void {
    const st: SettingsStore = SettingsStore.inst();
    // H-241：候选字号特殊在「它本来有一套按宽度自适应的档位（H-077：>=620→18 / >=460→20 / 其余→18）」。
    // 用户**没动过**这一项时必须让自适应继续说话，否则默认值 18 会把宽屏机型的 20 档永久压掉
    // （＝设置页还没点开就把键盘改坏了，这是新增功能绝不能带来的回归）。
    this.candFsUser = st.isUserSet('cand_font_size') ? st.num('cand_font_size') : 0;
    this.keyFs = st.num('key_font_size');
    this.longPressDelayMs = st.num('key_long_press_delay');
    this.popupOnPress = st.sw('popup_on_key_press');
    this.hapticOn = st.sw('kbd_haptic');
    this.preeditShown = st.sw('show_preedit');
    this.gridPageN = st.num('grid_page_size');
    this.spaceStepN = st.num('space_swipe_step');
    this.pageSizePref = st.isUserSet('page_size') ? st.num('page_size') : 0;
    // H-241 契约 §3-11「默认展开工具栏」：既管「下次调起键盘时的初态」，也管「现在就变」
    //（主人 §5-5 的收口标准是「拖一根滑条、看键盘当场变」，开关类同理——翻转后不该没反应）。
    // 读进镜像再判变化，而不是每次 sync 都强推一遍：否则打字途中改别的设置会把工具栏顶回来盖候选
    //（H-208 那条真机教训）。
    const expand: boolean = st.sw('expand_toolbar_by_default');
    const expandChanged: boolean = expand !== this.expandDefaultOn;
    this.expandDefaultOn = expand;
    keyboardController.applySettingsChanged();
    if (expandChanged) {
      this.setFuncBar(expand);
      this.funcBarPinned = expand;
      console.info(`${TAG} H-241 expand_toolbar_by_default flipped -> ${expand}`);
    }
    // 生效判据取证就看这行（H-239 每项改前/改后各量一次，对着 hilog 比）
    console.info(`${TAG} H-241 settings synced: keyFs=${this.keyFs} candFs=${this.candFsUser} ` +
      `lpp=${this.longPressDelayMs} popup=${this.popupOnPress} haptic=${this.hapticOn} ` +
      `preedit=${this.preeditShown} grid=${this.gridPageN} step=${this.spaceStepN} ` +
      `pageSize=${this.pageSizePref} h=${st.num('kbd_height_pct')}% rev=${this.settingsRev}`);
  }

  /** H-241：打开设置页覆盖层。入口＝长按空格、`···` 菜单里那枚「设置」。
   *  H-255（主人 2026-10-28 09:0x「二选一」）：**长按回车不再走这里**，改去开源主页——两个键
   *  不再重复同一个入口；回车那条见 `openGithubHome()`。 */
  private openSettings(): void {
    this.settingsOpen = true;
    console.info(`${TAG} H-241 settings panel opened`);
  }

  /**
   * H-278（Qoder 2026-10-30）：`···` 菜单里的「单手模式」——关 → 开·贴右 → 开·贴左 → 关 轮转。
   * 为什么按这个顺序：第一次打开的人多半右手持机 ⇒ 贴右；再点一下换边；第三下回到满宽。
   * 打开/换边后**顺手关掉菜单**（与「设置」行同款），让键面马上可见——菜单只是入口。
   */
  private toggleOneHandFromMenu(): void {
    if (!this.oneHandOn) {
      this.oneHandOn = true;
      this.oneHandSide = 'right';
    } else if (this.oneHandSide === 'right') {
      this.oneHandSide = 'left';
    } else {
      this.oneHandOn = false;
    }
    this.funcMenuOpen = false;
    console.info(`${TAG} H-278 one-hand on=${this.oneHandOn} side=${this.oneHandSide}`);
  }

  /** H-278：把单手模式切到另一侧（键面 ⇄ 手柄）。 */
  private flipOneHandSide(): void {
    this.oneHandSide = this.oneHandSide === 'left' ? 'right' : 'left';
    console.info(`${TAG} H-278 one-hand side -> ${this.oneHandSide}`);
  }

  /** H-255（Qoder 2026-10-28 09:0x）：长按回车＝去项目开源主页。
   *  真开浏览器受系统安全模式管制（基础模式拉不起 UIAbility，见 `GITHUB_HOME` 上方注释）⇒
   *  拉不起来就画卡片，把地址和「完整体验模式」开关位置写给他；**不留按了没反应的键**。 */
  private openGithubHome(): void {
    keyboardController.openExternalUrl(GITHUB_HOME).then((res: string) => {
      if (res === 'opened') {
        console.info(`${TAG} H-255 long-press enter -> github opened`);
        return;
      }
      this.githubCardOpen = true;
      console.info(`${TAG} H-255 long-press enter -> github card (${res})`);
    }).catch((e: Error) => {
      this.githubCardOpen = true;
      console.warn(`${TAG} H-255 openGithubHome: ${e.message}`);
    });
  }

  /** H-241：长按**开始**——Down 起计时，中途滑出阈值就撤（空格左右滑是移光标，不是开设置）。 */
  private settingsHoldStart(keyId: string, x: number, y: number): void {
    this.settingsHoldAbort();
    this.settingsHoldKey = keyId;
    this.settingsHoldDownX = x;
    this.settingsHoldDownY = y;
    this.settingsHoldTimer = setTimeout(() => {
      this.settingsHoldTimer = -1;
      const who: string = this.settingsHoldKey;
      this.settingsHoldFiredKey = who;
      this.settingsHoldKey = '';
      this.pressedKey = '';
      if (who === 'enter') {
        // H-255：主人的「二选一」——空格开设置，回车去开源主页。
        this.openGithubHome();
      } else {
        this.openSettings();
        console.info(`${TAG} H-241 long-press ${who} ${SETTINGS_HOLD_MS}ms -> settings`);
      }
    }, SETTINGS_HOLD_MS);
  }

  /** H-241：Move——位移超阈值说明这不是「按住不动」，撤计时。 */
  private settingsHoldMove(x: number, y: number): void {
    if (this.settingsHoldTimer < 0) {
      return;
    }
    if (Math.abs(x - this.settingsHoldDownX) > 12 || Math.abs(y - this.settingsHoldDownY) > 12) {
      this.settingsHoldAbort();
    }
  }

  /** H-241：抬手/取消——只清计时器，**不动**已触发标记（要留给紧随其后的 onClick 吞掉那一次输入）。 */
  private settingsHoldEnd(): void {
    if (this.settingsHoldTimer >= 0) {
      clearTimeout(this.settingsHoldTimer);
      this.settingsHoldTimer = -1;
    }
    this.settingsHoldKey = '';
  }

  /** H-241：彻底作废本次长按（新的 Down / 面板销毁）。 */
  private settingsHoldAbort(): void {
    if (this.settingsHoldTimer >= 0) {
      clearTimeout(this.settingsHoldTimer);
      this.settingsHoldTimer = -1;
    }
    this.settingsHoldKey = '';
    this.settingsHoldFiredKey = '';
  }

  /** H-241：长按触发过的那一下点击要吞掉，且只吞**同一个键**的那一下（绝不吞别的键的输入）。 */
  private settingsHoldConsume(keyId: string): boolean {
    if (this.settingsHoldFiredKey === keyId) {
      this.settingsHoldFiredKey = '';
      console.info(`${TAG} H-241/H-255 suppress click after long-press: ${keyId}（长按已开设置或主页，不再补发输入）`);
      return true;
    }
    return false;
  }


  /** H-190：候选注释文本。安卓 `CandidateItemUi.updateCandidate()` 把 comment 拼在**词的同一条目内**
   *  （`color(fg){text} color(commentColor){comment}`），不是拼进预编辑行。这里只做去空白，
   *  词与注释之间的间距由 L2 条目的 Row space 负责。返回空串＝这条候选没有注释。
   *
   *  H-202 真机返工（Qoder 2026-10-26 19:2x，主人「这种排列后面的注释显示不全」）：
   *  引擎给的 comment 是 `[fwaj] guihua`（五笔编码 + 拼音）两段拼一起。双列网格每格约 172vp，
   *  词 16fp 之后剩下的宽度只够一段，于是 `…` 截在拼音中间——真机上看得见（a2_grid.jpeg 第一行）。
   *  安卓网格里**只显示拼音**、不显示编码（编码对普通用户是噪音），照此把方括号编码段剥掉：
   *  剩下的拼音在双列里放得下，`…` 自然消失。L2 候选行同源受益（同一函数）。
   *  剥法保守：只有**行首**就是 `[...]` 且括号后有内容才剥；其它形态原样返回，不猜。 */
  private candCommentText(cand: RimeCandidate): string {
    const c: string = (cand.comment ?? '').trim();
    const m: RegExpMatchArray | null = c.match(/^\[[^\]]*\]\s*(.+)$/);
    return m !== null ? m[1].trim() : c;
  }

  /**
   * H-047/H-054：切换面板模式时联动 Rime 方案。
   * 进入九宫格 → selectSchema('sansheng_t9')，退出 → selectSchema('wubi_pinyin')。
   * H-054：进符号页时记 prevPanelMode，从符号页返回时回到 prevPanelMode。
   * 切方案会重置开关态，切完用 getOption 回填键面。
   */
  private switchPanelMode(newMode: PanelMode): void {
    const oldMode: PanelMode = this.panelMode;
    console.info(`${TAG} switchPanelMode: ${oldMode} → ${newMode}, prev=${this.prevPanelMode}`);
    if (newMode === oldMode) {
      console.warn(`${TAG} switchPanelMode: early return (same mode)`);
      return;
    }
    // H-054：进符号页时记住当前布局
    if (newMode === 'symbol' && oldMode !== 'symbol') {
      this.prevPanelMode = oldMode;
      this.resetActiveSymbolGroup();
      this.showSymbolAll = false;
    }
    // 进入 numpad 时不覆盖 prevPanelMode——prevPanelMode 保持为进入 symbol 时
    // 记录的字母布局（qwerty/t9），从 numpad 点 ABC 直接回字母键盘而非退回 symbol
    this.panelMode = newMode;
    // 引擎方案联动：t9 → sansheng_t9，qwerty → wubi_pinyin，symbol/numpad 不切方案
    if (newMode === 't9') {
      keyboardController.selectSchema('sansheng_t9');
      this.syncEngineOptions();
    } else if (newMode === 'qwerty') {
      keyboardController.selectSchema('wubi_pinyin');
      this.syncEngineOptions();
    }
    if (newMode === 'symbol' && oldMode !== 'symbol') {
      // H-057：进符号页重置到第一组（旧语义 symbolPage=0），按 id 记不按下标
      this.resetActiveSymbolGroup();
    }
    // H-220(CodeArts): sync bar height on panel mode switch
    this.syncPanelBarHeight();
  }

  /** H-047：切方案后开关态会被重置，从引擎读回真实状态回填键面。
   *  H-165（形态 B）：一并回填四枚功能磁贴的引擎开关态（先读后写，别把文案写反）。
   *  H-227（Qoder）：再加五枚滤镜开关——**一律以引擎读回为准**，不写死默认值，
   *  否则 `wubi_pinyin.custom.yaml` 里 `reset: 1`（encnDic/phraseExt/abbrEn 默认开）会在键面上显示成「关」。 */
  private syncEngineOptions(): void {
    this.asciiMode = keyboardController.getOption('ascii_mode');
    this.tradMode = keyboardController.getOption('zh_trad');
    this.fullShape = keyboardController.getOption('full_shape');
    this.extendedCharset = keyboardController.getOption('extended_charset');
    this.phraseComment = keyboardController.getOption('phraseComment');
    this.asciiPunct = keyboardController.getOption('ascii_punct');
    // H-227：五枚滤镜开关回填（引擎是唯一真相源；T9 方案下这些 getOption 返回 false，条目本身已置灰）
    this.encnDic = keyboardController.getOption('encnDic');
    this.phraseExtOn = keyboardController.getOption('phraseExt');
    this.phraseReplaceOn = keyboardController.getOption('phraseReplace');
    this.abbrEn = keyboardController.getOption('abbrEn');
    this.pinyinAnnot = keyboardController.getOption('pinyin');
  }

  /** H-165（形态 B）：功能磁贴统一切换入口——写引擎 + 回填本地态。
   *  磁贴大字＝当前状态，小字＝再点切到的目标（安卓语义）。 */
  private toggleFuncOption(name: string, cur: boolean): void {
    keyboardController.setOption(name, !cur);
    switch (name) {
      case 'ascii_mode':
        this.asciiMode = !cur;
        break;
      case 'zh_trad':
        this.tradMode = !cur;
        break;
      case 'full_shape':
        this.fullShape = !cur;
        break;
      case 'extended_charset':
        this.extendedCharset = !cur;
        break;
      case 'phraseComment':
        this.phraseComment = !cur;
        break;
      case 'ascii_punct':
        this.asciiPunct = !cur;
        break;
      // H-227（Qoder）：`···` 菜单新增的五枚滤镜开关，走的还是同一条 setOption 链（不造第二套开关）。
      case 'encnDic':
        this.encnDic = !cur;
        break;
      case 'phraseExt':
        this.phraseExtOn = !cur;
        break;
      case 'phraseReplace':
        this.phraseReplaceOn = !cur;
        break;
      case 'abbrEn':
        this.abbrEn = !cur;
        break;
      case 'pinyin':
        this.pinyinAnnot = !cur;
        break;
      default:
        break;
    }
    // H-227：真机取证用的可观测——「点了有没有反应」必须能用一条日志判定，不靠肉眼猜标签。
    // （紧接着的 syncEngineOptions 会从引擎读回，引擎没吃进去时标签会被打回原样＝不会假亮。）
    console.info(`${TAG} H-227 toggle option: ${name}=${!cur}`);
    // 切换后方案可能重置其它开关态，读回一次保持一致
    this.syncEngineOptions();
  }

  /** H-165（形态 B）：该磁贴在当前方案下是否可用。
   *  `extended_charset`/`phraseComment` 只在 wubi_pinyin 声明，九键（sansheng_t9）没有 ⇒ 置灰，
   *  否则主人点了没反应＝假按钮（spec §七）。
   *  H-227（Qoder）：清单收进 `WUBI_ONLY_OPTIONS` 常量——那五枚滤镜开关同样只在 wubi_pinyin 的
   *  `switches/+` 里声明（`sansheng_t9.schema.yaml:33` 只有四枚），以后再加开关只改那一处，别散着硬写。 */
  private funcTileEnabled(name: string): boolean {
    if (this.panelMode !== 't9') {
      return true;
    }
    return WUBI_ONLY_OPTIONS.indexOf(name) < 0;
  }

  /** H-165 返工：磁贴小字（再点切到的目标）——写死在 builder 体外会让按值参数冻住，见 FuncTile。 */
  private funcTileLabel(option: string): string {
    switch (option) {
      case 'zh_trad':
        return '简繁';
      case 'ascii_mode':
        return '中英';
      case 'full_shape':
        return '半全';
      case 'ascii_punct':
        return '标点';
      case 'extended_charset':
        return '增廣';
      case 'phraseComment':
        return '注释';
      default:
        return option;
    }
  }

  /** H-165 返工：磁贴大字＝引擎当前态（读 @State，syncEngineOptions 负责与引擎对齐）。 */
  private funcTileState(option: string): string {
    switch (option) {
      case 'zh_trad':
        return this.tradMode ? '简' : '繁';
      case 'ascii_mode':
        return this.asciiMode ? '英' : '中';
      case 'full_shape':
        return this.fullShape ? '全' : '半';
      case 'ascii_punct':
        return this.asciiPunct ? '中' : '英';
      case 'extended_charset':
        return this.extendedCharset ? '增廣' : '常用';
      case 'phraseComment':
        return this.phraseComment ? '开' : '关';
      default:
        return '';
    }
  }

  // ---- H-057 符号页数据驱动（M-046）----

  /** H-057：从 rawfile/symbols/symbols.json 读符号分类（Qoder 数据）。
   *  任何一步失败（文件不存在/解析失败/数据不合法）都静默回落写死表，不许白屏。 */
  private loadSymbolGroups(): void {
    let ctx: common.Context | undefined = undefined;
    try {
      ctx = getContext(this) as common.Context;
    } catch (e) {
      return;
    }
    if (ctx === undefined || ctx.resourceManager === undefined) {
      return;
    }
    try {
      const raw: Uint8Array = ctx.resourceManager.getRawFileContentSync('symbols/symbols.json');
      const text: string = this.decodeUtf8(raw);
      const groups: SymbolGroup[] = this.parseSymbolGroups(text);
      if (groups.length > 0) {
        this.symbolGroups = groups;
        this.resetActiveSymbolGroup();
        this.rebuildSymbolPages();
        console.info(`${TAG} symbols.json loaded: ${groups.length} groups`);
      } else {
        console.warn(`${TAG} symbols.json empty/invalid, fallback in use`);
      }
    } catch (e) {
      // 当前预期状态：Qoder 数据未落，rawfile/symbols/symbols.json 不存在 → 用写死表
      console.warn(`${TAG} rawfile symbols/symbols.json unavailable, fallback in use`);
    }
  }

  /** H-057：JSON.parse 结果逐字段类型收窄（ArkTS 严格模式不许无类型对象字面量直接用）。
   *  只有字段齐全且合法的分组才收进来；返回空数组 = 数据不合法，由调用方回落。 */
  private parseSymbolGroups(text: string): SymbolGroup[] {
    const out: SymbolGroup[] = [];
    let parsed: Object | null = null;
    try {
      parsed = JSON.parse(text) as Object;
    } catch (e) {
      return out;
    }
    if (parsed === null) {
      return out;
    }
    const root: Record<string, Object> = parsed as Record<string, Object>;
    const groupsObj: Object | undefined = root['groups'];
    if (groupsObj === undefined || !Array.isArray(groupsObj)) {
      return out;
    }
    const groupsArr: Object[] = groupsObj as Object[];
    for (let i = 0; i < groupsArr.length; i++) {
      const gr: Record<string, Object> = groupsArr[i] as Record<string, Object>;
      const id: Object | undefined = gr['id'];
      const label: Object | undefined = gr['label'];
      const itemsObj: Object | undefined = gr['items'];
      if (typeof id !== 'string' || typeof label !== 'string' ||
        id.length === 0 || label.length === 0 || itemsObj === undefined || !Array.isArray(itemsObj)) {
        continue;
      }
      const groupId: string = id;
      const groupLabel: string = label;
      const itemsArr: Object[] = itemsObj as Object[];
      const items: string[] = [];
      for (let j = 0; j < itemsArr.length; j++) {
        const it: Object = itemsArr[j];
        if (typeof it === 'string') {
          items.push(it);
        }
      }
      if (items.length > 0) {
        out.push({ id: groupId, label: groupLabel, items: items });
      }
    }
    return out;
  }

  /** H-057：Uint8Array → string——照 RimeDataInstaller.decodeUtf8 抄的 UTF-8 手工解码
   *  （ArkTS 无内置 TextDecoder，其实现是 private 无法复用）。 */
  private decodeUtf8(bytes: Uint8Array): string {
    let out: string = '';
    let i: number = 0;
    while (i < bytes.length) {
      const b0: number = bytes[i];
      let code: number = b0;
      let len: number = 1;
      if (b0 >= 0xF0) {
        code = b0 & 0x07;
        len = 4;
      } else if (b0 >= 0xE0) {
        code = b0 & 0x0F;
        len = 3;
      } else if (b0 >= 0xC0) {
        code = b0 & 0x1F;
        len = 2;
      }
      for (let k: number = 1; k < len && i + k < bytes.length; k++) {
        code = (code << 6) | (bytes[i + k] & 0x3F);
      }
      i += len;
      if (code > 0xFFFF) {
        const c: number = code - 0x10000;
        out += String.fromCharCode(0xD800 + (c >> 10), 0xDC00 + (c & 0x3FF));
      } else {
        out += String.fromCharCode(code);
      }
    }
    return out;
  }

  /** H-057：当前分组的符号表（按 id 找；找不到退第一组，永不返回空 → 不白屏）。 */
  private activeSymbolItems(): string[] {
    for (const g of this.symbolGroups) {
      if (g.id === this.activeSymbolGroupId) {
        // H-081（M-059-review2）：不重排数据——english 组 28 项靠主区翻页取全
        //（第 1 页前 19 项 + 第 2 页 9 项），`/`（27）与 `\`（21）在第 2 页可达。
        return g.items;
      }
    }
    if (this.symbolGroups.length > 0) {
      return this.symbolGroups[0].items;
    }
    return [];
  }


  /** H-057：重置当前分组到第一组（进符号页时调，等价旧 symbolPage=0）。 */
  private resetActiveSymbolGroup(): void {
    if (this.symbolGroups.length > 0) {
      this.activeSymbolGroupId = this.symbolGroups[0].id;
    }
    this.symbolPage = 0;
  }

  /** H-081：摊平页序列——7 一级分类 + 其余组，每组按 19 项/页分页。 */
  private rebuildSymbolPages(): void {
    let pages: FlatPage[] = [];
    for (const gid of SYMBOL_SWIPER_GROUPS) {
      const items: string[] = this.symbolItemsById(gid);
      const pageCount: number = Math.ceil(items.length / 19);
      for (let p: number = 0; p < pageCount; p++) {
        pages.push({ groupId: gid, page: p });
      }
    }
    for (const g of this.symbolGroups) {
      if (SYMBOL_SWIPER_GROUPS.indexOf(g.id) === -1) {
        const pageCount: number = Math.ceil(g.items.length / 19);
        for (let p: number = 0; p < pageCount; p++) {
          pages.push({ groupId: g.id, page: p });
        }
      }
    }
    this.symbolPages = pages;
  }

  /** H-081：按 id 取符号表（找不到退空数组）。 */
  private symbolItemsById(groupId: string): string[] {
    for (const g of this.symbolGroups) {
      if (g.id === groupId) {
        return g.items;
      }
    }
    return [];
  }

  /** H-081：groupId 在摊平序列中的第一页下标（找不到返 -1）。 */
  private flatFirstIndex(groupId: string): number {
    for (let i: number = 0; i < this.symbolPages.length; i++) {
      if (this.symbolPages[i].groupId === groupId) {
        return i;
      }
    }
    return -1;
  }

  // H-215(CodeArts)：符号页顶栏换工具栏后，每页 19 项分 3 行（7+6+6），
  // 配合 ListItem 4 Row 结构（数字行 + 3 行符号），多一行可视。
  private symbolRowItems(groupId: string, page: number, row: number): string[] {
    const items: string[] = this.symbolItemsById(groupId);
    const start: number = page * 19;
    if (row === 2) {
      return items.slice(start, start + 7);
    } else if (row === 3) {
      return items.slice(start + 7, start + 13);
    }
    return items.slice(start + 13, start + 19);
  }


  /**
   * M-037 弹性候选栏 v2 单行版：根据候选栏实测可用宽度动态计算页大小。
   * 单行模式 pageSize = 列数（一行能放几条候选）。
   * 布局宽度需扣除：▼ 展开按钮(40vp) + 反查行(不占候选宽度)。
   */
  /** H-050：按字符类型估算候选词渲染宽度（vp）。
   *  H-217 重标定：CJK 1em、ASCII 字母 0.45em、数字标点 0.55em（真机像素实测）。 */
  private estimateCandWidth(text: string, fontSize: number): number {
    // H-217（Qoder 2026-10-27，主人原话「候选词没有顶左边开始，好多空出一大截开始」）：
    // 真机标定（h217_typing.jpeg 像素量）证明旧系数系统性偏宽——ASCII 0.55em 实际≈0.33em、
    // 数字标点 0.8em 实际≈0.5em ⇒ ListItem 按估算定宽后右侧全是死区，
    // 「风格[fen]」与下一条之间空出 ~200px。系数下调到实测值。
    let w: number = 0;
    for (const ch of text) {
      const code: number = ch.charCodeAt(0);
      if (code > 0x4E00 && code < 0x9FFF) {
        w += fontSize;             // CJK ≈ 1em（实测「风格全额」0.92em，留余量）
      } else if ((ch >= 'a' && ch <= 'z') || (ch >= 'A' && ch <= 'Z')) {
        w += fontSize * 0.45;      // ASCII 字母 ≈ 0.45em（H-217 前为 0.55）
      } else {
        w += fontSize * 0.55;      // 数字标点 ≈ 0.55em（H-217 前为 0.8）
      }
    }
    return w;
  }

  private recomputePageSize(): void {
    if (this.candBarWidth <= 0) {
      return;
    }
    let expandBtnW: number = 36;
    let availW: number = this.candBarWidth - expandBtnW - 2 * CAND_PAD_H;
    if (availW <= 0) {
      return;
    }
    // H-077 ③：字号三档替换 availW > 360（竖屏 304vp 恒 false 的根因）
    let fontSize: number;
    let space: number;
    if (availW >= 620) {
      fontSize = 18;
      space = 4;
    } else if (availW >= 460) {
      fontSize = 20;
      space = 4;
    } else {
      fontSize = 18;
      space = 4;
    }
    this.compactMode = fontSize <= 18;
    this.candFs = fontSize;
    // H-077 ②：单条封顶 availW*0.30（长英文词不再吞行，格子上屏仍走 Ellipsis）
    let maxCandW: number = availW * 0.30;
    let columns: number = 1;
    if (this.allCandidates.length > 0) {
      let totalW: number = 0;
      columns = 0;
      for (const cand of this.allCandidates) {
        let cw: number = Math.min(this.estimateCandWidth(cand.text, fontSize), maxCandW) + space;
        if (totalW + cw > availW) {
          break;
        }
        totalW += cw;
        columns++;
      }
      if (columns < 1) {
        columns = 1;
      }
    } else {
      let colWidth: number = 2 * fontSize + space;
      columns = Math.floor(availW / colWidth);
    }
    // H-241 契约 §3-4「每页候选词数」（3/5/7/9）：用户定过就直接采用他那一档，不再让宽度自适应压它。
    // 「没定过」（store 里没这个键）时保持现状——按宽度估的 columns，横屏才仍拿得到 H-035 的 9 条。
    // 这条是真生效的：newSize 就是最后一次 `setPageSize(n)`，= 引擎一个菜单页给多少条
    // = L2 横向滑到第几条才由引擎续下一页（判据看 hilog `setPageSize(n)` + `H-164 scroll absLast`）。
    let newSize: number = this.pageSizePref > 0 ? this.pageSizePref : columns;
    newSize = Math.max(1, Math.min(newSize, this.gridPageN > 0 ? this.gridPageN : 50));
    if (newSize !== this.lastPageSize) {
      this.lastPageSize = newSize;
      this.uiPageSize = newSize;
      keyboardController.setPageSize(newSize);
      console.info(`${TAG} setPageSize(${newSize}) uiStart=${this.uiPageStart}`);
    }
  }

  // ---- H-060（M-047）UI 单一记账分页 ----

  /** H-060：屏上渲染切片——allCandidates 内 [uiPageStart, uiPageStart + uiPageSize)。
   *  引擎 notify 的 candidates 切片不再直接渲染（那是 H-060 错位的来源）；
   *  uiPageSize 尚未算出（0）时退全量，recompute 后首帧收敛。 */
  private pagedCandidates(): RimeCandidate[] {
    const all: RimeCandidate[] = this.allCandidates;
    if (all.length === 0) {
      return this.candidates;
    }
    let size: number = this.uiPageSize > 0 ? this.uiPageSize : all.length;
    let start: number = this.uiPageStart;
    if (start > all.length - 1) {
      start = this.lastScreenStart(all.length);
    }
    if (start < 0) {
      start = 0;
    }
    return all.slice(start, start + size);
  }

  /** H-164：L2 连续滚动数据源——本 Rime 菜单页内 [uiPageStart, 已加载末尾)。
   *  为什么不复用 pagedCandidates()：它恰好返回「一屏」（uiPageSize 由可视宽算出），
   *  内容宽度≈可视宽 ⇒ List 没有滚动溢出，等于把「整页硬切」换个壳（H-164 首版隐患）。
   *  Rime page_size=50（rawfile/rime/default.yaml），一页 50 条 ⇒ 一页内连续滑 7、8 屏不碰引擎。 */
  private scrollCandidates(): RimeCandidate[] {
    const all: RimeCandidate[] = this.allCandidates;
    if (all.length === 0) {
      return this.candidates;
    }
    const start: number = Math.max(0, Math.min(this.uiPageStart, all.length - 1));
    return all.slice(start);
  }

  /** H-164 判据⑤：单条候选宽度——与 recomputePageSize 同一套估宽，另加左右内边距。
   *  写死宽度（不吃 Ellipsis）保证长词「你好吗」在 List 里完整可见（H-042 语义）。
   *  H-190：comment 跟词同条目渲染后，宽度必须把注释一起算进去（注释按 0.8 字号估），
   *  否则注释会被 ListItem 截断/压到相邻候选上。 */
  private candItemWidth(cand: RimeCandidate): number {
    const fs: number = this.candFontSize();
    let w: number = this.estimateCandWidth(cand.text, fs);
    const cm: string = this.candCommentText(cand);
    if (cm.length > 0) {
      w += 4 + this.estimateCandWidth(cm, fs * 0.8);
    }
    // H-257(CodeArts): 余量从 +8 减到 +4（List space=4 已另计），减少右侧死区
    return Math.max(28, Math.ceil(w) + 4);
  }

  /** H-217r2(Qoder)：单条候选渲染封顶宽——availW*0.30（与 H-077 同口径），
   *  内容不足时按自然宽，超出才截断。availW 未量出（首帧）给 120vp 保守值。 */
  private candItemMaxWidth(): number {
    const availW: number = this.candBarWidth - 36 - 16;
    return availW > 0 ? Math.max(80, availW * 0.30) : 120;
  }

  /** H-164：把候选 List 滚回片首——统一入口。
   *  List 未挂载（首帧前/关于页/展开时被销毁）时不得调 scrollToIndex（控制器未绑定），
   *  故先看 candListReady；真异常也不许把整条 notify 链打断（键盘会卡在旧候选）。 */
  private candScrollToStart(): void {
    if (!this.candListReady) {
      return;
    }
    try {
      this.candListScroller.scrollToIndex(0, false);
    } catch (err) {
      console.info(`${TAG} H-164 scrollToIndex skipped: ${err}`);
    }
  }

  /** H-164：滑到本页尾 → 让引擎翻下一菜单页（一次滑动只续一次）。
   *  两个入口共用：onScrollIndex（手指还按着就到底了）与 onScrollStop（甩动惯性在抬手后才到底）。
   *  返回 true 表示真的发起了续页；false 含「未许可／没到底／已是最后一页」。 */
  private candTryContinue(lastVisible: number): boolean {
    const items: RimeCandidate[] = this.scrollCandidates();
    if (!this.candDragArmed || items.length === 0 || lastVisible < items.length - 1) {
      return false;
    }
    // 一次滑动只续一次：先撤销许可，再让引擎翻下一页（绝对下标接续由 pendingForwardAbs 记账）
    this.candDragArmed = false;
    const shownEndAbs: number = this.baseIndex + this.uiPageStart + items.length;
    const prevBase: number = this.baseIndex;
    const prevLen: number = this.allCandidates.length;
    this.pendingForwardAbs = shownEndAbs;
    keyboardController.flipPage(1);
    if (this.baseIndex === prevBase && this.allCandidates.length === prevLen) {
      // 引擎没翻动（已是最后一页）→ 撤销记账，原地不动
      this.pendingForwardAbs = -1;
      console.info(`${TAG} H-164 scroll-continue refused (last page)`);
      return false;
    }
    console.info(`${TAG} H-164 scroll-continue abs=${shownEndAbs}`);
    return true;
  }

  /** H-060：末屏起始偏移（allCandidates 长度内的最后一个整屏起点）。 */
  private lastScreenStart(len: number): number {
    if (len <= 0) {
      return 0;
    }
    const size: number = this.uiPageSize > 0 ? this.uiPageSize : len;
    return Math.max(0, (Math.ceil(len / size) - 1) * size);
  }

  /** H-060：候选翻页统一入口（候选栏手势 / 网格边界屏均走这里）。
   *  菜单页内翻 = uiPageStart 步进（起点恒为屏上末条 + 1，无重复无跳条）；
   *  菜单页边界才调引擎 flipPage 翻 Rime 菜单页，并对齐「新屏首条 = 已显示末条 + 1」。 */
  private flipCandidates(dir: number): void {
    const all: RimeCandidate[] = this.allCandidates;
    const size: number = this.uiPageSize > 0 ? this.uiPageSize : Math.max(all.length, 1);
    if (dir > 0) {
      if (this.uiPageStart + size < all.length) {
        // 菜单页内翻屏：绝对接续（上一屏末条的下一条开头）
        this.uiPageStart += size;
        this.gridScreenOffset = 0;
        // H-164：L2 数据源随 uiPageStart 换片，滚动位必须回片首，否则停在旧偏移
        this.candScrollToStart();
        return;
      }
      // 本菜单页已显示完 → 引擎翻下一 Rime 菜单页
      const shownEnd: number = this.baseIndex + this.uiPageStart + this.pagedCandidates().length;
      const prevBase: number = this.baseIndex;
      keyboardController.flipPage(1);
      // flipPage 同步 notify → allCandidates/baseIndex 已更新；据此对齐新屏起点
      if (this.baseIndex === prevBase && this.allCandidates.length === all.length) {
        // 引擎没翻动（已是最后一页）：保持原屏，禁止误跳回第 1 屏
        return;
      }
      if (this.baseIndex < shownEnd) {
        const offset: number = shownEnd - this.baseIndex;
        this.uiPageStart = offset < this.allCandidates.length ? offset : 0;
      } else {
        this.uiPageStart = 0;
      }
      this.gridScreenOffset = 0;
      return;
    }
    if (dir < 0) {
      if (this.uiPageStart > 0) {
        this.uiPageStart = Math.max(0, this.uiPageStart - size);
        this.gridScreenOffset = 0;
        // H-164：回看换片同样回片首（与正向一致）
        this.candScrollToStart();
        return;
      }
      // 本菜单页第 1 屏 → 引擎翻回上一 Rime 菜单页，从其末屏接续回看
      const prevBase: number = this.baseIndex;
      keyboardController.flipPage(-1);
      if (this.baseIndex !== prevBase) {
        // 引擎真的翻回了：显示翻回菜单页的末屏
        this.uiPageStart = this.lastScreenStart(this.allCandidates.length);
        this.gridScreenOffset = 0;
      }
      // 引擎没翻动（已在第 1 菜单页第 1 屏）：原地不动
    }
  }


  // ---- H-059（M-047）展开网格内翻屏 ----

  /** H-065（M-050）：展开网格列数——按面板可用宽度自适应。
   *  H-202（主人 2026-10-26「这种排列后面的注释显示不全，可以换成单列或双列」）：
   *  原来 4 列（每格约 90vp），「词 16fp + 注释 13fp」一格里塞不下，注释被 Ellipsis 截掉。
   *  改成 **双列**（窄屏单列）：360vp 屏每格约 172vp，词+注释整行放得下，与安卓
   *  CandidateItemUi「词＋右侧灰小字」一致。列数不再按 90vp 硬推，主人口径优先。
   *  宽度取 candBarWidth（候选栏与展开面板同为整宽兄弟节点，onSizeChange 已量）。 */
  private gridCols(): number {
    // H-257(CodeArts): 单列居中——主人原话「改成单列居中吧」
    return 1;
  }

  /** H-202：展开网格行数。原 2 行 × 4 列＝8 格；H-202 改 2 列后若仍 2 行，
   *  一屏只剩 4 条（50 条候选要翻 13 屏）。取 3 行：2×3＝6 条一屏，格高仍够
   *  （展开面板整块键区 ~200vp ÷ 3 ≈ 66vp，词 16fp + 注释 13fp 放得下）。 */
  private gridRows(): number {
    // H-257(CodeArts): 单列模式下一屏约 5 条（展开面板 ~200vp / 每条 ~40vp）
    return 5;
  }

  /** H-065（M-050）：网格一屏格数 = 列数 × 行数（原 GRID_PAGE_SIZE=6 常量的动态版）。
   *  H-059 翻屏语义不变：仍按整屏步进（gridFlip 的 maxOff 口径见 gridScreenCount）。 */
  private gridPageSize(): number {
    return this.gridCols() * this.gridRows();
  }

  /** H-065 ④ re2（M-050-review）：Grid 列模板——cols 列全 1fr（等宽无 margin，列数=渲染数）。 */
  private gridColsTemplate(): string {
    const cols: number = this.gridCols();
    let tpl: string[] = [];
    for (let i: number = 0; i < cols; i++) {
      tpl.push('1fr');
    }
    return tpl.join(' ');
  }

  /** H-202：Grid 行模板——rows 行全 1fr（与 gridPageSize 同源，改行数只改 gridRows()）。 */
  private gridRowsTemplate(): string {
    const rows: number = this.gridRows();
    let tpl: string[] = [];
    for (let i: number = 0; i < rows; i++) {
      tpl.push('1fr');
    }
    return tpl.join(' ');
  }

  /** H-059：网格当前屏切片（本页渲染切片内 [gridScreenOffset, gridScreenOffset + gridPageSize())）。 */
  private gridCandidates(): RimeCandidate[] {
    const paged: RimeCandidate[] = this.pagedCandidates();
    return paged.slice(this.gridScreenOffset, this.gridScreenOffset + this.gridPageSize());
  }

  /** H-059/H-174：网格总屏数（本页候选切片按 gridPageSize() 格一屏）——**按 gridFlip 的 maxOff 口径推**，不要用 ceil(len/step)。
   *  旧式 ceil(50/8)=7 屏，但 gridFlip 的 maxOff = len-step = 42 ⇒ 末屏 offset=42 时切片
   *  42..49 **正好 8 格满屏**，第 7 屏根本不存在：界面显示 `6/7` 而 7 永远不可达（H-174）。
   *  屏号从 1 起算，故「可达屏数」= floor(maxOff/step) + 1（maxOff=0 时至少 1 屏）。 */
  private gridScreenCount(): number {
    const len: number = this.pagedCandidates().length;
    const step: number = this.gridPageSize();
    const maxOff: number = Math.max(0, len - step);
    return Math.max(1, Math.floor(maxOff / step) + 1);
  }

  /** H-059：当前网格屏号（0 起）。 */
  private gridScreen(): number {
    return Math.floor(this.gridScreenOffset / this.gridPageSize());
  }

  aboutToAppear(): void {

    // H-057：先装符号分类数据（rawfile 缺失/损坏时内部回落写死表）
    this.loadSymbolGroups();
    this.rebuildSymbolPages();
    keyboardController.setUiListener((s: KeyboardState) => {
      const preeditChanged: boolean = s.preedit !== this.lastPreedit;
      const baseChanged: boolean = s.baseIndex !== this.lastBaseIndex;
      // H-164 连续滚动下「屏上渲染条数」不再恒等于 setPageSize（L2 渲染到本页尾），
      // 故判据改为「0 ≤ 已渲染 ≤ 已加载(50)，且可见首条绝对下标可从 onScrollIndex 日志判定」。
      console.info(`${TAG} state: cand=${s.candidates.length} all=${s.allCandidates.length}` +
        ` base=${s.baseIndex} page=${s.page} next=${s.hasNext}` +
        ` uiSize=${this.uiPageSize} uiStart=${this.uiPageStart}` +
        ` rendered=${Math.max(0, s.allCandidates.length - this.uiPageStart)}`);
      this.preedit = s.preedit;
      this.lastPreedit = s.preedit;
      this.candidates = s.candidates;
      this.allCandidates = s.allCandidates;  // H-055：接收全量候选
      this.baseIndex = s.baseIndex;          // H-060：渲染/点词记账基址
      this.rowHeight = s.rowHeight;
      this.barHeight = s.barHeight;
      this.selMode = s.selectionMode;   // H-220(Qoder)：⇆ 面板「选择」格/n 键角标跟着控制器走
      // 候选列表真正变空（引擎切片与全量都空）时才收起展开面板——
      // H-059/H-060：末菜单页再往后翻，引擎返回空切片但 allCandidates 仍是本页全量，
      // 此时网格不该被误收起（uiPageStart 原地不动）。
      if (s.candidates.length === 0 && s.allCandidates.length === 0) {
        this.expanded = false;
      }
      // H-060：新编码/新菜单 → 回第 1 屏；翻回上一菜单页 → 从其末屏接续回看
      if (preeditChanged) {
        this.uiPageStart = 0;
        this.gridScreenOffset = 0;
        // H-164 00:3x：新编码/选词上屏后，上一轮的续页许可与「可见末条」记住位一律作废，
        // 防数据刷新触发的 onScrollIndex/onScrollStop 误续页（H-034 复生路径）
        this.candDragArmed = false;
        this.candDragMoved = false;
        this.candLastVisible = 0;
        this.pendingForwardAbs = -1;
        // H-164 判据②：编码串一变（含选词上屏、退格到空）→ List 滚回首条，防滚动位残留
        this.candScrollToStart();
      } else if (baseChanged) {
        this.gridScreenOffset = 0;
        // H-164 00:3x：引擎换页（无论谁触发）都作废上一轮的续页许可，防「点空处拖一下」留下的
        // 陈旧许可在换页刷新时误续第二页
        this.candDragArmed = false;
        this.candDragMoved = false;
        this.candLastVisible = 0;
        // H-164 判据③：滑到本页尾、引擎翻页后，新一屏首条 = 已显示末条的下一条（绝对下标接续）。
        // 只有「用户真滑到底」才会置 pendingForwardAbs；普通翻页/回退仍走 H-060 原逻辑。
        const pending: number = this.pendingForwardAbs;
        if (pending >= s.baseIndex && pending < s.baseIndex + s.allCandidates.length) {
          this.uiPageStart = pending - s.baseIndex;
          console.info(`${TAG} H-164 continue-abs base=${s.baseIndex} start=${this.uiPageStart} pending=${pending}`);
        } else {
          this.uiPageStart = s.baseIndex < this.lastBaseIndex
            ? this.lastScreenStart(s.allCandidates.length) : 0;
        }
        this.pendingForwardAbs = -1;
        // H-164 判据②：跨引擎页（含回看）→ List 滚到当前切片首条
        this.candScrollToStart();
      }
      this.lastBaseIndex = s.baseIndex;
      // H-187：安卓口径（fcitx5-android `KawaiiBarStateMachine`）——工具栏属 Idle 态；
      // 用户手动展开后，commit 回 Idle（无 preedit、无候选）时工具栏自动回来。
      // 打字过程中不回来（preedit/候选任一非空就不显示），所以不会盖住候选。
      if (this.funcBarPinned && !this.showFuncBar && !this.expanded &&
        s.preedit.length === 0 && s.candidates.length === 0 && s.allCandidates.length === 0) {
        this.setFuncBar(true);
      }
      // H-055：只在编码串变化时重算页大小（翻页不重算，避免棘轮）
      if (preeditChanged) {
        this.recomputePageSize();
      }
      // H-203：候选/编码一变，栏高可能在 28↔44 之间切换 ⇒ 面板窗口同步（只在真变时 resize）。
      // 必须放在 setFuncBar(true) 兜底之后：工具栏展开时不是空闲态，窗口不能缩回 28。
      this.syncPanelBarHeight();
    });
    // H-241（契约 §1-③）：读设置——preferences 在**输入法进程自己的沙箱**里（契约 §1-②），
    // 所以这里用面板的 host context 取；load 之前所有读取点拿到的是契约默认值（不会出现 undefined
    // 把键面搞没），load 完 rev 自增 → syncFromSettings() 当场把键面刷成用户设定的样子。
    // 「默认展开工具栏」也在这条链上：load 后 sync 发现镜像从 关→开 就立刻展开（见 syncFromSettings），
    // 不在这里重复读一次——两处读同一开关就是第二个真相源（H-090 的病因）。
    this.syncFromSettings('appear');
    const hostCtx: common.Context | undefined = this.getUIContext().getHostContext() as common.Context;
    if (hostCtx !== undefined && hostCtx !== null) {
      SettingsStore.inst().load(hostCtx).then(() => {
        this.syncFromSettings('loaded');
      });
    } else {
      console.warn(`${TAG} H-241 hostContext 取不到，设置沿用契约默认值`);
    }
    // H-203：首帧就按空闲态真实栏高建窗口（28vp），别等第一次按键才缩。
    this.syncPanelBarHeight();
  }

  aboutToDisappear(): void {
    keyboardController.setUiListener(undefined);
    // M-049（H-062）：退格连删定时器清理，防泄漏
    this.stopBackspaceRepeat();
    // H-221（Qoder）：方向连发定时器同样在面板销毁时清理（收起键盘时手指还按着也算撒手）
    this.stopDirRepeat();
    // H-208（Qoder 2026-10-26 21:3x，真机复现「打字时工具栏自动展开盖住候选」）：
    // `funcBarPinned` 是**会话内**临时状态（用户这次手动展开过，commit 回 Idle 时自动回来）。
    // 但面板销毁（收起键盘/切走）时它仍留着真 ⇒ 下次一开键盘工具栏就自动展开，
    // 把候选行整行挤掉（真机 a1_typing.jpeg：打字态只看得见 ‹ ↶ ↷ ⇄ 📋 ⋯ ▼，候选一条没有）。
    // 安卓口径：工具栏不跨会话保留 ⇒ 面板销毁即复位。
    this.funcBarPinned = false;
    // H-241：面板销毁时长按计时器必须掐掉（手指还按着空格就收起键盘＝不该下次一进来就弹设置页），
    // 设置覆盖层跟着关（覆盖层是面板内的，面板没了它也没有存在的载体）。
    this.settingsHoldAbort();
    this.settingsOpen = false;
  }

  // ---- M-049（H-062）按键触摸体系：按下高亮 / 退格连删 / 触感 ----

  /** M-049：键背景色——按下（pressedKey 命中）用 BG_PRESSED，否则用基色。 */
  private keyBg(base: string, keyId: string): string {
    return this.pressedKey === keyId ? BG_PRESSED : base;
  }

  /** M-049：按下——置按下态 + 20ms 轻振（onTouch 只做视觉+振动，功能仍走 onClick）。 */
  private pressKey(keyId: string): void {
    this.pressedKey = keyId;
    this.vibrateLight();
  }

  /** M-049：抬手/取消——只有同一键才清按下态（滑到别的键不误清）。 */
  private releaseKey(keyId: string): void {
    if (this.pressedKey === keyId) {
      this.pressedKey = '';
    }
  }

  /** M-049：20ms 轻振（usage 'touch'）。无 ohos.permission.VIBRATE / 设备不支持 / 任何失败
   *  都静默降级（try/catch + Promise .catch 双保险），功能无副作用；50ms 节流防高频触发。 */
  private vibrateLight(): void {
    // H-241 契约 §3-5「按键时振动」：关掉后**一次 vibrate 调用都不发**（生效判据＝hilog 里
    // 只有这条 skip 日志、没有 startVibration），主人手上不抖。
    if (!this.hapticOn) {
      console.info(`${TAG} H-241 haptic off -> skip vibrate`);
      return;
    }
    const now: number = Date.now();
    if (now - this.lastVibrateTime < 50) {
      return;
    }
    this.lastVibrateTime = now;
    try {
      const effect: vibrator.VibrateTime = { type: 'time', duration: 20 };
      const attr: vibrator.VibrateAttribute = { id: 0, usage: 'touch' };
      vibrator.startVibration(effect, attr).catch(() => {
        // 无权限（201）/不支持：静默吞掉，等 Qoder 决定是否加权限
      });
    } catch (e) {
      // 振动不可用（无权限/不支持）：静默降级，不留调试日志
    }
  }

  /** M-049：退格连删启动——按住 500ms 后每 100ms 删一次（先清旧定时器防叠加）。 */
  /** M-049 → H-167(Qoder)：长按退格＝**清空输入框全部内容**（主人 19:2x 定），不再逐字连删。
   *  500ms 触发一次，按住不放不重复（防误删）；抬起后由 onTouch 的 bsRepeatStarted 标记跳过短按删除。
   */
  private startBackspaceRepeat(): void {
    this.stopBackspaceRepeat();
    this.bsDelay = setTimeout(() => {
      this.bsRepeatStarted = true;
      this.bsClearAllFired = true;      // H-206：记下「这次清空发生在本次按下里」，供手势前还原
      keyboardController.clearAllContent();
      console.info(`${TAG} bs_row longpress: clearAllContent`);
    }, 500);
  }

  /** M-049：退格连删停止——清两个定时器并复位标记（抬手/滑出/aboutToDisappear 都调，无泄漏）。 */
  private stopBackspaceRepeat(): void {
    if (this.bsDelay >= 0) {
      clearTimeout(this.bsDelay);
      this.bsDelay = -1;
    }
    if (this.bsTimer >= 0) {
      clearInterval(this.bsTimer);
      this.bsTimer = -1;
    }
    this.bsRepeatStarted = false;
  }

  /**
   * H-221（Qoder 2026-10-27 15:3x，主人「hjkl 上下左右，长按不撒手，他应该继续他的动作，
   * 连续执行，直到撒手」）：字母键 h/j/k/l 长按触发**之后**的连发。
   * 手感对齐 ⇆ 面板四向格（ToolPanels 用同一个 120ms），差别在**起步**：
   * 字母键的长按本身要 450ms 才认（否则正常打字会误移光标），所以是
   * 「按住 450ms 动第 1 次 ⇒ 之后每 120ms 一次 ⇒ 抬手/取消/面板销毁立刻停」。
   * 选择模式（长按 n 开的）开着时，moveEditorCursor 内部走的是扩选，
   * 于是按住＝连续扩大选区，与安卓长按方向键的行为一致。
   */
  private startDirRepeat(dir: number, ch: string): void {
    this.stopDirRepeat();
    this.dirRepeatCh = ch;
    this.dirRepeatTimer = setInterval(() => {
      keyboardController.moveEditorCursor(dir);
      console.info(`${TAG} H-221 hold ${ch} dir=${dir} repeat ${LETTER_DIR_REPEAT_MS}ms`);
    }, LETTER_DIR_REPEAT_MS);
  }

  /** H-221：停连发。抬手（Up）、被重定向（Cancel）、面板销毁都要调，防定时器泄漏。 */
  private stopDirRepeat(): void {
    if (this.dirRepeatTimer !== -1) {
      clearInterval(this.dirRepeatTimer);
      this.dirRepeatTimer = -1;
    }
    this.dirRepeatCh = '';
  }

  /**
   * H-206(Qoder 2026-10-26)：滑动/抬手动作前，把**本次按下**误触发的清空先还原。
   * 只在 bsClearAllFired 置位时动一次 undoLastAction()——撤销栈里那条 'clear' 记录
   * 就是刚才那次 clearAllContent，还原它不会吃掉用户真正想撤的动作。
   */
  private healAccidentalClearAll(): void {
    if (!this.bsClearAllFired) {
      return;
    }
    this.bsClearAllFired = false;
    keyboardController.undoLastAction();
    console.info(`${TAG} H-206 bs_row 手势前先还原本次误触发的清空（避免「多恢复一遍」）`);
  }

  /** 单键高度（vp）：整行高扣掉上下 margin。 */
  private keyH(): number {
    return this.rowHeight - 6;
  }

  /** Shift 是否激活（单击或锁定）。 */
  private shiftActive(): boolean {
    return this.shiftOn || this.shiftLocked;
  }

  /** 处理 Shift 键点击：锁定→取消；单击→变锁定；未激活→单击。 */
  private handleShift(): void {
    if (this.shiftLocked) {
      this.shiftLocked = false;
      this.shiftOn = false;
    } else if (this.shiftOn) {
      this.shiftOn = false;
      this.shiftLocked = true;
    } else {
      this.shiftOn = true;
    }
  }

  /** 发送字母键：如果 Shift 激活则转大写，shiftOn 在发一次后复位。 */
  private sendLetter(ch: string): void {
    if (this.shiftActive()) {
      this.typeChar(ch.toUpperCase());
      if (this.shiftOn) {
        this.shiftOn = false;
      }
    } else {
      this.typeChar(ch);
    }
  }

  /** H-077 ④：展开/收起统一入口。
   *  H-168：展开向引擎要**整菜单页**（GRID_FULL_PAGE=50），让展开网格里有「多屏」可上下滑翻；
   *    旧实现 setPageSize(gridCols()*2≈8) 导致 pagedCandidates 窗口恒 8 条、网格永远一屏且词少于候选栏。
   *  收起 recomputePageSize() 恢复行页大小；H-060 记账语义一行不动。 */
  private setExpanded(expanded: boolean): void {
    // H-189：展开候选网格也给一个 180ms 淡入+轻位移（主人 2026-10-26「没有展开过渡，太硬」）。
    // 与 H-168 翻屏同一套 gridOpacity/gridOffsetY 通道（ExpandedPanel 的 Grid 已绑这两个值），
    // 不新增容器、不动网格几何；收起仍即时（面板整个被换掉，做退场要改 build() 的互斥结构，先不冒险）。
    const opening: boolean = expanded && !this.expanded;
    if (opening) {
      this.gridOpacity = 0;
      this.gridOffsetY = 12;
    }
    this.expanded = expanded;
    if (expanded) {
      // H-241 契约 §3-9「展开网格每页条数」（20–80，默认 50＝原 GRID_FULL_PAGE）：
      // 向引擎要的整菜单页条数改读设置值 ⇒ 屏上网格总条数与「滑到第几条才换引擎页」当场跟着变。
      const gridN: number = this.gridPageN > 0 ? this.gridPageN : GRID_FULL_PAGE;
      this.lastPageSize = gridN;
      this.uiPageSize = gridN;
      this.uiPageStart = 0;
      this.gridScreenOffset = 0;
      keyboardController.setPageSize(gridN);
      if (opening) {
        animateTo({ duration: 180, curve: Curve.EaseOut }, () => {
          this.gridOpacity = 1;
          this.gridOffsetY = 0;
        });
      } else {
        this.gridOpacity = 1;
        this.gridOffsetY = 0;
      }
    } else {
      this.recomputePageSize();
    }
    // H-203：展开态一定不是空闲态（44vp），收起后若也没编码/候选就回到 28vp。
    this.syncPanelBarHeight();
  }

  /** H-168：展开网格整屏翻页——上下滑一滑翻一屏（gridScreenOffset 步进 gridPageSize），
   *  用 animateTo 做淡入+轻微位移动画（新屏从对侧滑入并淡入，不硬翻）。dir>0 下一屏、dir<0 上一屏；
   *  到本页首/末屏不翻（保持位置），返回是否真的翻了。
   *
   *  H-168 末屏边界（CodeArts M-192 复核揪出，我复算确认，见 scripts/h168_grid_flip_sim.py）：
   *  **不能要求「整屏对齐」**。旧条件 `off+step<=maxOff` 在 len 不被 step 整除时会把最后几条
   *  永远藏起来（例：len=17/step=10 ⇒ 7 条不可达；len=13/step=8 ⇒ 卡在第一屏），
   *  且「下一页」按钮仍显示可点 ⇒ 点了没反应＝死按钮。
   *  改为 `off < maxOff` + `min(off+step, maxOff)`：允许末屏步进不均匀（末屏可能不足 step 条），
   *  最后一屏完整可见，反向同理 `max(off-step, 0)`。 */
  private gridFlip(dir: number): boolean {
    const step: number = this.gridPageSize();
    const len: number = this.pagedCandidates().length;
    const maxOff: number = Math.max(0, len - step);
    let next: number;
    if (dir > 0 && this.gridScreenOffset < maxOff) {
      next = Math.min(this.gridScreenOffset + step, maxOff);
    } else if (dir < 0 && this.gridScreenOffset > 0) {
      next = Math.max(this.gridScreenOffset - step, 0);
    } else {
      return false;
    }
    const slide: number = dir > 0 ? 12 : -12; // 新屏从对侧（来向的相对边）滑入
    const prev: number = this.gridScreenOffset;
    // 先把内容瞬切到新屏并置于「不可见+偏移」态，再动画淡入归位——杜绝硬翻
    this.gridOpacity = 0;
    this.gridOffsetY = slide;
    this.gridScreenOffset = next;
    // H-168 真机验收：键盘面板在 dumpLayout 里没有文字节点，「翻到第几屏/末屏可达」只能按这行日志判（同 H-164 口径）
    console.info(`${TAG} H-168 gridFlip dir=${dir} step=${step} len=${len} maxOff=${maxOff} ` +
      `off=${prev}->${next} screen=${this.gridScreen() + 1}/${this.gridScreenCount()}`);
    animateTo({ duration: 200, curve: Curve.EaseOut }, () => {
      this.gridOpacity = 1;
      this.gridOffsetY = 0;
    });
    return true;
  }

  /** H-078：查字母键的次级字符（上滑上屏），无次级字符返回空串。 */
  private getAltChar(ch: string): string {
    for (let i: number = 0; i < ALT_LETTERS.length; i++) {
      if (ALT_LETTERS[i] === ch) {
        return ALT_CHARS[i];
      }
    }
    return '';
  }

  /** H-154：取触摸点的**屏幕绝对 Y**（displayY）。
   *  H-165(Qoder)（2026-10-24 17:5x）：原来取的是组件相对 y，手指上滑离开键面后 Up 事件被
   *  ArkUI 重定向到别的组件，Down 与 Up 的两个 y 不在同一坐标系 ⇒ dy 算成负数/小值
   *  ⇒ 退化成点击打字母（真机：q 上滑出的是 q 的五笔候选，不是 1）。
   *  displayY 是全屏绝对坐标，与组件归属无关；面板顶部也不会被钳位（钳位的是 windowY）。
   */
  private evY(event: TouchEvent): number {
    if (event.changedTouches !== undefined && event.changedTouches.length > 0) {
      return event.changedTouches[0].displayY;
    }
    if (event.touches.length > 0) {
      return event.touches[0].displayY;
    }
    return -1;
  }

  /** H-180：同 evY，取横向屏幕坐标（空格键左右滑移光标用）。 */
  private evX(event: TouchEvent): number {
    if (event.changedTouches !== undefined && event.changedTouches.length > 0) {
      return event.changedTouches[0].displayX;
    }
    if (event.touches.length > 0) {
      return event.touches[0].displayX;
    }
    return -1;
  }

  /** H-189/H-199：展开/收起工具栏的**唯一视觉入口**。
   *  主人 2026-10-26 原话「没有展开过渡，太硬」——原来 showFuncBar 一翻，整条候选栏瞬间换内容。
   *  现在：内容先淡出 80ms → 在透明度 0 时换内容（看不见跳变）→ 再淡入 140ms。
   *  **只淡内容**（工具栏行 / L1 / L2 各自 .opacity），不动栏底色与高度：
   *  candBarHeight()=44vp 的预算一秒没变，h165_bar_height_check.py 仍按原行高校验。
   *  animated=false 给「打字即收起」（H-180）用——输入要求立即响应，不做 220ms 延迟。
   *
   *  H-199（CodeArts M-223 C① 复核后采纳并自己复现了逻辑）：此前 showFuncBar 只在
   *  **第二个 animateTo 的闭包里**才赋值 ⇒ 展开后的 80ms 内它还是旧值 false。这段时间里
   *  「打字即收起」走 `setFuncBar(false, false)` 会因 `showFuncBar === open`（false===false）
   *  直接 return，而 80ms 前的展开回调随后仍把 showFuncBar 置 true ⇒ **刚打完字工具栏自己
   *  弹出来**，正好是主人骂的「打字盖候选」。修法：
   *    ① 新增 `funcBarTarget`（目标态，动画一开始就写）当去重判据，不再读到旧值；
   *    ② 新增 `funcBarGen` 代次：任何一次非动画调用都作废在途回调，闭包里先比代次，过期即弃；
   *    ③ 反向点击不进两套动画——新调用直接换代，旧回调自然失效。
   *  为什么不是「动画一开始就把 showFuncBar 翻过来」：那样淡出的 80ms 里会**立刻**显示新内容，
   *  主人说的「太硬」就回来了。内容交换仍必须压在 alpha=0 那一刻。 */
  private setFuncBar(open: boolean, animated: boolean = true): void {
    if (!animated) {
      this.funcBarGen++;             // 作废所有在途动画回调（打字不能被 80ms 前的展开回调覆盖）
      this.funcBarTarget = open;
      this.showFuncBar = open;
      this.barAlpha = 1;
      // H-203：工具栏开/关会改变空闲判据 ⇒ 窗口高度同步（空闲 28 / 展开 44）
      this.syncPanelBarHeight();
      return;
    }
    if (this.funcBarTarget === open) {
      return;                        // 同向重复（连点）：一套动画够了，别再叠
    }
    const gen: number = ++this.funcBarGen;
    this.funcBarTarget = open;
    animateTo({ duration: 80, curve: Curve.EaseIn, onFinish: () => {
      if (gen !== this.funcBarGen) {
        return;                      // 已被打字/收起作废
      }
      animateTo({ duration: 140, curve: Curve.EaseOut }, () => {
        this.showFuncBar = open;
        this.barAlpha = 1;
        // H-203：内容换完（alpha=0 那一刻）再改窗口高度，栏不会在半透明时抖；
        // 空闲→展开时窗口长 16vp，键区随之上移一行。
        this.syncPanelBarHeight();
      });
    } }, () => {
      if (gen === this.funcBarGen) {
        this.barAlpha = 0;
      }
    });
  }

  /** H-180：打字即收起顶部工具栏。
   *  主人 2026-10-26 原话「顶栏功能区，打字的时候会覆盖候选，逻辑有问题」——
   *  工具栏展开时整栏让给图标行（H-176 的整栏互换算高预算），此时一打字候选就看不见了。
   *  安卓的工具栏是**临时面板**：选完动作/一输入就回到候选。所以所有字符入口统一走这里。 */
  private typeChar(ch: string): void {
    this.funcSubPanel = '';            // H-194：打字收起时一并退出子面板，下次展开回到图标行
    this.funcMenuOpen = false;         // H-184：打字时菜单也一并关掉（菜单是临时面板）
    this.setFuncBar(false, false);
    keyboardController.onKey(ch);
  }

  /** H-180：退格也算「在打字」——工具栏展开时退格，候选也要能看见，所以同样先收起。 */
  private backChar(): void {
    this.funcMenuOpen = false;         // H-184：同 typeChar，菜单是临时面板
    this.setFuncBar(false, false);
    keyboardController.onBackspace();
  }

  /** H-180/H-186：把累计位移按 10vp 一步换算成光标移动；不足一步的余量留到下一段（Android 同口径）。
   *  H-241 契约 §3-10「空格划动移光标步长」（5–20 字符/vp，默认 10＝原 SPACE_CURSOR_STEP）：
   *  步长改读设置值 ⇒ 划同样的距离，hilog 报的 `moveCursor` 次数按 10/step 成反比变。
   *  值非法（0/NaN）时退回常量，绝不允许 while 死循环。 */
  private spaceSwipeConsume(): void {
    const step: number = this.spaceStepN > 0 ? this.spaceStepN : SPACE_CURSOR_STEP;
    while (Math.abs(this.spaceAccum) >= step) {
      const dir: number = this.spaceAccum > 0 ? 4 : 3;   // 3=左 4=右（InputClient.moveCursorSync 口径）
      keyboardController.moveEditorCursor(dir);
      this.spaceAccum -= (this.spaceAccum > 0 ? step : -step);
      this.spaceSwipeDone = true;
      console.info(`${TAG} H-180 space swipe cursor dir=${dir} step=${step}`);
    }
  }

  /** H-180：空格键左右滑移光标（主人 2026-10-26「滑动空格移动光标没有，加上这个功能」）。
   *  与安卓（fcitx5-android `BaseKeyboard.kt` 的 SpaceKey 分支）同语义：每 10vp 移一格；
   *  滑过的这一下**不上屏空格**（spaceSwipeDone 拦住 onClick）；抬手停在最后位置。
   *  Down 时无条件清标记，保证「滑完的下一次点按」不会被吞。
   *  H-186（2026-10-26 11:0x）：抬手时把**最后一段位移**补进来。此前只在 Move 里累计，
   *  真手指快速甩动时 Move 可能很稀疏/没有，最后一截只在 Up 坐标里 ⇒ 「滑了光标不动」；
   *  注入工具（`uitest uiInput swipe`）更是常常只给 Down/Up。补上后无论 Move 有几个，
   *  终点位移都按满额结算。 */
  private spaceSwipeHandle(event: TouchEvent): void {
    if (event.type === TouchType.Down) {
      this.pressKey('space');
      this.spaceDownX = this.evX(event);
      this.spaceLastX = this.spaceDownX;
      this.spaceAccum = 0;
      this.spaceSwipeDone = false;
      // H-241：主人点单的入口之一——长按空格（静止 600ms）调出设置页。
      // 静止判据在下面 Move 里：滑出去就撤计时（滑空格是移光标，不是开设置）。
      this.settingsHoldStart('space', this.spaceDownX, this.evY(event));
      return;
    }
    if (event.type === TouchType.Move) {
      const x: number = this.evX(event);
      this.settingsHoldMove(x, this.evY(event));
      if (x < 0 || this.spaceLastX < 0) {
        return;
      }
      this.spaceAccum += (x - this.spaceLastX);
      this.spaceLastX = x;
      this.spaceSwipeConsume();
      return;
    }
    if (event.type === TouchType.Up || event.type === TouchType.Cancel) {
      if (event.type === TouchType.Up) {
        const x: number = this.evX(event);
        if (x >= 0 && this.spaceLastX >= 0) {
          this.spaceAccum += (x - this.spaceLastX);
          this.spaceLastX = x;
          this.spaceSwipeConsume();
        }
      }
      this.settingsHoldEnd();
      this.releaseKey('space');
      this.spaceDownX = -1;
      this.spaceLastX = -1;
      this.spaceAccum = 0;
      return;
    }
  }

  /** H-180：空格短按上屏；刚滑过的那一下不算点击。
   *  H-241：刚长按开过设置的那一下也不算点击——「长按空格＝开设置」不得再补发一个空格。 */
  private spaceClick(): void {
    if (this.settingsHoldConsume('space')) {
      return;
    }
    if (this.spaceSwipeDone) {
      this.spaceSwipeDone = false;
      return;
    }
    this.typeChar(' ');
  }

  /** H-241：回车点击＝上屏；但**长按过回车开设置**的那一下不再上屏（与空格同口径）。
   *  只吞同键那一次，别的键的正常输入不受影响。 */
  private enterClick(): void {
    if (this.settingsHoldConsume('enter')) {
      return;
    }
    this.typeChar('Enter');
  }

  /** H-155/H-219(Qoder 2026-10-27 主人「adfghjklmn 键名上用小字标出功能，和 axcv 一样」)：
   *  长按动作键的功能名（键面小字标注）；其余返回空串。
   *  H-219 口径（=H-220r3 落地现状）：s=行首 d=行尾 h=← j=↑ k=↓ l=→ m=删除(光标后) n=选择；
   *  f/g 无动作（M-247③）不标。
   *  （H-216 复核时更正的旧行：原文还写着「s=全文首 d=全文尾 h/j/k/l=←↓↑→」，
   *   那是 H-210/H-220r2 之前的状态，j/k 已在 r3 对调、s/d 已改为按行。） */
  private funcLabel(ch: string): string {
    if (ch === 'a') {
      return '全选';
    }
    if (ch === 'x') {
      return '剪切';
    }
    if (ch === 'c') {
      return '复制';
    }
    if (ch === 'v') {
      return '粘贴';
    }
    if (ch === 's') {
      return '行首';
    }
    if (ch === 'd') {
      return '行尾';
    }
    if (ch === 'n') {
      return '选择';
    }
    if (ch === 'h') {
      return '左移';
    }
    if (ch === 'j') {
      // H-220r3(Qoder，主人「下移上移，互换位置」)：j/k 对调 ⇒ j=上移、k=下移。
      return '上移';
    }
    if (ch === 'k') {
      return '下移';
    }
    if (ch === 'l') {
      return '右移';
    }
    if (ch === 'm') {
      // H-220r3(Qoder，主人「不是左边那，和退格重复了」)：m=删除光标**右边**的字（Del）。
      return '删除';
    }
    if (ch === 'f') {
      // H-226(Qoder 2026-10-27 16:5x，主人「sd只针对行，那么fg就有用了，应该是页首页尾…没异议就加上吧」)：
      // **鸿蒙做不到「页」**——IME Kit 只给文本与光标下标，拿不到宿主可视区域，算不出一屏多长。
      // 所以落到唯一诚实的一档：f = 全文首（⇆ 面板「全首」格同一个动作 moveCursorToStart）。
      return '文首';
    }
    if (ch === 'g') {
      // H-226：g = 全文尾（同 ⇆ 面板「全尾」格，moveCursorToEnd）。
      return '文末';
    }
    return '';
  }

  /** H-219(Qoder)：长按走「编辑动作」而非气泡的键。此前这条线搭在 funcLabel!=='' 上
   *  （H-155 时四枚动作键恰好都有标注）；现在标注面扩到 s/d/h/j/k/l/m/n，
   *  必须拆开——f/g 有标注与否都不该挡气泡。 */
  private isEditorActionKey(ch: string): boolean {
    return ch === 'a' || ch === 'x' || ch === 'c' || ch === 'v' ||
      ch === 's' || ch === 'd' || ch === 'h' || ch === 'j' ||
      ch === 'k' || ch === 'l' || ch === 'm' || ch === 'n' ||
      ch === 'f' || ch === 'g';   // H-226(Qoder)：f/g 长按改走文首/文末，不再弹泡
  }

  /** H-155：查字母键的长按隐藏符号（气泡内容）；a/s/v/c 返回空（走编辑框动作）；其余返回通用集。 */
  private getHiddenSymbols(ch: string): string[] {
    for (let i: number = 0; i < ALT_LETTERS.length; i++) {
      if (ALT_LETTERS[i] === ch) {
        return HIDDEN_SYMS[i];
      }
    }
    return [];
  }

  /**
   * H-215(Qoder 2026-10-27)：长按气泡几何（vp，**面板窗口局部系**——顶层 Stack 的
   * .position 基准；键的 globalPosition 实测同为窗口系，见 screenOffXvp 标定注释）。
   * 三轮真机实验证明：气泡**嵌在键 Stack 里**时定位不可控——
   *  ① 百分比 position/translate 在内容自适应 Stack 里基准成环 ⇒ 飞屏幕左下角；
   *  ② offset().x / translate().x 在 IME 子窗口里被吞（q 键 shift 29.5/36.7/-127.9
   *    三轮，渲染恒贴屏幕左缘）；
   *  ③ 像素 .position() 在键 Stack 内只生效一部分（v5/v6 渲染右缘恒 256px，
   *    与目标 43.6vp 不符，y 也只按 ~40% 响应）。
   * ⇒ 气泡改画在 **build() 顶层 Stack**（H-213 修 ··· 菜单裁切的同款做法）：
   * 键的 globalPosition（onAreaChange 实测，窗口系）定锚，横向夹取到内容区
   * （屏宽 365.714vp）保证整泡可见。
   */
  private bubbleGeom(ch: string): BubbleGeom {
    const len: number = Math.max(1, this.getHiddenSymbols(ch).length);
    // H-215：屏幕真实 vp 宽（display 实测；失败兜底 Mate80 1280px/3.5=365.714）
    let scrW: number = 365.714;
    try {
      const d: display.Display = display.getDefaultDisplaySync();
      if (d.width > 0 && d.densityPixels > 0) {
        scrW = d.width / d.densityPixels;
      }
    } catch (e) {
      console.warn(`${TAG} H-215 display.getDefaultDisplaySync failed: ${e}`);
    }
    // H-215：格宽自适应——14 格（e 键）按 34vp 会到 476vp 超屏 ⇒ 最多铺满屏宽-4，
    // 少格键保持 34vp 舒适区。
    const cell: number = Math.min(34, (scrW - 4) / len);
    const bubbleW: number = len * cell;
    const half: number = bubbleW / 2;
    // H-278：优先用根 Stack 实测的**窗口宽**（单手模式下候选栏只有 80%，不能拿它当窗口宽）；
    // 根宽还没量到的首帧才退回 candBarWidth/360。
    const winW: number = this.rootWinW > 0 ? this.rootWinW : (this.candBarWidth > 0 ? this.candBarWidth : 360);
    // 透明窗口比屏幕宽 ⇒ 内容（键盘可见区）在窗口内水平居中；夹取按内容区，不按整窗。
    const contentLeft: number = (winW - scrW) / 2;
    const pos: Position | undefined = this.letterKeyGlobalPos.get(ch);
    const keyCx: number = pos !== undefined ? (pos.x as number) + this.keyWidthVp / 2 : winW / 2;
    const keyTop: number = pos !== undefined ? (pos.y as number) : 100;
    let wantCx: number = keyCx;
    if (wantCx < contentLeft + half + 2) {
      wantCx = contentLeft + half + 2;
    }
    if (wantCx > contentLeft + scrW - half - 2) {
      wantCx = contentLeft + scrW - half - 2;
    }
    const g: BubbleGeom = {
      left: wantCx - half,
      // 窗口顶被裁（v7 泡 y=0.86 上缘切掉）⇒ 泡底=键顶-2：高 40 的泡尽量贴键
      top: keyTop - 40 - 2 - this.screenOffYvp,
      width: bubbleW,
      cell: cell
    };
    return g;
  }

  /**
   * H-215(Qoder)：长按气泡态下，把手指**窗口 X**（TouchObject.windowX，vp）映射到符号格下标。
   * 探针标定（h38_v7diag）证明 windowX 与 globalPosition/.position 同属窗口系
   * （窗口左缘=屏幕左缘，x 恒等）⇒ 直接对 bubbleGeom().left 做区间映射，零换算。
   * 手指始终留在键上（出泡后键 onTouch 仍在收 Move；H-165 已证 Up 会被重定向，但 Move 不丢）。
   * 落在气泡横向范围外 → -1（松手取消，不输入）。
   */
  private symIdxAtWindowX(wx: number, ch: string): number {
    const syms: string[] = this.getHiddenSymbols(ch);
    const len: number = syms.length;
    if (len <= 0) {
      return -1;
    }
    const g: BubbleGeom = this.bubbleGeom(ch);
    const rel: number = wx - g.left;
    if (rel < 0 || rel >= g.width) {
      return -1;
    }
    const idx: number = Math.floor(rel / g.cell);
    return idx >= 0 && idx < len ? idx : -1;
  }


  /**
   * H-215(Qoder 2026-10-27)：长按符号气泡——画在 **build() 顶层 Stack**（H-213 同款），
   * 像素 .position()（窗口系，bubbleGeom 定锚+内容区夹取）。嵌在键 Stack 里时
   * offset/translate/百分比 position 全被 IME 子窗口吞掉或成环（三轮真机铁证）。
   * 触摸：ArkUI 会把 Move 流**重定向到手指下方的组件**（真机铁证 h38_v8_drag_q：
   * 手指滑进候选栏区后键不再收 Move，Up 被键当成上滑 ⇒ 出了 `1` 而不是 `_`），
   * 所以气泡本体也挂 onTouch：手指进泡后由泡接管高亮与松手上屏；
   * 键侧仍保留同一套映射（手指不离开键面时由键处理）。两处共用 bubbleTouchMove/Up。
   */
  @Builder
  LongPressBubble() {
    Row() {
      ForEach(this.getHiddenSymbols(this.longPressLetter), (s: string, idx: number) => {
        Text(s)
          .fontSize(this.bubbleGeom(this.longPressLetter).cell >= 30 ? 18 : 14)
          // H-215：泡底 BG_POP 是深色（#3A3F47）⇒ 未高亮格用白字（原 TEXT_KEY 深色
          // 深底几乎看不见，h38_v8_q 真机图即此状）；高亮格浅蓝底配深字。
          .fontColor(this.longPressSymIdx === idx ? TEXT_KEY : '#FFFFFF')
          .textAlign(TextAlign.Center)
          .width(`${100 / Math.max(1, this.getHiddenSymbols(this.longPressLetter).length)}%`)
          .height('100%')
          .backgroundColor(this.longPressSymIdx === idx ? BG_ACTIVE : Color.Transparent)
          .borderRadius(6)
      }, (s: string, idx: number) => `lpb_${this.longPressLetter}_${idx}_${this.longPressSymIdx === idx ? 1 : 0}`)
    }
    .width(this.bubbleGeom(this.longPressLetter).width)
    .height(40)
    .backgroundColor(BG_POP)
    .borderRadius(10)
    .zIndex(999)
    .position({ x: this.bubbleGeom(this.longPressLetter).left, y: this.bubbleGeom(this.longPressLetter).top })
    // H-215(Qoder)：手指滑进气泡后由泡接管（windowX 与 .position 同系，直接映射）
    .onTouch((ev: TouchEvent) => {
      this.bubbleTouched = true;  // H-216(CodeArts)：手指已进入气泡区域，后续 Move 直接选中
      if (ev.type === TouchType.Move && ev.touches.length > 0) {
        this.bubbleTouchMove(ev.touches[0].windowX as number);
      } else if (ev.type === TouchType.Up || ev.type === TouchType.Cancel) {
        this.bubbleTouchUp();
      }
    })
    // H-215(Qoder)：标定打点——渲染出的窗口系几何
    .onAreaChange((_oldV: Area, newV: Area) => {
      const gp: Position = newV.globalPosition as Position;
      console.info(`${TAG} H-215 v7 bubble ${this.longPressLetter} win x=${gp.x as number} y=${gp.y as number} w=${newV.width} h=${newV.height} kw=${this.keyWidthVp}`);
    })
  }

  /** H-215(Qoder)：气泡态 Move 共用逻辑——按窗口 X 映射高亮格（键侧与泡侧同调）。 */
  private bubbleTouchMove(wx: number): void {
    const ch: string = this.longPressLetter;
    if (ch === '' || this.getHiddenSymbols(ch).length <= 0) {
      return;
    }
    // H-216(CodeArts)：出泡后 ArkUI 持续触发假 Move（手指没动），windowX 与 Down 时
    // 几乎相同——只有手指真正水平移动（>5vp）或滑进气泡（bubbleTouched）后才选中。
    if (!this.bubbleTouched && this.letterTouchDownX >= 0 && Math.abs(wx - this.letterTouchDownX) < 5) {
      return;
    }
    const idx: number = this.symIdxAtWindowX(wx, ch);
    if (idx !== this.longPressSymIdx) {
      console.info(`${TAG} H-215 move ${ch} wx=${wx} idx=${idx}`);
    }
    // H-216(CodeArts)：出泡不预选（longPressSymIdx=-1），手指未进泡时保持 -1（取消态）；
    // 进过泡后恢复「泡外 = 取消」的 H-215 语义。
    if (idx < 0 && !this.bubbleEntered) {
      return;
    }
    if (idx >= 0) {
      this.bubbleEntered = true;
    }
    this.longPressSymIdx = idx;
  }

  /** H-215(Qoder)：气泡态松手共用逻辑——指向符号则上屏，统一关气泡并置 swallow 标志。 */
  private bubbleTouchUp(): void {
    const ch: string = this.longPressLetter;
    if (ch === '' || this.getHiddenSymbols(ch).length <= 0) {
      return; // 已被键侧处理（事件冒泡先后皆可，后置者见 longPressLetter='' 直接返回）
    }
    if (this.longPressSymIdx >= 0 && this.longPressSymIdx < this.getHiddenSymbols(ch).length) {
      const sym: string = this.getHiddenSymbols(ch)[this.longPressSymIdx];
      console.info(`${TAG} H-215 commit ${ch} -> ${sym}`);
      this.typeChar(sym);
    } else {
      console.info(`${TAG} H-215 cancel ${ch}`);
    }
    this.longPressLetter = '';
    this.longPressSymIdx = -1;
    this.bubbleEntered = false;
    this.bubbleTouched = false;
    this.bubbleUpSwallow = true;
  }


  private symbolPageCount(): number {
    const total: number = this.activeSymbolItems().length;
    return Math.max(1, Math.ceil(total / 19));
  }

  @Builder
  CandidateBar() {
    Column() {
      // H-165（形态 B，主人 2026-10-25 拍板）：最左 `>` 折叠三角 + 一排功能磁贴。
      // —— 真机返工（Qoder 2026-10-25 14:4x，Mate80 装机实测三处缺陷）——
      //  ① 原「独立 20vp 三角行 + 34vp 磁贴行」塞进 candBarHeight()=44vp 的容器里：
      //     44vp 已被 L1(16)+候选行(28) 占满，实测面板 983px ＝ 候选栏 152 ＋ 键区 665 ＋ 底栏 160，
      //     **零余量**（keyH() 定高、QwertyPanel 的 layoutWeight 只会把底栏顶出面板）。
      //     结果只加三角 20vp，候选行就被顶到主键区：候选字被 q 行键帽盖住，
      //     右侧「展开网格」的 ▼ 直接被键面遮住（后画的兄弟节点吃掉点击）⇒ H-168 真机点不开。
      //  ② 三角那行 Row 定宽 FUNC_TRI_WIDTH，父 Column 默认水平居中 ⇒ 画在屏幕正中，不是「左上」。
      //  ③ 磁贴大字走 @Builder 按值传参，状态变了不刷新（引擎 ascii_mode=1、底栏键已显示「英」，
      //     磁贴仍冻在「中」）⇒ 文案改到 @Builder 内部读 @State 派生。
      // 改法：收起态三角**内联**在候选行最左（0 额外高度，几何回到 H-165 之前）；
      //       展开态 L1/候选行让位（Visibility.None 不占高），整条候选栏换成图标行，
      //       高度仍是 candBarHeight()。代价：展开期间暂不看候选词，点 ▼ 收起即恢复。
      // H-176：工具栏**照安卓原样做成图标行**（`k1_toolbar.png`：‹/撤销/重做/移动光标/剪贴板/…/▼
      // 共 7 枚，每枚约 48vp，整行正好 336vp 放得进 360vp 屏宽）。
      // 为什么换掉原来的开关磁贴：那排（简繁/中英/半全/标点/增廣/注释）与键面上已有的功能重复
      //（主人 2026-10-25 16:0x 原话「这些在键盘上都有了，重复吗这不是」）。
      // H-176 当时的「▼＋6 磁贴」形态已废，现行形态见 spec §十一「落地现状」。
      // H-177/H-183 起这四枚**都已接上**（不再是提示）：
      //   撤销＝undoCommit 逐字撤回最近一次上屏；重做＝redoCommit 放回；
      //   光标＝moveEditorCursor 走 InputClient.moveCursorSync；
      // H-204（主人「粘贴你说是鸿蒙限制，怎么解决…反正得想办法解决啊」）：应用级输入法
      //   确实拿不到剪贴板，但**系统的 PasteButton 安全控件**能给一次性授权（点在控件上的那一下
      //   就是授权），点完在 onClick 里读一次 getPrimaryText 即可。所以这枚打开剪贴板面板，
      //   面板里放 PasteButton；不再走宿主 sendExtendAction(PASTE)（主人实测「粘贴没反应」，
      //   很多宿主根本没实现 PASTE）。**仍不申请 READ_PASTEBOARD**（system_basic，要 ACL 签名，
      //   还撞内容闸门 ⑧ 的「权限恰为 VIBRATE」）——不需要权限正是选 PasteButton 的理由。
      // 教训：16:1x 我曾自作聪明加「收起三角 + 网格三角」两枚 ⇒ 9 个元素超宽，右侧全被挤出屏幕。
      // 安卓的 `‹` 就是收起、`▼` 就是收起（最后一枚），照搬即可，不要加戏。
      if (this.showFuncBar) {
        // H-218r2：原 'cursor' 单行子面板分支已删——⇆ 改走 funcSubPanel==='textedit'，
        // 在 build() 里接管整个键区（见 build 注释），候选栏这里只留图标行/剪贴板两种。
        if (this.funcSubPanel === 'clipboard') {
          // H-204：剪贴板面板——系统 PasteButton（临时授权读一次当前剪贴板）+ 永久说明行。
          // ‹ = 返回图标行（不收起工具栏）；▼ = 收起整条工具栏。
          Row({ space: 4 }) {
            Stack() {
              SymbolGlyph($r('sys.symbol.chevron_up'))
                .fontSize(16)
                .fontColor([FG_TOOLBAR])
            }
            .rotate({ angle: 270 })
            .width(FUNC_TRI_WIDTH)
            .onClick(() => {
              this.funcSubPanel = '';        // H-194：只退到图标行，工具栏保持展开
            })
            ClipboardPad({ barHeight: this.candBarHeight() })
            Stack() {
              SymbolGlyph($r('sys.symbol.chevron_down'))
                .fontSize(16)
                .fontColor([FG_TOOLBAR])
            }
            .width(FUNC_TRI_WIDTH)
            .onClick(() => {
              this.funcSubPanel = '';
              this.setFuncBar(false);
              this.funcBarPinned = false;
            })
          }
          .width('100%')
          .justifyContent(FlexAlign.SpaceBetween)
          .height(this.candBarHeight())
          .alignItems(VerticalAlign.Center)
          // H-207(Qoder 2026-10-26 真机)：剪贴板这一支**去掉 opacity 和上下 padding**。
          // 官方把「父组件属性导致安全控件显示不完整」「负/过小的可用区域」列为临时授权失败原因，
          // 而真机日志是 `AceSecurityComponent: security component has not registered`——
          // 控件压根没注册上，点多少次都是 TEMPORARY_AUTHORIZATION_FAILED（主人「点多少次也粘不上」）。
          // barAlpha 在展开动画期间是 0（H-189 淡出→换→淡入），安全控件正是在这一帧挂载的，
          // 半透明/被裁的父节点会直接影响注册；左右各留 2vp 仍够，垂直方向不再挤压按钮高度。
          .padding({ left: 2, right: 2 })
        } else {
          Stack() {
            Row({ space: 4 }) {
              // ‹ 收起工具栏（安卓第一枚）。用已核实的 chevron_up 旋转 270° 得到左箭头。
              Stack() {
                SymbolGlyph($r('sys.symbol.chevron_up'))
                  .fontSize(16)
                  .fontColor([FG_TOOLBAR])
              }
              .rotate({ angle: 270 })
              .width(FUNC_TRI_WIDTH)
              .onClick(() => {
                this.funcSubPanel = '';
                this.setFuncBar(false);
                this.funcBarPinned = false;   // 用户主动收起 ⇒ 不再自动回来
              })
              this.FuncIcon('undo')
              this.FuncIcon('redo')
              this.FuncIcon('cursor')
              this.FuncIcon('clipboard')
              this.FuncIcon('more')
              // ▼ 收起（安卓最后一枚，与本行首枚 ‹ 同功能——双出口，安卓实物就这样）
              Stack() {
                SymbolGlyph($r('sys.symbol.chevron_down'))
                  .fontSize(16)
                  .fontColor([FG_TOOLBAR])
              }
              .width(FUNC_TRI_WIDTH)
              .onClick(() => {
                this.funcSubPanel = '';
                this.setFuncBar(false);
                this.funcBarPinned = false;   // 用户主动收起 ⇒ 不再自动回来
              })
            }
            .width('100%')
            .justifyContent(FlexAlign.SpaceBetween)
            .height(this.candBarHeight())
            .alignItems(VerticalAlign.Center)
            // H-179：左右留 2vp（不是候选行惯用的 CAND_PAD_H=8）。安卓实测七枚图标中心在
            // 5.4% / 18.9% / 34.4% / 50.0% / 65.5% / 81.1% / 94.4%，是**满宽等距**；
            // 用 8vp 时首枚中心落 7.1%、末端 93.0%（整体内缩）。2vp 后为 5.5% / 94.6%，与安卓一致。
            .padding({ left: 2, right: 2, top: 2, bottom: 2 })
            .opacity(this.barAlpha)
            // H-184 收口：`···` 引擎开关菜单（安卓式弹层）。锚在图标行上层、右对齐（`···` 在右端）。
            // H-208（Qoder 2026-10-26 21:0x，主人原话「顶栏展开右三角打开以后，那是屎吗，
            // 藏到键盘里面什么都看不见，这像 ai 干的活的吗」）：菜单**从这里移走**。
            // 原来它作为本 Row 的子节点，而 Row 固定 44vp 高 ⇒ 7 条开关全被裁掉
            // （真机 x2_menu_open.jpeg：只闪出一条「中文/英文」，其余被吃掉）。
            // 现挪至 build() 顶层 Stack（与 LangMenu/LayoutMenu 并列），见 H-213 注释。
          }
          .width('100%')
          .height(this.candBarHeight())
          .alignContent(Alignment.TopStart)
        }
      }

      // H-096：竖屏整宽显示 L1；横屏（barHeight<40）把预编辑并进候选行左侧
      // H-165 返工：展开功能磁贴时 L1/候选行让位（磁贴行独占 candBarHeight()，加不得高度）
      // H-203：没有 preedit 时不渲染空 L1——空闲态整条栏只剩一行候选行高（安卓窄条），
      // 打字后 preedit 出现，字母自动占上面一行（主人原话「字母自动上去一行」）。
      // H-212（Qoder 2026-10-26 22:2x，主人原话「候选词第一个，就不能在输入字母的正下面吗，
      // 跑在中间干嘛去了，看着跟分家一样」）：栏容器已改 `FlexAlign.Start`（L1 贴顶），
      // 但空闲态没 L1 ⇒ 只有 L2 一行 28vp，Start 会让它**贴栏顶**（离键区 16vp 缝），
      // 看起来又分家。改法：空闲态在 L2 **上方**补 16vp 空白，让 L2 落到底（贴键区上沿），
      // 视觉上仍是「窄条」；打字态 L1+L2 正好 44vp 填满，无缝。
      // H-215(CodeArts)：符号页时不渲染 L1/L2 候选行（顶栏已换成工具栏图标行）
      if (this.barHeight >= 40 && !this.showFuncBar && this.panelMode !== 'symbol' &&
        this.preedit.length === 0 && !this.expanded && this.candidates.length === 0) {
        // H-241 契约 §3-12：关掉「显示编码行」时，那 16vp 由下面那条分支补空行（不动几何）。
        Row().height(this.commentRowHeight()).width('100%')
      }
      // H-241 契约 §3-12「显示编码行」＝关：这一支不渲染，改由紧随其后的**同高（16vp）空行**补位。
      // 为什么补空行而不是让候选行拿回这 16vp：栏容器高＝candBarHeight()＝max(44, L1+候选行)，
      // 窗口预算 236vp 是 H-208 定稿（跟缩会让键盘一蹦一跳，主人 10-26 20:5x 骂过的那条）；
      // 动行高＝动几何＝引新 bug，所以这一项的生效判据是「那行灰字消失、位置与其余布局分毫不动」。
      if (this.barHeight >= 40 && !this.showFuncBar && this.panelMode !== 'symbol' &&
        this.preedit.length > 0 && this.preeditShown) {
        // L1 预编辑行（整宽 12fp 灰字）——在候选行上面（M-038: 照 fcitx5 层结构）
        // H-190（主人 2026-10-26 原话「字母行应该是干净的，比如 gavc 开始，字母行就应该只是 gavc，
        // 候选都在下面」）：这里**只放原始编码**。此前把「preedit · 第一条候选的 comment」拼成整行，
        // 打字时看到的是 `gavc · [开] 开始` 这种混合体。安卓 `s_toolbar.png` 的 L1 只有 `hao`，
        // 注释跟候选词同条目（CandidateItemUi），已挪到 L2 每条候选后面。
        Text(this.preedit)
          .fontSize(12)
          .fontColor(FG_HINT)
          .maxLines(1)
          .textOverflow({ overflow: TextOverflow.Ellipsis })
          .width('100%')
          .height(this.commentRowHeight())
          .padding({ left: CAND_PAD_H, right: CAND_PAD_H })
          .opacity(this.barAlpha)
      }
      // H-241 契约 §3-12 的另一半：有编码但用户关了「显示编码行」⇒ 这 16vp 画空行占住，
      // 候选行落在原来的位置（不让它往上跳 16vp——H-212 主人骂过「跟分家一样」的那条缝）。
      if (this.barHeight >= 40 && !this.showFuncBar && this.panelMode !== 'symbol' &&
        this.preedit.length > 0 && !this.preeditShown) {
        Row().height(this.commentRowHeight()).width('100%')
      }

      // L2 候选行——H-164：连续横向滚动 List（替代 M-042 的 Row+clip 硬切，根除 H-034「整页闪变」）。
      // 原生 List 横向滚动，跟手、无整页闪变；续页按「baseIndex + 绝对下标」定位续取（H-164 判据③），
      // 一次滑动只续一次；绝不用裸 onReachEnd→flipPage 驱动（H-034 症状①②成因，已避）。
      // H-065（M-050）：与 L1 统一 CAND_PAD_H 左右内边距（真机 x≈4px 贴边修复）
      Row() {
        // H-165 返工：折叠三角内联在候选行最左——独立成行会吃掉候选栏 44vp 里不存在的余量（见上）。
        // H-173：用 SymbolGlyph，不用 Text('▶')——U+25B6 命中系统 emoji 字体回退，
        // 渲成「蓝底白箭头圆角徽章」，与全 App 矢量风格不一致（主人 2026-10-25 16:0x 点名）。
        // SymbolGlyph 没有 rotation 属性（ArkTS 实测报错），右箭头用外层 Stack 旋转实现。
        // H-188：这枚是「展开工具栏」的 ›，位置要与展开后的第一枚 ‹ 重合（见 FUNC_TRI_LEFT_W）；
        // 补 pressed 反馈——原来按下去没有任何视觉变化，36vp 的命中盒比 16vp 的字形大一圈，
        // 主人会觉得「点的地方和反应的地方错位」。
        // H-201（主人 2026-10-26 13:2x 骂「出候选以后顶栏的左上角三角还在呢，也不折叠起来，直接影响候选」）：
        // 安卓 `ExpandButtonStateMachine` 口径——展开钮**只在空闲态（无 preedit、无候选）显示**；
        // 打字态整枚消失，候选顶到左端。照安卓抄：idle 才渲染。
        if (this.candidates.length === 0 && this.preedit.length === 0) {
          Stack() {
            SymbolGlyph($r('sys.symbol.chevron_up'))
              .fontSize(16)
              .fontColor([FG_HINT])
          }
          .rotate({ angle: 90 })
          .width(FUNC_TRI_LEFT_W)
          .height(this.candRowHeight())
          // H-201：撤掉按压灰底（安卓实物这枚三角没有任何底色）
          .onClick(() => {
            this.setFuncBar(true);
            this.funcBarPinned = true;   // H-187：用户手动展开 ⇒ 按安卓口径，commit 后自动回来
            // 展开前读回真实开关态，防磁贴文案与实际相反
            this.syncEngineOptions();
          })
        }
        // H-096：横屏时在候选行左侧显示预编辑（替代被隐藏的 L1）
        // H-176：整行随工具栏让位（见行尾 visibility），这里不再单独显隐
        // H-241 契约 §3-12：横屏这一支同样受「显示编码行」开关管（漏一处＝横屏关不掉）。
        if (this.barHeight < 40 && this.preedit.length > 0 && this.preeditShown) {
          Text(this.preedit)
            .fontSize(12)
            .fontColor(FG_HINT)
            .maxLines(1)
            .textOverflow({ overflow: TextOverflow.Ellipsis })
            .flexShrink(0)
            .margin({ right: 8 })
        }
        // H-164：横向滚动 List——lanes:1 即单行横向排列；List 原生滚动手势（非 PanGesture，本面板内 PanGesture 不触发）。
        // 数据源 = 本 Rime 菜单页已加载全量（最多 50 条），一页内连续滑；只有滑到本页尾才由引擎翻页。
        // 判据③：续页必须由「手指按下过 + 真到末尾」驱动，且一次滑动只续一次；初始布局不算。
        List({ scroller: this.candListScroller, space: 4 }) {
          ForEach(this.scrollCandidates(), (cand: RimeCandidate, index: number) => {
            ListItem() {
              // H-190：词 + 注释同条目（安卓 CandidateItemUi）。注释是灰小字（0.8 字号），
              // 没有注释时只剩词；不上屏成 L1 的一部分，字母行保持干净。
              // H-217r2(Qoder 2026-10-27，主人复测「候选还是没有顶格起，应该和输入的编码对齐」）：
              // 不再用估算宽定 ListItem——估算永远有误差，误差全变成词右侧死区。
              // 改「内容自然定宽 + 封顶」（H-077 单条封顶 30% 口径挪到渲染端），
              // 长词超封顶才走 Ellipsis。
              Row({ space: 4 }) {
                // H-260(CodeArts): 候选词完整显示——flexShrink(0) 不压缩、去掉 Ellipsis；
                // 主人原话「候选条上的词应该完整显示，不该有省略号；展开面板里才可以省略号」。
                // 注释（comment）保留 flexShrink(1)+Ellipsis——空间不足时先牺牲注释。
                Text(cand.text)
                  .fontSize(this.candFontSize())
                  .fontColor(FG_TEXT)
                  .maxLines(1)
                  .flexShrink(0)
                if (this.candCommentText(cand).length > 0) {
                  Text(this.candCommentText(cand))
                    .fontSize(this.candFontSize() * 0.8)
                    .fontColor(FG_HINT)
                    .maxLines(1)
                    .textOverflow({ overflow: TextOverflow.Ellipsis })
                    .flexShrink(1)
                }
              }
              .height(this.candRowHeight())
              .width('100%')
              .alignItems(VerticalAlign.Center)
              .justifyContent(FlexAlign.Start)   // H-217r2：封顶在内容 Row 上
            }
            // H-257(CodeArts): 恢复定宽——撤掉后候选词重叠（内容溢出 ListItem 边界）
            .width(this.candItemWidth(cand))
            .onClick(() => {
              // 判据④：点第 N 条上屏第 N 条，绝对下标 = baseIndex + uiPageStart + 列表 index，不许错位
              keyboardController.chooseCandidateAbs(this.baseIndex + this.uiPageStart + index);
            })
          }, (cand: RimeCandidate, index: number) => `cand_${this.uiPageStart + index}_${cand.text}`)
        }
        .listDirection(Axis.Horizontal)
        .lanes(1)
        .layoutWeight(1)
        .height(this.candRowHeight())
        .scrollBar(BarState.Off)
        .edgeEffect(EdgeEffect.None)
        // H-164：控制器绑定/解绑标记——只在 List 挂载期间允许 scrollToIndex（见 candScrollToStart）
        .onAppear(() => {
          this.candListReady = true;
        })
        .onDisAppear(() => {
          this.candListReady = false;
        })
        .onTouch((e: TouchEvent) => {
          // H-164：只记「手指按下」——续页许可；不复用 PanGesture（H-154 实测不触发）
          if (e.type === TouchType.Down) {
            this.candDragArmed = true;
            this.candDragMoved = false;
          } else if (e.type === TouchType.Move) {
            this.candDragMoved = true;
          } else if (e.type === TouchType.Up || e.type === TouchType.Cancel) {
            // H-164 00:3x：移动过的抬手先留着许可——甩动的索引事件常在抬手后才到尾部，
            // 由 onScrollStop 续页或撤销；白点/轻点（没移动）才立即撤销，防误续。
            if (!this.candDragMoved) {
              this.candDragArmed = false;
            }
          }
        })
        .onScrollIndex((first: number, last: number) => {
          const items: RimeCandidate[] = this.scrollCandidates();
          this.candLastVisible = last;
          // 判据②⑦：可见首/末条绝对下标——真机验收按这行日志判「滑到第几屏」，不靠看像素
          console.info(`${TAG} H-164 scroll first=${first} last=${last} n=${items.length}` +
            ` absFirst=${this.baseIndex + this.uiPageStart + first}` +
            ` absLast=${this.baseIndex + this.uiPageStart + last}`);
          // 判据③：非用户拖动（初始布局/数据刷新/程序复位）不续页，防首帧连跳、防 H-034 复生
          this.candTryContinue(last);
        })
        .onScrollStop(() => {
          // H-164 00:3x：甩动/惯性停止时兜底续页（onScrollIndex 可能在抬手后才到尾部）
          this.candTryContinue(this.candLastVisible);
          this.candDragArmed = false;
          this.candDragMoved = false;
        })

        // ▼/▲ 展开候选网格（36vp 宽）——单击折叠/展开（有候选=展开候选网格、无候选=折叠键盘），
        // 长按恒折叠键盘（H-109 三角双功能：单击随状态切换，长按恒折叠）。
        // H-176：工具栏展开时整行让位 ⇒ 这枚跟着藏；收起态它就在候选行最右，行为不变。
        // H-188：与展开后工具栏最后一枚 ▼ 的竖线对齐：Android `CandidateUi` 的 expandButton
        // 是 `endOfParent` 的 40dp 按钮（中心 94.4% 屏宽）。原来行右内边距 8vp ⇒ 中心 92.7%，
        // 收起/展开两次画在不同位置，主人会觉得「三角位置不正、点起来错位」。
        // 行右内边距改 2vp 后中心 = 100% − 2 − 18 = 94.4%，与工具栏 ▼（padding 2 + 18）同线。
        Stack() {
          if (this.expanded) {
            SymbolGlyph($r('sys.symbol.chevron_up'))
              .fontSize(16)
              .fontColor([FG_HINT])
          } else {
            SymbolGlyph($r('sys.symbol.chevron_down'))
              .fontSize(16)
              .fontColor([FG_HINT])
          }
        }
        .width(FUNC_TRI_WIDTH)
        .height(this.candRowHeight())
        // H-201：撤掉按压灰底（同左三角，安卓实物无底色）
        .onClick(() => {
          // 安卓行为：一个三角两个功能——有候选（打字中）= 展开/收起候选网格；
          // 无候选（空闲）= 折叠键盘
          if (this.candidates.length > 0 || this.preedit.length > 0) {
            // H-231r2(Qoder 2026-10-27 21:0x)：网格与子面板在 build() 里互斥。
            // 展开网格前先关子面板，否则状态与画面会错位：子面板开着时点 ▼ 展开网格，
            // 画面变成网格、子面板状态还挂着；再点 ⇆ 就变成「把看不见的面板关掉」，
            // 主人看着毫无反应（这正是 H-231② 的另一个入口）。
            if (!this.expanded && this.funcSubPanel !== '') {
              this.funcSubPanel = '';
            }
            this.setExpanded(!this.expanded);
          } else {
            keyboardController.hideKeyboard();
          }
        })
        .gesture(
          LongPressGesture({ repeat: false, duration: 500 })
            .onAction(() => {
              // 有候选时想收键盘走长按（补一个折叠出口）
              keyboardController.hideKeyboard();
            })
        )

      }
      .width('100%')
      .height(this.candRowHeight())
      // H-188：右内边距 8→2vp（见上，与工具栏 ▼ 同线）；左内边距保持 CAND_PAD_H=8。
      .padding({ left: CAND_PAD_H, right: 2 })
      // H-165/H-176：工具栏展开时整行让位（Visibility.None 不占布局高度，工具栏行独占 44vp）
      // ——拆成「只藏 List」是错的：行里还剩左右两枚三角（各 28vp 高），会与工具栏行双算溢出
      //（h165_bar_height_check.py 抓到过，实占 45vp > 预算 44vp）。整行让位最干净。
      .visibility(this.showFuncBar || this.panelMode === 'symbol' ? Visibility.None : Visibility.Visible)
      .opacity(this.barAlpha)
    }
    // H-208：`···` 引擎开关菜单——栏容器一级的绝对定位浮层（原来是图标行子节点，被 44vp
    // 裁得只剩一条）。负 y 让它向上弹出到键盘上沿之外，zIndex 高于键区。
    // 只覆盖候选栏上方一小块（约 200vp），不会挡住整个键盘；点 ✕ 或点条目外任意处收起。
    // 注意：属性链必须连在 Column 的第一个子节点上，所以把 .width/.height 等**提到 if 之前**，
    // if 块放在属性链之后（ArkTS 里 if 是子节点，属性链不能跨它）。
    .width('100%')
    // H-220(CodeArts)：符号页时候选栏高度为0——标签行就是顶栏（照安卓），省44vp给符号区
    .height(this.panelMode === 'symbol' ? 0 : this.candBarHeight())
    .backgroundColor(BG_BAR)
    // H-212（Qoder 2026-10-26 22:2x，主人原话「你的候选词第一个，就不能在输入字母的正下面吗，
    // 跑在中间干嘛去了，看着跟分家一样」）：栏容器恒 44vp（窗口不跳），但**内容必须贴顶**——
    // 打字态 L1 在上、候选行紧跟其下，中间不许有缝；空闲态只有一行候选，靠下贴着键区上沿
    // （上方 16vp 同色留白），所以两态各自都不"分家」。
    // 上一版这里用 FlexAlign.Center，打字时候选行被推到栏中间 ⇒ 正是主人骂的。
    .justifyContent(FlexAlign.Start)
    // H-164（Qoder 00:2x 修）：priorityGesture → 普通 gesture。
    // priorityGesture 挂在父级会抢在子级 List 的原生横向滚动之前，L2 根本滑不动（等于没改）。
    // 改普通 gesture 后：落在 List 上的左右滑交给 List 连续滚动；落在内边距/展开键等非 List 区的左右滑
    // 仍按 H-034 一滑一页、500ms 防抖；展开态网格翻引擎页也照旧走这里（按钮「上一页/下一页」仍在）。
    .gesture(
      SwipeGesture({ direction: SwipeDirection.Horizontal, speed: 20 })
        .onAction((event: GestureEvent) => {
          // H-059：展开态也放开翻页手势——网格翻到本页末屏后，翻引擎页交给这里；
          // 候选栏（顶部）与展开面板竖滚不重叠、方向正交，不冲突。
          // H-034：一次滑动只回调一次 onAction = 一次只翻一页
          // lastFlipTime 500ms 防抖保留作保险
          const now: number = Date.now();
          if (now - this.lastFlipTime <= 500) {
            return;
          }
          this.lastFlipTime = now;
          if (Math.abs(event.angle) > 90) {
            // 向左滑 → 下一页
            this.flipCandidates(1);
          } else {
            // 向右滑 → 上一页
            this.flipCandidates(-1);
          }
        })
    )
    .onSizeChange((oldSize: Size, newSize: Size) => {
      // M-030/H-042：量候选栏实测宽度，动态算条数调 setPageSize
      this.candBarWidth = newSize.width;
      this.recomputePageSize();
    })
  }

  /** H-176/H-179：工具栏图标（照安卓图标行位形）——一枚一个动作，36vp 见方、无常态底色
   *  （只有按压浅灰，安卓实物就是这样）、矢量符号。
   *  已接地：`back`（收起）/ `more`（收起，与首尾三角同功能）/ `undo` / `redo` / `cursor`（左右移光标）
   *  / `clipboard`（H-183：粘贴当前剪贴板内容，走 `sendExtendAction(PASTE)`，与长按 v 同一动作）。
   *  **剪贴板历史**仍做不了：要 `READ_PASTEBOARD`，会撞内容闸门 ⑧（权限恰为 VIBRATE）——
   *  所以这枚图标=「粘贴当前内容」，不是历史面板；CodeArts M-216③ 若核出合规读法再升级。
   *  不做静默假按钮（H-165 §七 的规矩）。 */
  /** H-184 收口（主人 2026-10-26 13:2x「照安卓抄」＝拍板）：`···` 弹出的引擎开关菜单。
   *  安卓 fcitx5 的 `···` 列动态 fcitx 开关；我们复用既有四枚磁贴＋繁简的同一套
   *  toggleFuncOption/setOption 链（不造第二套开关）。九键下 extended_charset/phraseComment
   *  不可用（funcTileEnabled 置灰，同磁贴口径）。点条目即切换并保持菜单开（安卓弹层语义：
   *  连续切几个开关不消菜单）；点 ○ 关闭。 */
  /** H-213 真机返工（Qoder 2026-10-27 00:2x，Mate80）：点「常用/增廣」后标签仍冻在「关」——
   *  正是 H-165 ③ 的同款坑：@Builder 按值传参（`on`）不随 @State 刷新。
   *  改法同磁贴：条目内部按 name 读 @State 派生，不接第三参。 */
  private funcOptionOn(name: string): boolean {
    switch (name) {
      case 'ascii_mode':
        return this.asciiMode;
      case 'zh_trad':
        return this.tradMode;
      case 'full_shape':
        return this.fullShape;
      case 'extended_charset':
        return this.extendedCharset;
      case 'phraseComment':
        return this.phraseComment;
      case 'ascii_punct':
        return this.asciiPunct;
      // H-227：五枚滤镜开关的当前态（@State 镜像，条目内部按 name 读——H-213 的按值参数冻结坑不许再犯）
      case 'encnDic':
        return this.encnDic;
      case 'phraseExt':
        return this.phraseExtOn;
      case 'phraseReplace':
        return this.phraseReplaceOn;
      case 'abbrEn':
        return this.abbrEn;
      case 'pinyin':
        return this.pinyinAnnot;
      default:
        return false;
    }
  }

  @Builder
  FuncMenu() {
    // H-241r2（Qoder 2026-10-28 03:4x，**改的是我自己在 H-241 里加的那行导致的回归**）：
    // 加「设置（键盘与候选）」后菜单实测高 268vp（标题22 + 7行×32 + 7缝×2 + 内边距8 + 外边距8），
    // 而面板窗口内容区真机量到的是 **236vp**（hilog `H-215 root area win? x=0 y=0 w=365.7 h=236`）。
    // Stack 居中 ⇒ 上下各裁 ~16vp，新行正好只剩半截——和 H-213 那次「末行被屏幕底裁半」同一个根因
    // （IME 窗口外的像素不画，也点不到，加 `.clip(false)` 没用）。
    // 修法照搬本仓已真机验过的设置卡通路（SettingsPanel 213 行）：**外壳固定尺寸 + 内层 Scroll**，
    // 圆角/背景/阴影留在外壳上，行在壳里滚。H-227 还要往这菜单补 5 个开关，也只能走这条路。
    Column() {
      Scroll() {
        Column({ space: 2 }) {
          Row() {
            Text('输入法开关')
              .fontSize(12)
              .fontColor(FG_HINT)
              .layoutWeight(1)
            Text('✕')
              .fontSize(12)
              .fontColor(FG_HINT)
              .padding({ left: 8, right: 4 })
              .onClick(() => {
                this.funcMenuOpen = false;
              })
          }
          .width('100%')
          .padding({ left: 12, right: 4, top: 4, bottom: 2 })

          this.FuncMenuItem('半角 / 全角', 'full_shape')
          this.FuncMenuItem('常用 / 增廣', 'extended_charset')
          this.FuncMenuItem('反查注释', 'phraseComment')
          this.FuncMenuItem('中 / 英标点', 'ascii_punct')
          this.FuncMenuItem('简体 / 繁體', 'zh_trad')
          this.FuncMenuItem('中文 / 英文', 'ascii_mode')
          // H-227（Qoder 2026-10-28 08:0x，M-271 核过／M-280 催过回执一直无回音 ⇒ 按「无人认领我自接」收口）：
          // 安卓 `···` 里能勾、我们**滤镜和数据早就在包里**却没有入口的五枚——
          // 文案取 `wubi_pinyin.custom.yaml:6-27` 各开关自己的 states 名，不自造说法（H-119 不许编功能）。
          // 走同一条 toggleFuncOption→setOption 链＋同一个 FuncMenuItem（态在条目内部按 name 读 @State）。
          // **加行之所以安全**：H-241r2 已把这个菜单改成定高壳（92%×236vp）＋内层 Scroll，
          // 契约 §3.1 r4 那条「任何加行必须自带滚动」的口径在这儿已满足；九键下这五枚置灰（WUBI_ONLY_OPTIONS）。
          this.FuncMenuItem('中英对照', 'encnDic')
          this.FuncMenuItem('拼音注音', 'pinyin')
          this.FuncMenuItem('英文缩写', 'abbrEn')
          this.FuncMenuItem('短语扩展', 'phraseExt')
          this.FuncMenuItem('敏感词替换', 'phraseReplace')
          // H-278（Qoder 2026-10-30，主人「单手模式还没做」）：单手模式开关。
          // 它不是 Rime 开关（不进引擎、九键下也照样能用）⇒ 不能走 FuncMenuItem（那支按 option 记账、
          // 还会按 WUBI_ONLY_OPTIONS 置灰），与下面「设置」同款单独一行。
          // 右侧小字＝当前状态；点一下就在 开（贴右）→ 开（贴左）→ 关 之间轮转，
          // 键面上的 ⇄ 手柄同义（菜单只是入口，用起来不用再开菜单）。
          Row() {
            Text('单手模式')
              .fontSize(14)
              .fontColor(FG_TEXT)
              .layoutWeight(1)
              .maxLines(1)
            Text(this.oneHandOn ? (this.oneHandSide === 'left' ? '开 · 贴左' : '开 · 贴右') : '关')
              .fontSize(12)
              .fontColor(this.oneHandOn ? FG_TOOLBAR : FG_HINT)
          }
          .width('100%')
          .height(32)
          .padding({ left: 12, right: 12 })
          .borderRadius(RADIUS_SM)
          // H-254：与 FuncMenuItem 同一条通路（不用 stateStyles 的 pressed——抬手不复位）。
          .backgroundColor(this.pressedMenuItem === 'onehand' ? FUNC_ICON_PRESSED : Color.Transparent)
          .onTouch((ev: TouchEvent) => {
            if (ev.type === TouchType.Down) {
              this.pressedMenuItem = 'onehand';
            } else if (ev.type === TouchType.Up || ev.type === TouchType.Cancel) {
              if (this.pressedMenuItem === 'onehand') {
                this.pressedMenuItem = '';
              }
            }
          })
          .onClick(() => {
            this.pressedMenuItem = '';
            this.toggleOneHandFromMenu();
          })
          // H-241（主人 2026-10-28 01:4x 点单的第二条入口）：`···` 菜单里加一枚「设置」。
          // 对应安卓 `StatusAreaWindow` 的工具区入口＋EXTRA_SETTINGS_ROUTE 深链；
          // 我们**不能** startAbility 拉 App（基础模式禁止，契约 §1-①），所以点开的是面板内覆盖层。
          // 不复用 FuncMenuItem：它按 Rime option 记账（开/关那列），设置页不是引擎开关。
          // 位置放最后（安卓也是把「设置」排在功能格子末尾），上面六行是 Rime 开关。
          Row() {
            Text('设置（键盘与候选）')
              .fontSize(14)
              .fontColor(FG_TEXT)
              .layoutWeight(1)
              .maxLines(1)
            Text('›')
              .fontSize(14)
              .fontColor(FG_HINT)
          }
          .width('100%')
          .height(32)
          .padding({ left: 12, right: 12 })
          .borderRadius(RADIUS_SM)
          // H-254：与 FuncMenuItem 同一条通路（不再走 stateStyles 的 pressed 分支——抬手不复位，见 H-238）。
          .backgroundColor(this.pressedMenuItem === 'settings' ? FUNC_ICON_PRESSED : Color.Transparent)
          .onTouch((ev: TouchEvent) => {
            if (ev.type === TouchType.Down) {
              this.pressedMenuItem = 'settings';
            } else if (ev.type === TouchType.Up || ev.type === TouchType.Cancel) {
              if (this.pressedMenuItem === 'settings') {
                this.pressedMenuItem = '';
              }
            }
          })
          .onClick(() => {
            this.pressedMenuItem = '';
            this.funcMenuOpen = false;
            this.openSettings();
          })
        }
        .width('100%')
      }
      .scrollBar(BarState.Auto)
      .width('100%')
      .layoutWeight(1)
      .align(Alignment.TopStart)
    }
    .width('64%')
    // H-241r2：外壳给死高度（92%×236vp ≈ 217vp），行在里面的 Scroll 里滚；
    // 内容 268vp ⇒ 可滚 ~51vp，末行「设置」滚一下就到，遮罩点任意处仍能直接关。
    .height('92%')
    .padding({ top: 2, bottom: 6 })
    .backgroundColor(BG_BAR)
    .borderRadius(RADIUS)
    .shadow({ radius: 12, color: 'rgba(0,0,0,0.18)', offsetY: 2 })
    // H-208：定位由调用方（栏容器一级的浮层）给，这里不再自己定位——
    // 原来 `.position({y:0})` 让它叠在 44vp 图标行内被裁（真机只闪一条）。
    .opacity(this.barAlpha)
  }

  /** H-184：菜单条目。右端小字＝当前态（安卓磁贴「大字当前、小字目标」同义）。
   *  九键下没在 `sansheng_t9.schema.yaml` 声明过的开关一律不可用 ⇒ 置灰（`funcTileEnabled`
   *  读 `WUBI_ONLY_OPTIONS`：extended_charset/phraseComment ＋ H-227 那五枚滤镜）。 */
  @Builder
  FuncMenuItem(label: string, name: string) {
    Row() {
      Text(label)
        .fontSize(14)
        .fontColor(this.funcTileEnabled(name) ? FG_TEXT : FG_HINT)
        .layoutWeight(1)
        .maxLines(1)
      Text(this.funcOptionOn(name) ? '开' : '关')
        .fontSize(12)
        .fontColor(this.funcOptionOn(name) ? FG_TOOLBAR : FG_HINT)
    }
    .width('100%')
    // H-213 真机（Mate80 2026-10-27 00:2x）：36vp 行高 ×6 + 标题 ≈ 888px，
    // 比 IME 窗口（键盘顶→屏幕底 ≈874px）高出一截，末行「中文/英文」被屏幕底裁半。
    // 收到 32vp（≈811px）整单进窗，仍在可点范围（工具栏磁贴同量级）。
    .height(32)
    .padding({ left: 12, right: 12 })
    .borderRadius(RADIUS_SM)
    // H-254（Qoder 2026-10-28 08:5x）：按下态从 stateStyles(pressed) 挪到显式 @State——
    // 真机实测（docs/evidence/2026-10-28/h227-device/after-y*.jpeg）点过的行底色停在
    // (219,226,236)≈#DCE2EC 不复位，与 H-238 顶栏图标同一根因。Down 上色、Up/Cancel 清色、
    // onClick 再兜一次底（tap 回调与 TouchUp 谁先到都不影响最终态）。
    .backgroundColor(this.pressedMenuItem === name ? FUNC_ICON_PRESSED : Color.Transparent)
    .onTouch((ev: TouchEvent) => {
      if (ev.type === TouchType.Down) {
        this.pressedMenuItem = name;
      } else if (ev.type === TouchType.Up || ev.type === TouchType.Cancel) {
        if (this.pressedMenuItem === name) {
          this.pressedMenuItem = '';
        }
      }
    })
    .onClick(() => {
      this.pressedMenuItem = '';        // H-254 兜底：同 H-238，防这次重渲染吞掉 TouchUp
      if (this.funcTileEnabled(name)) {
        this.toggleFuncOption(name, this.funcOptionOn(name));
      }
    })
  }

  @Builder
  FuncIcon(action: string) {
    Stack() {
      if (action === 'more') {
        // `···` 用文字三点（系统符号里没有「更多」，不猜名字）
        Text('···')
          .fontSize(14)
          .fontColor(FG_TOOLBAR)
          .maxLines(1)
      } else if (action === 'cursor') {
        // H-228(H-231 改回)：按安卓 `ic_cursor_move.xml` 原形状画，但 `Shape`+`Path` 在
        // HarmonyOS 26vp 以下不渲染（实机看到「成点了」），退回系统符号 `arrow_left_arrow_right`。
        // 语义是「左右移光标」，够用；不再赌 Shape 渲染。
        SymbolGlyph($r('sys.symbol.arrow_left_arrow_right'))
          .fontSize(this.funcIconGlyphSize())
          .fontColor([this.funcIconReady(action) ? FG_TOOLBAR : FG_HINT])
      } else {
        // H-179：撤销/重做/光标/剪贴板全部走系统符号。
        // 名字不是猜的——逐个在 SDK `openharmony/ets/build-tools/ets-loader/sysResource.js`
        // 的 symbol 节（4043 个资源名）里查到：undo / redo / arrow_left_arrow_right / text_clipboard。
        // CodeArts 另从 HMSymbolVF.ttf 的 cmap 独立查到同四个 glyph（M-213），两条证据互相对上。
        // 安卓那枚「光标」是 I 型竖线带左右箭头，系统符号里没有 I 型光标 ⇒ 用语义最近的
        // arrow_left_arrow_right（点击动作就是左右移光标），不用形状不对的图形冒充。
        SymbolGlyph(this.funcIconSymbol(action))
          .fontSize(this.funcIconGlyphSize())
          .fontColor([this.funcIconReady(action) ? FG_TOOLBAR : FG_HINT])
      }
    }
    .width(FUNC_ICON_SIZE + 16)
    .height(this.funcIconBox())
    .borderRadius(RADIUS_SM)
    // H-238（Qoder 2026-10-28 01:2x，主人原话「我说是顶栏的，文本编辑，折叠后还是灰底选中状态，
    // 没变回来」）：这枚的按压反馈原先挂在框架的按压样式态（stateStyles 的 pressed 分支，
    // 见本文件顶部 `FUNC_ICON_PRESSED` 那段——原 `@Styles funcIconPressed()` 已在 H-254 删除），
    // 真机量到**抬手不恢复** —— `scripts/h238_toolbar_cursor_check.py`
    // （01:03–01:04 装机包）：
    //   P1 工具栏展开、面板关着：⇆ 盒底色 = (242,243,245) 常态栏底
    //   P2 点 ⇆ 开面板：       ⇆ 盒底色 = (219,226,236) ＝ #DCE2EC 按压色
    //   P3 再点 ⇆ 折叠：       ⇆ 盒底色 = (219,226,236) **还停在那儿**（656 px）
    //   P4 点 ‹ 整条收起：     (242,243,245)（图标行没了）
    // 根因：按下态由框架内部状态机持有，而 onClick 里改 `funcSubPanel` 会让键区整块换 builder
    // （QwertyPanel ⇄ TextEditGridPanel，见 build() 的 if/else），这次重渲染后 pressed 没被复位。
    // 改法：走本文件 M-049 键面已经在用的同一条通路——显式 @State + onTouch，Down 上色、
    // Up/Cancel 清色，onClick 里再兜一次底（手势的 tap 回调与 TouchUp 谁先到都不影响最终态）。
    .backgroundColor(this.pressedFuncIcon === action ? FUNC_ICON_PRESSED
      : (this.funcIconOn(action) ? BG_ACTIVE : Color.Transparent))
    .onTouch((ev: TouchEvent) => {
      if (ev.type === TouchType.Down) {
        this.pressedFuncIcon = action;
      } else if (ev.type === TouchType.Up || ev.type === TouchType.Cancel) {
        if (this.pressedFuncIcon === action) {
          this.pressedFuncIcon = '';
        }
      }
    })
    .onClick(() => {
      this.onFuncIcon(action);
      this.pressedFuncIcon = '';        // H-238 兜底：万一这次重渲染吞掉 TouchUp
    })
  }

  /** H-238r2（主人 2026-10-28 01:2x，原话「现在连选中都没有颜色了！」）：
   *  我上一版只把「抬手不复位」修掉了，结果**面板开着时也没有任何选中色**——他要点的就是这层。
   *  所以选中态**显式由子面板开关驱动**（不是握在按压状态机里）：
   *  ⇆ 开着文本编辑面板 = 亮，剪贴板图标开着剪贴板面板 = 亮，折叠/切走 = 当场退。
   *  底色用本文件既有的功能键激活色 `BG_ACTIVE`（#B8C6E8，与 n 键「选择」开着、上档键开着同色），
   *  不新造颜色 ⇒ 主人认得出「这就是开着的那个」，也和 H-179 那排磁贴的按压浅灰分得开。 */
  private funcIconOn(action: string): boolean {
    if (action === 'cursor') {
      return this.funcSubPanel === 'textedit';
    }
    if (action === 'clipboard') {
      return this.funcSubPanel === 'clipboard';
    }
    return false;
  }

  /** H-176/H-179：工具栏图标 → 系统符号资源。
   *  **名字必须在 SDK 的 `sysResource.js`（symbol 节）里查实，不许凭感觉写**——
   *  2026-10-25 16:1x 我用 `return_down_left`(回车) 冒充撤销、`delete_left`(退格) 冒充剪贴板，
   *  真机图形完全不对（主人一眼看穿）；16:4x 又让三枚全落到 default 的 chevron_down，三枚一模一样。
   *  以上全是「猜」的代价，所以 H-179 起以资源表为准。 */
  private funcIconSymbol(action: string): Resource {
    switch (action) {
      case 'back':
        return $r('sys.symbol.chevron_up');
      case 'undo':
        return $r('sys.symbol.undo');
      case 'redo':
        return $r('sys.symbol.redo');
      case 'clipboard':
        return $r('sys.symbol.text_clipboard');
      default:
        return $r('sys.symbol.chevron_down');
    }
  }

  /** H-179：图标盒高度**必须随栏高收缩**。竖屏 candBarHeight()=44vp，盒 36vp 够；
   *  横屏（barHeight<40）candBarHeight()=max(24, barHeight-6) 只有 24vp，盒还写死 36vp 就会
   *  溢出压到键面上——H-170 ①「磁贴溢出压键」是同一类缺陷，这里一次说清。 */
  private funcIconBox(): number {
    return Math.min(FUNC_ICON_SIZE + 16, this.candBarHeight());
  }

  /** H-179：字形尺寸跟着盒走（横屏盒矮，16vp 字形塞不下就降到 12vp）。 */
  private funcIconGlyphSize(): number {
    return this.funcIconBox() >= 32 ? 16 : 12;
  }

  /** H-176：图标的中文名（H-179 起只用于无障碍描述/提示文案，键面本身画的是图形）。 */
  private funcIconLabel(action: string): string {
    switch (action) {
      case 'undo':
        return '撤销';
      case 'redo':
        return '重做';
      case 'cursor':
        return '光标';
      case 'clipboard':
        return '剪贴';
      default:
        return '';
    }
  }

  /** H-178：当前方案短名（五笔/九键/拼音）。
   *  **H-181 起空格键不再用它**——主人 2026-10-26 明确否掉「空格显示方案名」，空格固定「三生」。
   *  保留此方法＋`getSchemaId()` 读取链（设置页显示方案、以后可能的方案切换入口用得上），
   *  但**不许再往键面上贴**。映射短名是因为长名塞进 4.5 权重的空格位会挤。 */
  private schemaLabel(): string {
    const id: string = keyboardController.getSchemaId();
    if (id.indexOf('wubi') >= 0) {
      return '五笔';
    }
    if (id.indexOf('t9') >= 0) {
      return '九键';
    }
    if (id.indexOf('pinyin') >= 0 || id.indexOf('luna') >= 0) {
      return '拼音';
    }
    if (id.length > 0) {
      return id;
    }
    return '三生';
  }

  /** H-176：这个图标对应的动作是否已接地（未接地的置灰＋点它只提示）。
   *  H-177（主人 2026-10-25 16:5x「对照安卓抄」）：撤销/重做/光标三枚已接（见 onFuncIcon），
   *  H-204：clipboard 打开 PasteButton 面板（临时授权读一次），不再置灰。 */
  private funcIconReady(action: string): boolean {
    // H-183：clipboard 也接地了（粘贴当前内容）⇒ 不再置灰
    return action === 'back' || action === 'more' || action === 'undo' ||
      action === 'redo' || action === 'cursor' || action === 'clipboard';
  }

  /** H-234（Qoder 2026-10-28 00:4x，主人 2026-10-27 深夜原话「文本编辑折叠后，还显示灰色选中状态，
   *  没变回来」）：⇆ 文本编辑面板**一折叠就退出「选择」模式**。
   *  根因（读代码量出来的，不是猜）：控制器里 `selectionModeOn` 只有一个地方能关——
   *  `toggleSelectionMode()`（KeyboardController.ets 第 115 行初始化、第 709 行唯一改写点），
   *  而 `funcSubPanel = ''` 在 KeyboardIndex 里有**十处**赋值点（打字 / ‹ / ▼ / 再点 ⇆ /
   *  展开候选网格前 / 面板自身退出回调），没有一处管它 ⇒ 面板收了、格子里的「取消选择」再也点不到，
   *  键面 n 键还挂着激活底色 `BG_ACTIVE`＝#B8C6E8（本文件「n 键灰底」那一行），宿主里的选区也原样留着
   *  ＝主人说的「灰色选中状态没变回来」。
   *  做法：**复用**点「取消选择」那一条路（`toggleSelectionMode()`），不造第二套取消逻辑。
   *  边界：只在「从 textedit 折到关闭」时退出；切到剪贴板面板（'clipboard'）不动它——
   *  粘覆盖选区是另一件事，不能在这里顺手把选区抹了。
   *  留一句真话：这条路收拢选区用的是 `selectByRangeSync{idx,idx}`（零长度区间），H-229 真机证明
   *  宿主对零长度区间**不一定认**——所以「宿主的蓝/灰高亮有没有真的消失」仍以主人真手为准，
   *  我这侧只保证**键盘自己的态**（n 键底色、面板里的「选择/取消选择」文案）一定变回来。 */
  private onFuncSubPanelWatch(): void {
    const was: string = this.prevFuncSubPanel;
    this.prevFuncSubPanel = this.funcSubPanel;
    if (was === 'textedit' && this.funcSubPanel === '' && this.selMode) {
      keyboardController.toggleSelectionMode();
      this.selMode = keyboardController.isSelectionMode();
      console.info(`${TAG} H-234 折叠 ⇆ 面板 ⇒ 自动退出「选择」（与点「取消选择」同一条路径）`);
    }
  }

  /** H-176/H-177：图标行的点击分发。
   *  H-177：undo/redo/cursor 已接真功能（KeyboardController 的 undoCommit/redoCommit/
   *  moveEditorCursor）；clipboard 仍 stub（要权限）。
   *  H-192（主人 2026-10-26 原话「点击任一个时自动折叠不应该，操作还没完成，改成手动折叠工具」）：
   *  **动作键不收起工具栏**——光标要连点几次才移到位、撤销/重做要看结果再决定下一步。
   *  只有 `‹` / `▼` / `···`（`back`/`more`，它们语义就是收起）才关。打字仍按 H-180 收起
   *  （那是主人明确要的「打字别盖住候选」），这条不受影响。 */
  private onFuncIcon(action: string): void {
    switch (action) {
      case 'back':
        // ‹（首枚）仍是收起。H-184 起 `···` 不再共用这个分支——它有自己的菜单语义。
        // H-218r2：textedit 面板开着时 ‹ 先退回图标行（子面板出口，与 ✕ 同义），不收起工具栏。
        if (this.funcSubPanel === 'textedit') {
          this.funcSubPanel = '';
          break;
        }
        this.funcSubPanel = '';
        this.funcMenuOpen = false;
        // H-215(CodeArts)：符号页时 ‹ 回字母页（符号页没有候选栏可回）
        if (this.panelMode === 'symbol') {
          keyboardController.clear();
          this.switchPanelMode('qwerty');
        } else {
          this.setFuncBar(false);
          this.funcBarPinned = false;   // H-187：用户主动收起 ⇒ 不再自动回来
        }
        break;
      case 'more':
        // H-184 收口（主人「照安卓抄」）：`···` 弹出引擎开关菜单（安卓 fcitx 的动态开关条目同义），
        // 不再是「收起」——此前点它只会把工具栏关掉＝主人骂的「打开都是空的」。
        // 开关直接复用四枚磁贴的 toggleFuncOption（同一引擎 setOption 链，不造第二套）。
        this.funcSubPanel = '';
        this.funcMenuOpen = !this.funcMenuOpen;
        // H-241r2（Qoder 2026-10-28 04:4x）：补一条**「菜单开没开」的可观测**。
        // 真机取证 `h241_funcmenu_check.py` 原来只能靠像素团认「这是不是 `···`」——04:33 那次把
        // 工具栏第 5 枚「剪贴板」认成了 `···`，弹出来的是剪贴板说明条，脚本却当菜单在量，
        // 报出来的「裁切」证据其实是别人的浮层。有这条 ⇒ 认错簇＝hilog 0 命中，不会张冠李戴。
        console.info(`${TAG} H-241r2 func menu ${this.funcMenuOpen ? 'opened' : 'closed'}`);
        break;
      case 'undo':
        keyboardController.undoCommit();
        break;
      case 'redo':
        keyboardController.redoCommit();
        break;
      case 'cursor':
        // H-218r2（主人「文本编辑不在一行上，展开铺到键盘上，你没看安卓吗」）：
        // ⇆ 不再换候选栏那一行，而是**接管整个键区**（安卓 TextEditingWindow 同构）。
        // H-228(Qoder 2026-10-27 17:5x，主人「再次点击不能折叠」)：**改成开关**——
        // 原来是「永远置成 textedit」，所以点第二次什么都不发生。现在开着就收起。
        // H-231r2(Qoder 2026-10-27 21:0x)：**先把展开候选网格收起来**——
        // build() 里是 `if (expanded) ExpandedPanel() else if (funcSubPanel==='textedit') TextEditGridPanel()`，
        // 网格与子面板**互斥**：网格展开着的时候点 ⇆ 只改状态、画面纹丝不动，
        // 主人看到的还是那张网格 ⇒ 面板里的「选择」格自然「没有」。
        // 这是 H-231② 的**第二个根因**（与格子本身怎么写无关），先前只改格子是治了一半。
        if (this.expanded) {
          this.setExpanded(false);
        }
        this.funcSubPanel = this.funcSubPanel === 'textedit' ? '' : 'textedit';
        break;
      case 'clipboard':
        // H-204：整行换成剪贴板面板，面板里是系统 PasteButton（点＝临时授权读一次）。
        // **不申请 READ_PASTEBOARD**（system_basic + ACL，且撞内容闸门 ⑧ 的「权限恰为 VIBRATE」）。
        // H-231r2：与 ⇆ 同理，剪贴板面板也在互斥分支里 ⇒ 展开网格开着时先收网格。
        if (this.expanded) {
          this.setExpanded(false);
        }
        this.funcSubPanel = 'clipboard';
        break;
      default:
        this.funcIconToast(action);
        break;
    }
  }

  /**
   * H-204(Qoder)：轻提示。主人「复制没反应」的根因之一是**没有任何可见反馈**——
   * 宿主编辑框的选区收拢肉眼未必看得出来，所以每次复制后弹一条短 toast。
   * 单独包一层是为了 try/catch：promptAction 在部分宿主上会抛。
   */
  private showTip(msg: string): void {
    try {
      promptAction.showToast({ message: msg, duration: 2000 });
    } catch (e) {
      console.warn(`${TAG} showTip failed: ${JSON.stringify(e)}`);
    }
  }

  /** H-176：未接地动作的明确反馈（不做静默假按钮）。 */
  private funcIconToast(action: string): void {
    const names: Record<string, string> = {
      'clipboard': '剪贴板历史'
    };
    const what: string = names[action] !== undefined ? names[action] : action;
    console.info(`${TAG} H-176 func icon not ready: ${action}`);
    try {
      promptAction.showToast({ message: `${what}还没做，先记着` });
    } catch (e) {
      console.warn(`${TAG} funcIconToast failed: ${JSON.stringify(e)}`);
    }
  }

  @Builder
  ExpandedPanel() {
    Column() {
      // H-096：展开面板与候选栏之间加视觉分隔线
      Divider().color(BG_FUNC).strokeWidth(0.5)

      // H-257(CodeArts): 展开候选改单列连续滚动 List（替代 Grid 整屏翻页）——
      // 主人原话「把滑动改成丝滑的那种」「展开以后的候选现在是双列，不好看长注释也会相互影响，
      // 改成单列居中吧」。双列时长注释互相挤压，单列居中每条独立一行，注释不再互相影响。
      List({ scroller: this.expandedListScroller, space: 6 }) {
        ForEach(this.pagedCandidates(), (cand: RimeCandidate, index: number) => {
          ListItem() {
            // 词 + 注释同条目：词 16fp 主色，注释 13fp 灰字（与 L2 口径一致）
            Row({ space: 4 }) {
              Text(cand.text)
                .fontSize(16)
                .fontColor(FG_TEXT)
                .maxLines(1)
                .textOverflow({ overflow: TextOverflow.Ellipsis })
                .flexShrink(0)
              if (this.candCommentText(cand).length > 0) {
                Text(this.candCommentText(cand))
                  .fontSize(13)
                  .fontColor(FG_HINT)
                  .maxLines(2)
                  .textOverflow({ overflow: TextOverflow.Ellipsis })
                  .layoutWeight(1)
              }
            }
            .alignItems(VerticalAlign.Center)
            .justifyContent(FlexAlign.Start)
            .padding(6)
            .borderRadius(RADIUS)
            .backgroundColor(BG_KEY)
            .width('100%')
            .onClick(() => {
              keyboardController.chooseCandidateAbs(
                this.baseIndex + this.uiPageStart + index);
              this.setExpanded(false);
              this.preedit = '';
              this.candidates = [];
              this.allCandidates = [];
              this.uiPageStart = 0;
              this.gridScreenOffset = 0;
            })
          }
        }, (cand: RimeCandidate, index: number) =>
          `exp_${this.uiPageStart + index}_${cand.text}`)
      }
      .listDirection(Axis.Vertical)
      .lanes(1)
      .layoutWeight(1)
      .scrollBar(BarState.Auto)
      .edgeEffect(EdgeEffect.Spring)
      .padding({ left: CAND_PAD_H, right: CAND_PAD_H, top: 4, bottom: 4 })

      // 底部工具行：上一页 / 页码 / 下一页 / 取消 / 收起（保留）
      // H-257(CodeArts): 上一页/下一页改为 scrollToIndex（连续滚动模式下按步进滚动）
      Row({ space: 16 }) {
        Text(this.gridScreenOffset > 0 ? '上一页' : '本页首')
          .fontSize(14)
          .fontColor(this.gridScreenOffset > 0 ? FG_HINT : BG_FUNC)
          .padding(8)
          .onClick(() => {
            if (this.gridScreenOffset > 0) {
              const step: number = this.gridPageSize();
              this.gridScreenOffset = Math.max(0, this.gridScreenOffset - step);
              this.expandedListScroller.scrollToIndex(this.gridScreenOffset);
            }
          })
        Text(`${this.gridScreen() + 1}/${this.gridScreenCount()}`)
          .fontSize(12)
          .fontColor(FG_HINT)
          .padding(8)
        Text(this.gridScreenOffset + this.gridPageSize() < this.pagedCandidates().length ? '下一页' : '本页末')
          .fontSize(14)
          .fontColor(this.gridScreenOffset + this.gridPageSize() < this.pagedCandidates().length ? FG_HINT : BG_FUNC)
          .padding(8)
          .onClick(() => {
            if (this.gridScreenOffset + this.gridPageSize() < this.pagedCandidates().length) {
              const step: number = this.gridPageSize();
              this.gridScreenOffset = this.gridScreenOffset + step;
              this.expandedListScroller.scrollToIndex(this.gridScreenOffset);
            }
          })
        Text('取消')
          .fontSize(14)
          .fontColor(FG_HINT)
          .padding(8)
          .onClick(() => {
            keyboardController.clear();
            this.setExpanded(false);
          })
        Text('收起')
          .fontSize(14)
          .fontColor(FG_HINT)
          .padding(8)
          .onClick(() => {
            this.setExpanded(false);
          })
      }
      .height(36)
      .justifyContent(FlexAlign.Center)
    }
    .width('100%')
    .layoutWeight(1)
    .backgroundColor(BG_BAR)
    // H-257(CodeArts): 去掉 SwipeGesture——List 自带丝滑滚动手势
  }

  @Builder
  AboutPanel() {
    Scroll() {
      Column({ space: 10 }) {
        // 标题
        Text('三生输入法')
          .fontSize(22)
          .fontWeight(FontWeight.Bold)
          .fontColor(FG_TEXT)
          .textAlign(TextAlign.Center)
          .width('100%')

        Text('HarmonyOS · 五笔 · 拼音 · 英文三向混输')
          .fontSize(12)
          .fontColor(FG_HINT)
          .textAlign(TextAlign.Center)
          .width('100%')

        Divider().color(BG_FUNC)

        // 开源许可
        Text('开源许可')
          .fontSize(16)
          .fontWeight(FontWeight.Bold)
          .fontColor(FG_TEXT)
          .width('100%')

        Text('本软件基于 Apache License 2.0 开源。')
          .fontSize(13)
          .fontColor(FG_TEXT)
          .width('100%')

        Text('Copyright 2026 Lucas Y.C. Wang')
          .fontSize(12)
          .fontColor(FG_HINT)
          .width('100%')

        Divider().color(BG_FUNC)

        // 词库来源
        Text('词库来源')
          .fontSize(16)
          .fontWeight(FontWeight.Bold)
          .fontColor(FG_TEXT)
          .width('100%')

        Row({ space: 6 }) {
          Text('CC-CEDICT')
            .fontSize(13)
            .fontWeight(FontWeight.Bold)
            .fontColor(FG_TEXT)
            .layoutWeight(1)
          Text('CC BY-SA 4.0')
            .fontSize(11)
            .fontColor(FG_ACCENT)
        }
        .width('100%')
        Text('中英互译词库')
          .fontSize(11)
          .fontColor(FG_HINT)
          .width('100%')

        Row({ space: 6 }) {
          Text('ECDICT')
            .fontSize(13)
            .fontWeight(FontWeight.Bold)
            .fontColor(FG_TEXT)
            .layoutWeight(1)
          Text('MIT')
            .fontSize(11)
            .fontColor(FG_ACCENT)
        }
        .width('100%')
        Text('英中翻译词库')
          .fontSize(11)
          .fontColor(FG_HINT)
          .width('100%')

        Row({ space: 6 }) {
          Text('rime-wubi86-jidian')
            .fontSize(13)
            .fontWeight(FontWeight.Bold)
            .fontColor(FG_TEXT)
            .layoutWeight(1)
          Text('Apache-2.0')
            .fontSize(11)
            .fontColor(FG_ACCENT)
        }
        .width('100%')
        Text('86 五笔码表')
          .fontSize(11)
          .fontColor(FG_HINT)
          .width('100%')

        Row({ space: 6 }) {
          Text('rime-pinyin-simp')
            .fontSize(13)
            .fontWeight(FontWeight.Bold)
            .fontColor(FG_TEXT)
            .layoutWeight(1)
          Text('Apache-2.0')
            .fontSize(11)
            .fontColor(FG_ACCENT)
        }
        .width('100%')
        Text('简拼方案')
          .fontSize(11)
          .fontColor(FG_HINT)
          .width('100%')

        Row({ space: 6 }) {
          Text('OpenCC')
            .fontSize(13)
            .fontWeight(FontWeight.Bold)
            .fontColor(FG_TEXT)
            .layoutWeight(1)
          Text('Apache-2.0')
            .fontSize(11)
            .fontColor(FG_ACCENT)
        }
        .width('100%')
        Text('简繁转换')
          .fontSize(11)
          .fontColor(FG_HINT)
          .width('100%')

        Divider().color(BG_FUNC)

        // 隐私声明
        Text('隐私声明')
          .fontSize(16)
          .fontWeight(FontWeight.Bold)
          .fontColor(FG_TEXT)
          .width('100%')

        Text('本应用所有数据处理均在本地完成，不联网、不上传任何用户数据。')
          .fontSize(13)
          .fontColor(FG_TEXT)
          .width('100%')

        Divider().color(BG_FUNC)

        // 完整声明指引
        Text('完整许可声明可在关于页面查看。')
          .fontSize(12)
          .fontColor(FG_HINT)
          .width('100%')

        // 返回按钮
        Text('返回键盘')
          .fontSize(16)
          .fontColor(FG_ACCENT)
          .textAlign(TextAlign.Center)
          .width('100%')
          .padding(12)
          .backgroundColor(BG_KEY)
          .borderRadius(RADIUS)
          .margin({ top: 8 })
          .onClick(() => {
            this.showAbout = false;
          })
      }
      .width('100%')
      .padding({ left: 16, right: 16, top: 12, bottom: 12 })
    }
    .width('100%')
    .layoutWeight(1)
    .scrollBar(BarState.Auto)
    .backgroundColor(BG_PANEL)
  }

  @Builder
  LetterKey(ch: string) {
    Stack() {
      Column() {
        Text(this.shiftActive() ? ch.toUpperCase() : ch)
          // H-241 契约 §3-3「键面字母字号」（16–26，默认 20＝原写死值）。
          // 这一处和下面 T9Key 的数字面**必须同一个值**，漏一处就是「九键那半没跟着变」。
          .fontSize(this.keyFs)
          .fontColor(TEXT_KEY)
          .textAlign(TextAlign.Center)
        // H-155：a/x/c/v 编辑动作键——键面小字标注功能名（全选/剪切/复制/粘贴）
        if (this.funcLabel(ch) !== '') {
          Text(this.funcLabel(ch))
            .fontSize(9)
            .fontColor(TEXT_FUNC)
        }
      }
      .justifyContent(FlexAlign.Center)
      if (this.getAltChar(ch) !== '') {
        Text(this.getAltChar(ch))
          .fontSize(10)
          .fontColor(FG_HINT)
          .position({ x: 4, y: 2 })
      }
      // H-215(Qoder)：气泡**不再嵌在键 Stack 里**——键内定位在 IME 子窗口不可控
      // （百分比成环 / offset.x、translate.x 被吞 / 像素 position 只部分生效，
      // 详见 bubbleGeom 注释①②）。改画 build() 顶层，见 LongPressBubble。
    }
    // H-220(Qoder)：n = 「选择」开关，模式开着时键面用激活底色，和 ⇆ 面板里的状态一致。
    .backgroundColor(ch === 'n' && this.selMode ? BG_ACTIVE :
      (this.isEditorActionKey(ch) ? BG_FUNC : this.keyBg(BG_KEY, `letter_${ch}`)))
    .borderRadius(RADIUS)
    .layoutWeight(1)
    .height(this.keyH())
    .margin(KEY_MARGIN)
    // H-215(Qoder)：回填实测键宽 + 键全局坐标（vp，窗口系），供顶层长按气泡定锚。
    .onAreaChange((_oldV: Area, newV: Area) => {
      const w: number = newV.width as number;
      if (w > 0) {
        this.keyWidthVp = w;
      }
      const gp: Position = newV.globalPosition as Position;
      const gx: number = gp.x as number;
      if (!Number.isNaN(gx) && w > 0) {
        this.letterKeyGlobalPos.set(ch, gp);
        if (ch === 'q') {
          console.info(`${TAG} H-215 key q global x=${gx} y=${gp.y as number} w=${w}`);
        }
      }
    })
    .onTouch((event: TouchEvent) => {
      if (event.type === TouchType.Down) {
        this.pressKey(`letter_${ch}`);
        this.letterTouchDownY = this.evY(event);
        this.letterLastY = this.letterTouchDownY;
        this.letterPeakY = this.letterTouchDownY;
        this.letterBottomY = this.letterTouchDownY;
        this.swipeAltDone = false;
        this.editorActionDone = false;
        this.bubbleUpSwallow = false;
        this.longPressSymIdx = -1;
        this.bubbleTouched = false;
        // H-221(Qoder)：新的按下必须先掐掉上一把键可能残留的方向连发（ belt-and-braces：
        // 抬手/Cancel 已经各停一次，这里兜底，绝不允许「按一下 h 之后打字光标自己乱走」）。
        this.stopDirRepeat();
        // H-215(Qoder)：出泡计时（450ms，与手势同阈值）——只给「有符号集且非编辑动作键」
        // H-241 契约 §3-6/§3-7：阈值改读「长按触发时长」（与下面兜底手势同一个值），
        // 「按键时弹出字符」关掉时这里**不起计时**（也就不会有气泡去接管松手，键回到纯点按）。
        this.letterTouchDownX = event.touches.length > 0 ? (event.touches[0].windowX as number) : -1;
        this.letterHeld = true;
        if (this.popupOnPress && this.getHiddenSymbols(ch).length > 0 && !this.isEditorActionKey(ch)) {
          if (this.bubbleTimer >= 0) {
            clearTimeout(this.bubbleTimer);
          }
          this.bubbleTimer = setTimeout(() => {
            this.bubbleTimer = -1;
            // 仍按住（Up 未发生；滑进气泡引来的 Cancel 不算松手）且没滑过才出泡
            if (this.letterHeld && !this.swipeAltDone && !this.editorActionDone
              && this.longPressLetter === '') {
              this.longPressLetter = ch;
              // H-216(CodeArts)：出泡不预选——主人「不上滑选气泡的话松手不要上屏」
              // longPressSymIdx = -1 ⇒ 不滑进气泡松手=取消不上屏；滑进气泡才选中并上屏
              this.longPressSymIdx = -1;
              this.bubbleEntered = false;
              this.bubbleTouched = false;
              console.info(`${TAG} H-215 timer open bubble ${ch}`);
            }
          }, this.longPressDelayMs > 0 ? this.longPressDelayMs : 450);
        }
      } else if (event.type === TouchType.Move) {
        this.letterLastY = this.evY(event);
        // H-165(Qoder)：持续记录最高点（displayY 越小越靠上）与最低点
        if (this.letterLastY >= 0) {
          if (this.letterPeakY < 0 || this.letterLastY < this.letterPeakY) {
            this.letterPeakY = this.letterLastY;
          }
          if (this.letterLastY > this.letterBottomY) {
            this.letterBottomY = this.letterLastY;
          }
        }
        // H-221(Qoder)：连发期间手指**明显滑开**（>30vp，与键面滑动出次级字符同阈值）即停——
        // 抖动不会打断（同阈值），他一滑手就是要出角标/大写/进气泡，方向连发该让路。
        if (this.dirRepeatCh === ch && this.letterTouchDownY >= 0 && this.letterLastY >= 0) {
          const moved: number = Math.max(this.letterTouchDownY - this.letterPeakY,
            this.letterBottomY - this.letterTouchDownY);
          if (moved > 30) {
            this.stopDirRepeat();
            console.info(`${TAG} H-221 hold ${ch} 滑开 ${moved}vp -> 停连发`);
          }
        }
        // 长按气泡态：手指仍在键面上时由键处理（windowX 与气泡 .position 同系）
        if (this.longPressLetter === ch && this.getHiddenSymbols(ch).length > 0 && event.touches.length > 0) {
          this.bubbleTouchMove(event.touches[0].windowX as number);
        }
      } else if (event.type === TouchType.Up) {
        this.releaseKey(`letter_${ch}`);
        this.letterHeld = false;
        this.stopDirRepeat();   // H-221(Qoder)：撒手＝立刻停连发
        if (this.bubbleTimer >= 0) {
          clearTimeout(this.bubbleTimer);
          this.bubbleTimer = -1;
        }
        const upY: number = this.evY(event) >= 0 ? this.evY(event) : this.letterLastY;
        // H-165(Qoder)：上滑位移用「本次按下到达的最高点」算，不用 Up 时刻坐标——
        // Up 可能被重定向到别的组件，但 Move 期间的最高点是可信的。
        const peakY: number = (this.letterPeakY >= 0) ? this.letterPeakY : upY;
        const bottomY: number = (this.letterBottomY >= 0) ? this.letterBottomY : upY;
        const upDy: number = (this.letterTouchDownY >= 0 && peakY >= 0) ? (this.letterTouchDownY - peakY) : 0;
        const downDy: number = (this.letterTouchDownY >= 0 && bottomY >= 0) ? (bottomY - this.letterTouchDownY) : 0;
        // 两个方向都超过阈值时按位移大的那个算（防止抖动误判）
        const dy: number = upDy >= downDy ? upDy : -downDy;
        if (this.longPressLetter === ch && this.getHiddenSymbols(ch).length > 0) {
          // 长按气泡态松手（手指未离开键面，键侧先到）：指向某符号 -> 上屏；否则取消。统一关气泡。
          this.bubbleTouchUp();
        } else if (this.bubbleUpSwallow) {
          // H-215(Qoder)：气泡已接管松手（泡侧先处理并关了气泡）⇒ 键侧不再走点键/滑动分支
          console.info(`${TAG} H-215 key ${ch} up swallowed by bubble`);
        } else if (!this.editorActionDone) {
          if (dy > 30) {
            // 上滑：出次级字符（键面右上角小角标，如 q->1、w->2），onTouch 手写检测
            const alt: string = this.getAltChar(ch);
            if (alt !== '') {
              this.typeChar(alt);
              this.swipeAltDone = true;
              console.info(`${TAG} LetterKey swipe up: ${ch} -> ${alt}`);
            }
          } else if (-dy > 30) {
            // 下滑：上屏大写（不碰 shift 状态）
            this.typeChar(ch.toUpperCase());
            this.swipeAltDone = true;
            console.info(`${TAG} LetterKey swipe down: ${ch} -> ${ch.toUpperCase()}`);
          } else {
            this.sendLetter(ch);
          }
        }
        this.letterTouchDownY = -1;
        this.letterPeakY = -1;
        this.letterBottomY = -1;
        this.swipeAltDone = false;
        this.editorActionDone = false;
      } else if (event.type === TouchType.Cancel) {
        this.releaseKey(`letter_${ch}`);
        this.stopDirRepeat();   // H-221(Qoder)：触摸流被别的组件接管（如滑进气泡）＝同样立刻停
        if (this.bubbleTimer >= 0) {
          clearTimeout(this.bubbleTimer);
          this.bubbleTimer = -1;
        }
        this.letterTouchDownY = -1;
        this.letterPeakY = -1;
        this.letterBottomY = -1;
        // H-215(Qoder)：长按气泡已弹出时，手指**上滑进气泡**会让 ArkUI 把触摸流重定向
        // 到气泡 ⇒ 键收到的是 Cancel。此时**绝不能**关气泡（原逻辑一关，泡里松手就没了）。
        // 未出泡的 Cancel（真取消）照旧清理。
        if (this.longPressLetter !== ch) {
          this.longPressLetter = '';
          this.longPressSymIdx = -1;
          this.bubbleTouched = false;
        }
      }
    })
    // H-155：长按（静止不动 450ms）—普通 gesture，优先级低于上面的 priorityGesture(Pan)。
    // 滑动被 Pan 吃掉后 LongPress 不会触发；纯按住才弹气泡/编辑框动作。
    // H-241 契约 §3-6：阈值改读「长按触发时长」——与上面出泡计时器**同一个值**，
    // 否则会出现「按 400ms 出泡、按 500ms 才认编辑动作」这种两套口径。
    // 这里仍是**兜底**（H-215：滑进气泡时手势收不到后续事件，主路是那个计时器）。
    .gesture(
      LongPressGesture({ repeat: false, duration: this.longPressDelayMs > 0 ? this.longPressDelayMs : 450 })
        .onAction(() => {
          // 若本次按下已发生滑动（swipeAltDone 已置位），LongPress 不该再触发编辑动作/气泡——丢弃。
          if (this.swipeAltDone) {
            return;
          }
          if (ch === 'a') {
            keyboardController.sendEditorAction(inputMethodEngine.ExtendAction.SELECT_ALL);
            this.editorActionDone = true;
            console.info(`${TAG} LetterKey longpress a -> SELECT_ALL`);
          } else if (ch === 'x') {
            keyboardController.sendEditorAction(inputMethodEngine.ExtendAction.CUT);
            this.editorActionDone = true;
            console.info(`${TAG} LetterKey longpress x -> CUT`);
          } else if (ch === 'c') {
            // H-204：复制 + 收拢选区 + 可见反馈（主人「复制没反应…全选以后复制完了，
            // 应该退到光标状态，这样能看出来是复制了」）
            keyboardController.copyThenCollapse();
            this.showTip('已复制');
            this.editorActionDone = true;
            console.info(`${TAG} LetterKey longpress c -> COPY + collapse`);
          } else if (ch === 'v') {
            // H-204：应用级输入法不能自己读剪贴板，宿主的 PASTE 又常常没实现
            //（主人实测「粘贴没反应」）⇒ 长按 v 直接打开剪贴板面板，点系统「粘贴」
            // 安全控件（临时授权）即时上屏。不再是死动作。
            // H-205/H-207 真机返工（2026-10-26 20:1x）：这里**不能**置 funcBarPinned——
            // pinned 的语义是「用户想要工具栏常驻」（H-187），而长按 v 只是临时看一眼剪贴板。
            // 置了 pinned 后，只要回到 Idle 工具栏就自动重新展开 ⇒ 键盘每次重开都是 44vp 栏，
            // 空闲态永远回不到 28vp 窄条（真机 d2_home.jpeg 就是这样：工具栏常驻、栏 44vp、
            // 还把 a/x/c/v 的「全选/剪切/复制/粘贴」角标一直亮着）。
            this.setFuncBar(true);
            this.funcSubPanel = 'clipboard';
            this.editorActionDone = true;
            console.info(`${TAG} LetterKey longpress v -> clipboard panel (PasteButton)`);
          } else if (ch === 'h') {
            // H-210(CodeArts) M-247(Qoder)②：长按 h = 光标左移（三生 qwerty h=Left）
            keyboardController.moveEditorCursor(3);
            this.editorActionDone = true;
            this.startDirRepeat(3, 'h');   // H-221(Qoder)：按住不放＝连续左移，直到撒手
            console.info(`${TAG} H-210 LetterKey longpress h -> cursor left`);
          } else if (ch === 'j') {
            // H-220r3(Qoder，主人「下移上移，互换位置」)：j/k 对调 ⇒ **长按 j = 光标上移**（Direction 1=UP）
            keyboardController.moveEditorCursor(1);
            this.editorActionDone = true;
            this.startDirRepeat(1, 'j');   // H-221(Qoder)：按住不放＝连续上移，直到撒手
            console.info(`${TAG} H-220 LetterKey longpress j -> cursor up`);
          } else if (ch === 'k') {
            // H-220r3(Qoder)：**长按 k = 光标下移**（Direction 2=DOWN）
            keyboardController.moveEditorCursor(2);
            this.editorActionDone = true;
            this.startDirRepeat(2, 'k');   // H-221(Qoder)：按住不放＝连续下移，直到撒手
            console.info(`${TAG} H-220 LetterKey longpress k -> cursor down`);
          } else if (ch === 'l') {
            // H-210(CodeArts) M-247(Qoder)②：长按 l = 光标右移（三生 qwerty l=Right）
            keyboardController.moveEditorCursor(4);
            this.editorActionDone = true;
            this.startDirRepeat(4, 'l');   // H-221(Qoder)：按住不放＝连续右移，直到撒手
            console.info(`${TAG} H-210 LetterKey longpress l -> cursor right`);
          } else if (ch === 'm') {
            // H-220r3(Qoder，主人「长按m是删除右边的内容…不是左边那，和退格重复了」)：
            // **长按 m = 删除光标右边的字（Del/删除）**，不再复用退格（onBackspace 删左边，
            // 与实体退格键完全重复）。鸿蒙命名坑：deleteBackwardSync 删的才是光标**后**文。
            keyboardController.deleteAfterCursor();
            this.editorActionDone = true;
            console.info(`${TAG} H-220 LetterKey longpress m -> delete after cursor (Del)`);
          } else if (ch === 'f') {
            // H-226(Qoder，主人「sd只针对行，那么fg就有用了，应该是页首页尾，我们不要翻页」)：
            // 鸿蒙没有「页」——IME Kit 拿不到宿主可视区域。落到全文首（与 ⇆ 面板「全首」同一动作），
            // 不翻页、不滚视图，只挪光标。
            keyboardController.moveCursorToStart();
            this.editorActionDone = true;
            console.info(`${TAG} H-226 LetterKey longpress f -> doc start`);
          } else if (ch === 'g') {
            // H-226(Qoder)：g = 全文尾（同 ⇆ 面板「全尾」格）。
            keyboardController.moveCursorToEnd();
            this.editorActionDone = true;
            console.info(`${TAG} H-226 LetterKey longpress g -> doc end`);
          } else if (ch === 's') {
            // H-220(Qoder，主人「不是全首全尾，是行」)：长按 s = **行首**（安卓 Home 语义），
            // 全文首仍留在 ⇆ 面板「全首」格。算法见 KeyboardController.moveCursorToLineStart。
            keyboardController.moveCursorToLineStart();
            this.editorActionDone = true;
            console.info(`${TAG} H-220 LetterKey longpress s -> line start`);
          } else if (ch === 'd') {
            // H-220(Qoder)：长按 d = **行尾**（安卓 End 语义）；全文尾在面板「全尾」格。
            keyboardController.moveCursorToLineEnd();
            this.editorActionDone = true;
            console.info(`${TAG} H-220 LetterKey longpress d -> line end`);
          } else if (ch === 'n') {
            // H-220(Qoder，主人「安卓里面有个选择键，可以按方向选择文本」)：长按 n = 开/关
            // 「选择」模式——开着时 h/j/k/l（以及面板四向）扩展选区而不是移动光标。
            keyboardController.toggleSelectionMode();
            this.selMode = keyboardController.isSelectionMode();
            this.editorActionDone = true;
            console.info(`${TAG} H-220 LetterKey longpress n -> selection mode`);
          } else {
            // 其余字母：长按弹气泡（符号集非空才弹）
            // H-215(Qoder)：出泡主要由按下时的 bubbleTimer 负责（手指滑进气泡后
            // LongPressGesture 收不到后续事件）；此处兜底，已出泡则跳过。
            // H-241 契约 §3-7：兜底路径同样受「按键时弹出字符」控制（两处读取点同一开关）。
            if (this.popupOnPress && this.getHiddenSymbols(ch).length > 0 && this.longPressLetter === '') {
              this.longPressLetter = ch;
              this.longPressSymIdx = -1;             // H-216(CodeArts)：兜底路径同样不预选
              this.bubbleEntered = false;
              this.bubbleTouched = false;
              console.info(`${TAG} LetterKey longpress ${ch} -> bubble`);
            }
          }
        })
    )
  }

  /** H-218r2/H-218r3（主人「展开铺到键盘上」→「布局太乱了，你不能看看安卓吗」）：
   *  ⇆ 面板接管整个键区——TextEditPad full 模式，均匀网格、全满无空格、
   *  无浮动角标（r2 的 ‹ 角标压住「下页」被真机铁证，r3 起退出=顶栏 ‹）。
   *  **高度必须等于键区预算（4×rowHeight），不是 5×**（H-218r4 自查，Qoder 15:1x）：
   *  窗口高 = barVp(44) + ROW_COUNT(4)×rowVp(48) = 236vp，且 H-208 起**恒定不伸缩**
   *  （伸缩会让整块键盘一蹦一跳，主人骂过）。我 r3 传 5×48=240vp ⇒ 内容 44+240=284vp
   *  超窗 48vp ⇒ **第 5 行「选择」整行被裁到窗口外**（H-213 同款：888px 内容进 874px 窗口丢末行）。
   *  这也解释了主人为什么看不见选择键。现在 5 行挤进 192vp 预算（行高 35.2vp，见 ToolPanels.cellH）。 */
  @Builder
  TextEditGridPanel() {
    TextEditPad({
      full: true,
      panelHeight: this.rowHeight * 4,
      rows: 5,
      selOn: this.selMode,
      onExitRequest: () => {
        this.funcSubPanel = '';   // 只退子面板，工具栏保持展开
      }
    })
  }

  @Builder
  QwertyPanel() {
    Column() {
      Row() {
        ForEach(LETTER_ROW_1, (ch: string, index: number) => {
          this.LetterKey(ch);
        }, (ch: string, index: number) => `q1_${index}_${ch}`)
      }
      Row() {
        ForEach(LETTER_ROW_2, (ch: string, index: number) => {
          this.LetterKey(ch);
        }, (ch: string, index: number) => `q2_${index}_${ch}`)
      }
      .padding({ left: 14, right: 14 })
      Row() {
        // H-063（M-050）：⇧ 字形换 SymbolGlyph（sys.symbol.arrow_up）——图标色随激活态走 FG_ACCENT/TEXT_FUNC，
        // 底色激活通道不变（BG_ACTIVE/按下色优先）；onTouch/onClick/keyId 与 M-049 体系原样保留
        Stack() {
          SymbolGlyph($r('sys.symbol.arrow_up'))
            .fontSize(FUNC_ICON_SIZE)
            .fontColor([this.shiftActive() ? FG_ACCENT : TEXT_FUNC])
        }
        .backgroundColor(this.pressedKey === 'shift' ? BG_PRESSED : (this.shiftActive() ? BG_ACTIVE : BG_FUNC))
        .borderRadius(RADIUS)
        .layoutWeight(1.4)
        .height(this.keyH())
        .margin(KEY_MARGIN)
        .onClick(() => {
          this.handleShift();
        })
        .onTouch((event: TouchEvent) => {
          // M-049（H-062）：按下色优先于激活色（shiftActive 仍在，抬手后恢复）
          if (event.type === TouchType.Down) {
            this.pressKey('shift');
          } else if (event.type === TouchType.Up || event.type === TouchType.Cancel) {
            this.releaseKey('shift');
          }
        })
        ForEach(LETTER_ROW_3, (ch: string, index: number) => {
          this.LetterKey(ch);
        }, (ch: string, index: number) => `q3_${index}_${ch}`)
        // H-063（M-050）：⌫ 字形换 SymbolGlyph（sys.symbol.delete_left）；
        // M-049 退格状态机：短按删 1 字、长按 500ms 清空全部（H-167）。
        // H-175：上下滑接回（主人 2026-10-25 16:0x 点名要，语义同 H-166 真机验过的版本）：
        //   上滑＝清除到上一个分隔符（clearToLastSeparator）
        //   下滑＝撤销最近一次上屏/清除（undoLastAction）
        Stack() {
          SymbolGlyph($r('sys.symbol.delete_left'))
            .fontSize(FUNC_ICON_SIZE)
            .fontColor([TEXT_FUNC])
        }
        .backgroundColor(this.keyBg(BG_FUNC, 'bs_row'))
        .borderRadius(RADIUS)
        .layoutWeight(1.4)
        .height(this.keyH())
        .margin(KEY_MARGIN)
        .onTouch((event: TouchEvent) => {
          if (event.type === TouchType.Down) {
            this.pressKey('bs_row');
            // 长按 500ms 由 startBackspaceRepeat 内 clearAllContent 清空；未触发长按则短按补删 1 字
            this.startBackspaceRepeat();
            this.bsClearAllFired = false;   // H-206：每次按下重新记账
            this.bsTouchDownY = this.evY(event);
            this.bsLastY = this.bsTouchDownY;
            this.bsPeakY = this.bsTouchDownY;
            this.bsBottomY = this.bsTouchDownY;
          } else if (event.type === TouchType.Move) {
            this.bsLastY = this.evY(event);
            if (this.bsLastY >= 0) {
              if (this.bsPeakY < 0 || this.bsLastY < this.bsPeakY) {
                this.bsPeakY = this.bsLastY;
              }
              if (this.bsLastY > this.bsBottomY) {
                this.bsBottomY = this.bsLastY;
              }
              // H-206：位移一超过「滑动意图」阈值（20vp，比手势判据 30vp 早一档）就撤掉长按
              // 定时器——滑动过程中不该发生清空，否则后面的撤销只是在还原这次自己造的清空。
              const moved: number = Math.max(
                this.bsTouchDownY - (this.bsPeakY >= 0 ? this.bsPeakY : this.bsTouchDownY),
                this.bsBottomY - this.bsTouchDownY);
              if (moved > 20 && this.bsDelay >= 0) {
                clearTimeout(this.bsDelay);
                this.bsDelay = -1;
                console.info(`${TAG} H-206 bs_row 滑动中撤销长按清空 dy=${moved.toFixed(1)}`);
              }
            }
          } else if (event.type === TouchType.Up || event.type === TouchType.Cancel) {
            this.releaseKey('bs_row');
            this.stopBackspaceRepeat();
            // H-175：上下滑判定（与字母键同款算法——Up 被重定向也用 Move 期间的峰值，位移取大者判向）
            const upY: number = this.evY(event) >= 0 ? this.evY(event) : this.bsLastY;
            const bsPeak: number = (this.bsPeakY >= 0) ? this.bsPeakY : upY;
            const bsBottom: number = (this.bsBottomY >= 0) ? this.bsBottomY : upY;
            const bsUpDy: number = (this.bsTouchDownY >= 0 && bsPeak >= 0) ? (this.bsTouchDownY - bsPeak) : 0;
            const bsDownDy: number = (this.bsTouchDownY >= 0 && bsBottom >= 0) ? (bsBottom - this.bsTouchDownY) : 0;
            if (bsUpDy > 30 && bsUpDy >= bsDownDy) {
              // 上滑：清除到上一个分隔符（onTouch 手写检测，PanGesture 在本 IME 面板不触发）
              this.healAccidentalClearAll();   // H-206：先还原本次按下里已发生的清空
              keyboardController.clearToLastSeparator();
              console.info(`${TAG} bs_row swipe up: clearToLastSeparator dy=${bsUpDy.toFixed(1)}`);
              this.bsTouchDownY = -1;
              this.bsPeakY = -1;
              this.bsBottomY = -1;
              return;
            }
            if (bsDownDy > 30) {
              // 下滑：撤销最近一次上屏/清除
              this.healAccidentalClearAll();   // H-206：不先还原就会「多恢复一遍」
              keyboardController.undoLastAction();
              console.info(`${TAG} bs_row swipe down: undoLastAction dy=${bsDownDy.toFixed(1)}`);
              this.bsTouchDownY = -1;
              this.bsPeakY = -1;
              this.bsBottomY = -1;
              return;
            }
            this.bsTouchDownY = -1;
            this.bsPeakY = -1;
            this.bsBottomY = -1;
            // 长按已清空则跳过；否则补一次短按退格（删 1 字）
            if (!this.bsRepeatStarted) {
              this.backChar();
            }
          }
        })
      }
    }
    .width('100%')
  }

  @Builder
  T9Key(num: string, label: string) {
    Column() {
      Text(num)
        // H-241 契约 §3-3：九键数字面与 26 键字母面共用「键面字母字号」（两处读取点同值）。
        .fontSize(this.keyFs)
        .fontColor(TEXT_KEY)
      if (label.length > 0) {
        Text(label)
          .fontSize(9)
          .fontColor(FG_HINT)
      }
    }
    .justifyContent(FlexAlign.Center)
    .alignItems(HorizontalAlign.Center)
    .backgroundColor(this.keyBg(BG_KEY, `t9_${num}`))
    .borderRadius(RADIUS)
    .layoutWeight(1)
    .height(this.keyH())
    .margin(KEY_MARGIN)
    .onClick(() => {
      this.typeChar(num);
    })
    .onTouch((event: TouchEvent) => {
      // M-049（H-062）：只做按下态+振动，T9 上屏仍走 onClick（不重复触发）
      if (event.type === TouchType.Down) {
        this.pressKey(`t9_${num}`);
      } else if (event.type === TouchType.Up || event.type === TouchType.Cancel) {
        this.releaseKey(`t9_${num}`);
      }
    })
}

@Builder
T9Panel() {
  Column() {
    Row() {
      this.T9Key(T9_NUM[0], T9_LABEL[0]);
      this.T9Key(T9_NUM[1], T9_LABEL[1]);
      this.T9Key(T9_NUM[2], T9_LABEL[2]);
    }
    Row() {
      this.T9Key(T9_NUM[3], T9_LABEL[3]);
      this.T9Key(T9_NUM[4], T9_LABEL[4]);
      this.T9Key(T9_NUM[5], T9_LABEL[5]);
    }
    Row() {
      this.T9Key(T9_NUM[6], T9_LABEL[6]);
      this.T9Key(T9_NUM[7], T9_LABEL[7]);
      this.T9Key(T9_NUM[8], T9_LABEL[8]);
    }
  }
  .width('100%')
}

  @Builder
  NumpadKey(num: string) {
    Text(num)
      .fontSize(24)
      .fontColor(TEXT_KEY)
      .textAlign(TextAlign.Center)
      .backgroundColor(this.keyBg(BG_KEY, `numpad_${num}`))
      .borderRadius(RADIUS)
      .layoutWeight(2.33)
      .height('100%')
      .margin(KEY_MARGIN)
      .onClick(() => {
        this.typeChar(num);
      })
      .onTouch((event: TouchEvent) => {
        if (event.type === TouchType.Down) {
          this.pressKey(`numpad_${num}`);
        } else if (event.type === TouchType.Up || event.type === TouchType.Cancel) {
          this.releaseKey(`numpad_${num}`);
        }
      })
  }


  @Builder
  NumpadPanel() {
    Column() {
      Row() {
        Text('+')
          .fontSize(20)
          .fontColor(TEXT_KEY)
          .textAlign(TextAlign.Center)
          .backgroundColor(this.keyBg(BG_KEY, 'np_plus'))
          .borderRadius(RADIUS)
          .layoutWeight(1.5)
          .height('100%')
          .margin(KEY_MARGIN)
          .onClick(() => { this.typeChar('+'); })
          .onTouch((event: TouchEvent) => {
            if (event.type === TouchType.Down) { this.pressKey('np_plus'); }
            else if (event.type === TouchType.Up || event.type === TouchType.Cancel) { this.releaseKey('np_plus'); }
          })
        this.NumpadKey('1')
        this.NumpadKey('2')
        this.NumpadKey('3')
        Text('/')
          .fontSize(20)
          .fontColor(TEXT_KEY)
          .textAlign(TextAlign.Center)
          .backgroundColor(this.keyBg(BG_KEY, 'np_slash'))
          .borderRadius(RADIUS)
          .layoutWeight(1.5)
          .height('100%')
          .margin(KEY_MARGIN)
          .onClick(() => { this.typeChar('/'); })
          .onTouch((event: TouchEvent) => {
            if (event.type === TouchType.Down) { this.pressKey('np_slash'); }
            else if (event.type === TouchType.Up || event.type === TouchType.Cancel) { this.releaseKey('np_slash'); }
          })
      }
      .layoutWeight(1)

      Row() {
        Text('-')
          .fontSize(20)
          .fontColor(TEXT_KEY)
          .textAlign(TextAlign.Center)
          .backgroundColor(this.keyBg(BG_KEY, 'np_minus'))
          .borderRadius(RADIUS)
          .layoutWeight(1.5)
          .height('100%')
          .margin(KEY_MARGIN)
          .onClick(() => { this.typeChar('-'); })
          .onTouch((event: TouchEvent) => {
            if (event.type === TouchType.Down) { this.pressKey('np_minus'); }
            else if (event.type === TouchType.Up || event.type === TouchType.Cancel) { this.releaseKey('np_minus'); }
          })
        this.NumpadKey('4')
        this.NumpadKey('5')
        this.NumpadKey('6')
        Text('空')
          .fontSize(16)
          .fontColor(TEXT_KEY)
          .textAlign(TextAlign.Center)
          .backgroundColor(this.keyBg(BG_KEY, 'np_space'))
          .borderRadius(RADIUS)
          .layoutWeight(1.5)
          .height('100%')
          .margin(KEY_MARGIN)
          .onClick(() => { this.typeChar(' '); })
          .onTouch((event: TouchEvent) => {
            if (event.type === TouchType.Down) { this.pressKey('np_space'); }
            else if (event.type === TouchType.Up || event.type === TouchType.Cancel) { this.releaseKey('np_space'); }
          })
      }
      .layoutWeight(1)

      Row() {
        Text('*')
          .fontSize(20)
          .fontColor(TEXT_KEY)
          .textAlign(TextAlign.Center)
          .backgroundColor(this.keyBg(BG_KEY, 'np_star'))
          .borderRadius(RADIUS)
          .layoutWeight(1.5)
          .height('100%')
          .margin(KEY_MARGIN)
          .onClick(() => { this.typeChar('*'); })
          .onTouch((event: TouchEvent) => {
            if (event.type === TouchType.Down) { this.pressKey('np_star'); }
            else if (event.type === TouchType.Up || event.type === TouchType.Cancel) { this.releaseKey('np_star'); }
          })
        this.NumpadKey('7')
        this.NumpadKey('8')
        this.NumpadKey('9')
        Stack() {
          SymbolGlyph($r('sys.symbol.delete_left'))
            .fontSize(FUNC_ICON_SIZE)
            .fontColor([TEXT_FUNC])
        }
        .backgroundColor(this.keyBg(BG_FUNC, 'bs_num'))
        .borderRadius(RADIUS)
        .layoutWeight(1.5)
        .height('100%')
        .margin(KEY_MARGIN)
        .onTouch((event: TouchEvent) => {
          if (event.type === TouchType.Down) {
            this.pressKey('bs_num');
            this.startBackspaceRepeat();
          } else if (event.type === TouchType.Up || event.type === TouchType.Cancel) {
            this.releaseKey('bs_num');
            const repeated: boolean = this.bsRepeatStarted;
            this.stopBackspaceRepeat();
            if (!repeated) {
              this.backChar();
            }
          }
        })
      }
      .layoutWeight(1)

      Row() {
        Text('ABC')
          .fontSize(16)
          .fontColor(TEXT_FUNC)
          .textAlign(TextAlign.Center)
          .backgroundColor(this.keyBg(BG_FUNC, 'np_abc'))
          .borderRadius(RADIUS)
          .layoutWeight(1.5)
          .height('100%')
          .margin(KEY_MARGIN)
          // H-081 续：ABC 字面=字母键盘，一律回 26 键（不回 prevPanelMode，避免九键→?123→ABC→又回九键死循环）
          .onClick(() => { keyboardController.clear(); this.switchPanelMode('qwerty'); })
          .onTouch((event: TouchEvent) => {
            if (event.type === TouchType.Down) { this.pressKey('np_abc'); }

          })
        Text(',')
          .fontSize(16)
          .fontColor(TEXT_KEY)
          .textAlign(TextAlign.Center)
          .backgroundColor(this.keyBg(BG_KEY, 'np_comma'))
          .borderRadius(RADIUS)
          .layoutWeight(1.0)
          .height('100%')
          .margin(KEY_MARGIN)
          .onClick(() => { this.typeChar(','); })
          .onTouch((event: TouchEvent) => {
            if (event.type === TouchType.Down) { this.pressKey('np_comma'); }
            else if (event.type === TouchType.Up || event.type === TouchType.Cancel) { this.releaseKey('np_comma'); }
          })
        Text('!?#')
          .fontSize(14)
          .fontColor(TEXT_FUNC)
          .textAlign(TextAlign.Center)
          .backgroundColor(this.keyBg(BG_FUNC, 'np_sym'))
          .borderRadius(RADIUS)
          .layoutWeight(1.0)
          .height('100%')
          .margin(KEY_MARGIN)
          .onClick(() => { this.switchPanelMode('symbol'); })
          .onTouch((event: TouchEvent) => {
            if (event.type === TouchType.Down) { this.pressKey('np_sym'); }
            else if (event.type === TouchType.Up || event.type === TouchType.Cancel) { this.releaseKey('np_sym'); }
          })
        this.NumpadKey('0')
        Text('=')
          .fontSize(16)
          .fontColor(TEXT_KEY)
          .textAlign(TextAlign.Center)
          .backgroundColor(this.keyBg(BG_KEY, 'np_eq'))
          .borderRadius(RADIUS)
          .layoutWeight(1.0)
          .height('100%')
          .margin(KEY_MARGIN)
          .onClick(() => { this.typeChar('='); })
          .onTouch((event: TouchEvent) => {
            if (event.type === TouchType.Down) { this.pressKey('np_eq'); }
            else if (event.type === TouchType.Up || event.type === TouchType.Cancel) { this.releaseKey('np_eq'); }
          })
        Text('.')
          .fontSize(16)
          .fontColor(TEXT_KEY)
          .textAlign(TextAlign.Center)
          .backgroundColor(this.keyBg(BG_KEY, 'np_dot'))
          .borderRadius(RADIUS)
          .layoutWeight(1.0)
          .height('100%')
          .margin(KEY_MARGIN)
          .onClick(() => { this.typeChar('.'); })
          .onTouch((event: TouchEvent) => {
            if (event.type === TouchType.Down) { this.pressKey('np_dot'); }
            else if (event.type === TouchType.Up || event.type === TouchType.Cancel) { this.releaseKey('np_dot'); }
          })
        Stack() {
          SymbolGlyph($r('sys.symbol.return_down_left'))
            .fontSize(FUNC_ICON_SIZE)
            .fontColor(['#FFFFFF'])
        }
        .backgroundColor(this.pressedKey === 'np_enter' ? BG_PRESSED : BG_ENTER)
        .borderRadius(this.keyH() / 2)
        .layoutWeight(1.5)
        .height('100%')
        .margin(KEY_MARGIN)
        .onClick(() => { this.typeChar('Enter'); })
        .onTouch((event: TouchEvent) => {
          if (event.type === TouchType.Down) { this.pressKey('np_enter'); }
          else if (event.type === TouchType.Up || event.type === TouchType.Cancel) { this.releaseKey('np_enter'); }
        })
      }
      .layoutWeight(1)
    }
    .width('100%')
    .layoutWeight(1)
  }

  @Builder

  SymbolPanel() {
    Column() {
      Scroll() {
        Row() {
          ForEach(SYMBOL_CATEGORIES, (cat: SymbolCategory, index: number) => {
            Text(cat.groupId === '' ? (this.showSymbolAll ? '折叠' : '全') : cat.label)
              .fontSize(14)
              .fontColor(cat.groupId === this.activeSymbolGroupId ? FG_ACCENT :
                (cat.groupId === '' && this.showSymbolAll ? FG_ACCENT : FG_HINT))
              .fontWeight(cat.groupId === this.activeSymbolGroupId ||
                (cat.groupId === '' && this.showSymbolAll) ? FontWeight.Bold : FontWeight.Normal)
              .textAlign(TextAlign.Center)
              .height('100%')
              .padding({ left: 8, right: 8 })
              .onClick(() => {
                if (cat.groupId === '') {
                  this.showSymbolAll = !this.showSymbolAll;
                } else {
                  this.showSymbolAll = false;
                  const idx: number = this.flatFirstIndex(cat.groupId);
                  if (idx >= 0) {
                    this.symbolScroller.scrollToIndex(idx, false);
                  }
                }
              })
          }, (cat: SymbolCategory, index: number) => `symcat_${index}_${cat.groupId}`)
        }
        .width('100%')
        .height('100%')
      }
      .scrollable(ScrollDirection.Horizontal)
      .scrollBar(BarState.Off)
      .width('100%')
      .height(28)
      .backgroundColor(BG_FUNC)

      if (this.showSymbolAll) {
        Scroll() {
          Column() {
            ForEach(this.symbolGroups, (g: SymbolGroup, index: number) => {
              Row() {
                Text(g.label)
                  .fontSize(16)
                  .fontColor(g.id === this.activeSymbolGroupId ? FG_ACCENT : FG_TEXT)
                  .fontWeight(g.id === this.activeSymbolGroupId ? FontWeight.Bold : FontWeight.Normal)
                  .maxLines(1)
                  .textOverflow({ overflow: TextOverflow.Ellipsis })
                Blank()
                Text(`${g.items.length}项`)
                  .fontSize(12)
                  .fontColor(FG_HINT)
              }
              .width('100%')
              .alignItems(VerticalAlign.Center)
              .padding({ left: 16, right: 16, top: 10, bottom: 10 })
              .onClick(() => {
                this.activeSymbolGroupId = g.id;
                this.showSymbolAll = false;
                this.symbolPage = 0;
                const idx: number = this.flatFirstIndex(g.id);
                if (idx >= 0) {
                  setTimeout(() => {
                    this.symbolScroller.scrollToIndex(idx, false);
                  }, 50);
                }
              })
            }, (g: SymbolGroup, index: number) => `symall_${index}_${g.id}`)
          }
          .width('100%')
        }
        .width('100%')
        .layoutWeight(1)
        .clip(true)
        .scrollBar(BarState.Auto)
      } else {
        List({ scroller: this.symbolScroller }) {
          ForEach(this.symbolPages, (fp: FlatPage, index: number) => {
            ListItem() {
              Column() {
                if (index === 0) {
                  Row() {
                    ForEach(DIGIT_ROW, (num: string, dIdx: number) => {
                      Text(num)
                        .fontSize(20)
                        .fontColor(TEXT_KEY)
                        .textAlign(TextAlign.Center)
                        .padding({ bottom: 3 })
                        .backgroundColor(this.keyBg(BG_KEY, `digit_${num}`))
                        .borderRadius(RADIUS)
                        .layoutWeight(1)
                        .height('100%')
                        .onClick(() => {
                          this.typeChar(num);
                        })
                        .onTouch((event: TouchEvent) => {
                          if (event.type === TouchType.Down) {
                            this.pressKey(`digit_${num}`);
                          } else if (event.type === TouchType.Up || event.type === TouchType.Cancel) {
                            this.releaseKey(`digit_${num}`);
                          }
                        })
                    }, (num: string, dIdx: number) => `sd_${index}_${num}`)
                  }
                  .width('100%')
                  .layoutWeight(1)
                }

                Row() {
                  ForEach(this.symbolRowItems(fp.groupId, fp.page, 2), (ch: string, sIdx: number) => {
                    Text(ch)
                      .fontSize(20)
                      .fontColor(TEXT_KEY)
                      .textAlign(TextAlign.Center)
                      .padding({ bottom: 3 })
                      .backgroundColor(this.keyBg(BG_KEY, `sym_${ch}`))
                      .borderRadius(RADIUS)
                      .layoutWeight(1)
                      .height('100%')
                      .onClick(() => {
                        this.typeChar(ch);
                      })
                      .onTouch((event: TouchEvent) => {
                        if (event.type === TouchType.Down) {
                          this.pressKey(`sym_${ch}`);
                        } else if (event.type === TouchType.Up || event.type === TouchType.Cancel) {
                          this.releaseKey(`sym_${ch}`);
                        }
                      })
                  }, (ch: string, sIdx: number) => `sr2_${index}_${sIdx}_${ch}`)
                }
                .width('100%')
                .layoutWeight(1)

                Row() {
                  ForEach(this.symbolRowItems(fp.groupId, fp.page, 3), (ch: string, sIdx: number) => {
                    Text(ch)
                      .fontSize(20)
                      .fontColor(TEXT_KEY)
                      .textAlign(TextAlign.Center)
                      .padding({ bottom: 3 })
                      .backgroundColor(this.keyBg(BG_KEY, `sym_${ch}`))
                      .borderRadius(RADIUS)
                      .layoutWeight(1)
                      .height('100%')
                      .onClick(() => {
                        this.typeChar(ch);
                      })
                      .onTouch((event: TouchEvent) => {
                        if (event.type === TouchType.Down) {
                          this.pressKey(`sym_${ch}`);
                        } else if (event.type === TouchType.Up || event.type === TouchType.Cancel) {
                          this.releaseKey(`sym_${ch}`);
                        }
                      })
                  }, (ch: string, sIdx: number) => `sr3_${index}_${sIdx}_${ch}`)
                }
                .width('100%')
                .layoutWeight(1)

                // H-215(CodeArts)：第4行符号 + 退格键（原第3行退格挪到此行）
                Row() {
                  ForEach(this.symbolRowItems(fp.groupId, fp.page, 4), (ch: string, sIdx: number) => {
                    Text(ch)
                      .fontSize(20)
                      .fontColor(TEXT_KEY)
                      .textAlign(TextAlign.Center)
                      .padding({ bottom: 3 })
                      .backgroundColor(this.keyBg(BG_KEY, `Dsym_${ch}`))
                      .borderRadius(RADIUS)
                      .layoutWeight(1)
                      .height('100%')
                      .onClick(() => {
                        this.typeChar(ch);
                      })
                      .onTouch((event: TouchEvent) => {
                        if (event.type === TouchType.Down) {
                          this.pressKey(`Dsym_${ch}`);
                        } else if (event.type === TouchType.Up || event.type === TouchType.Cancel) {
                          this.releaseKey(`Dsym_${ch}`);
                        }
                      })
                  }, (ch: string, sIdx: number) => `sr4_${index}_${sIdx}_${ch}`)
                  Stack() {
                    SymbolGlyph($r('sys.symbol.delete_left'))
                      .fontSize(FUNC_ICON_SIZE)
                      .fontColor([TEXT_FUNC])
                  }
                  .backgroundColor(this.keyBg(BG_FUNC, 'bs_sym'))
                  .borderRadius(RADIUS)
                  .layoutWeight(1)
                  .height('100%')
                  .onTouch((event: TouchEvent) => {
                    if (event.type === TouchType.Down) {
                      this.pressKey('bs_sym');
                      this.startBackspaceRepeat();
                    } else if (event.type === TouchType.Up || event.type === TouchType.Cancel) {
                      this.releaseKey('bs_sym');
                      const repeated: boolean = this.bsRepeatStarted;
                      this.stopBackspaceRepeat();
                      if (!repeated) {
                        this.backChar();
                      }
                    }
                  })
                }
                .width('100%')
                .layoutWeight(1)
              }
              .height('100%')
            }
            .width('100%')
          }, (fp: FlatPage, index: number) => `sp_${index}_${fp.groupId}_${fp.page}`)
        }
        .listDirection(Axis.Horizontal)
        .scrollBar(BarState.Off)
        .edgeEffect(EdgeEffect.Spring)
        .onScrollIndex((first: number) => {
          if (first >= 0 && first < this.symbolPages.length) {
            const fp: FlatPage = this.symbolPages[first];
            this.activeSymbolGroupId = fp.groupId;
            this.symbolPage = fp.page;
          }
        })
        .onAppear(() => {
          if (this.pendingFlatIndex > 0) {
            this.symbolScroller.scrollToIndex(this.pendingFlatIndex, false);
            this.pendingFlatIndex = 0;
          }
        })
        .width('100%')
        .layoutWeight(1)
      }
    }
    .width('100%')
    .layoutWeight(1)
  }



  @Builder
  BottomBar() {
    if (this.panelMode === 'symbol') {
      Row() {

        Text('ABC')
          .fontSize(16)
          .fontColor(TEXT_FUNC)
          .textAlign(TextAlign.Center)
          .backgroundColor(this.pressedKey === 'sym123' ? BG_PRESSED : BG_ACTIVE)
          .borderRadius(RADIUS)
          .layoutWeight(1.2)
          .height(this.keyH())
          .margin(KEY_MARGIN)
          // H-081 续：ABC 字面=字母键盘，一律回 26 键（不回 prevPanelMode，避免九键→?123→ABC→又回九键死循环）
          .onClick(() => {
            keyboardController.clear();
            this.switchPanelMode('qwerty');
          })
          .onTouch((event: TouchEvent) => {
            if (event.type === TouchType.Down) {
              this.pressKey('sym123');

            }
          })
        Text(',')
          .fontSize(16)
          .fontColor(TEXT_KEY)
          .textAlign(TextAlign.Center)
          .backgroundColor(this.keyBg(BG_KEY, 'comma'))
          .borderRadius(RADIUS)
          .layoutWeight(0.8)
          .height(this.keyH())
          .margin(KEY_MARGIN)
          .onClick(() => {
            this.typeChar(',');
          })
          .onTouch((event: TouchEvent) => {
            if (event.type === TouchType.Down) {
              this.pressKey('comma');
            } else if (event.type === TouchType.Up || event.type === TouchType.Cancel) {
              this.releaseKey('comma');
            }
          })
        Stack() {
          Column() {
            Text('12')
              .fontSize(10)
              .fontColor(TEXT_FUNC)
              .textAlign(TextAlign.Center)
            Text('34')
              .fontSize(10)
              .fontColor(TEXT_FUNC)
              .textAlign(TextAlign.Center)
          }
        }
        .backgroundColor(this.keyBg(BG_FUNC, 'numpad_switch'))
        .borderRadius(RADIUS)
        .layoutWeight(0.8)
        .height(this.keyH())
        .margin(KEY_MARGIN)
        .onClick(() => {
          this.switchPanelMode('numpad');
        })
        .onTouch((event: TouchEvent) => {
          if (event.type === TouchType.Down) {
            this.pressKey('numpad_switch');
          } else if (event.type === TouchType.Up || event.type === TouchType.Cancel) {
            this.releaseKey('numpad_switch');
          }
        })
        // H-181：空格位固定品牌标识。H-178 我曾按安卓 `Rime(五)` 改成显示当前方案名（五笔/九键），
        // 主人 2026-10-26 明确否掉：「谁让你把空格的名字改成五笔了？该改的不改，不该改的乱改」。
        // ⇒ 品牌名不外露方案名，退回固定「三生」。
        // 2026-10-30：主人要求把「三生」文字换成鱼眼图标（空心环+中心实心点，正式版 sansheng_icon）。
        Stack() {
          Image($r('app.media.sansheng_icon'))
            .objectFit(ImageFit.Contain)
            .width(this.keyH() - 8)
            .height(this.keyH() - 8)
        }
        .alignContent(Alignment.Center)
        .backgroundColor(this.keyBg(BG_KEY, 'space'))
        .borderRadius(RADIUS)
        .layoutWeight(4.5)
        .height(this.keyH())
        .margin(KEY_MARGIN)
        .onClick(() => {
          // H-180：短按出空格；刚左右滑过（移了光标）的这一下不算点击
          this.spaceClick();
        })
        .onTouch((event: TouchEvent) => {
          // H-180：左右滑移光标
          this.spaceSwipeHandle(event);
        })
        Text('.')
          .fontSize(16)
          .fontColor(TEXT_KEY)
          .textAlign(TextAlign.Center)
          .backgroundColor(this.keyBg(BG_KEY, 'dot'))
          .borderRadius(RADIUS)
          .layoutWeight(0.8)
          .height(this.keyH())
          .margin(KEY_MARGIN)
          .onClick(() => {
            if (this.swipeDotDone) {
              this.swipeDotDone = false;
              return;
            }
            this.typeChar('.');
          })
          .onTouch((event: TouchEvent) => {
            if (event.type === TouchType.Down) {
              this.pressKey('dot');
              this.dotTouchDownY = this.evY(event);
              this.dotLastY = this.dotTouchDownY;
              this.swipeDotDone = false;
            } else if (event.type === TouchType.Move) {
              this.dotLastY = this.evY(event);
            } else if (event.type === TouchType.Up || event.type === TouchType.Cancel) {
              this.releaseKey('dot');
              const upY: number = this.evY(event) >= 0 ? this.evY(event) : this.dotLastY;
              const dy: number = (this.dotTouchDownY >= 0 && upY >= 0) ? (this.dotTouchDownY - upY) : 0;
              if (dy > 30) {
                // H-155：上滑出半角英文点 '.'（绕过 Rime 中文标点转写，直接 insertRaw；onTouch 手写检测）
                keyboardController.insertRaw('.');
                this.swipeDotDone = true;
                console.info(`${TAG} DotKey swipe up -> '.'`);
              }
              this.dotTouchDownY = -1;
            }
          })
        Stack() {
          SymbolGlyph($r('sys.symbol.return_down_left'))
            .fontSize(FUNC_ICON_SIZE)
            .fontColor(['#FFFFFF'])
        }
        .backgroundColor(this.pressedKey === 'enter' ? BG_PRESSED : BG_ENTER)
        .borderRadius(this.keyH() / 2)
        .layoutWeight(1.3)
        .height(this.keyH())
        .margin(KEY_MARGIN)
        .onClick(() => {
          this.enterClick();
        })
        .onTouch((event: TouchEvent) => {
          // H-255：长按回车＝去项目开源主页（主人 09:0x「二选一」；设置页只留长按空格那一条）。
          if (event.type === TouchType.Down) {
            this.pressKey('enter');
            this.settingsHoldStart('enter', this.evX(event), this.evY(event));
          } else if (event.type === TouchType.Move) {
            this.settingsHoldMove(this.evX(event), this.evY(event));
          } else if (event.type === TouchType.Up || event.type === TouchType.Cancel) {
            this.settingsHoldEnd();
            this.releaseKey('enter');
          }
        })
      }
      .width('100%')
    } else {
      Row() {

        // H-081（九宫格死循环修复）：t9 态该键文案变 ABC，单击一键回 26 键字母；
        // qwerty 态保持 ?123 进符号页。长按仍弹 LayoutMenu（可切回九键）。
        Text(this.panelMode === 't9' ? 'ABC' : '?123')
          .fontSize(16)
          .fontColor(TEXT_FUNC)
          .textAlign(TextAlign.Center)
          .backgroundColor(this.pressedKey === 'sym123' ? BG_PRESSED : BG_FUNC)
          .borderRadius(RADIUS)
          .layoutWeight(1.2)
          .height(this.keyH())
          .margin(KEY_MARGIN)
          .onClick(() => {
            if (this.panelMode === 't9') {
              keyboardController.clear();
              this.switchPanelMode('qwerty');
            } else {
              this.switchPanelMode('symbol');
            }
          })
          .onTouch((event: TouchEvent) => {
            if (event.type === TouchType.Down) {
              this.pressKey('sym123');
            } else if (event.type === TouchType.Up || event.type === TouchType.Cancel) {
              this.releaseKey('sym123');
            }
          })
          .gesture(
            LongPressGesture({ repeat: false, duration: 500 })
              .onAction(() => {
                this.pressedKey = '';
                this.showLayoutMenu = true;
              })
          )

        // 逗号键（安卓行为对齐）：短按直接上屏逗号；长按进符号面板 emoji 分类
        // （长按路径与符号页分类条 emoji 项一致：切面板 + 分类状态 + 滚动定位）
        Stack({ alignContent: Alignment.TopEnd }) {
          Text(',')
            .fontSize(20)
            .fontColor(TEXT_FUNC)
            .width('100%')
            .height('100%')
            .textAlign(TextAlign.Center)
          Text('😊')
            .fontSize(11)
            .margin({ top: 4, right: 6 })
        }
        .backgroundColor(this.keyBg(BG_FUNC, 'emoji'))
        .borderRadius(RADIUS)
          .layoutWeight(1.0)
          .height(this.keyH())
          .margin(KEY_MARGIN)
          .onClick(() => {
            this.typeChar(',');
          })
          .gesture(
            LongPressGesture({ repeat: false, duration: 500 })
              .onAction(() => {
                this.pressedKey = '';
                keyboardController.clear();
                this.switchPanelMode('symbol');
                this.showSymbolAll = false;
                this.activeSymbolGroupId = 'emoji';
                const idx: number = this.flatFirstIndex('emoji');
                if (idx >= 0) {
                  setTimeout(() => {
                    this.symbolScroller.scrollToIndex(idx, false);
                  }, 100);
                }
              })
          )
          .onTouch((event: TouchEvent) => {
            if (event.type === TouchType.Down) {
              this.pressKey('emoji');
            } else if (event.type === TouchType.Up || event.type === TouchType.Cancel) {
              this.releaseKey('emoji');
            }
          })
        // 语言键（简/繁/英）：单击切中英、长按弹简繁菜单、上滑切繁
        Text(this.asciiMode ? '英' : (this.tradMode ? '繁' : '简'))
          .fontSize(16)
          .textAlign(TextAlign.Center)
          .fontColor(this.asciiMode || this.tradMode ? FG_ACCENT : TEXT_FUNC)
          .backgroundColor(this.keyBg(BG_FUNC, 'lang'))
          .borderRadius(RADIUS)
          .layoutWeight(1.0)
          .height(this.keyH())
          .margin(KEY_MARGIN)
          .onClick(() => {
            if (this.langLongPressed) {
              this.langLongPressed = false;
              return;
            }
            keyboardController.clear();
            this.asciiMode = !this.asciiMode;
            keyboardController.setOption('ascii_mode', this.asciiMode);
          })
          .onTouch((event: TouchEvent) => {
            if (event.type === TouchType.Down) {
              this.pressKey('lang');
              if (event.touches.length > 0) {
                this.langTouchDownY = event.touches[0].windowY;
              }
            } else if (event.type === TouchType.Up || event.type === TouchType.Cancel) {
              if (event.touches.length > 0) {
                const upY: number = event.touches[0].windowY;
                if (this.langTouchDownY >= 0 && (this.langTouchDownY - upY) > 30) {
                  this.langLongPressed = true;      // 阻止 onClick 切中英
                  this.tradMode = !this.tradMode;   // 上滑 toggle：简→繁，繁→再上滑回简
                  keyboardController.setOption('zh_trad', this.tradMode);
                  this.showLangMenu = false;        // H-256(CodeArts): 上滑切换简繁后关闭菜单，否则气泡不回落
                }
              }
              this.langTouchDownY = -1;
              this.releaseKey('lang');
            }
          })
          .gesture(
            LongPressGesture({ repeat: false, duration: 500 })
              .onAction(() => {
                this.pressedKey = '';
                this.langLongPressed = true;
                this.showLangMenu = true;
              })
          )
        // H-181：空格位固定品牌标识。H-178 我曾按安卓 `Rime(五)` 改成显示当前方案名（五笔/九键），
        // 主人 2026-10-26 明确否掉：「谁让你把空格的名字改成五笔了？该改的不改，不该改的乱改」。
        // ⇒ 品牌名不外露方案名，退回固定「三生」。
        // 2026-10-30：主人要求把「三生」文字换成鱼眼图标（空心环+中心实心点，正式版 sansheng_icon）。
        Stack() {
          Image($r('app.media.sansheng_icon'))
            .objectFit(ImageFit.Contain)
            .width(this.keyH() - 8)
            .height(this.keyH() - 8)
        }
        .alignContent(Alignment.Center)
        .backgroundColor(this.keyBg(BG_KEY, 'space'))
        .borderRadius(RADIUS)
        .layoutWeight(4.5)
        .height(this.keyH())
        .margin(KEY_MARGIN)
        .onClick(() => {
          // H-180：短按出空格；刚左右滑过（移了光标）的这一下不算点击
          this.spaceClick();
        })
        .onTouch((event: TouchEvent) => {
          // H-180：左右滑移光标
          this.spaceSwipeHandle(event);
        })
        Text('.')
          .fontSize(16)
          .fontColor(TEXT_KEY)
          .textAlign(TextAlign.Center)
          .backgroundColor(this.keyBg(BG_KEY, 'dot'))
          .borderRadius(RADIUS)
          .layoutWeight(0.8)
          .height(this.keyH())
          .margin(KEY_MARGIN)
          .onClick(() => {
            if (this.swipeDotDone) {
              this.swipeDotDone = false;
              return;
            }
            this.typeChar('.');
          })
          .onTouch((event: TouchEvent) => {
            if (event.type === TouchType.Down) {
              this.pressKey('dot');
              this.dotTouchDownY = this.evY(event);
              this.dotLastY = this.dotTouchDownY;
              this.swipeDotDone = false;
            } else if (event.type === TouchType.Move) {
              this.dotLastY = this.evY(event);
            } else if (event.type === TouchType.Up || event.type === TouchType.Cancel) {
              this.releaseKey('dot');
              const upY: number = this.evY(event) >= 0 ? this.evY(event) : this.dotLastY;
              const dy: number = (this.dotTouchDownY >= 0 && upY >= 0) ? (this.dotTouchDownY - upY) : 0;
              if (dy > 30) {
                // H-155：上滑出半角英文点 '.'（绕过 Rime 中文标点转写，直接 insertRaw；onTouch 手写检测）
                keyboardController.insertRaw('.');
                this.swipeDotDone = true;
                console.info(`${TAG} DotKey swipe up -> '.'`);
              }
              this.dotTouchDownY = -1;
            }
          })
        Stack() {
          SymbolGlyph($r('sys.symbol.return_down_left'))
            .fontSize(FUNC_ICON_SIZE)
            .fontColor(['#FFFFFF'])
        }
        .backgroundColor(this.pressedKey === 'enter' ? BG_PRESSED : BG_ENTER)
        .borderRadius(this.keyH() / 2)
        .layoutWeight(1.3)
        .height(this.keyH())
        .margin(KEY_MARGIN)
        .onClick(() => {
          this.enterClick();
        })
        .onTouch((event: TouchEvent) => {
          // H-255：长按回车＝去项目开源主页（主人 09:0x「二选一」；设置页只留长按空格那一条）。
          if (event.type === TouchType.Down) {
            this.pressKey('enter');
            this.settingsHoldStart('enter', this.evX(event), this.evY(event));
          } else if (event.type === TouchType.Move) {
            this.settingsHoldMove(this.evX(event), this.evY(event));
          } else if (event.type === TouchType.Up || event.type === TouchType.Cancel) {
            this.settingsHoldEnd();
            this.releaseKey('enter');
          }
        })
      }
      .width('100%')
    }
  }

  /** 简繁切换小菜单——长按语言键弹出，只显示一个字：当前是简则显示「繁」，当前是繁则显示「简」。
   *  点击切换简繁，点遮罩关闭。 */
  @Builder
  LangMenu() {
    Column() {
      Text(this.tradMode ? '简' : '繁')
        .fontSize(18)
        .fontColor(FG_ACCENT)
        .fontWeight(FontWeight.Bold)
        .textAlign(TextAlign.Center)
        .width('100%')
        .padding({ left: 14, right: 14, top: 10, bottom: 10 })
        .onClick(() => {
          this.tradMode = !this.tradMode;
          keyboardController.setOption('zh_trad', this.tradMode);
          this.showLangMenu = false;
        })
    }
    .width(60)
    .borderRadius(RADIUS)
    .backgroundColor(BG_KEY)
    .clip(true)
    // 对准「简」键上方：简键中心≈27.5% 面板宽，气泡宽 60vp，left 20% 使气泡中心落在简键上
    .margin({ left: '20%', bottom: this.rowHeight + 8 })
  }

  /** H-078（M-058，D-014）：长按 ?123/ABC 弹出的布局切换菜单（26键/九键）。
   *  复用 LangMenu 浮层形态；切换前 keyboardController.clear() 清挂起编码。 */
  @Builder
  LayoutMenu() {
    Column() {
      Row() {
        Text('26键')
          .fontSize(15)
          .fontColor(this.panelMode === 'qwerty' ? FG_ACCENT : TEXT_FUNC)
        Blank()
        if (this.panelMode === 'qwerty') {
          Text('✓')
            .fontSize(15)
            .fontColor(FG_ACCENT)
        }
      }
      .width('100%')
      .padding({ left: 14, right: 14, top: 12, bottom: 12 })
      .backgroundColor(this.keyBg(BG_KEY, 'lay_26'))
      .onClick(() => {
        keyboardController.clear();
        this.switchPanelMode('qwerty');
        this.showLayoutMenu = false;
      })
      .onTouch((event: TouchEvent) => {
        if (event.type === TouchType.Down) {
          this.pressKey('lay_26');
        } else if (event.type === TouchType.Up || event.type === TouchType.Cancel) {
          this.releaseKey('lay_26');
        }
      })
      Divider().color(BG_FUNC)
      Row() {
        Text('九键')
          .fontSize(15)
          .fontColor(this.panelMode === 't9' ? FG_ACCENT : TEXT_FUNC)
        Blank()
        if (this.panelMode === 't9') {
          Text('✓')
            .fontSize(15)
            .fontColor(FG_ACCENT)
        }
      }
      .width('100%')
      .padding({ left: 14, right: 14, top: 12, bottom: 12 })
      .backgroundColor(this.keyBg(BG_KEY, 'lay_9'))
      .onClick(() => {
        keyboardController.clear();
        this.switchPanelMode('t9');
        this.showLayoutMenu = false;
      })
      .onTouch((event: TouchEvent) => {
        if (event.type === TouchType.Down) {
          this.pressKey('lay_9');
        } else if (event.type === TouchType.Up || event.type === TouchType.Cancel) {
          this.releaseKey('lay_9');
        }
      })
    }
    .width(160)
    .borderRadius(RADIUS)
    .backgroundColor(BG_KEY)
    .clip(true)
    .margin({ left: 8, bottom: this.rowHeight + 8 })
  }

  /**
   * H-278（Qoder 2026-10-30）：单手模式的留白侧＋两枚手柄。
   * 手柄贴底（拇指自然落点，单手时不用抬手够顶栏），上下两枚：⇄ 换边、✕ 退出。
   * 按下态走显式 @State（H-238／H-254 同一条真机验过的通路，**不用** stateStyles(pressed)——
   * 那条抬手不复位）。分隔线画在朝向键面的一侧，标出键面实际到哪儿为止。
   * 字形：换边用系统符号 `arrow_left_arrow_right`（与顶栏 ⇆ 同一枚，名字查过、不猜）；
   * 退出用 `×`（U+00D7 乘号，任何字体都有）——**不用** ⇄(U+21C4)／✕(U+2715) 这类生僻码点，
   * H-173 的真机教训：生僻码点会命中 emoji 字体回退，渲成彩色图或豆腐块。
   */
  @Builder
  OneHandGutter() {
    Column({ space: 10 }) {
      // 盒＝Stack（默认居中），与 FuncIcon 同构：glyph 自己不带尺寸，盒子定 36×36 圆底。
      Stack() {
        SymbolGlyph($r('sys.symbol.arrow_left_arrow_right'))
          .fontSize(20)
          .fontColor([FG_TOOLBAR])
      }
      .width(36)
      .height(36)
      .borderRadius(18)
      .backgroundColor(this.pressedMenuItem === 'oh_side' ? FUNC_ICON_PRESSED : BG_BAR)
      .shadow({ radius: 6, color: 'rgba(0,0,0,0.15)', offsetY: 1 })
      .onTouch((ev: TouchEvent) => {
        if (ev.type === TouchType.Down) {
          this.pressedMenuItem = 'oh_side';
        } else if (ev.type === TouchType.Up || ev.type === TouchType.Cancel) {
          if (this.pressedMenuItem === 'oh_side') {
            this.pressedMenuItem = '';
          }
        }
      })
      .onClick(() => {
        this.pressedMenuItem = '';
        this.flipOneHandSide();
      })
      Stack() {
        Text('×')
          .fontSize(22)
          .fontColor(FG_HINT)
      }
      .width(36)
      .height(36)
      .borderRadius(18)
      .backgroundColor(this.pressedMenuItem === 'oh_exit' ? FUNC_ICON_PRESSED : BG_BAR)
      .shadow({ radius: 6, color: 'rgba(0,0,0,0.15)', offsetY: 1 })
      .onTouch((ev: TouchEvent) => {
        if (ev.type === TouchType.Down) {
          this.pressedMenuItem = 'oh_exit';
        } else if (ev.type === TouchType.Up || ev.type === TouchType.Cancel) {
          if (this.pressedMenuItem === 'oh_exit') {
            this.pressedMenuItem = '';
          }
        }
      })
      .onClick(() => {
        this.pressedMenuItem = '';
        this.oneHandOn = false;
        console.info(`${TAG} H-278 one-hand off (gutter)`);
      })
    }
    .width('20%')
    .height('100%')
    .justifyContent(FlexAlign.End)
    .alignItems(HorizontalAlign.Center)
    .padding({ bottom: 18 })
    .backgroundColor(BG_PANEL)
    .borderWidth({
      left: this.oneHandSide === 'left' ? 1 : 0,
      right: this.oneHandSide === 'right' ? 1 : 0
    })
    .borderColor('#C9CEDA')
  }

  /** H-255：基础模式下长按回车 → 这张卡片（系统安全模式挡住浏览器时的兜底）。
   *  与 H-207「点了没反应」相反：按下去一定有可见结果，且写明怎么改成真跳转。 */
  @Builder
  GithubCard() {
    Column() {
      Row() {
        Text('开源主页')
          .fontSize(15)
          .fontColor(FG_TEXT)
          .layoutWeight(1)
        Text('✕')
          .fontSize(14)
          .fontColor(FG_HINT)
          .onClick(() => {
            this.githubCardOpen = false;
          })
      }
      .width('100%')
      .height(26)

      Text(GITHUB_HOME)
        .fontSize(13)
        .fontColor(FG_TEXT)
        .width('100%')
        .maxLines(2)
        .margin({ top: 4 })

      // H-255(CodeArts): 主人确认——与「本机不联网」定位不矛盾：输入法引擎全本地运算，
      // 此入口仅指向项目开源主页，不是输入功能依赖网络。
      Text('输入法本身不联网，此为项目链接入口。')
        .fontSize(12)
        .fontColor(FG_HINT)
        .width('100%')
        .maxLines(2)
        .margin({ top: 4 })

      Text('系统「基础模式」下输入法不能替你打开浏览器。到系统设置里给三生输入法打开「完整体验模式」，长按回车就会直接跳转。')
        .fontSize(12)
        .fontColor(FG_HINT)
        .width('100%')
        .maxLines(3)
        .margin({ top: 6 })
    }
    .width('94%')
    .padding(12)
    .margin({ left: 11, bottom: 30 })
    .backgroundColor(BG_BAR)
    .borderRadius(RADIUS)
    .shadow({ radius: 12, color: 'rgba(0,0,0,0.18)', offsetY: 2 })
  }

  build() {
    Stack({ alignContent: Alignment.BottomStart }) {
      // H-278：单手模式外壳——键面 80% 宽贴左/贴右，另一侧留白放手柄（⇄/✕）。
      // 只收窄容器、不改键高键距，也不改面板窗口尺寸（面板高由 computePanelSize 按行数算，与宽无关）。
      Row() {
        if (this.oneHandOn && !this.showAbout && this.oneHandSide === 'right') {
          this.OneHandGutter()
        }
        Column() {
          if (this.showAbout) {
            // H-052：关于/第三方声明面板——覆盖整个面板区域
            this.AboutPanel()
          } else {
            this.CandidateBar()
            // H-203：空闲/打字两态的实际栏高由 syncPanelBarHeight() 同步给控制器，
            // 面板窗口随之伸缩（空闲 28vp / 打字 44vp）；这里**不留**补高块——
            // 留白会把窗口撑回原高，字母就永远不会「上去一行」，等于没改。

            if (this.expanded) {
              this.ExpandedPanel()
            } else {
              // H-218r2：⇆ 文本编辑子面板接管键区（等高替换，窗口不伸缩），底栏一并隐藏。
              if (this.funcSubPanel === 'textedit') {
                this.TextEditGridPanel()
              } else if (this.panelMode === 'symbol') {
                this.SymbolPanel()
              } else if (this.panelMode === 't9') {
                this.T9Panel()
              } else if (this.panelMode === 'numpad') {
                this.NumpadPanel()
              } else {
                this.QwertyPanel()
              }

              if (this.panelMode !== 'numpad' && this.funcSubPanel !== 'textedit') {
                this.BottomBar()
              }
            }
          }
        }
        // H-278：关于/声明这类整页文字保持满宽（版式是照着满宽排的），单手模式只管键面。
        .width(this.oneHandOn && !this.showAbout ? '80%' : '100%')
        .height('100%')
        .justifyContent(FlexAlign.Start)
        .backgroundColor(BG_PANEL)
        if (this.oneHandOn && !this.showAbout && this.oneHandSide === 'left') {
          this.OneHandGutter()
        }
      }
      .width('100%')
      .height('100%')
      .backgroundColor(BG_PANEL)

      // H-063（M-050）：中/英 · 简/繁小菜单——布局键长按弹出，浮在底栏上方（贴左），
      // 点半透明遮罩任意处关闭；菜单不挡键盘（底栏仍在，收起菜单即恢复操作）
      if (this.showLangMenu) {
        Column()
          .width('100%')
          .height('100%')

          .onClick(() => {
            this.showLangMenu = false;
          })
        this.LangMenu()
      }

      // H-078：长按 ?123/ABC 弹出的布局切换菜单（26键/九键）
      if (this.showLayoutMenu) {
        Column()
          .width('100%')
          .height('100%')
          .backgroundColor('#66000000')
          .onClick(() => {
            this.showLayoutMenu = false;
          })
        this.LayoutMenu()
      }
      // H-213：将 FuncMenu 移至顶层 Stack，与 LangMenu/LayoutMenu 并列，彻底解决
      // 菜单被 CandidateBar 的 44vp 高度裁切问题（原位于栏内部，仅显示顶部一条）
      if (this.funcMenuOpen) {
        Column()
          .width('100%')
          .height('100%')
          .backgroundColor('#66000000')
          .onClick(() => {
            this.funcMenuOpen = false;
          })
        this.FuncMenu()
      }
      // H-215(Qoder)：顶层长按符号气泡（嵌键内定位被 IME 子窗口吞，见 bubbleGeom 注释）
      // H-241 契约 §3-7：「按键时弹出字符」关掉 ⇒ 气泡整个不画（渲染侧也挡一道，
      // 防手指已经进了出泡路径后才改开关时留下半口气泡）。
      if (this.popupOnPress && this.longPressLetter !== '' &&
        this.getHiddenSymbols(this.longPressLetter).length > 0) {
        this.LongPressBubble()
      }
      // H-241：设置页——**面板顶层覆盖层**，与 LangMenu/LayoutMenu/FuncMenu 同一通路
      //（H-213/H-215 已真机验过：只有画在这棵树里才不会被 IME 窗口静默裁）。
      // 不放最前：设置页开着时它必须盖住候选与气泡；遮罩点任意处关闭（与另三个菜单同口径）。
      if (this.settingsOpen) {
        Column()
          .width('100%')
          .height('100%')
          .backgroundColor('#66000000')
          .onClick(() => {
            this.settingsOpen = false;
          })
        SettingsPanel({ visible: $settingsOpen })
      }
      // H-255：长按回车 → 项目开源主页。完整体验模式下直接开浏览器；基础模式（系统默认）下
      // 系统禁止输入法拉 UIAbility ⇒ 卡片兜底，把地址与开关位置写在屏上。
      if (this.githubCardOpen) {
        Column()
          .width('100%')
          .height('100%')
          .backgroundColor('#66000000')
          .onClick(() => {
            this.githubCardOpen = false;
          })
        this.GithubCard()
      }
    }
    .id('ssRoot')
    .width('100%')
    .height('100%')
    // H-215(Qoder)：标定打点——顶层 Stack（=面板窗口内容区）实测几何，
    // globalPosition 给窗口/屏幕系定标（装机截图 y 若整体偏移，据此改 screenOffYvp）。
    .onAreaChange((_oldV: Area, newV: Area) => {
      const gp: Position = newV.globalPosition as Position;
      // H-278：根宽＝窗口宽，气泡定锚/夹取只认它（单手模式下候选栏 80%，不是窗口宽）。
      this.rootWinW = newV.width as number;
      console.info(`${TAG} H-215 root area win? x=${gp.x as number} y=${gp.y as number} w=${newV.width} h=${newV.height}`);
    })
  }
}