/*
 * 三生输入法 · 键盘控制器（M1.1）
 * 归属：CodeArts（鸿蒙 UI）。
 * 面板生命周期 / setUiContent→resize / inputStart 路由 / 横竖屏尺寸重算借鉴自
 * nanaseyuu/hMixedKeyboard (Apache-2.0) 的 model/MixedController.ets，
 * 本项目裁剪为手机固定键盘（FLG_FIXED），引擎替换为 EngineProvider.get()。
 */
import { inputMethodEngine, InputMethodExtensionContext } from '@kit.IMEKit';
import { display } from '@kit.ArkUI';
import { BusinessError, pasteboard } from '@kit.BasicServicesKit';
import { Want } from '@kit.AbilityKit';
import { EngineProvider } from '../engine/EngineProvider';
import { RimeCandidate, RimeContext, RimeEngine } from '../engine/RimeEngine';
// H-241（契约 §2）：键盘高度百分比 / 可撤销步数两项的读取点在本文件。
// store 在**输入法进程自己的沙箱**里，未 load 前 num()/on() 返回契约默认值 ⇒ 行为与改动前一致。
import { SettingsStore } from '../common/SettingsStore';

const TAG: string = 'SSKeyboardController';
const PANEL_PAGE: string = 'pages/KeyboardIndex';

// 面板高（vp）= 候选区 + 4 行（3 字母/T9 + 1 功能行）
// M-037：主人拍板改回单行——竖屏：单行候选(28vp) + 反查行(16vp) = 44vp
const PORTRAIT_BAR_VP: number = 44;
const PORTRAIT_ROW_VP: number = 48;
// 横屏：单行候选(28vp) + 反查行(16vp) = 44vp
const LANDSCAPE_BAR_VP: number = 44;
const LANDSCAPE_ROW_VP: number = 34;
const ROW_COUNT: number = 4;

/** 计算出的面板尺寸（px）与行高（vp）。 */
interface PanelSize {
  widthPx: number;
  heightPx: number;
  rowVp: number;
  barVp: number;
  /**
   * H-205（Qoder 2026-10-26 真机）：**方向预算栏高**（竖/横都 44vp），与 `barVp`（实时栏高）分开。
   * 回推给 UI 的 `state.barHeight` 必须是这个预算值，绝不能是实时值——见 notify()。
   */
  defaultBarVp: number;
}

/** 推送给键盘面板的状态快照。 */
export interface KeyboardState {
  preedit: string;
  /** 当前页的候选切片，UI 直接渲染。 */
  candidates: RimeCandidate[];
  /**
   * v0.2.0：当前 Rime 菜单页的**全部**候选。
   * 候选栏要按「全量候选的实测宽度」决定一页放几条，**不能**从当页切片反推——
   * 那样会单调棘轮下落到 1 条（H-050 回归）。
   */
  allCandidates: RimeCandidate[];
  /** v0.2.0：allCandidates[0] 的全局绝对下标（UI 自己分页时选词要用）。 */
  baseIndex: number;
  page: number;
  hasNext: boolean;
  rowHeight: number; // vp，随横竖屏变化
  barHeight: number; // vp，随横竖屏变化
  /** H-220(Qoder)：「选择」扩展选区模式是否开着（键盘 n 键 / ⇆ 面板「选择」格同一状态）。 */
  selectionMode: boolean;
}

export type KeyboardListener = (state: KeyboardState) => void;


/** H-154 撤销栈记录：'commit' = 一次上屏文本；'clear' = 一次上滑清除保存的原文。 */
interface UndoRecord {
  type: string; // 'commit' | 'clear'
  text: string;
}

/** H-154：撤销栈上限（防内存膨胀；超出丢最旧）。 */
const UNDO_STACK_LIMIT: number = 10;

/**
 * 键盘控制器：单例。负责面板生命周期、输入事件路由、状态推送、横竖屏重算。
 */
export class SsKeyboardController {
  private context: InputMethodExtensionContext | undefined = undefined;
  private panel: inputMethodEngine.Panel | undefined = undefined;
  private kbController: inputMethodEngine.KeyboardController | undefined = undefined;
  private inputClient: inputMethodEngine.InputClient | undefined = undefined;
  private engine: RimeEngine = EngineProvider.get();
  private listener: KeyboardListener | undefined = undefined;
  private engineInited: boolean = false;
  /** H-068：引擎懒加载完成前面板已可见，此时按键先入队，ready 后按序回放，避免冷启吞键。 */
  private engineReady: boolean = false;
  private pendingInputs: string[] = [];
  private appliedW: number = 0;
  private appliedH: number = 0;
  private rowVp: number = PORTRAIT_ROW_VP;
  private barVp: number = PORTRAIT_BAR_VP;
  /** H-241 契约 §3-8：撤销栈上限，初值＝常量 10；面板读到设置值后由 applySettingsChanged() 更新。 */
  private undoLimit: number = UNDO_STACK_LIMIT;
  /**
   * H-205(Qoder 2026-10-26)：回推给 UI 的 `barHeight`（**方向预算**，竖/横都 44vp）。
   * 真机教训（Mate80，主人「你把顶栏输入和候选弄成一行了」）：H-203 把**实时**栏高
   * （空闲 28vp）当 barHeight 推回去，而 UI 里 `barHeight < 40` 是 H-096 的**横屏判据**
   * （`candBarHeight()` 横屏分支 + L1 是否独立成行都看它）⇒ 竖屏空闲一缩栏高，
   * UI 就永久认定自己在横屏：28 → max(24,28-6)=24 → 再推回去 → 稳定在 24vp，
   * 打字时再也回不到 44vp，窗口自然也不会「长一行」，L1 还被并排画进候选行（实测日志
   * `state:` 后没有任何 relayout resize）。实时值只用于**窗口尺寸**，预算值才给 UI 当布局依据。
   */
  private defaultBarVp: number = PORTRAIT_BAR_VP;
  /** H-203(Qoder)：UI 报上来的**候选栏实际高度**（vp）。0 = 还没同步，按方向默认值。
   *  为什么要这个：面板窗口高度 = barVp + rowVp*4，从前恒按 44vp 算 ⇒ 空闲态（无 preedit、
   *  无候选）那 16vp 的 L1 空行也照样占着，主人看着就是「顶栏太宽，安卓的窄」。
   *  窗口跟着 UI 实际高度缩，字母区才会随候选出现/消失整体上移一行（安卓同口径）。 */
  private uiBarVp: number = 0;
  private relayoutTimer: number = -1;
  private kbHidden: boolean = false;
  /** H-154：UI/controller 侧撤销栈（引擎只读无 undo 接口）。记录上屏与上滑清除两类动作。 */
  private undoStack: UndoRecord[] = [];
  // H-177：重做栈——撤销时把记录挪进来，重做时挪回去；有新动作即清空（见 pushUndo）。
  private redoStack: UndoRecord[] = [];
  /** H-154：最近一次上屏文本（insertText 记录，无编码态上滑清除时兜底保存用）。 */
  private lastCommitText: string = '';
  /** H-220(Qoder)：「选择」模式（安卓 TextEditingWindow 的选择键）——开着时方向键
   *  走 `selectByMovementSync` 扩展选区，而不是移动光标。锚点=开模式时的光标位。 */
  private selectionModeOn: boolean = false;
  /** H-220：选区固定端锚点（getTextIndexAtCursorSync 下标）。 */
  private selAnchor: number = 0;
  /** H-220：选区活动端记账位（鸿蒙读不到宿主选区，只能自己算）。 */
  private selCursor: number = 0;
  /** H-275(Qoder 2026-10-29)：我们自己发的 SELECT_ALL 旗标。宿主选区读不到，
   *  不能靠「getForwardSync 空 + getBackwardSync 有值」猜(会误删光标停在文首的普通场景)，
   *  所以发 SELECT_ALL 时记旗标，下一次退格/长按 m 当成「整框删除 + 一条 'clear' 撤销记录」。
   *  任何字符输入、光标移动、选择开关、其它编辑动作都清掉它，避免过期旗标把后续一次退格误删整框。 */
  private selectAllRequested: boolean = false;
  /** H-166(Qoder)：本次输入会话内**连续上屏**的累计文本（段与段之间只要没有手动退格/光标移动就算连续）。
   *  上滑清除删的是这一整段，而不是最后一段——主人原话「应该是最近的输入一段时间的连续输入，一次清除」。 */
  private sessionCommitText: string = '';

  onCreate(context: InputMethodExtensionContext): void {
    this.context = context;
    this.initEngine();
    this.registerInputListener();
    this.registerDisplayListener();
  }

  onDestroy(): void {
    display.off('change');
    try {
      display.off('foldStatusChange');
    } catch (e) {
      const err = e as BusinessError;
      console.warn(`${TAG} foldStatusChange unsubscribe: ${err.code}`);
    }
    if (this.relayoutTimer !== -1) {
      clearTimeout(this.relayoutTimer);
      this.relayoutTimer = -1;
    }
    const p = this.panel;
    this.panel = undefined;
    this.inputClient = undefined;
    if (p) {
      inputMethodEngine.getInputMethodAbility().destroyPanel(p)
        .catch((err: BusinessError) => {
          console.warn(`${TAG} onDestroy destroyPanel: ${err.code}`);
        });
    }
    try {
      this.engine.finalize();
    } catch (e) {
      const ferr = e as BusinessError;
      console.warn(`${TAG} onDestroy finalize: ${ferr.code}`);
    }
    this.engineInited = false;
    this.engineReady = false;
    this.pendingInputs = [];
  }

