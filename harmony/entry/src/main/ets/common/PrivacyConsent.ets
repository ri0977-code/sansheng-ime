/*
 * 三生输入法 · 首次启动隐私政策弹窗（H-074，M6）
 * 归属：CodeArts（鸿蒙 UI）。
 * 华为应用市场审核「隐私合规 TOP7」：首次启动需以显著方式提示阅读隐私政策。
 * 自绘模态层（Stack 上层遮罩 + 白底卡片），不用 AlertDialog——按钮文案可控；
 * 「同意并继续」/「暂不同意」两个明确按钮，任一都写入 preferences 并关弹层，
 * 拒绝不退出应用、之后冷启不再弹（本应用不收集信息）。
 * 弹层内《隐私政策》《用户协议》可点跳 LegalPage（doc 参数）。
 */
import preferences from '@ohos.data.preferences';

/** H-074：弹窗按钮动作回调。 */
export enum ConsentAction {
  ACTION_AGREE = 0,
  ACTION_DECLINE = 1
}

const PREF_STORE: string = 'sansheng_prefs';
const PREF_KEY_AGREED: string = 'privacy_agreed';

@Component
export struct PrivacyConsent {
  /** 弹层是否可见（父组件持有：未同意过才显示）。 */
  @Link visible: boolean;
  /** 用户点击弹层内政策链接时由父组件跳转（父持有 router 上下文）。 */
  onOpenLegal: (doc: string) => void = (_doc: string) => {};

  private prefStore: preferences.Preferences | undefined = undefined;

  aboutToAppear(): void {
    this.initPrefs();
  }

  private async initPrefs(): Promise<void> {
    try {
      const ctx: Context = this.getUIContext().getHostContext() as Context;
      if (ctx === undefined || ctx === null) {
        return;
      }
      this.prefStore = await preferences.getPreferences(ctx, PREF_STORE);
    } catch (e) {
      // preferences 不可用：保持弹层默认可见（保守路径，宁可多提示）
    }
  }

  private async persistAgreed(): Promise<void> {
    try {
      if (this.prefStore !== undefined) {
        await this.prefStore.put(PREF_KEY_AGREED, true);
        await this.prefStore.flush();
      }
    } catch (e) {
      // 写入失败：本次会话内不再弹（visible 已关），下次冷启再提示
    }
  }

  /** 任一按钮动作：都写入同意标记并关弹层（拒绝不退出、不再弹）。 */
  private settle(action: ConsentAction): void {
    this.persistAgreed();
    this.visible = false;
    if (action === ConsentAction.ACTION_AGREE) {
      console.info('PrivacyConsent: user agreed');
    } else {
      console.info('PrivacyConsent: user declined (app continues, no more prompt)');
    }
  }

  build() {
    if (this.visible) {
      Stack() {
        // 半透明遮罩（拦截误触，点击不关闭——必须二选一）
        Column()
          .width('100%')
          .height('100%')
          .backgroundColor('rgba(0,0,0,0.45)')
          .onClick(() => {
            // 故意不处理：审核要求明确选择，点遮罩不等于同意
          })

        // 白底卡片
        Column() {
          Text('隐私政策提示')
            .fontSize(20)
            .fontWeight(FontWeight.Bold)
            .fontColor('#1A1C1E')
            .width('100%')
            .textAlign(TextAlign.Center)
            .margin({ top: 24 })

          Text('在使用三生输入法前，请阅读并了解《隐私政策》与《用户协议》。')
            .fontSize(15)
            .fontColor('#1A1C1E')
            .width('100%')
            .margin({ top: 16 })

          Text('输入内容只在本机处理，应用不联网、不上传、不收集个人信息。')
            .fontSize(15)
            .fontColor('#1A1C1E')
            .width('100%')
            .margin({ top: 8 })

          // 政策链接行
          Row({ space: 8 }) {
            Text('《隐私政策》')
              .fontSize(14)
              .fontColor('#2B5FBF')
              .onClick(() => {
                this.onOpenLegal('privacy');
              })
            Text('《用户协议》')
              .fontSize(14)
              .fontColor('#2B5FBF')
              .onClick(() => {
                this.onOpenLegal('terms');
              })
          }
          .width('100%')
          .justifyContent(FlexAlign.Center)
          .margin({ top: 12 })

          // 两个明确按钮（不默认勾选、不只给一个）
          Button('同意并继续')
            .fontSize(16)
            .fontColor('#FFFFFF')
            .backgroundColor('#2B5FBF')
            .borderRadius(8)
            .width('100%')
            .height(44)
            .margin({ top: 24 })
            .onClick(() => {
              this.settle(ConsentAction.ACTION_AGREE);
            })
          Button('暂不同意')
            .fontSize(16)
            .fontColor('#1A1C1E')
            .backgroundColor('#E4E7EC')
            .borderRadius(8)
            .width('100%')
            .height(44)
            .margin({ top: 10, bottom: 24 })
            .onClick(() => {
              this.settle(ConsentAction.ACTION_DECLINE);
            })
        }
        .width('86%')
        .borderRadius(12)
        .backgroundColor('#FFFFFF')
        .padding({ left: 20, right: 20 })
      }
      .width('100%')
      .height('100%')
      .alignContent(Alignment.Center)
    }
  }
}