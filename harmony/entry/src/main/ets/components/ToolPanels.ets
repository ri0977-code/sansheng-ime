// H-194(CodeArts): 工具面板组件——光标移动 + 剪贴板
// 上游参考：fcitx5-android TextEditingWindow/ClipboardWindow（LGPL-2.1-or-later），仅参考思路
// 红线：不改 KeyboardIndex.ets/KeyboardController.ets/module.json5/sign/**；不申请权限

import { keyboardController } from '../inputmethod/KeyboardController';
import { promptAction } from '@kit.ArkUI';
import { inputMethodEngine } from '@kit.IMEKit';   // H-218: ExtendAction(全选/剪切)
// H-207(Qoder 2026-10-26)：PasteButton 的 onClick 第三参是 BusinessError<void>（见 SDK
// `declarations/paste_button.d.ts:208`）。要把它连错误码一起打出来才能分清「没注册上」
// 和「样式不合法」，所以这里必须显式导入——ArkTS 不像 TS 有全局 BusinessError。
import { BusinessError } from '@kit.BasicServicesKit';

const TAG: string = 'SSClipboardPad';

const BG_BAR: string = '#F2F3F5';
const FG_TOOLBAR: string = '#17203A';
const FG_HINT: string = '#8A8F99';
const BG_KEY: string = '#FFFFFF';
/** H-220(Qoder)：「选择」模式开启时的格子底色（与键面功能底色同一族）。 */
const BG_KEY_ACTIVE: string = '#B8C6E8';
/** H-231(Qoder)：「选择」格开启态的字色（与键面功能色同族，见 KeyboardIndex.FG_ACCENT='#2B5FBF'）。 */
const FG_ACCENT: string = '#2B5FBF';
const CURSOR_REPEAT_MS: number = 120;

// H-232(Qoder 2026-10-27 22:4x 真机实测)：⤶ 面板上下内边距（与 build() 里 Row 的 padding 一致）。
const PANEL_PAD: number = 6;
// H-232：⤶ 右操作列格子之间的间隙（与 build() 里 Column({space:4}) 一致）。
const RIGHT_GAP: number = 4;
// H-232：⤶ 右操作列的格数＝全选/剪切/复制/粘贴/⌫（改格数必须同步改这里，否则粘贴徽章又被拉扁）。
const RIGHT_CELLS: number = 5;

// H-204(Qoder)：剪贴板说明只在本次进程第一次打开面板时弹一次（主人要「开始使用时加说明」）
let clipboardHintShown: boolean = false;

@Styles
function keyPressed() {
  .backgroundColor('#DCE2EC')
}

// H-194(CodeArts): 光标移动面板——四向箭头 + 按住连续移动
// 上游 TextEditingWindow.kt:51-57 用 CustomGestureView.repeatEnabled 实现连续
// 我们用 ArkTS 定时器：onTouch Down 启动定时器，每 120ms 发一次方向键；Up/Cancel 停止
@Component
export struct CursorPad {
  @Prop barHeight: number = 44;

  private repeatTimer: number = -1;

  private startRepeat(dir: number): void {
    keyboardController.moveEditorCursor(dir);
    this.repeatTimer = setInterval(() => {
      keyboardController.moveEditorCursor(dir);
    }, CURSOR_REPEAT_MS);
  }

  private stopRepeat(): void {
    if (this.repeatTimer !== -1) {
      clearInterval(this.repeatTimer);
      this.repeatTimer = -1;
    }
  }

  // H-200(CodeArts): 组件消失时清定时器，防止面板被换掉后仍往宿主移光标
  aboutToDisappear(): void {
    this.stopRepeat();
  }