  private initEngine(): void {
    if (this.engineInited) {
      return;
    }
    this.engineInited = true;
    const base: string = this.context ? this.context.filesDir : '';
    // M2/Qoder 最小改动：IME 扩展里全局 getContext() 为空，数据释放需要
    // 控制器把 InputMethodExtensionContext 显式交给引擎（接口 v0.1.5 可选参数）。
    this.engine.init(base + '/rime', this.context).then(() => {
      console.info(`${TAG} engine ready`);
      this.engineReady = true;
      this.replayPendingInputs();
    }).catch((err: Error) => {
      console.error(`${TAG} engine init failed: ${err.message}`);
      this.pendingInputs = [];
    });
  }

  private registerInputListener(): void {
    const ability = inputMethodEngine.getInputMethodAbility();
    ability.on('inputStart', (kbController: inputMethodEngine.KeyboardController,
      inputClient: inputMethodEngine.InputClient) => {
      console.info(`${TAG} inputStart`);
      this.kbController = kbController;
      this.inputClient = inputClient;
      // H-154：新输入会话清撤销栈（不持久化，避免与宿主编辑器状态不一致）
      this.undoStack = [];
      this.lastCommitText = '';
      this.sessionCommitText = '';
      this.engine.clear();
      this.showPanel();
      this.notify();

    });
    ability.on('inputStop', () => {
      console.info(`${TAG} inputStop`);
      this.kbController = undefined;
      this.inputClient = undefined;
      this.kbHidden = false;
      // H-154：输入法会话结束，撤销栈清空（不持久化）
      this.undoStack = [];
      this.lastCommitText = '';
      this.sessionCommitText = '';
      // H-068：上一个会话排队但没来得及回放的键，不能漏到下一个输入框
      this.pendingInputs = [];
      this.engine.clear();
      this.hidePanel();
      this.notify();
    });
  }

  /** 显示几何变化（含旋转）合并为一次防抖重算。 */
  private registerDisplayListener(): void {
    display.on('change', () => {
      this.scheduleRelayout();
    });
    try {
      display.on('foldStatusChange', () => {
        this.scheduleRelayout();
      });
    } catch (e) {
      const err = e as BusinessError;
      console.warn(`${TAG} foldStatusChange subscribe: ${err.code}`);
    }
  }

  private scheduleRelayout(): void {
    if (this.relayoutTimer !== -1) {
      return;
    }
    this.relayoutTimer = setTimeout(() => {
      this.relayoutTimer = -1;
      this.applyPanelSize();
    }, 300);
  }

  /** 依据当前 display（含 rotation）计算面板尺寸与行高。 */
  private computePanelSize(): PanelSize {
    let widthPx: number = 0;
    let density: number = 1;
    let isLandscape: boolean = false;
    try {
      const dis = display.getDefaultDisplaySync();
      widthPx = dis.width;
      density = dis.densityPixels > 0 ? dis.densityPixels : 1;
      // rotation: 1=90°, 3=270° 视为横屏
      isLandscape = dis.rotation === 1 || dis.rotation === 3;
    } catch (e) {
      const err = e as BusinessError;
      console.warn(`${TAG} computePanelSize display: ${err.code}`);
    }
    const barVp: number = isLandscape ? LANDSCAPE_BAR_VP : PORTRAIT_BAR_VP;
    // H-241 契约 §3-1「键盘高度百分比」（80–120%，默认 100＝原样）：
    // 只缩放**键区四行**的行高，候选栏 44vp 一分不动（那是 H-203/H-208 定稿的稳定区）。
    // 窗口高跟着键区一起算 ⇒ 键帽整体变高/变矮，屏幕底边上沿对齐，不会盖住输入框。
    // 这是**用户主动**改高度，和 H-208 骂的「出候选自己蹦跳」不是一回事：这里只在设置变了才 resize。
    // 读不到/未 load 时 num() 给契约默认 100 ⇒ 与改动前逐像素一致。
    const pct: number = SettingsStore.inst().on('kbd_height_pct', 100);
    const rowVp: number = (isLandscape ? LANDSCAPE_ROW_VP : PORTRAIT_ROW_VP) * pct / 100;
    // H-203：UI 同步过实际栏高就用它（空闲 28vp / 打字 44vp），否则用方向默认值。
    // 取值范围兜底：栏高恒小于一整行以上才算合理，异常值（0/NaN/过大）一律退回默认。
    // H-208（Qoder 2026-10-26 20:5x，主人原话「怎么出候选键盘还往上跳上来，打完字又跳下去呢？
    // 哪个输入法键盘不是稳定的啊，一蹦一跳的像什么话！服了，大问题」）：**窗口高度恒定**。
    // 根因就是 H-203 的「窗口跟缩」：空闲 927px ↔ 打字 983px，差 56px=16vp，
    // 每次出候选整块键盘上跳一次、commit 后又掉回来——主人骂的正是这个。
    // 现在只用方向预算，UI 报的实时栏高不再参与窗口尺寸（applyBarHeightVp 仍记录，
    // 但不再影响 heightPx；保留它是因为 h165_bar_height_check 与 UI 侧仍要读实际栏高）。
    // 空闲态「窄条观感」改在栏**内部**做（KeyboardIndex 的 candBarHeight() 空闲返回 28vp，
    // 上方 16vp 由同色容器补满，视觉仍是窄条但键盘不动）。主人 2026-10-26 20:5x 拍板。
    const liveBarVp: number = barVp;
    const heightVp: number = liveBarVp + rowVp * ROW_COUNT;
    const size: PanelSize = {
      widthPx: widthPx,
      heightPx: Math.round(heightVp * density),
      rowVp: rowVp,
      barVp: liveBarVp,
      defaultBarVp: barVp
    };
    return size;
  }

  /** H-203(Qoder)：候选栏实际高度变化（空闲↔打字/工具栏）时，把面板窗口高度同步过去。
   *  只做「真变才 resize」——键盘每个状态推送都调一次，不变时立刻返回，不会有抖动成本。
   *  注意：resize 是**窗口**变化，键区随底边对齐整体上移/下移，正是主人要的
   *  「输入的时候有候选的时候字母自动上去一行」。 */
  applyBarHeightVp(barVp: number): void {
    if (!(barVp > 0) || !isFinite(barVp)) {
      return;
    }
    if (Math.abs(barVp - this.uiBarVp) < 0.01) {
      return;
    }
    this.uiBarVp = barVp;
    this.applyPanelSize();
  }

  /**
   * H-241（契约 §3-1/§3-8）：设置页写完值后由面板调用，把**窗口级**的变化落到控制器。
   * 目前两件：① 键盘高度百分比 → 重算行高与窗口高（applyPanelSize 内部「真变才 resize」，
   * 没变直接返回，绝不会造成 H-208 那种蹦跳）；② 可撤销步数 → 当场裁剪已有栈。
   * 字号/振动/气泡这类**纯 UI** 项不进这里，由 KeyboardIndex 的 @State 镜像直接重绘。
   */
  applySettingsChanged(): void {
    this.undoLimit = SettingsStore.inst().on('undo_stack_limit', UNDO_STACK_LIMIT);
    while (this.undoStack.length > this.undoLimit) {
      this.undoStack.shift();
    }
    this.applyPanelSize();
    console.info(`${TAG} H-241 applySettingsChanged: row=${this.rowVp}vp undoLimit=${this.undoLimit}`);
  }

  /** 方向/尺寸变化后重算并 resize（用 px），推送给面板更新行高。 */
  private applyPanelSize(): void {
    const p = this.panel;
    if (!p) {
      return;
    }
    const size: PanelSize = this.computePanelSize();
    if (size.widthPx === this.appliedW && size.heightPx === this.appliedH) {
      return;
    }
    this.appliedW = size.widthPx;
    this.appliedH = size.heightPx;
    this.rowVp = size.rowVp;
    this.barVp = size.barVp;
    this.defaultBarVp = size.defaultBarVp;
    p.resize(size.widthPx, size.heightPx).then(() => {
      console.info(`${TAG} relayout resize ${size.widthPx}x${size.heightPx}px row ${size.rowVp}vp ` +
        `bar ${size.barVp}vp budget ${size.defaultBarVp}vp`);
    }).catch((err: BusinessError) => {
      console.warn(`${TAG} relayout resize failed: ${err.code}`);
    });
    this.notify();
  }

  private showPanel(): void {
    this.kbHidden = false;
    if (this.panel) {
      this.panel.show().catch((err: BusinessError) => {
        console.warn(`${TAG} panel.show: ${err.code}`);
      });
      return;
    }
    this.createPanel();
  }

