import { common } from '@kit.AbilityKit';
import { RimeCandidate, RimeContext, RimeEngine } from './RimeEngine';

const INPUT_CHARS: string = 'abcdefghijklmnopqrstuvwxyz';
const INPUT_CHARS_UPPER: string = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';

/**
 * 候选总量 15 条 / 每页 5 条 = 3 页。
 * 必须有第二页：真机要靠「滑动后候选变不变」判断翻页手势是否生效。
 * 若 mock 只有一页，`flipPage` 无论被不被调用，候选栏都纹丝不动，
 * 主人只会报「左右滑也没反应」——和 Shift 那次大写不进编码是同一类假信号。
 */
const MOCK_PAGE_SIZE: number = 5;
const MOCK_CANDIDATES: RimeCandidate[] = [
  { text: '你', comment: 'ni' },
  { text: '尼', comment: 'ni' },
  { text: '泥', comment: 'ni' },
  { text: '呢', comment: 'ne' },
  { text: '你好', comment: 'ni hao' },
  { text: '你的', comment: 'ni de' },
  { text: '你们', comment: 'ni men' },
  { text: '拟', comment: 'ni' },
  { text: '逆', comment: 'ni' },
  { text: '匿', comment: 'ni' },
  { text: '泥巴', comment: 'ni ba' },
  { text: '逆风', comment: 'ni feng' },
  { text: '匿名', comment: 'ni ming' },
  { text: '呢喃', comment: 'ni nan' },
  { text: '尼龙', comment: 'ni long' }
];

/**
 * M1 用的假引擎：只验证键盘 UI / 候选栏 / 上屏链路，不碰 native。
 * 归属：Qoder。CodeArts 不要修改本文件。
 */
export class MockRimeEngine implements RimeEngine {
  private composing: string = '';
  /** 当前候选页码，从 0 开始；编码一变化就回到首页（与真 Rime 一致）。 */
  private page: number = 0;
  /** v0.1.5：每页候选数，默认 5；测试横屏可设为 9。 */
  private pageSize: number = MOCK_PAGE_SIZE;
  /** v0.1.8：getOption 要能读回 setOption 写进去的状态（和真 Rime 行为对齐）。 */
  private options: Map<string, boolean> = new Map<string, boolean>();

  init(sharedPath: string, context?: common.Context): Promise<void> {
    console.info(`[MockRimeEngine] init: ${sharedPath} ctx=${context !== undefined}`);
    return Promise.resolve();
  }

  processKey(key: string): RimeContext {
    if (key === 'Backspace') {
      return this.deleteBackward();
    }
    if (key === 'Escape') {
      return this.clear();
    }
    if (key === 'Space' || key === ' ') {
      // 有编码选首选；无编码直接上屏一个空格（与真引擎/系统行为一致）
      const committed: string = this.composing.length > 0 ? this.selectCandidate(0) : ' ';
      const ctx: RimeContext = this.getContext();
      ctx.commitText = committed;
      return ctx;
    }
    if (key === 'Enter') {
      // 有编码上屏原文；无编码插入换行
      const committed: string = this.composing.length > 0 ? this.composing : '\n';
      this.composing = '';
      this.page = 0;
      const ctx: RimeContext = this.getContext();
      ctx.commitText = committed;
      return ctx;
    }
    // 字母进编码：大小写都算（Shift 状态归 UI，面板送出的是已转大小的字母）。
    // 若这里只认小写，真机按 ⇧ 打 N 会被当成标点直接上屏，看不出「Shift 生效」。
    if (key.length === 1 && (INPUT_CHARS.includes(key) || INPUT_CHARS_UPPER.includes(key))) {
      this.composing += key;
      this.page = 0;
      return this.getContext();
    }
    // 其他可打印单字符键：mock 不参与编码，直接上屏，验证 UI → InputClient 链路。
    // 手机端数字、`-`、`=`、标点和英文撇号均直接上屏；翻页只由候选栏左右滑手势调用 `flipPage()`。
    if (key.length === 1) {
      const ctx: RimeContext = this.getContext();
      ctx.commitText = key;
      return ctx;
    }
    return this.getContext();
  }

