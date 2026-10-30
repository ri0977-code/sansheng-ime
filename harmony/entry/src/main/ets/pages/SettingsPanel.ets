/*
 * 三生输入法 · 设置页（H-239/H-240 契约 `docs/SETTINGS-CONTRACT.md`）
 * 第一版：Qoder 2026-10-28 02:4x 落**能用**的最小形态（12 项逐条可改、改完键盘当场变），
 * 目的是今晚能把「入口＋生效」这条链跑通并逐条取证；**整文件由 CodeArts 接手重做成安卓口径**
 * （两页签「虚拟键盘」「候选窗口」＋滑条，见 M-284 与契约 §2/§3）。
 *
 * H-239(CodeArts): 整页按安卓两页签重做——Tab 导航替代 SectionHeader 分节，
 * 每个页签各自 Scroll，外壳定高 + 内层滚动（契约 §3.1 r4 通路）。
 *
 * 规矩（契约 §3）：条目**只能用契约表里那 12 个键名**，不许新增表外条目——
 * H-090 那次 71 项 0 生效就是死在「页面上有、键盘不读」，主人 10-22 因此拍 D-021。
 *
 * 高度死线（契约 §1，H-213/H-218r4 两次真机事故）：IME 面板窗口高恒 236vp，
 * **内容超出会被静默裁掉、不报错** ⇒ 列表必须自带 Scroll，卡片高度由父层给定。
 */
import { SettingsStore, SETTINGS_REV_KEY } from '../common/SettingsStore';

const TAG: string = 'SSKeyboardSettings';
const CARD_BG: string = '#FFFFFF';
const FG_TITLE: string = '#17203A';
const FG_LABEL: string = '#1A1C1E';
const FG_HINT: string = '#8A8F99';
const FG_ACCENT: string = '#2B5FBF';
const BG_STEP: string = '#E4E7EC';
const BG_TAB_ACTIVE: string = '#EFF4FF';
const RADIUS: number = 8;
const ROW_H: number = 32;
/** 连续项（滑条）双行高度：第一行 label+数值 20vp，第二行 Slider 24vp，含 4vp 内上下分布。 */
const SLIDER_ROW_H: number = 48;
/** 页签栏高度 */
const TAB_BAR_H: number = 34;

/** 一行的视图模型（从 store ＋ 契约表推导，面板不自己存值 ⇒ 只有一个真相源）。 */
class RowVM {
  key: string = '';
  label: string = '';
  /** 这一行在 store.keys() 里的原序号 ⇒ 加减/开关回写时定位 `this.rows[oi]`，与分组渲染顺序无关。 */
  oi: number = 0;
  isBool: boolean = false;
  /** 数值行的当前值；开关行忽略。 */
  value: number = 0;
  min: number = 0;
  max: number = 0;
  allow: number[] = [];
  /** 右侧显示的文字（数值带单位／开关＝开·关）。 */
  text: string = '';
  /** 数值行的步进（滑条类 1，字号类 1，长按延迟 25）。 */
  step: number = 1;
  /** 后缀单位文案。 */
  unit: string = '';

  constructor(key: string, label: string) {
    this.key = key;
    this.label = label;
  }
}

/** 契约 §3 的 12 项，顺序＝表序；文案照安卓页名（「虚拟键盘」「候选窗口」两节）。 */
const LABELS: string[] = [
  '键盘高度', '候选词字号', '键面字母字号', '每页候选词数', '按键时振动', '长按触发时长',
  '按键时弹出字符', '可撤销步数', '展开网格每页条数', '空格划动移光标步长', '默认展开工具栏', '显示编码行',
];
const UNITS: string[] = ['%', 'vp', 'vp', '条', '', 'ms', '', '步', '条', 'vp', '', ''];
const STEPS: number[] = [5, 1, 1, 0, 0, 25, 0, 1, 5, 1, 0, 0];

/*
 * 安卓口径两节分组（M-284：对应物＝fcitx5-android「虚拟键盘」页＋「候选窗口」页；
 * 10-28 06:5x Qoder 接手把「一列 12 行」按这两节分开头）。
 * **只用契约 §3 那 12 个键名**（键名不新增、不改），只是把同一批行按 key 归到两节渲染 ⇒
 * `settings_effective_check.py` 判据不受影响。按 key 名归属、不按序号，防以后表序变动串节。
 */