  /** 创建面板：先 setUiContent 再 resize（px），最后 show。 */
  private async createPanel(): Promise<void> {
    const ctx = this.context;
    if (!ctx) {
      console.error(`${TAG} createPanel: no context`);
      return;
    }
    try {
      const info: inputMethodEngine.PanelInfo = {
        type: inputMethodEngine.PanelType.SOFT_KEYBOARD,
        flag: inputMethodEngine.PanelFlag.FLG_FIXED
      };
      const p = await inputMethodEngine.getInputMethodAbility().createPanel(ctx, info);
      this.panel = p;
      // 先算尺寸并更新行高，再 setUiContent：面板页 aboutToAppear 注册监听时会立即
      // 读到正确行高。否则首帧按竖屏 48vp 渲染，横屏 168vp 面板放不下 4 行，
      // 功能行被裁掉，直到第一次按键才恢复（2026-10-21 真机实测）。
      const size: PanelSize = this.computePanelSize();
      this.appliedW = size.widthPx;
      this.appliedH = size.heightPx;
      this.rowVp = size.rowVp;
      this.barVp = size.barVp;
      this.defaultBarVp = size.defaultBarVp;
      // 顺序不能反：setUiContent 必须先于 resize，否则面板 UI 为空（参考壳实测坑）
      await p.setUiContent(PANEL_PAGE);
      // H-203：面板页 aboutToAppear 会把**候选栏实际高度**（空闲 28vp）报回来；
      // setUiContent 之后重算一次，别拿挂载前的 44vp 把窗口又撑回去（否则空闲仍显宽）。
      const live: PanelSize = this.computePanelSize();
      this.appliedW = live.widthPx;
      this.appliedH = live.heightPx;
      this.rowVp = live.rowVp;
      this.barVp = live.barVp;
      this.defaultBarVp = live.defaultBarVp;
      await p.resize(live.widthPx, live.heightPx);
      await p.show();
      // 面板页可能已在 setUiContent 后注册监听并拿到首帧；show 完再推一次兜底。
      this.notify();
      console.info(`${TAG} panel created ${live.widthPx}x${live.heightPx}px row ${live.rowVp}vp ` +
        `bar ${live.barVp}vp budget ${live.defaultBarVp}vp`);
    } catch (e) {
      const err = e as BusinessError;
      console.error(`${TAG} createPanel: ${err.code} ${err.message}`);
      this.panel = undefined;
    }
  }

  private hidePanel(): void {
    const p = this.panel;
    this.panel = undefined;
    // H-203：新会话一定从空闲态开始；上一会话残留的栏高（44）会让首帧偏宽，清掉。
    this.uiBarVp = 0;
    if (p) {
      inputMethodEngine.getInputMethodAbility().destroyPanel(p)
        .catch((err: BusinessError) => {
          console.warn(`${TAG} hidePanel destroyPanel: ${err.code}`);
        });
    }
  }

  /** H-085：用户主动收起键盘——panel.hide() 不销毁面板，光标变化时自动弹回。 */
  hideKeyboard(): void {
    this.engine.clear();
    this.kbHidden = true;
    const p = this.panel;
    if (p) {
      p.hide().catch((err: BusinessError) => {
        console.warn(`${TAG} hideKeyboard panel.hide: ${err.code}`);
      });
    }
    this.notify();
  }

  /**
   * H-255（Qoder 2026-10-28 09:0x，主人「把回车设置成长按到 github 主页」）：
   * 用系统浏览器打开一个网址。返回给 UI 的三种结果：
   *   'opened'  = startAbility 成功（完整体验模式）；
   *   'blocked' = 基础模式（IME 安全模式），系统禁止输入法扩展拉起任何 UIAbility
   *               （官方 ime-kit-security 原文；实测错误码 16000069 "The extension cannot start
   *               the third party application"）⇒ 由面板画「开源主页」卡片兜底；
   *   'failed'  = 其它失败（没有 context／系统异常），同样走卡片，不留静默。
   * 先读 `getSecurityMode()` 只为把模式写进日志（排查时一眼看出是不是模式问题）；
   * **判定以 startAbility 的真实结果为准**，不拿"应该是基础模式"当结论。
   */
  async openExternalUrl(url: string): Promise<string> {
    const ctx: InputMethodExtensionContext | undefined = this.context;
    if (!ctx) {
      return 'failed';
    }
    let mode: string = 'unknown';
    try {
      mode = inputMethodEngine.getInputMethodAbility().getSecurityMode() ===
        inputMethodEngine.SecurityMode.FULL ? 'FULL' : 'BASIC';
    } catch (e) {
      const err = e as BusinessError;
      console.warn(`${TAG} H-255 getSecurityMode: ${err.code}`);
    }
    const want: Want = {
      action: 'ohos.want.action.viewData',
      entities: ['entity.system.browsable'],
      uri: url
    };
    try {
      await ctx.startAbility(want);
      console.info(`${TAG} H-255 openExternalUrl ok mode=${mode} url=${url}`);
      return 'opened';
    } catch (e) {
      const err = e as BusinessError;
      console.warn(`${TAG} H-255 openExternalUrl failed: ${err.code} ${err.message} mode=${mode}`);
      return mode === 'BASIC' ? 'blocked' : 'failed';
    }
  }

  // ---- 输入事件路由（面板 → 引擎 → 上屏/状态） ----

  /** 字母 / 数字 / 标点 / Space / Enter 等：交给引擎，commitText 有值就上屏。 */
  onKey(key: string): void {
    this.selectAllRequested = false;          // H-275：打字＝替换选区，整框删除旗标作废
    if (!this.engineReady) {
      // H-068：冷启时面板先可见、引擎约 1–2 s 后才 ready，期间按键不能丢
      this.queueInput(key);
      return;
    }
    const ctx: RimeContext = this.engine.processKey(key);
    if (ctx.commitText !== undefined && ctx.commitText.length > 0) {
      this.insertText(ctx.commitText);
    }
    this.notify(ctx);
  }

  /** 点候选：上屏并刷新。 */
  chooseCandidate(index: number): void {
    const text: string = this.engine.selectCandidate(index);
    if (text.length > 0) {
      this.insertText(text);
    }
    this.notify();
  }

  /**
   * v0.2.0：按**全局绝对下标**点候选。
   * UI 若自己按实测宽度分页（各页条数不必相等），用它点词就不会和引擎切片错位；
   * 绝对下标 = `state.baseIndex` + 页内下标。
   */
  chooseCandidateAbs(absIndex: number): void {
    const text: string = this.engine.selectCandidateAbs(absIndex);
    if (text.length > 0) {
      this.insertText(text);
    }
    this.notify();
  }

  /** H-275(Qoder 2026-10-29，主人「长按a全选后退格删不掉 / 选区后退格下滑撤销逐字 / 长按m删选区无法恢复」)：
   *  选区删除必须「整体删 + 压一条 'clear' 撤销记录」，否则就是逐字删(逐字撤销)或不记记录(无法恢复)。
   *  选区来源两种：① 选择模式(长按n开)→ 锚点 selAnchor 固定，活动端用**实时光标位**(getextIndexAtCursorSync)，
   *  不用记账的 selCursor(H-220 铁证原生 selectByMovementSync 不回写 selCursor，记账会漂移→误判选区大小)；
   *  ② 全选(编辑框动作)→ 发 SELECT_ALL 时记 selectAllRequested 旗标，靠旗标判定(不猜，猜会误删光标停文首的普通场景)。
   *  选中文案：**必须先收拢选区再读**——2026-10-30 真机铁证表明选区激活时读整段返回空串
   *  (`textLen=0 deleted=56`)，撤销记录就成了 0 字。收拢后走「精确长度读」+「逐字先读后删」两级兜底。
   *  删：关模式+一次原生移动收拢，走到选区起点，deleteBackwardSync(1) 循环删右侧正文，
   *  最后压一条 {type:'clear',text:整段} 供下滑/顶栏撤销整体恢复。 */
  private tryDeleteSelection(): boolean {
    const client = this.inputClient;
    if (!client) {
      return false;
    }
    // ① 选择模式：长按 n 开「选择」后，锚点 selAnchor 固定、活动端用**实时光标位**(getTextIndexAtCursorSync)
    //    —— 不能用记账的 selCursor：H-220 已铁证原生 selectByMovementSync 不回写 selCursor，记账会漂移，
    //    导致「以为选了 32 字、实际选区 1 字」，于是删多删少、撤销只回 1 字(就是之前 H-275 的根因)。
    if (this.selectionModeOn) {
      const anchor: number = this.selAnchor;
      const liveCur: number = this.cursorIndex();          // 活动端＝宿主真实光标位
      const a: number = Math.min(anchor, liveCur);
      const b: number = Math.max(anchor, liveCur);
      if (b - a > 0) {
        this.selectionModeOn = false;
        // 收拢宿主选区：关模式后一次原生移动(编辑器把移动当取消选中，H-220 copyThenCollapse 同款)，
        // 方向取「远离选区内部」那侧，避免被当成扩选。
        this.rawMoveCursor(liveCur >= anchor ? 4 : 3);
        this.walkCursorTo(a);                              // 走到选区起点(此时已无选区，纯移动)
        // H-275b(Qoder 2026-10-30 00:2x)：真机铁证 `sel-delete anchor=510 liveCur=454 [454,510]
        //  textLen=0 deleted=56` ——上一版在**选区还活着**时读 65536 字全文，本机回空串
        //  ⇒ 撤销记录 0 字，删完恢复不了（主人「下滑/顶栏撤销都没用」）。
        //  根因只可能是「选区激活时读不到」或「超大 n 读不到」，所以改成**先收拢再读**，两种读法兜底：
        //   ① 精确长度读：光标在右端⇒选中文在光标前(getForwardSync)，否则在光标后(getBackwardSync)；
        //   ② ①读不满 b-a ⇒ 逐字「先读后删」：删之前读光标后 1 字，读到的必然就是被删掉的那个字。
        let text: string = '';
        let deleted: number = 0;
        if (liveCur >= anchor) {
          try { text = client.getForwardSync(b - a); } catch (e) { text = ''; }
        } else {
          try { text = client.getBackwardSync(b - a); } catch (e) { text = ''; }
        }
        if (text.length === b - a) {
          for (let i = 0; i < b - a; i++) {
            try { client.deleteBackwardSync(1); deleted++; } catch (e) { break; }
          }
        } else {
          text = '';
          for (let i = 0; i < b - a; i++) {
            let ch: string = '';
            try { ch = client.getBackwardSync(1); } catch (e) { ch = ''; }
            try { client.deleteBackwardSync(1); deleted++; } catch (e) { break; }
            text += ch;                                    // 逐字读出＝文档顺序，直接追加
          }
        }
        const afterPos: number = this.cursorIndex();
        this.selectAllRequested = false;
        if (text.length > 0) {
          this.pushUndo({ type: 'clear', text: text });
        }
        this.resetSelAnchor();
        console.info(`${TAG} H-275 sel-delete anchor=${anchor} liveCur=${liveCur} [${a},${b}] textLen=${text.length} deleted=${deleted} afterPos=${afterPos} head=${text.slice(0, 12)}`);
        this.notify();
        return true;
      }
      // 选区长度为 0：关模式收拢，交给常规退格
      this.selectionModeOn = false;
      this.resetSelAnchor();
    }
    // ② 全选路径：我们**自己发的 SELECT_ALL**，靠旗标判断(宿主选区读不到，不能用
    //   「getForwardSync 空 + getBackwardSync 有值」猜——那会误删光标停在文首的普通场景)。
    if (this.selectAllRequested) {
      this.selectAllRequested = false;
      this.walkCursorTo(0);                         // 收拢选区并走到文首(收拢后读文本才准，见 H-275b)
      // H-275b：全选删除不预读整框(选区激活时读回空串)，改为「先读后删」一直删到光标后无字，
      // 读到的字按顺序拼成撤销文本；删不动(读不到)就退回常规退格，保证不空转。
      let fullText: string = '';
      let deleted: number = 0;
      const cap: number = 200000;                   // 防御：任何情况下都不许死循环
      for (let i = 0; i < cap; i++) {
        let ch: string = '';
        try { ch = client.getBackwardSync(1); } catch (e) { ch = ''; }
        if (ch.length === 0) {
          break;
        }
        try { client.deleteBackwardSync(1); } catch (e) { break; }
        fullText += ch;
        deleted++;
      }
      if (deleted > 0) {
        const afterPos: number = this.cursorIndex();
        this.pushUndo({ type: 'clear', text: fullText });
        console.info(`${TAG} H-275 select-all delete deleted=${deleted} afterPos=${afterPos} head=${fullText.slice(0, 12)}`);
        this.notify();
        return true;
      }
      console.info(`${TAG} H-275 select-all delete: 读不到文本, 退回常规退格`);
      this.resetSelAnchor();
    }
    return false;
  }

