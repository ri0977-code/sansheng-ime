/*
 * 三生输入法 · 设置存储层（H-239/H-240 · 契约 `docs/SETTINGS-CONTRACT.md` §4）
 * 归属：Qoder 先落第一版（2026-10-28 02:2x），CodeArts 接手时**只许加方法、不许改签名**；
 * 键名/类型/默认值/范围＝契约 §3 那张表，**不许新增表外条目**（D-021「只留真实生效的项」）。
 *
 * 为什么存在这里而不是 App 的 `sansheng_prefs`：
 *   官方「进程模型」写明输入法组件跑在**独立进程**，「输入法安全模式」又写明
 *   **输入法扩展使用独立沙箱，与应用主入口不可互相访问** ⇒ 键盘侧根本读不到 App 那份 preferences。
 *   这正是 H-090 那 71 项「页面有、键盘不读」的根因之一。跨进程共享的唯一官方通路是
 *   `Options.dataGroupId`（要动 AGC 申请＋重出 profile＋重签）⇒ 已登记 H-243 等主人点头，
 *   在那之前**只有一个真相源＝本文件**。
 *
 * 渲染期只允许同步读（`num()/sw()/on()`）：`.fontSize()` 里不许 `await`。
 * 写侧 `set()` 立刻改内存缓存 ⇒ `AppStorage('settingsRev')` 自增 ⇒ 键面 `@StorageLink` 重绘，
 * 随后异步 `putSync + flush` 落盘；**不要求重启输入法**。
 */
import preferences from '@ohos.data.preferences';
import common from '@ohos.app.ability.common';
import { BusinessError } from '@ohos.base';

/** 输入法进程独立沙箱里的 store 名（契约 §4）。 */
export const SETTINGS_STORE_NAME: string = 'sansheng_kb_prefs';

/** `@StorageLink` 用的版本号键：写侧自增，键面靠它立刻重绘。 */
export const SETTINGS_REV_KEY: string = 'settingsRev';

/** 一个受契约管的设置项的元信息（类型＋默认值＋取值范围）。 */
class KeySpec {
  key: string = '';
  /** true＝开关（存 boolean）；false＝数值（存 number）。 */
  isBool: boolean = false;
  def: number = 0;
  min: number = 0;
  max: number = 0;
  /** 离散白名单（如每页候选数只许 3/5/7/9）；空数组＝连续范围内任意值。 */
  allow: number[] = [];
}

/** 造一个数值项元信息（用函数建，避免 ArkTS 对对象字面量的限制）。 */
function mkNum(key: string, def: number, min: number, max: number, allow: number[]): KeySpec {
  const s = new KeySpec();
  s.key = key;
  s.isBool = false;
  s.def = def;
  s.min = min;
  s.max = max;
  s.allow = allow;
  return s;
}

/** 造一个开关项元信息（def：1＝开，0＝关）。 */
function mkBool(key: string, def: number): KeySpec {
  const s = new KeySpec();
  s.key = key;
  s.isBool = true;
  s.def = def;
  s.min = 0;
  s.max = 1;
  return s;
}

/**
 * 契约 §3 的第一批 12 项。键名是双方接口，改这里必须先在契约「变更记录」写一行并通知对方。
 * 顺序与契约表一致，守卫 `scripts/settings_effective_check.py` 按这张表对账。
 */
const NONE: number[] = [];
const SPECS: KeySpec[] = [
  mkNum('kbd_height_pct', 100, 80, 120, NONE),
  mkNum('cand_font_size', 18, 14, 22, NONE),
  mkNum('key_font_size', 20, 16, 26, NONE),
  mkNum('page_size', 5, 3, 9, [3, 5, 7, 9]),
  mkBool('kbd_haptic', 1),
  mkNum('key_long_press_delay', 450, 300, 700, NONE),
  mkBool('popup_on_key_press', 1),
  mkNum('undo_stack_limit', 10, 5, 30, NONE),
  mkNum('grid_page_size', 50, 20, 80, NONE),
  mkNum('space_swipe_step', 10, 5, 20, NONE),
  mkBool('expand_toolbar_by_default', 0),
  mkBool('show_preedit', 1),
];