  build() {
    Row() {
      Stack() {
        SymbolGlyph($r('sys.symbol.chevron_left'))
          .fontSize(20)
          .fontColor([FG_TOOLBAR])
      }
      .width('25%')
      .height(this.barHeight)
      .backgroundColor(BG_KEY)
      .borderRadius(8)
      .stateStyles({ pressed: keyPressed })
      .onTouch((e: TouchEvent) => {
        if (e.type === TouchType.Down) {
          this.startRepeat(3);
        } else if (e.type === TouchType.Up || e.type === TouchType.Cancel) {
          this.stopRepeat();
        }
      })

      Stack() {
        SymbolGlyph($r('sys.symbol.chevron_up'))
          .fontSize(20)
          .fontColor([FG_TOOLBAR])
      }
      .width('25%')
      .height(this.barHeight)
      .backgroundColor(BG_KEY)
      .borderRadius(8)
      .stateStyles({ pressed: keyPressed })
      .onTouch((e: TouchEvent) => {
        if (e.type === TouchType.Down) {
          this.startRepeat(1);
        } else if (e.type === TouchType.Up || e.type === TouchType.Cancel) {
          this.stopRepeat();
        }
      })

      Stack() {
        SymbolGlyph($r('sys.symbol.chevron_down'))
          .fontSize(20)
          .fontColor([FG_TOOLBAR])
      }
      .width('25%')
      .height(this.barHeight)
      .backgroundColor(BG_KEY)
      .borderRadius(8)
      .stateStyles({ pressed: keyPressed })
      .onTouch((e: TouchEvent) => {
        if (e.type === TouchType.Down) {
          this.startRepeat(2);
        } else if (e.type === TouchType.Up || e.type === TouchType.Cancel) {
          this.stopRepeat();
        }
      })

      Stack() {
        SymbolGlyph($r('sys.symbol.chevron_right'))
          .fontSize(20)
          .fontColor([FG_TOOLBAR])
      }
      .width('25%')
      .height(this.barHeight)
      .backgroundColor(BG_KEY)
      .borderRadius(8)
      .stateStyles({ pressed: keyPressed })
      .onTouch((e: TouchEvent) => {
        if (e.type === TouchType.Down) {
          this.startRepeat(4);
        } else if (e.type === TouchType.Up || e.type === TouchType.Cancel) {
          this.stopRepeat();
        }
      })
    }
    .width('100%')
    .height(this.barHeight)
    .justifyContent(FlexAlign.SpaceAround)
    .alignItems(VerticalAlign.Center)
    .padding({ left: 4, right: 4 })
    .backgroundColor(BG_BAR)
  }
}

// H-194(CodeArts): 剪贴板面板
// H-204(Qoder 2026-10-26)：主人实测「粘贴没反应」+「加说明让用户开权限（像百度那样）」。
// 鸿蒙的硬事实（华为官方答复）：应用级输入法**不允许**直接读剪贴板（即使开「完整体验模式」），
// 申请 READ_PASTEBOARD 是受限权限（system_basic，要 AGC 配 ACL 签名），普通分发拿不到；
// 系统给的唯一合规通道是**安全控件 PasteButton**：用户点一下＝对当前剪贴板临时授权一次，
// 回调里读 getData() 再 insertText。所以这里不放自定义「粘贴」按钮，也不做假权限弹窗。
// 说明文案写死在本面板里（不只靠 toast），用户随时能看到为什么必须点这个系统按钮。
@Component
export struct ClipboardPad {
  @Prop barHeight: number = 44;

  aboutToAppear(): void {
    if (clipboardHintShown) {
      return;
    }
    clipboardHintShown = true;
    try {
      promptAction.showToast({
        message: '剪贴板：点系统「粘贴」按钮＝授权读一次当前内容，不需要去设置里开权限',
        duration: 4000
      });
    } catch (e) {
      console.warn(`H-204 clipboard hint toast failed: ${JSON.stringify(e)}`);
    }
  }