  /** 退格：有编码先删编码；无编码才删编辑器字符。 */
  onBackspace(): void {
    // H-166(Qoder)：手动退格打断「连续输入」段——之后上滑清除只清退格之后新打的内容
    this.sessionCommitText = '';
    if (!this.engineReady) {
      // H-068：与字符键同队，ready 后按原顺序回放（U+0008 为退格哨兵）
      this.queueInput('\u0008');
      return;
    }
    // H-275(Qoder)：选区删除优先——长按 n 选择态或我们发的全选，整体删 + 压一条 'clear'
    // 撤销记录，让下滑/顶栏撤销一次性恢复（不再逐字删、逐字撤销，也不再不记记录无法恢复）。
    if (this.tryDeleteSelection()) {
      return;
    }
    const before: RimeContext = this.engine.getContext();
    if (before.preedit.length > 0) {
      // 编码态：删的是 IME 缓冲区（还没进宿主文本框），不进撤销栈（与安卓一致）
      const ctx: RimeContext = this.engine.deleteBackward();
      this.notify(ctx);
      return;
    }
    // H-261(Qoder 2026-10-28 16:0x，主人「退格删的字下滑反不回、顶栏撤销/重做也不认」)：
    // 删前先取光标前 1 字（backspace 删的就是它），记成 'clear' 记录，让下滑
    // undoLastAction 与顶栏 undoCommit/redoCommit 都能还原它。
    // 命名坑同 H-210（d.ts:1233/1282）：getForwardSync 才是光标**前**文（= deleteForwardSync 删的那侧）。
    const client = this.inputClient;
    let removed: string = '';
    if (client) {
      try {
        const head: string = client.getForwardSync(1);
        if (head.length > 0) {
          removed = head;
        }
      } catch (err) {
        const e = err as BusinessError;
        console.warn(`${TAG} onBackspace getForwardSync failed: ${e.code} ${e.message}`);
      }
    }
    if (removed.length > 0) {
      this.deleteEditor(1);
      this.pushUndo({ type: 'clear', text: removed });
    } else {
      // 已在行首（光标前无字）：只清编码，不记撤销
      this.deleteEditor(0);
    }
    this.engine.clear();
    this.notify();
  }

  /** 翻页：direction = 1 下一页，-1 上一页。 */
  flipPage(direction: number): void {
    const ctx: RimeContext = this.engine.flipPage(direction);
    this.notify(ctx);
  }

  /** 选项开关：ascii_mode = 中/英，zh_trad = 简/繁。
   *  H-067：开关切换后立即重取 context 并推给面板——挂码时切简繁，候选不能等下一次按键才转换。 */
  setOption(name: string, value: boolean): void {
    this.engine.setOption(name, value);
    this.notify();
  }

  /** v0.1.8：读引擎开关当前值（切方案后开关会重置，UI 需用此方法回填键面状态）。 */
  getOption(name: string): boolean {
    return this.engine.getOption(name);
  }

  /**
   * v0.1.6（H-042 弹性候选栏）：UI 按**实测可用宽度**决定一页几条候选并调本方法。
   * 调过之后引擎不再按横竖屏覆盖（`RealRimeEngine.uiPinned`），所以转屏时
   * 面板要自己重新量宽度再调一次——条数永远跟着宽度走，不跟取向硬绑。
   * 1..50，越界由引擎钳到边界；改变后页码回到 0。
   */
  setPageSize(size: number): void {
    const ctx: RimeContext = this.engine.setPageSize(size);
    this.notify(ctx);
  }

  /**
   * v0.1.7（H-028 ① 智能九键）：切 Rime 方案。
   * 九宫格面板 `panelMode==='t9'` 时切 `'sansheng_t9'`（数字→拼音由拼写代数完成），
   * 回 26 键/符号页时切回 `'wubi_pinyin'`。切方案会清空编码并回到第 0 页，
   * 所以这里直接把新 context 推给面板，不需要 UI 再自己刷新。
   * 不在引擎里自动判断按键类型：`?123` 里的数字必须继续直出，不能被当成九键编码。
   */
  selectSchema(id: string): boolean {
    const ok: boolean = this.engine.selectSchema(id);
    this.notify(this.engine.getContext());
    return ok;
  }

  /** H-178：当前方案 id（如 wubi_pinyin / sansheng_t9 / luna_pinyin）。 */
  getSchemaId(): string {
    return this.engine.getSchemaId();
  }

  /** 清空编码。 */
  clear(): void {
    const ctx: RimeContext = this.engine.clear();
    this.notify(ctx);
  }

  /** 面板页注册状态监听；传 undefined 注销。注册时立即推一次当前状态。 */
  setUiListener(listener: KeyboardListener | undefined): void {
    this.listener = listener;
    if (listener) {
      this.notify();
    }
  }

  // ---- 底层：上屏 / 删除 / 状态推送 ----

  /** H-068：引擎未就绪时按下的键先入队（最多 64 个，超限丢最旧）。 */
  private queueInput(token: string): void {
    if (this.pendingInputs.length >= 64) {
      this.pendingInputs.shift();
    }
    this.pendingInputs.push(token);
  }

  /** H-068：引擎 ready 后按原顺序回放排队按键；U+0008 走退格。 */
  private replayPendingInputs(): void {
    if (this.pendingInputs.length === 0) {
      return;
    }
    const queued: string[] = this.pendingInputs;
    this.pendingInputs = [];
    console.info(`${TAG} replay early keys: ${queued.length}`);
    for (let i = 0; i < queued.length; i++) {
      if (queued[i] === '\u0008') {
        this.onBackspace();
      } else {
        this.onKey(queued[i]);
      }
    }
  }

  private insertText(text: string, recordUndo: boolean = true): void {
    const client = this.inputClient;
    if (!client) {
      console.warn(`${TAG} insertText skipped (no client): "${text}"`);
      return;
    }
    // P1-2 修复：pushUndo/lastCommitText 必须在上屏**成功回调**里执行——
    // 若上屏失败仍写入，会留「幽灵 commit 记录」，之后下滑撤销 deleteEditor(N) 会平白删用户正文且不可恢复。
    // H-261(Qoder 2026-10-28)：recordUndo=false 用于「撤销/重做」把文字插回——此时绝不能再 pushUndo，
    // 因为 pushUndo 会 `redoStack=[]` 把重做栈清空 ⇒ 重做只能做一次（主人「重做只能重做一次，两个不统一」）。
    client.insertText(text).then(() => {
      if (recordUndo) {
        this.pushUndo({ type: 'commit', text: text });
      }
      this.lastCommitText = text;
      this.sessionCommitText += text;   // H-166(Qoder)：连续上屏累计
    }).catch((err: BusinessError) => {
      console.error(`${TAG} insertText: ${err.code} ${err.message}`);
    });
  }

  /** H-154：压撤销栈（上限 10，超限丢最旧）。
   *  H-241 契约 §3-8「可撤销步数」（5–30，默认 10）：上限改读设置值；
   *  设置页改小时 applySettingsChanged() 当场裁到新的封顶（判据＝连打 N+2 段后只能撤回 N 段）。 */
  private pushUndo(record: UndoRecord): void {
    if (this.undoStack.length >= this.undoLimit) {
      this.undoStack.shift();
    }
    this.undoStack.push(record);
    // H-177：一旦有新动作，之前的「可重做」记录全部作废（标准撤销栈语义）
    this.redoStack = [];
  }