/**
 * 单例：键盘侧、设置面板侧共用同一份内存缓存。
 * `load()` 之前（或 load 失败）读到的就是契约默认值 ⇒ **任何时刻都有确定值**，不会出现「读到 undefined 就不生效」。
 */
export class SettingsStore {
  private static instance: SettingsStore | undefined = undefined;
  private numCache: Map<string, number> = new Map<string, number>();
  private boolCache: Map<string, boolean> = new Map<string, boolean>();
  private specByKey: Map<string, KeySpec> = new Map<string, KeySpec>();
  /** 落盘过的键（用于区分「用户没动过」与「用户动了但等于默认值」）。 */
  private loadedKeys: Set<string> = new Set<string>();
  private store: preferences.Preferences | undefined = undefined;
  private rev: number = 0;

  private constructor() {
    for (let i = 0; i < SPECS.length; i++) {
      const s: KeySpec = SPECS[i];
      this.specByKey.set(s.key, s);
      if (s.isBool) {
        this.boolCache.set(s.key, s.def !== 0);
      } else {
        this.numCache.set(s.key, s.def);
      }
    }
    this.rev = AppStorage.get<number>(SETTINGS_REV_KEY) ?? 0;
  }

  static inst(): SettingsStore {
    if (SettingsStore.instance === undefined) {
      SettingsStore.instance = new SettingsStore();
    }
    return SettingsStore.instance;
  }

  /** 契约 §4：onCreate / panel.on('show') 调；失败保持默认值，不抛。 */
  load(ctx: common.Context): Promise<void> {
    return this.loadInner(ctx);
  }

  private async loadInner(ctx: common.Context): Promise<void> {
    try {
      if (ctx === undefined || ctx === null) {
        return;
      }
      const st: preferences.Preferences = await preferences.getPreferences(ctx, SETTINGS_STORE_NAME);
      this.store = st;
      this.specByKey.forEach((s: KeySpec, key: string) => {
        if (s.isBool) {
          const v: boolean = st.getSync(key, s.def !== 0) as boolean;
          this.boolCache.set(key, v);
        } else {
          const raw: number = st.getSync(key, s.def) as number;
          this.numCache.set(key, this.clamp(s, raw));
        }
        // hasSync（不是 has）：`has()` 返回 Promise ⇒ 直接放进 if 会被 ArkTS 判成
        // 「条件恒真」并**编译失败**（10605999，本次构建实测）。同步版才是这里要的。
        if (st.hasSync(key)) {
          this.loadedKeys.add(key);
        }
      });
      this.rev = this.rev + 1;
      AppStorage.setOrCreate<number>(SETTINGS_REV_KEY, this.rev);
      console.info(`SSKeyboard SettingsStore: loaded ${this.loadedKeys.size}/${this.specByKey.size} keys rev=${this.rev}`);
    } catch (e) {
      const err: BusinessError = e as BusinessError;
      console.warn(`SSKeyboard SettingsStore: load failed code=${err.code} msg=${err.message}, keep defaults`);
    }
  }

  /** 契约 §4：同步读缓存（渲染期唯一读取方式）。 */
  num(key: string): number {
    const v: number | undefined = this.numCache.get(key);
    return v === undefined ? 0 : v;
  }

  /** 契约 §4：带默认值读（默认值仍受范围钳制）。 */
  on(key: string, d: number): number {
    if (!this.has(key)) {
      return d;
    }
    const v: number | undefined = this.numCache.get(key);
    if (v === undefined) {
      return d;
    }
    const s: KeySpec | undefined = this.specByKey.get(key);
    return s === undefined ? v : this.clamp(s, v);
  }

  /** 契约 §4：开关。表外键名返回 false ⇒ 拼错键名会立刻暴露（守卫也会红），不静默生效。 */
  sw(key: string): boolean {
    const v: boolean | undefined = this.boolCache.get(key);
    return v === true;
  }