  build() {
    // H-207(Qoder 2026-10-26 19:4x 真机定论)：安全控件在本输入法进程里**注册不上**，
    // 与样式/高度/父节点都无关（三种摆法都试过，结论一致）：
    //   `AceSecurityComponent: load security component service failed.`
    //   → `SecCompClient: [RegisterSecurityComponent]Proxy is null.`
    //   → `SecCompKit: register security component fail, error: -50`
    // 另一次还出现 `[RegisterSecurityComponentBody]Failed to get bundle info for bundle name
    // com.sansheng.ime`——当前装的是**自签调试包**（`bm dump` 实测 isSystemApp=false、
    // signatureKey 为空），安全控件服务按 bundle 查不到正式签名登记。
    // 「让宿主自己贴」也实测走不通：`sendExtendAction(PASTE)` 确实送到了宿主
    //（`AceTextField: HandleOnPaste`），但剪贴板服务拒了宿主本身：
    //   `PBS: IsPermissionGranted# permission denied, perm=ohos.permission.READ_PASTEBOARD`
    //   `PBC: ProcessPasteData# Invalid raw data size:0` ⇒ `HandleOnPaste fail, data is empty`
    // 华为官方答复（论坛 2025-08-29）：应用级输入法**只能**用 PasteButton，即使开完整体验
    // 模式也不许直接读。所以：
    //   · 保留系统 PasteButton（不自定义样式）：正式签名/上架后若系统放行，它自动可用；
    //   · 失败时给**明确原因**，不弹「请再点一次」这种骗人的话；
    //   · 界面上常驻一行说明，用户随时知道为什么点不动、该怎么办。
    // 主人 2026-10-26 19:4x 拍板：按「上架后走正式签名再验」收口，现在不做假按钮。
    Column({ space: 2 }) {
      PasteButton({ icon: PasteIconStyle.LINES, text: PasteDescription.PASTE, buttonType: ButtonType.Capsule })
        .onClick((event: ClickEvent, result: PasteButtonOnClickResult, error?: BusinessError<void>) => {
          console.info(`${TAG} H-207 PasteButton click result=${result} err=${error === undefined ? 'none' : `${error.code} ${error.message}`}`);
          if (result !== PasteButtonOnClickResult.SUCCESS) {
            // 当前自签包必然走到这里（error -50 / Proxy is null）。如实说明，不哄用户重点。
            promptAction.showToast({
              message: '当前调试版系统不授权剪贴板（正式版可用）；先在自己应用里长按粘贴',
              duration: 3000
            });
            return;
          }
          keyboardController.pasteClipboardText((ok: boolean, msg: string) => {
            try {
              promptAction.showToast({ message: msg, duration: 2000 });
            } catch (e) {
              console.warn(`H-204 paste toast failed: ${JSON.stringify(e)}`);
            }
            console.info(`H-204 paste result ok=${ok} msg=${msg}`);
          });
        })
      // H-194 闸门要求界面上有永久说明（含「剪贴板/授权」字样）
      Text('剪贴板：需系统授权才能读（正式版可用）；当前可长按输入框粘贴')
        .fontSize(10)
        .fontColor(FG_HINT)
        .maxLines(1)
        .textOverflow({ overflow: TextOverflow.Ellipsis })
        .width('100%')
        .textAlign(TextAlign.Center)
    }
    .width('100%')
    .height(this.barHeight)
    .justifyContent(FlexAlign.Center)
  }
}

