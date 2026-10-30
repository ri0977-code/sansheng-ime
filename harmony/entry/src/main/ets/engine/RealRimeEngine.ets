import nativeRime from 'libfanxing_rime.so';
import { display } from '@kit.ArkUI';
import { common } from '@kit.AbilityKit';
import { BusinessError } from '@kit.BasicServicesKit';
import { RimeCandidate, RimeContext, RimeEngine } from './RimeEngine';
import { RimeDataInstaller } from './RimeDataInstaller';
// H-241（契约 §2/§3-4）：每页候选词数的读取点之一在本文件（另一处在 KeyboardIndex.recomputePageSize）。
import { SettingsStore } from '../common/SettingsStore';

const TAG: string = 'SSRealRimeEngine';
const PORTRAIT_PAGE_SIZE: number = 5;
/** 横屏 8–10 条（H-035），取 9 兼顾宽度与可点性 */
const LANDSCAPE_PAGE_SIZE: number = 9;

interface NativeCandidate {
  text: string;
  comment?: string;
}

interface NativeContext {
  preedit: string;
  candidates: NativeCandidate[];
  /** v0.2.0：当前 Rime 菜单页的全部候选（不按页大小切片）。 */
  allCandidates?: NativeCandidate[];
  /** v0.2.0：allCandidates[0] 的全局绝对下标。 */
  baseIndex?: number;
  page: number;
  hasNext: boolean;
  commitText?: string;
}

interface RimeNativeApi {
  initEngine(sharedPath: string): Promise<void>;
  processKey(key: string): NativeContext;
  selectCandidate(index: number): string;
  /** v0.2.0：按全局绝对下标选词（UI 自己分页时用）。 */
  selectCandidateAbs(index: number): string;
  deleteBackward(): NativeContext;
  flipPage(direction: number): NativeContext;
  clear(): NativeContext;
  getContext(): NativeContext;
  setOption(name: string, value: boolean): void;
  getOption(name: string): boolean;
  setPageSize(size: number): NativeContext;
  switchSchema(id: string): boolean;
  /** H-178：读当前方案 id（napi getSchemaId → rime get_current_schema）。 */
  getSchemaId(): string;
  /** v0.5.0（M4）：引擎收尾（destroy_session + finalize）。 */
  finalizeEngine(): boolean;
}

const nativeApi: RimeNativeApi = nativeRime as RimeNativeApi;

/**
 * M2 真 Rime 引擎门面：只做 native 结果 → RimeContext 的形状转换，
 * 不在这里做分页/编码逻辑（那些在 C++ 桥里，键盘 UI 不用改）。
 * 归属：Qoder。
 */
export class RealRimeEngine implements RimeEngine {
  private inited: boolean = false;
  private displayBound: boolean = false;
  private pageSize: number = PORTRAIT_PAGE_SIZE;

  async init(sharedPath: string, context?: common.Context): Promise<void> {
    if (this.inited) {
      return;
    }
    await RimeDataInstaller.ensure(sharedPath, context);
    await nativeApi.initEngine(sharedPath);
    this.inited = true;
    this.bindDisplay();
    this.applyOrientation();
    console.info(`${TAG} ready, pageSize=${this.pageSize}`);
  }

  processKey(key: string): RimeContext {
    return this.toContext(nativeApi.processKey(key));
  }

  selectCandidate(index: number): string {
    return nativeApi.selectCandidate(index);
  }

  /** v0.2.0：按全局绝对下标选词。 */
  selectCandidateAbs(index: number): string {
    return nativeApi.selectCandidateAbs(index);
  }

  deleteBackward(): RimeContext {
    return this.toContext(nativeApi.deleteBackward());
  }

  flipPage(direction: number): RimeContext {
    return this.toContext(nativeApi.flipPage(direction));
  }

  clear(): RimeContext {
    return this.toContext(nativeApi.clear());
  }

  getContext(): RimeContext {
    return this.toContext(nativeApi.getContext());
  }

  setOption(name: string, value: boolean): void {
    nativeApi.setOption(name, value);
  }

  getOption(name: string): boolean {
    return nativeApi.getOption(name);
  }

  /**
   * H-035 的 5/9 只是**兜底默认值**。UI 一旦按实测宽度显式调过 `setPageSize`
   * （H-042 弹性候选栏），本标志置真，之后转屏不再由引擎覆盖——
   * 宽度是 UI 量的，条数就该由 UI 定，定死的档位满足不了横竖屏两种排布。
   */
  private uiPinned: boolean = false;