  /**
   * H-154（需求 3）：上滑清除内容并记录——编码态保存 preedit，无编码态保存最近上屏文本，
   * 压 { type: 'clear' } 入栈后执行清除。UI（退格键上滑）调用。
   */
  clearAllAndRecord(): void {
    const before: RimeContext = this.engine.getContext();
    if (before.preedit.length > 0) {
      // 编码态：保存 preedit 供撤销恢复，清编码即可
      const pre: string = before.preedit;
      if (pre.length > 0) {
        this.pushUndo({ type: 'clear', text: pre });
      }
      this.engine.clear();
    } else {
      // P1-1 修复：已上屏态必须真正删除编辑器里的文本（此前只 engine.clear()，
      // preedit 为空 ⇒ 看着没反应，真机上是空动作）。保存后 deleteEditor 删回，撤销时恢复。
      // H-166(Qoder)：删的是**本次会话连续上屏的整段**（sessionCommitText），不是最后一段；
      // 会话内还没上过屏时退回 lastCommitText。
      const saved: string = this.sessionCommitText.length > 0 ? this.sessionCommitText : this.lastCommitText;
      if (saved.length > 0) {
        this.pushUndo({ type: 'clear', text: saved });
        this.deleteEditor(saved.length);
        this.lastCommitText = '';
        this.sessionCommitText = '';
      }
      this.engine.clear();
    }
    this.notify();
  }

  /**
   * H-154（需求 3）：下滑撤销——取栈顶记录：
   *  'commit'（上屏记录）→ deleteForward 删掉该文本 + clear()（回编码前态）；
   *  'clear'（上滑清除记录）→ insertText(savedText) 恢复原文；
   *  空栈 → 无操作。
   */
  /** H-167(Qoder)：下滑——撤销最近一次「清除」（上滑删到标点 / 长按清空全部）。
   *  只认 'clear' 记录；栈里的 'commit' 不是清除，跳过不动（主人原话：下滑只撤回清除）。
   *  H-177（主人 2026-10-25 16:5x「对照安卓抄」）：工具栏「撤销」按钮要能撤**上屏**，
   *  所以这里分两路——`undoLastAction()` 保持下滑语义（只撤 clear），
   *  `undoCommit()` 是按钮语义（撤 commit）。两条路互不干扰，退格下滑行为不变。 */
  undoLastAction(): void {
    let cleared: UndoRecord | undefined = undefined;
    while (this.undoStack.length > 0) {
      const r: UndoRecord | undefined = this.undoStack.pop();
      if (r !== undefined && r.type === 'clear') {
        cleared = r;
        break;
      }
    }
    if (cleared === undefined) {
      console.info(`${TAG} undoLastAction: no clear record`);
      return;
    }
    this.insertText(cleared.text);
    // H-167(Qoder)：撤销后把内容补回缓冲区（保持账实一致）
    this.sessionCommitText += cleared.text;
    this.notify();
    console.info(`${TAG} undo clear restore ${cleared.text.length} chars`);
  }

  /** H-177：工具栏「撤销」——撤回最近一次**上屏**（安卓工具栏第一枚功能）。
   *  实现要点：IME Kit 的 deleteForward(n) 真机上只删 1 个（H-167 实测 n=17/45 都只删 1），
   *  所以按记录文本长度**逐个删**；删完把记录挪到 redoStack，「重做」能把这段文字放回去。 */
  undoCommit(): void {
    let rec: UndoRecord | undefined = undefined;
    while (this.undoStack.length > 0) {
      const r: UndoRecord | undefined = this.undoStack.pop();
      // H-261：工具栏「撤销」也认退格删字——'clear' 记录（整框清空／退格单删都记成 'clear'）
      if (r !== undefined && (r.type === 'commit' || r.type === 'clear')) {
        rec = r;
        break;
      }
    }
    if (rec === undefined) {
      console.info(`${TAG} undoCommit: no commit/clear record`);
      return;
    }
    if (rec.type === 'commit') {
      const n: number = rec.text.length;
      if (n > 0) {
        this.deleteEditor(n);
      }
      // 缓冲区账实一致：撤掉这段累计文本
      if (this.sessionCommitText.endsWith(rec.text)) {
        this.sessionCommitText = this.sessionCommitText.slice(0, this.sessionCommitText.length - n);
      }
    } else {
      // 'clear'（退格单删／整框清空）：把删掉的字放回光标处。
      // H-261：recordUndo=false —— 撤销这一步不能再 pushUndo（否则清空重做栈，重做失效）；
      // sessionCommitText 的累计由 insertText 回调统一做，这里不再手加（防重复计）。
      this.insertText(rec.text, false);
    }
    this.redoStack.push(rec);
    this.notify();
    console.info(`${TAG} undoCommit: ${rec.type} restored ${rec.text.length} chars, redo depth ${this.redoStack.length}`);
  }

  /** H-177：工具栏「重做」——把最近一次撤销掉的上屏放回去。 */
  redoCommit(): void {
    const rec: UndoRecord | undefined = this.redoStack.pop();
    if (rec === undefined) {
      console.info(`${TAG} redoCommit: redo stack empty`);
      return;
    }
    if (rec.type === 'commit') {
      // 重做＝把撤掉的上屏文字放回。H-261：recordUndo=false —— 不得 pushUndo（会清空重做栈），
      // 否则「重做」只能做一次；记录由下面 undoStack.push(rec) 原样归位。
      this.insertText(rec.text, false);
    } else {
      // 'clear'（退格单删／整框清空）重做＝把刚还原的字再删掉
      this.deleteEditor(rec.text.length);
    }
    this.undoStack.push(rec);
    this.notify();
    console.info(`${TAG} redoCommit: ${rec.type} reapplied ${rec.text.length} chars`);
  }

  /** H-177：工具栏「移动光标」——`InputClient.moveCursorSync(direction)`
   *  （`@ohos.inputMethodEngine.d.ts:1371`；direction 1=上 2=下 3=左 4=右）。
   *  鸿蒙 IME 的输入框是宿主 app 的，光标移动必须走这个 API，自己算位置不可行。 */
  moveEditorCursor(direction: number): void {
    // H-220(Qoder)：「选择」开着 ⇒ 方向键变成扩展选区（安卓选择键口径），不再动光标。
    if (this.selectionModeOn) {
      this.extendSelection(direction);
      return;
    }
    this.rawMoveCursor(direction);
    this.resetSelAnchor();
  }

  /** H-220：真正的裸光标移动（`moveCursorSync`），不带选区语义。 */
  private rawMoveCursor(direction: number): void {
    const client = this.inputClient;
    if (!client) {
      console.warn(`${TAG} H-177 moveEditorCursor skipped (no client)`);
      return;
    }
    this.selectAllRequested = false;          // H-275：光标移动 ⇒ 整框删除旗标作废
    try {
      client.moveCursorSync(direction);
      console.info(`${TAG} H-177 moveEditorCursor dir=${direction} ok`);
    } catch (err) {
      const e = err as BusinessError;
      console.error(`${TAG} H-177 moveEditorSync(${direction}): ${e.code} ${e.message}`);
    }
  }

  /** H-220(Qoder)：开/关「选择」模式（安卓文本编辑窗的选择键）。
   *  开=锚定当前光标位；关=把选区收拢回光标（`selectByRangeSync{idx,idx}`，
   *  1413 行），与安卓「取消选择」一致。 */
  toggleSelectionMode(): void {
    this.selectionModeOn = !this.selectionModeOn;
    this.selectAllRequested = false;          // H-275：开/关「选择」接管选区语义，整框旗标作废
    if (this.selectionModeOn) {
      this.selAnchor = this.cursorIndex();
    } else {
      const client = this.inputClient;
      if (client) {
        try {
          const idx: number = client.getTextIndexAtCursorSync();
          client.selectByRangeSync({ start: idx, end: idx });
          this.selCursor = idx;
          this.selAnchor = idx;
        } catch (e) { /* ignore */ }
      }
    }
    console.info(`${TAG} H-220 toggleSelectionMode -> ${this.selectionModeOn} anchor=${this.selAnchor}`);
    this.notify();
  }

  isSelectionMode(): boolean {
    return this.selectionModeOn;
  }

  /** H-220：当前光标下标（读不到给 0）。 */
  private cursorIndex(): number {
    const client = this.inputClient;
    if (!client) {
      return 0;
    }
    try {
      return client.getTextIndexAtCursorSync();
    } catch (e) {
      return 0;
    }
  }