// H-218(Qoder 2026-10-27)：文本编辑全量面板——主人原话「重做后面那个工具，文本编辑内容不对，
// 现在只有光标左右移动，把放弃的行首行尾上页下页上下左右全选复制粘贴都放进去，参照安卓版」。
// 安卓参照：fcitx5-android TextEditingWindow（上下左右/行首页尾/全选/复制/剪切/粘贴）。
// H-218r2（主人 2026-10-27 14:4x「文本编辑不在一行上，展开铺到键盘上，你没看安卓吗」）：
// 安卓那个面板是**接管整个键区**的，不是候选栏里挤一条 ⇒ 新增 full 模式：3 行 ×4 列铺满
// 键区高度（panelHeight=4×rowHeight），单行模式保留给旧调用位。方向键按住连续（复用
// CursorPad 的 120ms 定时器口径），上5行/下5行=纵向 5 行（KeyboardController.moveCursorPage；
// H-235 起标签不再写「页」——鸿蒙拿不到宿主可视区域，「页」是假承诺）。
// 粘贴沿用系统 PasteButton（H-207 定论：自签包注册不上、正式版自动可用，失败给真话 toast）。
@Component
export struct TextEditPad {
  @Prop barHeight: number = 44;
  /** H-218r2：true = 铺满键区（3×4 网格）；false = 单行 12 枚（旧位）。 */
  @Prop full: boolean = false;
  /** H-218r2：full 模式下面板总高（vp），由调用方给 4×rowHeight（=键区等高，窗口不伸缩）。 */
  @Prop panelHeight: number = 192;
  /** H-218r2：full 模式行数（H-220 起 5 行：4×4 全满 + 第 5 行「选择/取消」）。 */
  @Prop rows: number = 5;
  /** H-220（Qoder，主人「安卓里面有个选择键，可以按方向选择文本」）：控制器扩展选区
   *  模式的镜像态（KeyboardIndex.selMode 传下来，真源是 KeyboardController）。 */
  @Prop selOn: boolean = false;
  /** H-218r2：退出子面板回调（「退出」格用；由 KeyboardIndex 传入置空 funcSubPanel）。 */
  onExitRequest: () => void = () => {};

  private repeatTimer: number = -1;

  private cellW(): string {
    return this.full ? '25%' : '8.33%';
  }

  private cellH(): number {
    // H-218r4(Qoder)：full 模式按**键区预算**等高切 5 行——外层 Column 每两行之间有 4vp space，
    // 所以单格高 = (面板高 − (行数−1)×4) / 行数，正好铺满不超窗（超一个 rowHeight 就会把末行
    // 裁到 IME 窗口外，H-213 同款事故；窗口高恒定，见 KeyboardIndex.TextEditGridPanel 注释）。
    return this.full ? (this.panelHeight - (this.rows - 1) * 4) / this.rows : this.barHeight - 8;
  }

  private glyphSize(): number {
    return this.full ? 24 : 18;
  }

  private wordSize(): number {
    return this.full ? 16 : 11;
  }

  private startRepeat(dir: number): void {
    if (this.repeatTimer !== -1) {
      return;   // H-218r2: 按住连发期间重复 Down 不再叠定时器
    }
    keyboardController.moveEditorCursor(dir);
    this.repeatTimer = setInterval(() => {
      keyboardController.moveEditorCursor(dir);
    }, CURSOR_REPEAT_MS);
  }

  private stopRepeat(): void {
    if (this.repeatTimer !== -1) {
      clearInterval(this.repeatTimer);
      this.repeatTimer = -1;
    }
  }

  aboutToDisappear(): void {
    this.stopRepeat();
  }

  @Builder
  glyph(icon: Resource, onTap: () => void) {
    Stack() {
      SymbolGlyph(icon)
        .fontSize(this.glyphSize())
        .fontColor([FG_TOOLBAR])
    }
    .width(this.cellW())
    .height(this.cellH())
    .backgroundColor(BG_KEY)
    .borderRadius(8)
    .stateStyles({ pressed: keyPressed })
    .onClick(onTap)
  }

  /** H-220：`active` 只给「选择/取消」格用——模式开着时格子必须看得出开着。 */
  @Builder
  word(label: string, onTap: () => void, active: boolean = false) {
    Stack() {
      Text(label)
        .fontSize(this.wordSize())
        .fontColor(FG_TOOLBAR)
        .maxLines(1)
    }
    .width(this.cellW())
    .height(this.cellH())
    .backgroundColor(active ? BG_KEY_ACTIVE : BG_KEY)
    .borderRadius(8)
    .stateStyles({ pressed: keyPressed })
    .onClick(onTap)
  }

