/*
 * 三生输入法 · 应用正式首页（H-072，M6）
 * 归属：CodeArts（鸿蒙 UI）。
 * 原 mock 引擎冒烟页已退役（开发探针走启动参数 m3_probe=1 → pages/M3Probe）。
 * 本页：应用名+版本（bundleInfo.versionName）、启用方法说明、
 * 试打 TextArea、隐私政策/用户协议/关于三个入口。
 */
import bundleManager from '@ohos.bundle.bundleManager';
import preferences from '@ohos.data.preferences';
import { PrivacyConsent } from '../common/PrivacyConsent';

/** H-072：LegalPage 路由参数（ArkTS 严格模式要求显式类型）。 */
class LegalRouteParams {
  doc: string = 'privacy';

  constructor(doc: string) {
    this.doc = doc;
  }
}

const PREF_STORE: string = 'sansheng_prefs';
const PREF_KEY_AGREED: string = 'privacy_agreed';

@Entry
@Component
struct Index {
  @State versionName: string = '1.0.0';
  // H-074：首次启动隐私弹窗（未读过同意记录才显示）
  @State showConsent: boolean = false;
  private prefStore: preferences.Preferences | undefined = undefined;

  aboutToAppear(): void {
    this.initPrefs();
    try {
      bundleManager.getBundleInfoForSelf(bundleManager.BundleFlag.GET_BUNDLE_INFO_DEFAULT)
        .then((info: bundleManager.BundleInfo) => {
          if (info.versionName !== undefined && info.versionName.length > 0) {
            this.versionName = info.versionName;
          }
        })
        .catch(() => {
          // 查询失败：保持回退版本号 1.0.0
        });
    } catch (e) {
      // 同步异常：保持回退版本号 1.0.0
    }
  }

  /** H-074：读 preferences——无 privacy_agreed 记录才弹窗。 */
  private async initPrefs(): Promise<void> {
    try {
      const ctx: Context = this.getUIContext().getHostContext() as Context;
      if (ctx === undefined || ctx === null) {
        // 上下文异常：不弹（避免永久弹窗死循环）
        return;
      }
      this.prefStore = await preferences.getPreferences(ctx, PREF_STORE);
      const agreed: preferences.ValueType = this.prefStore.getSync(PREF_KEY_AGREED, false);
      this.showConsent = agreed !== true;
    } catch (e) {
      // preferences 不可用：不弹（避免异常环境下反复打扰）
      this.showConsent = false;
    }
  }

  private openLegal(doc: string): void {
    this.getUIContext().getRouter().pushUrl({
      url: 'pages/LegalPage',
      params: new LegalRouteParams(doc)
    });
  }

  private openAbout(): void {
    this.getUIContext().getRouter().pushUrl({
      url: 'pages/AboutPage'
    });
  }


  build() {
    Stack() {
      Scroll() {
        Column() {
          // 应用名 + 版本
          Text('三生输入法')
          .fontSize(28)
          .fontWeight(FontWeight.Bold)
          .fontColor('#1A1C1E')
          .textAlign(TextAlign.Center)
          .width('100%')
          .margin({ top: 48 })

        Text(`v${this.versionName}`)
          .fontSize(14)
          .fontColor('#8A8F99')
          .textAlign(TextAlign.Center)
          .width('100%')
          .margin({ top: 6 })

        Text('五笔 · 拼音 · 英文 三向混输')
          .fontSize(14)
          .fontColor('#8A8F99')
          .textAlign(TextAlign.Center)
          .width('100%')
          .margin({ top: 4 })

        // 启用方法
        Column({ space: 6 }) {
          Text('启用方法')
            .fontSize(18)
            .fontWeight(FontWeight.Bold)
            .fontColor('#1A1C1E')
            .width('100%')
          Text('1. 打开「设置」→「系统和更新」→「语言和输入法」')
            .fontSize(14)
            .fontColor('#1A1C1E')
            .width('100%')
          Text('2. 进入「默认输入法」或「输入法管理」')
            .fontSize(14)
            .fontColor('#1A1C1E')
            .width('100%')
          Text('3. 选择「三生输入法」并确认')
            .fontSize(14)
            .fontColor('#1A1C1E')
            .width('100%')
          Text('4. 在任意输入框中长按，切换到三生输入法即可使用')
            .fontSize(14)
            .fontColor('#1A1C1E')
            .width('100%')
        }
        .width('100%')
        .padding({ left: 20, right: 20, top: 16 })
        .alignItems(HorizontalAlign.Start)

        Divider().color('#E4E7EC')
          .margin({ top: 20, bottom: 20, left: 20, right: 20 })

        // 试打区
        Column({ space: 8 }) {
          Text('试一试')
            .fontSize(18)
            .fontWeight(FontWeight.Bold)
            .fontColor('#1A1C1E')
            .width('100%')
          TextArea({ placeholder: '点这里试打一行' })
            .fontSize(16)
            .fontColor('#1A1C1E')
            .placeholderColor('#8A8F99')
            .placeholderFont({ size: 15 })
            .backgroundColor('#FFFFFF')
            .borderRadius(8)
            .width('100%')
            .height(120)
            .padding(12)
        }
        .width('100%')
        .padding({ left: 20, right: 20 })

        // 法律与关于入口
        Column({ space: 10 }) {

          Button('隐私政策')
            .fontSize(15)
            .fontColor('#2B5FBF')
            .backgroundColor('#FFFFFF')
            .borderRadius(8)
            .width('100%')
            .height(42)
            .onClick(() => {
              this.openLegal('privacy');
            })
          Button('用户协议')
            .fontSize(15)
            .fontColor('#2B5FBF')
            .backgroundColor('#FFFFFF')
            .borderRadius(8)
            .width('100%')
            .height(42)
            .onClick(() => {
              this.openLegal('terms');
            })
          Button('关于与第三方声明')
            .fontSize(15)
            .fontColor('#2B5FBF')
            .backgroundColor('#FFFFFF')
            .borderRadius(8)
            .width('100%')
            .height(42)
            .onClick(() => {
              this.openAbout();
            })
        }
        .width('100%')
        .padding({ left: 20, right: 20, top: 20, bottom: 32 })
      }
      .width('100%')
    }
    .width('100%')
    .height('100%')
    .backgroundColor('#F2F3F5')
    .scrollBar(BarState.Auto)

    // H-074：首次启动隐私政策弹窗（自绘模态层，未同意过才渲染）
    PrivacyConsent({
      visible: this.showConsent,
      onOpenLegal: (doc: string) => {
        this.openLegal(doc);
      }
    })
    }
    .width('100%')
    .height('100%')
  }
}