  /** H-224/H-229(Qoder)：把光标定位到 pos。**两条路，按有没有选区分开**。
   *  ① 开着「选择」⇒ 落**非空区间** `{min(anchor,pos), max(anchor,pos)}`，一次 `selectByRangeSync`。
   *     宿主认这条（H-224 主人真手 16:5x「长按 n 再长按 sd 管用」），且**只能写一次**——
   *     写第二次会被当「重新落选区」，把刚才的选区抹掉。
   *     注意 `anchor` 的取用分两种（H-230，主人 18:3x「开选择时行首行尾选的是前半文后半文不是一行」）：
   *       · 全文级移动（f/g=文首/文末）⇒ 用 `selAnchor`（开选择时的起选点），扩到文首/文尾，正确。
   *       · 行级移动（s/d=行首/行尾，`lineMove=true`）⇒ **重新以当前光标实时位（`cursorIndex()`）起选**，
   *         选区只落在「当前行」内（光标↔当前行首/行尾），不会跨到开选择时那一行、选成半篇文。
   *         改前用 `selAnchor` 起选，一旦 anchor 在别处，min/max 就跨了多行＝主人说的「前半文/后半文」。
   *  ② 关着「选择」⇒ **绝不用 `selectByRangeSync`**（H-229 定论）：`{pos,pos}` 这种零长度区间
   *     宿主**一律不认**，写一次不认、写两次也不认，而且会把后续定位一起带坏。
   *     真机铁证（2026-10-27 18:23，主人「ssdfg都不管用了」）：
   *       s 写 pos=66 → 回读 86 ／ f 写 pos=0 → 回读 86 ／ g 写 pos=130 → 回读 86。
   *     改走 `moveCursorSync(direction)` 逐步走（hjkl 连发用的就是它，主人真手验过有效）。
   *  **为什么不能有「中间收拢」**（14:58 真手铁证，`docs/evidence/2026-10-27/h220_owner_hilog.txt`）：
   *  宿主把每次 `selectByRangeSync` 当重新落选区 ⇒ 先收拢再扩回去的两次写，在开着选择按 s/d 时
   *  中间那次收拢会把选区抹掉（「选择白开了」）。 */
  private afterCursorJump(pos: number, lineMove: boolean = false): void {
    const client = this.inputClient;
    if (!client) {
      this.selCursor = pos;
      this.selAnchor = pos;
      return;
    }
    if (this.selectionModeOn) {
      // 开着「选择」⇒ 落**非空区间**（宿主认这条，H-224 真手验过）。
      // 只写一次：写第二次会被宿主当成「重新落选区」，把刚才的选区抹掉。
      // H-230：行级移动用「当前光标实时位」重新起选（选区锁在当前行），全文级移动沿用开选择时的起选点。
      // 注意必须用实时 read（`cursorIndex()`）而不是记账的 `selCursor`：选择模式下 hjkl 走宿主原生
      // `selectByMovementSync`（H-220 主路径），它不回写 `selCursor`，记账值会停在开选择那刻，
      // 用它起选又会跨行选成半篇文。关选择在 afterCursorJump 里统一把 selCursor 跟到新位，这里只读即可。
      const anchor: number = lineMove ? this.cursorIndex() : this.selAnchor;
      const start: number = Math.min(anchor, pos);
      const end: number = Math.max(anchor, pos);
      try {
        client.selectByRangeSync({ start: start, end: end });
        console.info(`${TAG} H-230 cursorJump pos=${pos} anchor=${anchor} range=${start},${end} lineMove=${lineMove} selMode=true`);
      } catch (e) {
        const err = e as BusinessError;
        console.warn(`${TAG} H-224 afterCursorJump selectByRangeSync(${start},${end}): ${err.code} ${err.message} ⇒ 只记账`);
      }
      this.selCursor = pos;
      return;
    }
    // 关着「选择」⇒ **不许用 selectByRangeSync 落位**。
    // H-229（Qoder 2026-10-27 18:2x，主人「ssdfg都不管用了」）真机定论：
    // `selectByRangeSync({pos,pos})` 这种**零长度区间宿主一律不认**——写一次不认、写两次也不认
    // （我 18:10 补的第二次写同样无效），而且它会让后续定位全都不生效：
    //   18:23:20 s 写 pos=66  → 回读 idx=86
    //   18:23:23 f 写 pos=0   → 回读 idx=86
    //   18:23:24 g 写 pos=130 → 回读 idx=86
    // 之前 s/d「管用」都是**开着选择**测的（那时写的是非空区间），关着选择从来没真的动过。
    // 改走主人已验证可用的那条 API：`moveCursorSync(direction)`（hjkl 连发就是它，真手确认有效），
    // 按「当前位置 → 目标位置」的差值逐步走。3=左 4=右。
    this.walkCursorTo(pos);
    this.selCursor = pos;
    this.selAnchor = pos;
  }

  /** H-229：把光标从当前位置**逐步**挪到 pos（只用 `moveCursorSync`，不用零长度落位）。
   *  步数上限 4000 是防呆（远超任何输入框的合理长度），到上限就停并告警，不无限循环。
   *  每一步都回读，宿主不认（回读值没变）就立刻停，不在原地空转。 */
  private walkCursorTo(pos: number): void {
    const client = this.inputClient;
    if (!client) {
      return;
    }
    this.selectAllRequested = false;          // H-275：光标移动 ⇒ 整框删除旗标作废
    let cur: number = this.cursorIndex();
    if (cur === pos) {
      console.info(`${TAG} H-229 walkCursorTo already at ${pos}`);
      return;
    }
    const step: number = pos > cur ? 4 : 3;   // 4=右 3=左（与 moveEditorCursor 同口径）
    let guard: number = 0;
    while (cur !== pos && guard < 4000) {
      try {
        client.moveCursorSync(step);
      } catch (e) {
        const err = e as BusinessError;
        console.warn(`${TAG} H-229 moveCursorSync(${step}) failed: ${err.code} ${err.message}`);
        break;
      }
      const next: number = this.cursorIndex();
      if (next === cur) {
        console.warn(`${TAG} H-229 walkCursorTo stuck at ${cur} (want ${pos}) ⇒ 宿主不认这个方向`);
        break;
      }
      cur = next;
      guard++;
    }
    console.info(`${TAG} H-229 walkCursorTo pos=${pos} now=${cur} steps=${guard}`);
  }

  /** H-220：无选区时把光标记账位跟上去（下次开「选择」从这里起选）。 */
  private resetSelAnchor(): void {
    this.selCursor = this.cursorIndex();
  }

  /** H-220：扩展选区。鸿蒙 `EditorAttribute` 读不到选区（只有 isTextPreviewSupported），
   *  所以选区另一端由我们自己记账：横移直接加减，纵移问一次 `getTextIndexAtCursorSync`
   *  （IME Kit 对宿主上下移动不改文本长度，返回值就是移动后的光标位），再
   *  `selectByRangeSync({min(anchor,cursor), max(...)})` 落选区（`d.ts:1413`）。
   *  宿主没实现 selectByRange 时退回 `selectByMovementSync`（`d.ts:1455`，交给宿主选一格）。 */
  private extendSelection(direction: number): void {
    const client = this.inputClient;
    if (!client) {
      console.warn(`${TAG} H-220 extendSelection skipped (no client)`);
      return;
    }
    // 主路径：**宿主原生**扩选（`selectByMovementSync`，`d.ts:1455`）——锚点由宿主自己记，
    // 来回走能扩能缩。真机教训（主人 14:58 手测：连按右移 range 恒为 `x,40`）：先前用
    // 「自己算位 + selectByRangeSync」当主路径，宿主把每次 selectByRange 当成**重新落选区**
    // 而不是延续锚点 ⇒ 越动越不对。现在只在宿主不认 selectByMovement 时才退回记账式。
    try {
      client.selectByMovementSync({ direction: direction as inputMethodEngine.Direction });
      console.info(`${TAG} H-220 extendSelection native dir=${direction} ok`);
      return;
    } catch (err) {
      const e = err as BusinessError;
      console.warn(`${TAG} H-220 selectByMovementSync(${direction}): ${e.code} ${e.message} ⇒ 退记账式 selectByRangeSync`);
    }
    if (direction === 3) {
      this.selCursor = Math.max(0, this.selCursor - 1);
    } else if (direction === 4) {
      this.selCursor = this.selCursor + 1;
    } else {
      const idx: number = this.cursorIndex();
      this.selCursor = idx > 0 || this.selCursor === 0 ? idx : this.selCursor;
    }
    const a: number = Math.min(this.selAnchor, this.selCursor);
    const b: number = Math.max(this.selAnchor, this.selCursor);
    try {
      client.selectByRangeSync({ start: a, end: b });
      console.info(`${TAG} H-220 extendSelection fallback dir=${direction} range=${a},${b} ok`);
    } catch (err2) {
      const e2 = err2 as BusinessError;
      console.error(`${TAG} H-220 selectByRangeSync(${a},${b}): ${e2.code} ${e2.message}`);
    }
  }

  /** H-210(Qoder)：M-249(CodeArts) 等的封装——长按 s = 全文首（安卓三生 s=Home）。
   *  鸿蒙 IME 没有「行首/翻屏」概念，只能定位宿主编辑框光标 ⇒ 交给 `afterCursorJump(0)`
   *  一次落位（H-224：开着「选择」时是**扩选到全文首**，不再先 `{0,0}` 把选区抹掉）。
   *  （此处原有一条「全文尾——用选区定位实现」的注释挂在全文首函数头上，位置放错、
   *    与 `moveCursorToEnd` 自己的注释重复，H-224 一并清掉。） */
  moveCursorToStart(): void {
    const client = this.inputClient;
    if (!client) {
      console.warn(`${TAG} H-210 moveCursorToStart skipped (no client)`);
      return;
    }
    try {
      this.afterCursorJump(0);
      console.info(`${TAG} H-210 moveCursorToStart ok`);
    } catch (err) {
      const e = err as BusinessError;
      console.error(`${TAG} H-210 moveCursorToStart: ${e.code} ${e.message}`);
    }
  }