  @Builder
  holdDir(dir: number) {
    Stack() {
      SymbolGlyph(dir === 3 ? $r('sys.symbol.chevron_left') :
        dir === 4 ? $r('sys.symbol.chevron_right') :
          dir === 1 ? $r('sys.symbol.chevron_up') : $r('sys.symbol.chevron_down'))
        .fontSize(this.glyphSize())
        .fontColor([FG_TOOLBAR])
    }
    .width(this.cellW())
    .height(this.cellH())
    // H-220(Qoder)：扩展选区开着时四向格亮底（同「选择」行），表示按下去是选字。
    .backgroundColor(this.selOn ? BG_KEY_ACTIVE : BG_KEY)
    .borderRadius(8)
    .stateStyles({ pressed: keyPressed })
    .onTouch((e: TouchEvent) => {
      if (e.type === TouchType.Down) {
        this.startRepeat(dir);
      } else if (e.type === TouchType.Up || e.type === TouchType.Cancel) {
        this.stopRepeat();
      }
    })
  }

  /** H-232(Qoder 2026-10-27 22:4x 真机实测)：右列每格的**真实行高**（vp）。
   *  右列 5 格的高度是布局引擎按 layoutWeight 均分给的，公式＝（面板高 − 上下 padding 12
   *  − 列内 4 个 4vp 间隙）÷ 5。本函数把**同一个行高当宽度用** ⇒ 粘贴格是正方形，
   *  系统粘贴徽章画成正圆；修复前它被 cellW/cellH 算成 26.7×35.2vp，实测成 95×123px
   *  的椭圆，还比兄弟格（113px 行高）高出 10px 溢出行格（22:31 真机截图量到）。 */
  private rightCellW(): number {
    return (this.panelHeight - 2 * PANEL_PAD - (RIGHT_CELLS - 1) * RIGHT_GAP) / RIGHT_CELLS;
  }

  /** H-218r2/H-207：粘贴结果统一处理（full 模式格与单行旧格共用，H-232 抽出来的）。 */
  private onPasteResult(result: PasteButtonOnClickResult, error?: BusinessError<void>): void {
    console.info(`${TAG} H-218 PasteButton result=${result} err=${error === undefined ? 'none' : `${error.code} ${error.message}`}`);
    if (result !== PasteButtonOnClickResult.SUCCESS) {
      try {
        promptAction.showToast({
          message: '当前调试版系统不授权剪贴板（正式版可用）；先在自己应用里长按粘贴',
          duration: 3000
        });
      } catch (e) {
        console.warn(`H-218 paste toast failed: ${JSON.stringify(e)}`);
      }
      return;
    }
    keyboardController.pasteClipboardText((ok: boolean, msg: string) => {
      try {
        promptAction.showToast({ message: msg, duration: 2000 });
      } catch (e) {
        console.warn(`H-218 paste toast failed: ${JSON.stringify(e)}`);
      }
    });
  }

  /** H-218r2: 粘贴枚（PasteButton 安全控件）。
   *  H-207 定论：外层不得加 opacity/裁切，失败给真话 toast。
   *  H-232(Qoder 2026-10-27 22:4x 真机实测)：右列 5 格里**只有**这一枚还在用 cellW/cellH——
   *  宽按 25% 算成 26.7vp、高按 cellH() 算成 35.2vp（cellH 少扣了外层 12vp padding），
   *  系统徽章被拉成 95×123px 椭圆并溢出行格。现在与兄弟格**完全同构**：
   *  外层格子照兄弟格 layoutWeight 均分，内层徽章取「右列行高」见方 ⇒ 正圆、不越界。
   *  注意：PasteButton 是系统控件，**不支持 layoutWeight**（实测 ArkTS 编译报
   *  「Property 'layoutWeight' does not exist on type 'PasteButtonAttribute'」），
   *  所以均分只能落在外层容器上。 */
  @Builder
  pasteCell() {
    Column() {
      PasteButton({ icon: PasteIconStyle.LINES, text: PasteDescription.PASTE, buttonType: ButtonType.Capsule })
        .width(this.rightCellW())
        .height(this.rightCellW())
        .fontSize(12)
        .onClick((event: ClickEvent, result: PasteButtonOnClickResult, error?: BusinessError<void>) => {
          this.onPasteResult(result, error);
        })
    }
    .layoutWeight(1)
    .height('100%')
    .width('100%')
    .justifyContent(FlexAlign.Center)
    .alignItems(HorizontalAlign.Center)
  }