const SECTION_KBD: string = '虚拟键盘';
const SECTION_CAND: string = '候选窗口';
const KBD_KEYS: string[] = [
  'kbd_height_pct', 'key_font_size', 'kbd_haptic', 'key_long_press_delay',
  'popup_on_key_press', 'space_swipe_step', 'expand_toolbar_by_default', 'show_preedit',
];
const CAND_KEYS: string[] = ['cand_font_size', 'page_size', 'grid_page_size', 'undo_stack_limit'];

@Component
export struct SettingsPanel {
  /** 父层持有：关掉整页（长按空格/回车开，✕ 或点遮罩关）。 */
  @Link visible: boolean;
  /** 写侧自增的版本号 ⇒ 任一处改了设置，这页跟着重画。 */
  @StorageLink(SETTINGS_REV_KEY) @Watch('reload') rev: number = 0;
  @State rows: RowVM[] = [];
  /** 按安卓两节分好组的视图模型（`reload()` 里重算，渲染时不再判归属）。 */
  @State kbdRows: RowVM[] = [];
  @State candRows: RowVM[] = [];
  /** H-239(CodeArts): 当前页签索引——0=虚拟键盘, 1=候选窗口 */
  @State currentTab: number = 0;

  aboutToAppear(): void {
    this.reload();
  }

  /** 从 store ＋ 契约范围重建行模型（不在 build 里读 store，避免每帧重算＋类型分叉）。 */
  reload(): void {
    const st: SettingsStore = SettingsStore.inst();
    const ks: string[] = st.keys();
    const next: RowVM[] = [];
    for (let i = 0; i < ks.length; i++) {
      const key: string = ks[i];
      const label: string = i < LABELS.length ? LABELS[i] : key;
      const vm = new RowVM(key, label);
      vm.oi = i;
      vm.isBool = st.isBoolKey(key);
      vm.min = st.minOf(key);
      vm.max = st.maxOf(key);
      vm.allow = st.allowOf(key);
      vm.unit = i < UNITS.length ? UNITS[i] : '';
      vm.step = i < STEPS.length && STEPS[i] > 0 ? STEPS[i] : 1;
      if (vm.isBool) {
        vm.text = st.sw(key) ? '开' : '关';
      } else {
        vm.value = st.num(key);
        vm.text = `${vm.value}${vm.unit}`;
      }
      next.push(vm);
    }
    this.rows = next;
    // 按 key 名归到安卓两节；未列入任一节的历史键不显示（防「表外条目出现在页面上」＝守卫判红）。
    const kb: RowVM[] = [];
    const cd: RowVM[] = [];
    for (let i = 0; i < next.length; i++) {
      const r: RowVM = next[i];
      if (KBD_KEYS.indexOf(r.key) >= 0) {
        kb.push(r);
      } else if (CAND_KEYS.indexOf(r.key) >= 0) {
        cd.push(r);
      }
    }
    this.kbdRows = kb;
    this.candRows = cd;
  }

  /** 数值行加减：离散白名单（每页候选数）走吸附，连续项钳到 [min,max]。 */
  private bump(idx: number, dir: number): void {
    const vm: RowVM | undefined = this.rows[idx];
    if (vm === undefined || vm.isBool) {
      return;
    }
    const st: SettingsStore = SettingsStore.inst();
    let target: number = vm.value + dir * vm.step;
    if (vm.allow.length > 0) {
      // 白名单：取「当前值之后（或之前）的下一个允许值」，越界则钳回首/尾
      const cur: number = vm.allow.indexOf(vm.value);
      const at: number = cur < 0 ? 0 : cur;
      const nxt: number = dir > 0 ? Math.min(vm.allow.length - 1, at + 1) : Math.max(0, at - 1);
      target = vm.allow[nxt];
    }
    st.set(vm.key, target);
    console.info(`${TAG} bump ${vm.key}: ${vm.value} -> ${target}`);
    this.reload();
  }

  private flip(idx: number): void {
    const vm: RowVM | undefined = this.rows[idx];
    if (vm === undefined || !vm.isBool) {
      return;
    }
    const st: SettingsStore = SettingsStore.inst();
    st.set(vm.key, !st.sw(vm.key));
    console.info(`${TAG} flip ${vm.key} -> ${st.sw(vm.key)}`);
    this.reload();
  }