  /**
   * 契约 §4：写缓存＋flush＋AppStorage 通知。
   * 值先按契约范围钳制（滑条越界、非法离散值都在这挡掉），落盘异步做。
   */
  set(key: string, v: number | boolean): void {
    const s: KeySpec | undefined = this.specByKey.get(key);
    if (s === undefined) {
      console.warn(`SSKeyboard SettingsStore: set(${key}) 不在契约表内，忽略`);
      return;
    }
    if (s.isBool) {
      const b: boolean = (typeof v === 'boolean') ? (v as boolean) : ((v as number) !== 0);
      this.boolCache.set(key, b);
      this.persist(key, b);
    } else {
      const n: number = this.clamp(s, (typeof v === 'number') ? (v as number) : ((v as boolean) ? 1 : 0));
      this.numCache.set(key, n);
      this.persist(key, n);
    }
    this.rev = this.rev + 1;
    AppStorage.setOrCreate<number>(SETTINGS_REV_KEY, this.rev);
    console.info(`SSKeyboard SettingsStore: set ${key}=${v} rev=${this.rev}`);
  }

  /** 契约 §4：已注册键（守卫用来对账）。 */
  keys(): string[] {
    const out: string[] = [];
    this.specByKey.forEach((_s: KeySpec, key: string) => {
      out.push(key);
    });
    return out;
  }

  /**
   * 追加方法（不改 §4 签名）：该键是否受契约管。`num()` 对开关键返回 0，用这个先分流。
   */
  has(key: string): boolean {
    return this.specByKey.has(key);
  }

  /** 追加方法：是否为开关键。 */
  isBoolKey(key: string): boolean {
    const s: KeySpec | undefined = this.specByKey.get(key);
    return s !== undefined && s.isBool;
  }

  /** 追加方法：用户是否显式写过这一项（横屏每页条数「没动过就仍用 9」靠它）。 */
  isUserSet(key: string): boolean {
    return this.loadedKeys.has(key);
  }

  /** 追加方法：取契约默认值（设置页「恢复默认」用）。 */
  defOf(key: string): number {
    const s: KeySpec | undefined = this.specByKey.get(key);
    return s === undefined ? 0 : s.def;
  }

  /** 追加方法：取契约范围 [min, max]（设置页画滑条用）。 */
  minOf(key: string): number {
    const s: KeySpec | undefined = this.specByKey.get(key);
    return s === undefined ? 0 : s.min;
  }

  maxOf(key: string): number {
    const s: KeySpec | undefined = this.specByKey.get(key);
    return s === undefined ? 0 : s.max;
  }

  /** 追加方法：离散白名单（空数组＝连续）。 */
  allowOf(key: string): number[] {
    const s: KeySpec | undefined = this.specByKey.get(key);
    return s === undefined ? [] : s.allow;
  }

  private clamp(s: KeySpec, raw: number): number {
    let n: number = Math.round(raw);
    // 盘上万一存着别的类型（历史上手改过 store、或表外键撞名），getSync 会原样返回 ⇒ 落到默认值，
    // 不能让 NaN 传进 .fontSize()/.height()（那会是「设置一改键面就没了」这种更难查的病）。
    if (n !== n) {
      return s.def;
    }
    if (s.allow.length > 0) {
      // 离散项：吸附到最近的允许值（滑条/键盘输入越界也不会写出 4/6/8 这种页面没有的值）
      let best: number = s.allow[0];
      let bestD: number = Math.abs(n - best);
      for (let i = 1; i < s.allow.length; i++) {
        const d: number = Math.abs(n - s.allow[i]);
        if (d < bestD) {
          best = s.allow[i];
          bestD = d;
        }
      }
      return best;
    }
    if (n < s.min) {
      n = s.min;
    }
    if (n > s.max) {
      n = s.max;
    }
    return n;
  }

  private persist(key: string, v: preferences.ValueType): void {
    const st: preferences.Preferences | undefined = this.store;
    if (st === undefined) {
      return;
    }
    try {
      st.putSync(key, v);
      const p: Promise<void> = st.flush();
      p.then(() => {
        this.loadedKeys.add(key);
      }).catch((err: BusinessError) => {
        console.warn(`SSKeyboard SettingsStore: flush(${key}) failed code=${err.code} msg=${err.message}`);
      });
    } catch (e) {
      const err: BusinessError = e as BusinessError;
      console.warn(`SSKeyboard SettingsStore: putSync(${key}) failed code=${err.code} msg=${err.message}`);
    }
  }
}