  /** H-232：单行旧位（full=false）的粘贴枚，尺寸口径保持原样（8.33% 宽、栏内高）。
   *  该调用位当前没有活路径（唯一调用位是 full=true），按 H-129「证明、记录、留着」保留。 */
  @Builder
  pasteCellLegacy() {
    PasteButton({ icon: PasteIconStyle.LINES, text: PasteDescription.PASTE, buttonType: ButtonType.Capsule })
      .width(this.cellW())
      .height(this.cellH())
      .fontSize(9)
      .onClick((event: ClickEvent, result: PasteButtonOnClickResult, error?: BusinessError<void>) => {
        this.onPasteResult(result, error);
      })
  }

  /** H-218r2: 单行模式的 14 枚（旧调用位保留；full 网格不用它，行内直接摆）。
   *  H-235/H-236（Qoder 2026-10-28 00:4x）：实机**走不到这一支**——KeyboardIndex 里 TextEditPad
   *  只有一处实例化且 `full: true`（KeyboardIndex.ets:3238），所以这里保留旧标签「上页/下页」和
   *  复制图标不做同步修改，按 H-129 口径「证明、记录、留着」（不是删，也不是偷偷改）。 */
  @Builder
  editActions() {
    this.glyph($r('sys.symbol.undo'), () => {
      keyboardController.undoCommit();
    })
    this.glyph($r('sys.symbol.redo'), () => {
      keyboardController.redoCommit();
    })
    this.word('全选', () => {
      keyboardController.sendEditorAction(inputMethodEngine.ExtendAction.SELECT_ALL);
    })
    this.word('剪切', () => {
      keyboardController.sendEditorAction(inputMethodEngine.ExtendAction.CUT);
    })
    this.glyph($r('sys.symbol.doc_filled_on_doc'), () => {
      keyboardController.copyThenCollapse();
    })
    this.pasteCellLegacy()
    this.holdDir(3)
    this.holdDir(4)
    this.holdDir(1)
    this.holdDir(2)
    this.word('行首', () => {
      keyboardController.moveCursorToLineStart();
    })
    this.word('行尾', () => {
      keyboardController.moveCursorToLineEnd();
    })
    this.word('上页', () => {
      keyboardController.moveCursorPage(-5);
    })
    this.word('下页', () => {
      keyboardController.moveCursorPage(5);
    })
  }

  /** H-228(Qoder 2026-10-27 17:5x，主人「展开丑的一批」「那个图标也不合适，参考安卓那个图标吧」)：
   *  full 模式改成**照安卓 TextEditingUi.kt 的真实结构**（证据
   *  `docs/evidence/2026-10-26/h194-panels-upstream/README.md` §2.1）：
   *  左侧约 70% 是 **3×3 方向/定位簇**（←↑→ / 上页·选择·下页 / 行首·↓·行尾），
   *  右侧约 30% 是 **操作列**（全选/剪切/复制/粘贴/退格）。
   *  旧版是 5 行等宽等高的文字格子，一行 4 枚、全是小字，主人说丑——安卓根本不是那个形状。
   *  **高度不再算死**：整块用 layoutWeight 均分，容器给多少就吃多少，
   *  从根上消掉 H-213/H-218r3「内容超窗把末行裁掉」那一类事故（不用再手算 cellH）。
   *  「全首/全尾」不在面板里了——它们已经搬到字母键 f/g 的长按（H-226），面板不重复摆。 */
  @Builder
  gridGlyph(icon: Resource, onTap: () => void) {
    Stack() {
      SymbolGlyph(icon)
        .fontSize(this.glyphSize())
        .fontColor([FG_TOOLBAR])
    }
    .layoutWeight(1)
    .height('100%')
    .backgroundColor(BG_KEY)
    .borderRadius(8)
    .stateStyles({ pressed: keyPressed })
    .onClick(onTap)
  }