  /** 滑条松手时提交（mode=End/Click），钳到 [min,max] 并取整。 */
  private sliderSet(idx: number, raw: number): void {
    const vm: RowVM | undefined = this.rows[idx];
    if (vm === undefined || vm.isBool) {
      return;
    }
    const target: number = Math.max(vm.min, Math.min(vm.max, Math.round(raw)));
    const st: SettingsStore = SettingsStore.inst();
    st.set(vm.key, target);
    console.info(`${TAG} slider ${vm.key}: ${vm.value} -> ${target}`);
    this.reload();
  }

  /** Toggle 松手时直接写目标值（不翻转，避免与视觉状态冲突）；同值时不 reload()（防止不必要的重渲染）。 */
  private setBool(idx: number, on: boolean): void {
    const vm: RowVM | undefined = this.rows[idx];
    if (vm === undefined || !vm.isBool) {
      return;
    }
    const cur: boolean = vm.text === '开';
    if (cur === on) {
      return; // 同值，不写不刷新
    }
    const st: SettingsStore = SettingsStore.inst();
    st.set(vm.key, on);
    console.info(`${TAG} toggle ${vm.key} -> ${on}`);
    this.reload();
  }

  @Builder
  SettingRow(r: RowVM) {
    if (r.isBool) {
      // 开关行：Toggle(Switch) ＝安卓原生形态；isOn 读 vm.text（"开"=true）；
      // setBool 直接写目标值，不走 flip（flip 会再次翻转）。同值守卫防多余 reload()。
      Row({ space: 6 }) {
        Text(r.label)
          .fontSize(13)
          .fontColor(FG_LABEL)
          .layoutWeight(1)
          .maxLines(1)
          .textOverflow({ overflow: TextOverflow.Ellipsis })
        Toggle({ type: ToggleType.Switch, isOn: r.text === '开' })
          .selectedColor(FG_ACCENT)
          .switchPointColor('#FFFFFF')
          .width(44)
          .height(26)
          .onChange((on: boolean) => {
            this.setBool(r.oi, on);
          })
      }
      .width('100%')
      .height(ROW_H)
      .padding({ left: 10, right: 10 })
      .alignItems(VerticalAlign.Center)
    } else if (r.allow.length > 0) {
      // 离散白名单（page_size [3,5,7,9]）：加减按钮吸附下一个合法值，与滑条区分明确。
      Row({ space: 6 }) {
        Text(r.label)
          .fontSize(13)
          .fontColor(FG_LABEL)
          .layoutWeight(1)
          .maxLines(1)
          .textOverflow({ overflow: TextOverflow.Ellipsis })
        Text('－')
          .fontSize(15)
          .fontColor(FG_TITLE)
          .width(28)
          .height(26)
          .textAlign(TextAlign.Center)
          .backgroundColor(BG_STEP)
          .borderRadius(RADIUS)
          .onClick(() => {
            this.bump(r.oi, -1);
          })
        Text(r.text)
          .fontSize(13)
          .fontColor(FG_LABEL)
          .width(54)
          .textAlign(TextAlign.Center)
        Text('＋')
          .fontSize(15)
          .fontColor(FG_TITLE)
          .width(28)
          .height(26)
          .textAlign(TextAlign.Center)
          .backgroundColor(BG_STEP)
          .borderRadius(RADIUS)
          .onClick(() => {
            this.bump(r.oi, 1);
          })
      }
      .width('100%')
      .height(ROW_H)
      .padding({ left: 10, right: 10 })
    } else {
      // 连续项：双行布局，第一行标签＋当前值，第二行全宽滑条（契约 §3「滑条」要求）。
      // 高度 48vp：20(label行) + 24(slider) + 4(列内均分)。
      // onChange 只在 End/Click 提交，不在 Moving 里写 store（避免每帧落盘）。
      Column() {
        Row({ space: 4 }) {
          Text(r.label)
            .fontSize(13)
            .fontColor(FG_LABEL)
            .layoutWeight(1)
            .maxLines(1)
            .textOverflow({ overflow: TextOverflow.Ellipsis })
          Text(r.text)
            .fontSize(13)
            .fontColor(FG_ACCENT)
            .width(54)
            .textAlign(TextAlign.End)
        }
        .width('100%')
        .height(20)

        Slider({
          value: r.value,
          min: r.min,
          max: r.max,
          step: r.step > 0 ? r.step : 1,
          style: SliderStyle.OutSet
        })
          .width('100%')
          .height(24)
          .blockColor(FG_ACCENT)
          .selectedColor(FG_ACCENT)
          .trackColor(BG_STEP)
          .trackThickness(4)
          .onChange((val: number, mode: SliderChangeMode) => {
            if (mode === SliderChangeMode.End || mode === SliderChangeMode.Click) {
              this.sliderSet(r.oi, val);
            }
          })
      }
      .width('100%')
      .height(SLIDER_ROW_H)
      .padding({ left: 10, right: 10 })
      .justifyContent(FlexAlign.SpaceBetween)
    }
  }

