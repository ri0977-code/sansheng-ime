/**
 * 三生输入法 · 引擎门面（v0.1）
 * 归属：Qoder。键盘 UI 只依赖本文件，不直接依赖 NAPI。
 */
import { common } from '@kit.AbilityKit';

export interface RimeCandidate {
  text: string;
  comment?: string;
}

export interface RimeContext {
  preedit: string;
  /** 当前页的候选切片（长度 ≤ 每页条数），UI 直接渲染它。 */
  candidates: RimeCandidate[];
  /**
   * v0.2.0：当前 Rime 菜单页的**全部**候选（不做页大小切片）。
   * UI 拿它按实测宽度算「这一页能完整放下几条」——**不能**再从 `candidates`
   * 反推页大小：那样会单调棘轮下落到 1 条（H-050 回归）。
   */
  allCandidates: RimeCandidate[];
  /** v0.2.0：`allCandidates[0]` 在全局候选序列里的绝对下标（跨 Rime 菜单页连续）。 */
  baseIndex: number;
  page: number;
  hasNext: boolean;
  /** 需要立刻上屏的文本（空格/回车等），没有则为 undefined */
  commitText?: string;
}

export interface RimeEngine {
  /**
   * v0.1.5：`context` 是 InputMethodExtensionContext（ime 扩展里全局 getContext()
   * 拿不到 resourceManager，必须由控制器显式传入）。mock 会忽略它。
   */
  init(sharedPath: string, context?: common.Context): Promise<void>;
  processKey(key: string): RimeContext;
  selectCandidate(index: number): string;
  /**
   * v0.2.0：按**全局绝对下标**选词。
   * UI 若自己按实测宽度分页（各页条数不必相等），用它选词就不会和引擎切片错位；
   * 绝对下标 = `context.baseIndex` + 页内下标。
   */
  selectCandidateAbs(index: number): string;
  deleteBackward(): RimeContext;
  flipPage(direction: number): RimeContext;
  clear(): RimeContext;
  getContext(): RimeContext;
  setOption(name: string, value: boolean): void;
  /**
   * v0.1.8（H-041 ascii_mode 排障 + UI 需要）：读回引擎当前的开关状态。
   * 「中/英」键要显示真实状态，不能只靠 UI 自己记一份（UI 记的和引擎里的会分叉：
   * 切方案、reset:0、Ctrl+Shift+F 都会改引擎侧而 UI 不知道）。
   * 名字用 Rime 的开关名：ascii_mode / zh_trad / ascii_punct / full_shape …
   */
  getOption(name: string): boolean;
  /** v0.1.5：每页候选数（竖屏 5 / 横屏 9），返回重置到第 0 页后的 context。 */
  setPageSize(size: number): RimeContext;
  /**
   * v0.1.7（H-028 ① 智能九键）：切换 Rime 方案。
   * `wubi_pinyin` = 26 键主方案（五笔·拼音·英文混输），`sansheng_t9` = 九宫格数字方案。
   * 九宫格面板按下去的是数字，只有切到 T9 方案才会被拼写代数解释成拼音；
   * 所以这个口子必须由 UI 在面板切换时调，不能在引擎里猜（猜了 `?123` 的数字直出就废了）。
   * 返回是否切换成功；编码会清空，页码回到第 0 页。
   */
  selectSchema(id: string): boolean;
  /**
   * H-178（主人 2026-10-25 16:5x「对照安卓抄」）：读当前方案 id。
   * 安卓底栏那颗 `Rime(五)` 显示**当前方案名**；我们此前只有 selectSchema（写）
   * 没有读 ⇒ 空格位只能固定显示「三生」，切了方案用户也看不出来。
   * 返回如 `wubi_pinyin` / `sansheng_t9` / `luna_pinyin`；引擎未就绪返回空串。
   */
  getSchemaId(): string;
  /**
   * v0.5.0（M4）：引擎收尾 —— 销毁 session 与引擎，释放 Lua 脚本 / OpenCC / 用户词典句柄。
   *
   * 为什么 UI 侧需要这个口子：librime 的用户词典（tabledb）是**纯内存**的，
   * 只有 db 析构时才写回磁盘。桌面端 Rime 退出时会自己 finalize，鸿蒙这边
   * IME 进程常驻、桥上原本没有 finalize ⇒ 自造词/自调频跨会话丢失。
   * 现在 schema 已改用 LevelDb（每次提交即落盘），本接口用于**干净收尾**。
   *
   * 调用后引擎不可用，需重新 `init()` 才能再用。
   */
  finalize(): void;
}