  selectCandidate(index: number): string {
    const list: RimeCandidate[] = this.pageCandidates();
    const picked: string = index >= 0 && index < list.length ? list[index].text : '';
    this.composing = '';
    this.page = 0;
    return picked;
  }

  /** v0.2.0：按全局绝对下标选词（mock 的全量就是 MOCK_CANDIDATES）。 */
  selectCandidateAbs(index: number): string {
    const picked: string = index >= 0 && index < MOCK_CANDIDATES.length ? MOCK_CANDIDATES[index].text : '';
    this.composing = '';
    this.page = 0;
    return picked;
  }

  deleteBackward(): RimeContext {
    if (this.composing.length > 0) {
      this.composing = this.composing.substring(0, this.composing.length - 1);
      this.page = 0;
    }
    return this.getContext();
  }

  /**
   * 翻页：direction = 1 下一页，-1 上一页；**不循环**，越界保持原页（与 M-010/M-012 要求一致）。
   * 候选按 `MOCK_PAGE_SIZE` 分页，滑动后面板能肉眼看到变化 —— 这是真机判翻页手势是否生效的唯一依据。
   */
  flipPage(direction: number): RimeContext {
    const lastPage: number = Math.max(0, Math.ceil(MOCK_CANDIDATES.length / this.pageSize) - 1);
    const target: number = this.page + direction;
    if (target >= 0 && target <= lastPage) {
      this.page = target;
    }
    console.info(`[MockRimeEngine] flipPage: ${direction} -> page ${this.page}/${lastPage}`);
    return this.getContext();
  }

  clear(): RimeContext {
    this.composing = '';
    this.page = 0;
    return this.getContext();
  }

  getContext(): RimeContext {
    const candidates: RimeCandidate[] = this.composing.length > 0 ? this.pageCandidates() : [];
    const lastPage: number = Math.max(0, Math.ceil(MOCK_CANDIDATES.length / this.pageSize) - 1);
    const ctx: RimeContext = {
      preedit: this.composing,
      candidates: candidates,
      // v0.2.0：mock 的「全量」就是整张表（真引擎是一个 Rime 菜单页的量）。
      allCandidates: this.composing.length > 0 ? MOCK_CANDIDATES : [],
      baseIndex: 0,
      page: this.page,
      hasNext: this.page < lastPage
    };
    return ctx;
  }

  setOption(name: string, value: boolean): void {
    this.options.set(name, value);
    console.info(`[MockRimeEngine] setOption: ${name}=${value}`);
  }

  getOption(name: string): boolean {
    const v: boolean | undefined = this.options.get(name);
    return v === true;
  }

  setPageSize(size: number): RimeContext {
    this.pageSize = Math.max(1, Math.min(MOCK_CANDIDATES.length, Math.floor(size)));
    this.page = 0;
    console.info(`[MockRimeEngine] setPageSize: ${this.pageSize}`);
    return this.getContext();
  }

  /** v0.1.7：mock 没有多方案，只记录切换意图，让 UI 的分阶段联调不阻塞。 */
  selectSchema(id: string): boolean {
    console.info(`[MockRimeEngine] selectSchema: ${id}`);
    this.composing = '';
    this.page = 0;
    return true;
  }

  /** H-178：mock 记一份「当前方案」，与 selectSchema 对账，供 UI 显示用。 */
  private mockSchemaId: string = 'wubi_pinyin';

  getSchemaId(): string {
    console.info(`[MockRimeEngine] getSchemaId: ${this.mockSchemaId}`);
    return this.mockSchemaId;
  }

  /** v0.5.0（M4）：mock 没有 native 引擎，收到收尾请求只清状态。 */
  finalize(): void {
    console.info(`[MockRimeEngine] finalize`);
    this.composing = '';
    this.page = 0;
  }

  /** 当前页的候选切片（首页 5 条与 `v0.2.x` 真机记录里的「你/尼/泥/呢/你好」保持一致，方便对比）。 */
  private pageCandidates(): RimeCandidate[] {
    const start: number = this.page * this.pageSize;
    return MOCK_CANDIDATES.slice(start, start + this.pageSize);
  }
}