  // H-239(CodeArts): 页签按钮 Builder——安卓口径两页签，选中态蓝色加粗+底色，未选中灰色
  @Builder
  TabButton(title: string, index: number) {
    Column() {
      Text(title)
        .fontSize(13)
        .fontColor(this.currentTab === index ? FG_ACCENT : FG_HINT)
        .fontWeight(this.currentTab === index ? FontWeight.Bold : FontWeight.Normal)
    }
    .width('50%')
    .height(TAB_BAR_H)
    .justifyContent(FlexAlign.Center)
    .backgroundColor(this.currentTab === index ? BG_TAB_ACTIVE : CARD_BG)
    .onClick(() => {
      this.currentTab = index;
      console.info(`${TAG} H-239 tab switch -> ${index === 0 ? SECTION_KBD : SECTION_CAND}`);
    })
  }

  build() {
    Column({ space: 0 }) {
      // 标题栏：设置 + 恢复默认 + 关闭
      Row({ space: 8 }) {
        Text('设置')
          .fontSize(14)
          .fontWeight(FontWeight.Bold)
          .fontColor(FG_TITLE)
          .layoutWeight(1)
        Text('恢复默认')
          .fontSize(12)
          .fontColor(FG_ACCENT)
          .onClick(() => {
            const st: SettingsStore = SettingsStore.inst();
            const ks: string[] = st.keys();
            for (let i = 0; i < ks.length; i++) {
              const k: string = ks[i];
              st.set(k, st.isBoolKey(k) ? st.defOf(k) !== 0 : st.defOf(k));
            }
            console.info(`${TAG} reset all to defaults`);
            this.reload();
          })
        Text('✕')
          .fontSize(14)
          .fontColor(FG_HINT)
          .padding({ left: 8, right: 4 })
          .onClick(() => {
            this.visible = false;
          })
      }
      .width('100%')
      .height(24)
      .padding({ left: 10, right: 8 })

      // H-239(CodeArts): 页签栏——两页签替代 SectionHeader，安卓口径
      Row() {
        this.TabButton(SECTION_KBD, 0)
        this.TabButton(SECTION_CAND, 1)
      }
      .width('100%')
      .height(TAB_BAR_H)
      .borderWidth({ bottom: 0.5 })
      .borderColor('#D0D5DD')

      // H-239(CodeArts): 页签内容——各自 Scroll，互不干扰
      if (this.currentTab === 0) {
        // 虚拟键盘页签：8 项
        Scroll() {
          Column({ space: 2 }) {
            ForEach(this.kbdRows, (r: RowVM) => {
              this.SettingRow(r)
            }, (r: RowVM) => `${r.key}|${r.text}`)
          }
          .width('100%')
        }
        .scrollBar(BarState.Auto)
        .width('100%')
        .layoutWeight(1)
        .align(Alignment.TopStart)
      } else {
        // 候选窗口页签：4 项
        Scroll() {
          Column({ space: 2 }) {
            ForEach(this.candRows, (r: RowVM) => {
              this.SettingRow(r)
            }, (r: RowVM) => `${r.key}|${r.text}`)
          }
          .width('100%')
        }
        .scrollBar(BarState.Auto)
        .width('100%')
        .layoutWeight(1)
        .align(Alignment.TopStart)
      }
    }
    .width('88%')
    .height('100%')
    .padding({ top: 6, bottom: 6 })
    .backgroundColor(CARD_BG)
    .borderRadius(RADIUS)
    .shadow({ radius: 12, color: 'rgba(0,0,0,0.18)', offsetY: 2 })
    .onClick(() => {
      // 卡片内点击不透给遮罩（遮罩＝关闭）；空实现即可，别在这里再挂业务
    })
  }
}