  /** H-210(Qoder)：长按 d = 全文尾（安卓三生 d=End）。IME Kit 没有「全文长度」API，
   *  只能算出来：`getTextIndexAtCursorSync()`（:1496，光标下标）＋ 光标后取字（:1233/:1282）
   *  指数试探——返回值短于请求值即已取到文尾，全文尾下标 = 光标下标 + 光标后文字长度，
   *  再交给 `afterCursorJump(end)` 一次落位（H-224：开选择 ⇒ 扩选到全文尾）。
   *  **命名坑（Mate80 2026-10-27 00:3x 实锤，测试串 ABC→1→9 得 `1A9BC` 才暴露）**：
   *  取光标**后**文字要用 `getBackwardSync`（d.ts:1270 "text after the cursor"），
   *  `getForwardSync` 是光标**前**（d.ts:1221 "text before the cursor"）——名字与方向相反，
   *  与 `deleteForward` 删光标前文同族。用 getForward 探"tail"实为光标前文，
   *  end 算成 idx+idx ⇒ 光标落进文中。 */
  moveCursorToEnd(): void {
    const client = this.inputClient;
    if (!client) {
      console.warn(`${TAG} H-210 moveCursorToEnd skipped (no client)`);
      return;
    }
    try {
      const idx = client.getTextIndexAtCursorSync();
      let probe = 512;
      let tail = '';
      for (let i = 0; i < 12; i++) {           // 512*4^11 > 5 亿字，实际两三轮就够
        tail = client.getBackwardSync(probe);
        if (tail.length < probe) {
          break;
        }
        probe *= 4;
      }
      const end = idx + tail.length;
      this.afterCursorJump(end);
      console.info(`${TAG} H-210 moveCursorToEnd idx=${idx} tail=${tail.length} ok`);
    } catch (err) {
      const e = err as BusinessError;
      console.error(`${TAG} H-210 moveCursorToEnd: ${e.code} ${e.message}`);
    }
  }

  /** H-218(Qoder 2026-10-27，主人「把行首行尾上页下页上下左右全选复制粘贴都放进去，参照安卓版」）：
   *  行首 = 光标回退到「光标前文」最后一个换行符（'
'）之后。命名坑同 H-210：`getForwardSync` 是光标**前**文。
   *  取文用指数试探（同 moveCursorToEnd 的套路），覆盖长文。 */
  moveCursorToLineStart(): void {
    const client = this.inputClient;
    if (!client) {
      console.warn(`${TAG} H-218 moveCursorToLineStart skipped (no client)`);
      return;
    }
    try {
      const idx = client.getTextIndexAtCursorSync();
      let probe = 512;
      let head = '';
      for ( let i = 0; i < 12 && idx > head.length; i++) {
        head = client.getForwardSync(Math.min(probe, idx));
        if (head.length < probe || head.length >= idx) {
          break;
        }
        probe *= 4;
      }
      const nl = head.lastIndexOf('\n');
      const pos = nl < 0 ? 0 : idx - head.length + nl + 1;
      this.afterCursorJump(pos, true);
      console.info(`${TAG} H-218 moveCursorToLineStart idx=${idx} pos=${pos} ok`);
    } catch (err) {
      const e = err as BusinessError;
      console.error(`${TAG} H-218 moveCursorToLineStart: ${e.code} ${e.message}`);
    }
  }

  /** H-218：行尾 = 光标前进到「光标后文」第一个 '\n' 之前（找不到即全文尾）。
   *  光标后文 = `getBackwardSync`（命名反转，见 H-210 坑注）。 */
  moveCursorToLineEnd(): void {
    const client = this.inputClient;
    if (!client) {
      console.warn(`${TAG} H-218 moveCursorToLineEnd skipped (no client)`);
      return;
    }
    try {
      const idx = client.getTextIndexAtCursorSync();
      let tail = '';
      try {
        tail = client.getBackwardSync(4096);
      } catch (e1) {
        tail = '';
      }
      const nl = tail.indexOf('\n');
      const pos = nl < 0 ? idx + tail.length : idx + nl;
      this.afterCursorJump(pos, true);
      console.info(`${TAG} H-218 moveCursorToLineEnd idx=${idx} pos=${pos} ok`);
    } catch (err) {
      const e = err as BusinessError;
      console.error(`${TAG} H-218 moveCursorToLineEnd: ${e.code} ${e.message}`);
    }
  }

  /** H-218：上5行/下5行（面板格标签，H-235 起不再写「上页/下页」）= 光标纵向连移 N 行。
   *  **为什么不是「页」**：IME Kit 拿不到宿主可视区域 ⇒ 没有「页」这个量可算（与 H-226 把 f/g
   *  角标改成「文首/文末」同一个理由）；5 行是安卓 TextEditingWindow 同族键盘一屏正文的经验值。
   *  宿主不支持 UP/DOWN 时静默无效果（这条如实写进台账，别当已验）。 */
  moveCursorPage(lines: number): void {
    const step: number = lines > 0 ? 2 : 1;   // CursorExtensionType: 1=UP 2=DOWN
    const n: number = Math.min(8, Math.abs(lines));
    for (let i = 0; i < n; i++) {
      this.moveEditorCursor(step);
    }
    console.info(`${TAG} H-218 moveCursorPage n=${n} dir=${step}`);
  }

  /**
   * 删除光标前 length 个字符。注意：IME Kit 的 deleteBackward/deleteForward
   * 语义与直觉相反，退格方向要用 deleteForward（参考壳实测结论）。
   */
  /**
   * H-155：编辑框级动作（全选/剪切/复制/粘贴），直接操作宿主编辑框文字内容。
   * 通过 InputClient.sendExtendAction 实现（@ohos.inputMethodEngine，API 10+）。
   * 注意：PASTE 需要宿主 app 自己申请 ohos.permission.READ_PASTEBOARD，
   *       个别 app 可能静默失败（非输入法侧权限），属正常。
   */
  sendEditorAction(action: inputMethodEngine.ExtendAction): void {
    const client = this.inputClient;
    if (!client) {
      console.warn(`${TAG} sendEditorAction skipped (no client): ${action}`);
      return;
    }
    // H-275(Qoder)：全选后我们**自己知道**有整框选区(宿主选区读不到)，记旗标让下一次退格/长按 m
    // 当「整框删除 + 一条 'clear' 撤销记录」处理；其它编辑动作(CUT/COPY/PASTE…)一律清旗标，
    // 避免过期旗标把后续一次退格误删整框。
    this.selectAllRequested = (action === inputMethodEngine.ExtendAction.SELECT_ALL);
    client.sendExtendAction(action).catch((err: BusinessError) => {
      console.error(`${TAG} sendExtendAction(${action}): ${err.code} ${err.message}`);
    });
  }

  /** H-204(Qoder)：复制后把选区收拢到光标——主人 2026-10-26 原话「全选以后，复制完了，
   *  应该退到光标状态，这样能看出来是复制了」。先发 COPY，等 150ms 让宿主把选区内容记进
   *  剪贴板，再 `moveCursorSync(4=右)` 收拢选区（编辑器把光标移动视为取消选中）。
   *  立即移动会有竞态：宿主还没读选区，选区就被取消 ⇒ 反而复制不到。 */
  copyThenCollapse(): void {
    this.sendEditorAction(inputMethodEngine.ExtendAction.COPY);
    setTimeout(() => {
      this.moveEditorCursor(4);
    }, 150);
  }

  /** H-204(Qoder)：读剪贴板并把文字上屏。**只能在 PasteButton.onClick 返回 SUCCESS 之后调用**
   *  ——安全控件给的是「对本次点击的临时读权限」，回调外调用会被系统拒绝（错误码 201）。
   *  为什么不让宿主自己贴：`sendExtendAction(PASTE)` 要求宿主实现 handleExtendAction 且持有
   *  READ_PASTEBOARD；主人实测多数 app 没反应（「cv 的复制粘贴还是不行」）。本方法读到文字后
   *  直接 insertText，与宿主是否支持 PASTE 无关。
   *  华为官方答复：应用级输入法直接读剪贴板会被拒（即使开「完整体验模式」），PasteButton 是
   *  系统给的唯一合规通道——所以不申请 READ_PASTEBOARD（受限权限，需 ACL 签名）。
   *  onResult(ok, 提示文案) 用于 UI 弹 toast，成功/失败都给可见反馈。 */
  pasteClipboardText(onResult: (ok: boolean, msg: string) => void): void {
    let board: pasteboard.SystemPasteboard;
    try {
      board = pasteboard.getSystemPasteboard();
    } catch (e) {
      const err = e as BusinessError;
      console.error(`${TAG} H-204 getSystemPasteboard: ${err.code} ${err.message}`);
      onResult(false, '剪贴板不可用');
      return;
    }
    let has: boolean = false;
    try {
      has = board.hasDataSync();   // 官方建议：先判断有无数据，避免无效读取（hasData() 返回 Promise，这里要同步版）
    } catch (e) {
      has = true;                  // 读不到状态（无权限会抛）也别拦，交给 getData 的真实结果判
    }
    if (!has) {
      onResult(false, '剪贴板是空的');
      return;
    }
    board.getData().then((data: pasteboard.PasteData) => {
      let text: string = '';
      try {
        text = data.getPrimaryText();
      } catch (e) {
        text = '';
      }
      if (text.length === 0) {
        onResult(false, '剪贴板里没有文字');
        return;
      }
      this.insertText(text);
      console.info(`${TAG} H-204 pasteClipboardText ${text.length} chars`);
      onResult(true, `已粘贴 ${text.length} 字`);
    }).catch((err: BusinessError) => {
      console.error(`${TAG} H-204 getData: ${err.code} ${err.message}`);
      onResult(false, `读剪贴板失败（${err.code}）`);
    });
  }