  @Builder
  gridWord(label: string, onTap: () => void) {
    Stack() {
      Text(label)
        .fontSize(this.wordSize())
        .fontColor(FG_TOOLBAR)
        .maxLines(1)
    }
    .layoutWeight(1)
    .height('100%')
    .backgroundColor(BG_KEY)
    .borderRadius(8)
    .stateStyles({ pressed: keyPressed })
    .onClick(onTap)
  }

  @Builder
  gridHold(dir: number) {
    Stack() {
      SymbolGlyph(dir === 3 ? $r('sys.symbol.chevron_left') :
        dir === 4 ? $r('sys.symbol.chevron_right') :
          dir === 1 ? $r('sys.symbol.chevron_up') : $r('sys.symbol.chevron_down'))
        .fontSize(this.glyphSize())
        .fontColor([FG_TOOLBAR])
    }
    .layoutWeight(1)
    .height('100%')
    .backgroundColor(this.selOn ? BG_KEY_ACTIVE : BG_KEY)
    .borderRadius(8)
    .stateStyles({ pressed: keyPressed })
    .onTouch((e: TouchEvent) => {
      if (e.type === TouchType.Down) {
        this.startRepeat(dir);
      } else if (e.type === TouchType.Up || e.type === TouchType.Cancel) {
        this.stopRepeat();
      }
    })
  }

  /** H-231（Qoder 2026-10-27 20:0x，主人「图标成点了，里面没有选择按钮」）：
   *  「选择」格＝扩选模式的开关，**没有它就开不了扩选**（H-220 的功能根）。
   *  H-228 那版把它写成 Row 里的**内联 Stack**，和左右两枚 @Builder 格子混排——实机（主人
   *  19:0x）恰恰看不见这一格。现在改走与兄弟格**完全同构的 @Builder 路径**：结构一样，
   *  不会再出现「整排都在、只有中间这格不在」。
   *  状态 `this.selOn` 在 builder 内部直接读（按值传进来是 H-165③ 同款坑）。
   *  文案：关＝「选择」，开＝「取消选择」——**两种状态都带「选择」二字**，
   *  开着的时候也一眼认得出这就是选择开关（先前写「取消」，主人按「找选择按钮」找不到）。 */
  @Builder
  gridSelect() {
    Stack() {
      Text(this.selOn ? '取消选择' : '选择')
        .fontSize(this.wordSize())
        .fontColor(this.selOn ? FG_ACCENT : FG_TOOLBAR)
        .maxLines(1)
    }
    .layoutWeight(1)
    .height('100%')
    .backgroundColor(this.selOn ? BG_KEY_ACTIVE : BG_KEY)
    .borderRadius(8)
    .stateStyles({ pressed: keyPressed })
    .onClick(() => {
      keyboardController.toggleSelectionMode();
      console.info(`${TAG} H-231 gridSelect tapped selOn=${this.selOn}`);
    })
  }