  /** v0.1.6：UI 显式指定每页条数后，引擎不再按取向覆盖（H-042 弹性候选栏）。 */
  setPageSize(size: number): RimeContext {
    const clamped: number = Math.max(1, Math.min(50, Math.floor(size)));
    this.pageSize = clamped;
    this.uiPinned = true;
    console.info(`${TAG} setPageSize=${clamped} (UI pinned)`);
    return this.toContext(nativeApi.setPageSize(clamped));
  }

  /**
   * v0.1.7（H-028 ① 智能九键）：切到九宫格方案 `sansheng_t9` 或回主方案 `wubi_pinyin`。
   * native 的 switchSchema 已经把编码清空、UI 页码归 0，这里只透传结果。
   */
  selectSchema(id: string): boolean {
    const ok: boolean = nativeApi.switchSchema(id);
    console.info(`${TAG} selectSchema(${id}) = ${ok}`);
    return ok;
  }

  /** H-178：读当前方案 id（napi getSchemaId → rime get_current_schema）。 */
  getSchemaId(): string {
    const id: string = nativeApi.getSchemaId();
    console.info(`${TAG} getSchemaId() = "${id}"`);
    return id;
  }

  /**
   * v0.5.0（M4）：引擎收尾。native 侧会 destroy_session + finalize，
   * 于是用户词典（LevelDb）与 Lua 脚本、OpenCC 句柄都被干净释放。
   * 调用后引擎不可用，需要重新 init()。
   */
  finalize(): void {
    if (!this.inited) {
      return;
    }
    nativeApi.finalizeEngine();
    this.inited = false;
    console.info(`${TAG} finalize ok`);
  }

  private bindDisplay(): void {
    if (this.displayBound) {
      return;
    }
    try {
      display.on('change', this.handleDisplayChange);
      this.displayBound = true;
    } catch (e) {
      const err = e as BusinessError;
      console.warn(`${TAG} display.on failed: ${err.code} ${err.message}`);
    }
  }

  private handleDisplayChange = (): void => {
    this.applyOrientation();
  };

  private applyOrientation(): void {
    if (this.uiPinned) {
      // UI 已按实测宽度接管分页，取向变化由 UI 自己重算并再调 setPageSize。
      return;
    }
    let landscape: boolean = false;
    try {
      const d: display.Display = display.getDefaultDisplaySync();
      landscape = d.rotation === 1 || d.rotation === 3;
    } catch (e) {
      const err = e as BusinessError;
      console.warn(`${TAG} getDefaultDisplaySync failed: ${err.code}`);
    }
    // H-241 契约 §3-4「每页候选词数」的另一处读取点（也是冷启第一次分页的读取点）：
    // 用户在设置页定过（store 里有这个键）就用他的档，横竖屏都听他的；
    // **没定过时一字不改**——仍走 H-035 的 竖 5 / 横 9，横屏不会因为我这里加了设置就掉成 5 条。
    const st: SettingsStore = SettingsStore.inst();
    const pref: number = st.isUserSet('page_size') ? st.num('page_size') : 0;
    const target: number = pref > 0 ? pref : (landscape ? LANDSCAPE_PAGE_SIZE : PORTRAIT_PAGE_SIZE);
    if (target !== this.pageSize) {
      this.pageSize = target;
      nativeApi.setPageSize(target);
      console.info(`${TAG} pageSize -> ${target} (${landscape ? 'landscape' : 'portrait'})`);
    }
  }

  private toContext(native: NativeContext): RimeContext {
    const candidates: RimeCandidate[] = [];
    if (native.candidates !== undefined) {
      for (const c of native.candidates) {
        const item: RimeCandidate = { text: c.text };
        if (c.comment !== undefined && c.comment.length > 0) {
          item.comment = c.comment;
        }
        candidates.push(item);
      }
    }
    // v0.2.0：全量候选（当前 Rime 菜单页）；老 native 没有这个字段时退回当页切片。
    const allCandidates: RimeCandidate[] = [];
    if (native.allCandidates !== undefined) {
      for (const c of native.allCandidates) {
        const item: RimeCandidate = { text: c.text };
        if (c.comment !== undefined && c.comment.length > 0) {
          item.comment = c.comment;
        }
        allCandidates.push(item);
      }
    }
    const ctx: RimeContext = {
      preedit: native.preedit !== undefined ? native.preedit : '',
      candidates: candidates,
      allCandidates: allCandidates.length > 0 ? allCandidates : candidates,
      baseIndex: native.baseIndex !== undefined ? native.baseIndex : 0,
      page: native.page,
      hasNext: native.hasNext
    };
    if (native.commitText !== undefined && native.commitText.length > 0) {
      ctx.commitText = native.commitText;
    }
    return ctx;
  }
}