  /**
   * H-155：绕过 Rime 标点转写，直接把原始字符串上屏（用于句号键上滑出半角英文点等）。
   * 不走 onKey（onKey 经引擎会被中文标点转写成全角），直接 insertText 到编辑框。
   */
  insertRaw(text: string): void {
    this.insertText(text);
  }

  /** H-167(Qoder)：删光标前 length 个字符。
   *  鸿蒙 IME Kit 的 deleteForward(n)/deleteForwardSync(n) 真机上都只删 1 个字符
   *  （实测 n=17／45 都只产生一条 rangeBefore [x,x+1] 记录），所以必须逐个删。
   *  IME 扩展进程里 setTimeout 不可靠（实测循环 3 次就停），改成同步紧循环——
   *  deleteForwardSync 是同步 IPC，背靠背调用实测能连续生效。
   */
  private deleteEditor(length: number): void {
    const client = this.inputClient;
    if (!client) {
      return;
    }
    for (let i: number = 0; i < length; i++) {
      try {
        client.deleteForwardSync(1);
      } catch (err) {
        const e = err as BusinessError;
        console.error(`${TAG} deleteForwardSync(1) at ${i}: ${e.code} ${e.message}`);
        return;
      }
    }
  }

  /** H-220r3(Qoder，主人「长按m是删除右边的内容…和退格重复了」)：删**光标后**1 个字符＝Del/删除。
   *  命名坑（d.ts 权威口径，`@ohos.inputMethodEngine.d.ts:1086/1135`）：
   *  `deleteForwardSync` 删的是「text **before** the cursor」（= 退格），
   *  `deleteBackwardSync` 删的才是「text **after** the cursor」（= 删除/Del）。
   *  所以 m 用 deleteBackwardSync，不能复用退格那条 deleteEditor 路径。
   */
  deleteAfterCursor(): void {
    const client = this.inputClient;
    if (!client) {
      return;
    }
    // H-275(Qoder)：长按 m 删除。有选区(选择态/全选)时整体删 + 压一条 'clear' 撤销记录，
    // 否则才走原来的「删光标后 1 字」(Del)。没选区时 tryDeleteSelection 返回 false，落到下面。
    if (this.tryDeleteSelection()) {
      return;
    }
    try {
      client.deleteBackwardSync(1);
    } catch (err) {
      const e = err as BusinessError;
      console.error(`${TAG} H-220 deleteBackwardSync(1): ${e.code} ${e.message}`);
    }
  }

  /** H-167(Qoder)：算「删到上一个标点/空格为止」要删几个字符——**只看缓冲区**。
   *  从缓冲区尾部往前找第一个分隔符，删到它之后；找不到就删整个缓冲区。
   */
  private segmentLengthToDelete(): number {
    return this.segmentLengthToDeleteIn(this.sessionCommitText);
  }

  /** H-208：对**给定文本**算「删到上一个分隔符」的段长（编辑框真实文本与账本共用同一套规则）。 */
  private segmentLengthToDeleteIn(back: string): number {
    if (back.length === 0) {
      return 0;
    }
    // H-167(Qoder)：分隔符判断——全角标点用字符串包含，控制字符与反斜杠用码点判（避开转义）
    const SEP_STR: string = ' ，。、；：？！（）【】《》「」“”…—·,.;:?!()[]{}<>`~@#$%^&*+=/|-_';
    const isSep = (c: string): boolean => {
      const code: number = c.charCodeAt(0);
      if (code === 32 || code === 9 || code === 10 || code === 13) { return true; }  // 空格/制表/换行
      if (code === 92) { return true; }  // 反斜杠
      if (code === 39 || code === 34) { return true; }  // 单/双引号
      return SEP_STR.indexOf(c) >= 0;
    };
    for (let i: number = back.length - 1; i >= 0; i--) {
      if (isSep(back.charAt(i))) {
        const n: number = back.length - 1 - i;
        return n > 0 ? n : 1;   // 光标紧贴标点：至少删 1 个（那个标点本身）
      }
    }
    return back.length;
  }

  /** H-208（Qoder 2026-10-26 21:0x，主人原话「下滑退格出的内容和上滑删除的对不上，你没看见吗」）：
   *  上滑「删到上一个分隔符」原来**只按 `sessionCommitText` 账本算**，而账本是「每次 commit 拼起来」，
   *  与编辑框里真实字符顺序不一定一致（整词上屏、宿主自己插字、光标挪过都会错位）。
   *  真机实测（v0/v2 截图）：上滑删掉 `止shame规下灯你的划欧式`，下滑恢复的却是
   *  `ame规划欧式下灯你的划欧式`——字数一样、内容不同，正是主人说的「对不上」。
   *  修法：**以编辑框为准**——先 `getBackward(n)` 读光标前真实文本，用**它**算分隔符位置，
   *  删多少、存什么（undo 记录）都取真实文本；账本只跟着同步，不再当依据。
   *  读失败（无 client / 异常）才退回账本，且日志写明「用的是账本，可能与编辑框不一致」。 */
  clearToLastSeparator(): void {
    const client = this.inputClient;
    // H-208 真机返工（2026-10-26 21:1x）：原来用异步 `getBackward()`，真机上**返回空串**
    // （日志 `clearToLastSeparator: getBackward 空 ⇒ 退回账本`），等于没修。改同步版
    // `getBackwardSync()`——它在同一帧直接返回光标前文本，不受 attach 时序影响。
    let real: string = '';
    if (client !== undefined) {
      try {
        real = client.getBackwardSync(200);
      } catch (err) {
        const e = err as BusinessError;
        console.warn(`${TAG} clearToLastSeparator getBackwardSync failed: ${e.code} ${e.message}`);
        real = '';
      }
    }
    if (real.length === 0) {
      console.info(`${TAG} clearToLastSeparator: 读不到编辑框文本（client=${client === undefined ? '无' : '有'}）⇒ 退回账本`);
      this.clearToLastSeparatorFromBuffer();
      return;
    }
    const n: number = this.segmentLengthToDeleteIn(real);
    if (n <= 0) {
      this.notify();
      return;
    }
    const saved: string = real.slice(-n);
    this.pushUndo({ type: 'clear', text: saved });
    this.deleteEditor(n);
    // 账本**按真实文本重建**（不再凭长度猜：编辑框 20 字、账本 8 字的错位就是这么来的）
    this.sessionCommitText = real.slice(0, real.length - n);
    this.lastCommitText = '';
    this.engine.clear();
    this.notify();
    console.info(`${TAG} clearToLastSeparator(编辑框为准): deleted ${n} chars，实际删除 ${saved.length} 字` +
      `，恢复文本=${saved}`);
  }

  /** H-208：读不到编辑框时的旧路径（只按账本），保留作兜底并在日志里说明。 */
  private clearToLastSeparatorFromBuffer(): void {
    const n: number = this.segmentLengthToDelete();
    if (n <= 0) {
      this.notify();
      return;
    }
    const saved: string = this.sessionCommitText.slice(-n);
    if (saved.length > 0) {
      this.pushUndo({ type: 'clear', text: saved });
    }
    this.deleteEditor(n);
    this.sessionCommitText = this.sessionCommitText.slice(0, -n);
    this.lastCommitText = '';
    this.engine.clear();
    this.notify();
    console.info(`${TAG} clearToLastSeparator(账本兜底): deleted ${n} chars, buffer left ${this.sessionCommitText.length}`);
  }

  /** H-167(Qoder)：长按——清空缓冲区全部内容（逐个删，可撤销）。
   *  H-208（2026-10-26 21:1x）：同样**以编辑框真实文本为准**——账本可能落后于编辑框
   *  （真机实测账本 8 字 / 编辑框 20 字），按账本删会漏删、按账本存会恢复出错误内容。
   *  读不到编辑框时才退回账本。 */
  clearAllContent(): void {
    let back: string = this.sessionCommitText;
    const client = this.inputClient;
    if (client !== undefined) {
      try {
        const real: string = client.getBackwardSync(200);
        if (real.length > 0) {
          back = real;
        }
      } catch (err) {
        const e = err as BusinessError;
        console.warn(`${TAG} clearAllContent getBackwardSync failed: ${e.code} ${e.message} ⇒ 用账本`);
      }
    }
    if (back.length === 0) {
      this.engine.clear();
      this.notify();
      return;
    }
    this.pushUndo({ type: 'clear', text: back });
    this.deleteEditor(back.length);
    this.lastCommitText = '';
    this.sessionCommitText = '';
    this.engine.clear();
    this.notify();
    console.info(`${TAG} clearAllContent: deleted ${back.length} chars（按编辑框真实文本）`);
  }

  private notify(ctx?: RimeContext): void {
    const l = this.listener;
    if (!l) {
      return;
    }
    const c: RimeContext = ctx !== undefined ? ctx : this.engine.getContext();
    const state: KeyboardState = {
      preedit: c.preedit,
      candidates: c.candidates,
      allCandidates: c.allCandidates !== undefined ? c.allCandidates : c.candidates,
      baseIndex: c.baseIndex !== undefined ? c.baseIndex : 0,
      page: c.page,
      hasNext: c.hasNext,
      rowHeight: this.rowVp,
      // H-205：这里**必须**是方向预算（44vp），不是实时栏高（空闲 28vp）。
      // UI 的 `barHeight < 40` 是横屏判据，喂实时值会让竖屏永久落进横屏分支
      // （顶栏 L1 与候选被挤成一行，且窗口再也不长一行）。真机 2026-10-26 实测。
      barHeight: this.defaultBarVp,
      selectionMode: this.selectionModeOn
    };
    l(state);
  }
}

/** 全局单例。 */
export const keyboardController: SsKeyboardController = new SsKeyboardController();