  build() {
    if (this.full) {
      // 左 3×3（权重 2.2）+ 右操作列（权重 1），整体铺满容器，不写死任何高度。
      Row({ space: 6 }) {
        Column({ space: 4 }) {
          Row({ space: 4 }) {
            this.gridHold(3)
            this.gridHold(1)
            this.gridHold(4)
          }
          .layoutWeight(1)
          .width('100%')
          Row({ space: 4 }) {
            // H-235（Qoder 2026-10-28 00:4x，主人 2026-10-27 深夜「上页下页怎么定义的，我看不出来」）：
            // 改成实话标签「上5行/下5行」。鸿蒙 IME **拿不到宿主可视区域**⇒ 根本没有「页」这个量
            // （与 H-226 把 f/g 角标从「页首/页尾」改成「文首/文末」同一个理由），底层动作是
            // `moveCursorSync` 连发 5 次上/下（KeyboardController.moveCursorPage），也就是**跳 5 行**。
            // 写「页」＝假承诺；写「5 行」＝按下去就知道会发生什么。开着「选择」时同样 5 行，只是扩选。
            this.gridWord('上5行', () => {
              keyboardController.moveCursorPage(-5);
            })
            // 选择：安卓 selectButton 的居中位；开着时亮底 + 文案变「取消选择」
            // H-231：改走 @Builder（gridSelect），不再用内联 Stack——见 gridSelect 注释。
            this.gridSelect()
            this.gridWord('下5行', () => {
              keyboardController.moveCursorPage(5);
            })
          }
          .layoutWeight(1)
          .width('100%')
          Row({ space: 4 }) {
            this.gridWord('行首', () => {
              keyboardController.moveCursorToLineStart();
            })
            this.gridHold(2)
            this.gridWord('行尾', () => {
              keyboardController.moveCursorToLineEnd();
            })
          }
          .layoutWeight(1)
          .width('100%')
        }
        .layoutWeight(2.2)
        .height('100%')

        Column({ space: 4 }) {
          this.gridWord('全选', () => {
            keyboardController.sendEditorAction(inputMethodEngine.ExtendAction.SELECT_ALL);
          })
          this.gridWord('剪切', () => {
            keyboardController.sendEditorAction(inputMethodEngine.ExtendAction.CUT);
          })
          // H-236（Qoder 2026-10-28 00:4x，主人 2026-10-27 深夜「复制还是个图标形式，全选，剪切都是
          // 文字」）：「复制」从系统符号图标改成**文字格**，与兄弟格同口径。这不是我拍脑袋——安卓上游
          // 实物就是整列文字：`selectAllButton`「全选」/`cutButton`「剪切」/`copyButton`「复制」/
          // `pasteButton`「粘贴」都是文字按钮，只有 `backspaceButton` 用 ⌫ 图标（altStyle）。
          // 证据：docs/evidence/2026-10-26/h194-panels-upstream/README.md §2.1。
          // ⇒ 本列现状＝全选/剪切/复制/退格四枚我们自己画（三枚文字＋末一枚 ⌫ 图标，与安卓一致），
          //   中间「粘贴」那枚是**系统安全控件 PasteButton**：它必须保持系统原样才拿得到剪贴板临时授权
          //   （H-207 铁证：父节点加 opacity/padding 挤压 ⇒ `security component has not registered` ⇒
          //   点多少次都失败），所以它没法改成文字格，是这一列里唯一改不了的一枚，已如实登记 H-236。
          this.gridWord('复制', () => {
            keyboardController.copyThenCollapse();
          })
          this.pasteCell()
          // 安卓 backspaceButton：⌫ 退格（删光标前），不是 m 的 Del（删光标后）。
          // H-236：这一枚**保持图标**——安卓实物 backspaceButton 就是 ⌫ 图标，不是文字。
          this.gridGlyph($r('sys.symbol.delete_left'), () => {
            keyboardController.onBackspace();
          })
        }
        .layoutWeight(1)
        .height('100%')
      }
      .width('100%')
      .height(this.panelHeight)
      .padding({ left: 6, right: 6, top: 6, bottom: 6 })
      .backgroundColor(BG_BAR)
    } else {
      Row() {
        this.editActions()
      }
      .width('100%')
      .height(this.barHeight)
      .justifyContent(FlexAlign.SpaceEvenly)
      .alignItems(VerticalAlign.Center)
      .padding({ left: 2, right: 2 })
      .backgroundColor(BG_BAR)
    }
  }
}
