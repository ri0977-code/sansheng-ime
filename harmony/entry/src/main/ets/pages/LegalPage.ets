/*
 * 三生输入法 · 法律文本页（H-070，M6）
 * 归属：CodeArts（鸿蒙 UI）。
 * Web 组件加载 rawfile/legal/ 下 Qoder 预置的 privacy.html / terms.html，
 * 本地渲染、无网络请求（不加 INTERNET 权限）。
 * 路由参数 doc=privacy|terms 决定首屏文档；顶栏两钮切换。
 * H-073（M-055）：切换时显式 loadUrl 重载正文——Web 的 src 只在首次 attach 生效，
 * 单改 @State doc 不会触发重载，导致按钮高亮与正文矛盾；
 * 加载期间用占位遮罩（onPageBegin 置 loading / onPageEnd 复位），
 * 保证任何时刻屏上正文与高亮按钮一致。
 */
import { webview } from '@kit.ArkWeb';
import router from '@ohos.router';

interface LegalPageParams {
  doc?: string;
}

@Entry
@Component
struct LegalPage {
  @State doc: string = 'privacy';
  @State loading: boolean = false;
  private webController: webview.WebviewController = new webview.WebviewController();
  private controllerReady: boolean = false;

  aboutToAppear(): void {
    const params: LegalPageParams = router.getParams() as LegalPageParams;
    if (params !== undefined && params !== null) {
      const d: string | undefined = params.doc;
      if (d === 'terms' || d === 'notice') {
        this.doc = d;
      }
    }
  }

  private docUrl(): string {
    const map: Record<string, string> = {
      'privacy': 'resource://rawfile/legal/privacy.html',
      'terms': 'resource://rawfile/legal/terms.html',
      'notice': 'resource://rawfile/legal/notice.html',
    };
    return map[this.doc] ?? 'resource://rawfile/legal/privacy.html';
  }

  private switchDoc(target: string): void {
    if (target === this.doc) {
      return;
    }
    this.doc = target;
    // H-073：显式重载——控制器已 attach 才调 loadUrl，避免抛错；
    // 未 attach（首帧前）时 src 会按新 docUrl() 渲染，无需手动加载。
    if (this.controllerReady) {
      this.loading = true;
      try {
        this.webController.loadUrl(this.docUrl());
      } catch (e) {
        // 加载失败：撤销占位，保持旧文档可见
        this.loading = false;
      }
    }
  }

  build() {
    Column() {
      // 顶栏：返回 + 隐私政策/用户协议切换
      Row() {
        Button('返回')
          .fontSize(15)
          .fontColor('#1A1C1E')
          .backgroundColor('#E4E7EC')
          .borderRadius(6)
          .height(36)
          .padding({ left: 12, right: 12 })
          .onClick(() => {
            this.getUIContext().getRouter().back();
          })
        Text('隐私政策')
          .fontSize(15)
          .fontColor(this.doc === 'privacy' ? '#FFFFFF' : '#1A1C1E')
          .textAlign(TextAlign.Center)
          .backgroundColor(this.doc === 'privacy' ? '#2B5FBF' : '#E4E7EC')
          .borderRadius(6)
          .height(36)
          .padding({ left: 14, right: 14 })
          .margin({ left: 10 })
          .onClick(() => {
            this.switchDoc('privacy');
          })
        Text('用户协议')
          .fontSize(15)
          .fontColor(this.doc === 'terms' ? '#FFFFFF' : '#1A1C1E')
          .textAlign(TextAlign.Center)
          .backgroundColor(this.doc === 'terms' ? '#2B5FBF' : '#E4E7EC')
          .borderRadius(6)
          .height(36)
          .padding({ left: 14, right: 14 })
          .margin({ left: 10 })
          .onClick(() => {
            this.switchDoc('terms');
          })
      }
      .width('100%')
      .padding({ left: 12, right: 12, top: 10, bottom: 10 })

      // 本地文档渲染（无网络）——H-073：加载期间占位遮罩，旧文档不残留
      Stack() {
        Web({ src: this.docUrl(), controller: this.webController })
          .width('100%')
          .height('100%')
          .onControllerAttached(() => {
            this.controllerReady = true;
          })
          .onPageBegin(() => {
            this.loading = true;
          })
          .onPageEnd(() => {
            this.loading = false;
          })

        if (this.loading) {
          Column() {
            Text('加载中…')
              .fontSize(14)
              .fontColor('#8A8F99')
          }
          .width('100%')
          .height('100%')
          .justifyContent(FlexAlign.Center)
          .alignItems(HorizontalAlign.Center)
          .backgroundColor('#F2F3F5')
        }
      }
      .width('100%')
      .layoutWeight(1)
    }
    .width('100%')
    .height('100%')
    .backgroundColor('#F2F3F5')
  }
}