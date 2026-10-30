/*
 * 三生输入法 · 关于 / 第三方声明页（H-052）
 * 归属：CodeArts（鸿蒙 UI）。
 * 内容以根 NOTICE 文件为准（Apache-2.0 §4(d) 要求）。
 * H-069（M6）：版本号改读 bundleInfo.versionName（失败回退 1.0.0）。
 * H-070（M6）：新增「隐私政策 / 用户协议」入口（router 到 LegalPage）。
 */
import bundleManager from '@ohos.bundle.bundleManager';

/** H-070：LegalPage 路由参数（ArkTS 严格模式要求显式类型）。 */
class LegalRouteParams {
  doc: string = 'privacy';

  constructor(doc: string) {
    this.doc = doc;
  }
}


@Entry
@Component
struct AboutPage {
  @State versionName: string = '1.0.0';

  aboutToAppear(): void {
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

  private openLegal(doc: string): void {
    this.getUIContext().getRouter().pushUrl({
      url: 'pages/LegalPage',
      params: new LegalRouteParams(doc)
    });
  }

  build() {
    Scroll() {
      Column({ space: 16 }) {
        // 标题
        Text('三生输入法')
          .fontSize(28)
          .fontWeight(FontWeight.Bold)
          .fontColor('#1A1C1E')
          .textAlign(TextAlign.Center)
          .width('100%')

        Text('HarmonyOS 版 · 五笔 · 拼音 · 英文三向混输')
          .fontSize(14)
          .fontColor('#8A8F99')
          .textAlign(TextAlign.Center)
          .width('100%')

        // 版本号
        Row() {
          Text('版本：')
            .fontSize(14)
            .fontColor('#8A8F99')
          Text(this.versionName)
            .fontSize(14)
            .fontColor('#1A1C1E')
        }
        .width('100%')
        .justifyContent(FlexAlign.Center)

        Divider().color('#E4E7EC')

        // H-070（M6）：法律文本入口
        Column({ space: 10 }) {
          Text('法律文本')
            .fontSize(18)
            .fontWeight(FontWeight.Bold)
            .fontColor('#1A1C1E')
            .width('100%')
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
        }
        .width('100%')
        .padding({ left: 16, right: 16 })

        Divider().color('#E4E7EC')

        // 许可声明
        Column({ space: 8 }) {
          Text('开源许可')
            .fontSize(18)
            .fontWeight(FontWeight.Bold)
            .fontColor('#1A1C1E')
            .width('100%')

          Text('本软件基于 Apache License 2.0 开源。')
            .fontSize(14)
            .fontColor('#1A1C1E')
            .width('100%')

          Text('Copyright 2026 Lucas Y.C. Wang')
            .fontSize(13)
            .fontColor('#8A8F99')
            .width('100%')
        }
        .width('100%')
        .padding({ left: 16, right: 16 })

        Divider().color('#E4E7EC')

        // 词库来源
        Column({ space: 8 }) {
          Text('词库来源')
            .fontSize(18)
            .fontWeight(FontWeight.Bold)
            .fontColor('#1A1C1E')
            .width('100%')

          // CC-CEDICT
          Row({ space: 8 }) {
            Text('CC-CEDICT')
              .fontSize(14)
              .fontWeight(FontWeight.Bold)
              .fontColor('#1A1C1E')
              .layoutWeight(1)
            Text('CC BY-SA 4.0')
              .fontSize(12)
              .fontColor('#2B5FBF')
          }
          .width('100%')
          Text('中英互译词库（zh2en 系列）')
            .fontSize(12)
            .fontColor('#8A8F99')
            .width('100%')

          // cn_pinyin_wp
          Row({ space: 8 }) {
            Text('cn_pinyin_wp')
              .fontSize(14)
              .fontWeight(FontWeight.Bold)
              .fontColor('#1A1C1E')
              .layoutWeight(1)
            Text('Apache-2.0')
              .fontSize(12)
              .fontColor('#2B5FBF')
          }
          .width('100%')
          Text('拼音词库（由 pinyin_simp 重新整理生成）')
            .fontSize(12)
            .fontColor('#8A8F99')
            .width('100%')

          // ECDICT
          Row({ space: 8 }) {
            Text('ECDICT')
              .fontSize(14)
              .fontWeight(FontWeight.Bold)
              .fontColor('#1A1C1E')
              .layoutWeight(1)
            Text('MIT')
              .fontSize(12)
              .fontColor('#2B5FBF')
          }
          .width('100%')
          Text('英中翻译词库（en2zh_v2 系列）')
            .fontSize(12)
            .fontColor('#8A8F99')
            .width('100%')

          // 86五笔极点码表
          Row({ space: 8 }) {
            Text('rime-wubi86-jidian')
              .fontSize(14)
              .fontWeight(FontWeight.Bold)
              .fontColor('#1A1C1E')
              .layoutWeight(1)
            Text('Apache-2.0')
              .fontSize(12)
              .fontColor('#2B5FBF')
          }
          .width('100%')
          Text('86 五笔极点码表（KyleBing/rime-wubi86-jidian）')
            .fontSize(12)
            .fontColor('#8A8F99')
            .width('100%')

          // 86 五笔主码表（LGPL-3.0）——与上面的极点权重层分开列
          Row({ space: 8 }) {
            Text('rime-wubi（86 五笔主码表）')
              .fontSize(14)
              .fontWeight(FontWeight.Bold)
              .fontColor('#1A1C1E')
              .layoutWeight(1)
            Text('LGPL-3.0')
              .fontSize(12)
              .fontColor('#2B5FBF')
          }
          .width('100%')
          Text('五笔主码表本体；极点权重与补充词条见上一项（Apache-2.0）')
            .fontSize(12)
            .fontColor('#8A8F99')
            .width('100%')

          // pinyin_simp
          Row({ space: 8 }) {
            Text('rime-pinyin-simp')
              .fontSize(14)
              .fontWeight(FontWeight.Bold)
              .fontColor('#1A1C1E')
              .layoutWeight(1)
            Text('Apache-2.0')
              .fontSize(12)
              .fontColor('#2B5FBF')
          }
          .width('100%')
          Text('简拼方案（rime/rime-pinyin-simp）')
            .fontSize(12)
            .fontColor('#8A8F99')
            .width('100%')

          // OpenCC
          Row({ space: 8 }) {
            Text('OpenCC')
              .fontSize(14)
              .fontWeight(FontWeight.Bold)
              .fontColor('#1A1C1E')
              .layoutWeight(1)
            Text('Apache-2.0')
              .fontSize(12)
              .fontColor('#2B5FBF')
          }
          .width('100%')
          Text('简繁转换数据（BYVoid/OpenCC）')
            .fontSize(12)
            .fontColor('#8A8F99')
            .width('100%')
        }
        .width('100%')
        .padding({ left: 16, right: 16 })

        Divider().color('#E4E7EC')

        // 第三方软件
        Column({ space: 8 }) {
          Text('第三方软件')
            .fontSize(18)
            .fontWeight(FontWeight.Bold)
            .fontColor('#1A1C1E')
            .width('100%')

          Row({ space: 8 }) {
            Text('librime')
              .fontSize(14)
              .fontWeight(FontWeight.Bold)
              .fontColor('#1A1C1E')
              .layoutWeight(1)
            Text('BSD-3-Clause')
              .fontSize(12)
              .fontColor('#2B5FBF')
          }
          .width('100%')
          Text('Rime 输入法引擎核心')
            .fontSize(12)
            .fontColor('#8A8F99')
            .width('100%')

          Row({ space: 8 }) {
            Text('harmonyos-next-rime-har')
              .fontSize(14)
              .fontWeight(FontWeight.Bold)
              .fontColor('#1A1C1E')
              .layoutWeight(1)
            Text('MIT')
              .fontSize(12)
              .fontColor('#2B5FBF')
          }
          .width('100%')
          Text('鸿蒙版 Rime 引擎工程（chuanis）')
            .fontSize(12)
            .fontColor('#8A8F99')
            .width('100%')

          Row({ space: 8 }) {
            Text('hMixedKeyboard')
              .fontSize(14)
              .fontWeight(FontWeight.Bold)
              .fontColor('#1A1C1E')
              .layoutWeight(1)
            Text('Apache-2.0')
              .fontSize(12)
              .fontColor('#2B5FBF')
          }
          .width('100%')
          Text('鸿蒙输入法面板参考实现（nanaseyuu）')
            .fontSize(12)
            .fontColor('#8A8F99')
            .width('100%')

          Row({ space: 8 }) {
            Text('kanonIME')
              .fontSize(14)
              .fontWeight(FontWeight.Bold)
              .fontColor('#1A1C1E')
              .layoutWeight(1)
            Text('MIT')
              .fontSize(12)
              .fontColor('#2B5FBF')
          }
          .width('100%')
          Text('候选栏 UI 布局参考（ysk0518）')
            .fontSize(12)
            .fontColor('#8A8F99')
            .width('100%')
        }
        .width('100%')
        .padding({ left: 16, right: 16 })

        Divider().color('#E4E7EC')

        // 隐私声明
        Column({ space: 8 }) {
          Text('隐私声明')
            .fontSize(18)
            .fontWeight(FontWeight.Bold)
            .fontColor('#1A1C1E')
            .width('100%')

          Text('本应用所有数据处理均在本地完成，不联网、不上传任何用户数据。')
            .fontSize(14)
            .fontColor('#1A1C1E')
            .width('100%')
        }
        .width('100%')
        .padding({ left: 16, right: 16 })

        Divider().color('#E4E7EC')

        // 完整声明指引
        Column({ space: 8 }) {
          Text('完整许可声明')
            .fontSize(18)
            .fontWeight(FontWeight.Bold)
            .fontColor('#1A1C1E')
            .width('100%')

          Text('本页下面是摘要；完整正文（NOTICE 与全部第三方许可全文）可在应用内直接阅读。')
            .fontSize(14)
            .fontColor('#1A1C1E')
            .width('100%')

          Button('查看完整许可声明')
            .fontSize(15)
            .fontColor('#2B5FBF')
            .backgroundColor('#FFFFFF')
            .borderRadius(8)
            .width('100%')
            .height(42)
            .onClick(() => {
              this.openLegal('notice');
            })
        }
        .width('100%')
        .padding({ left: 16, right: 16 })

        // 返回按钮
        Button('返回')
          .fontSize(16)
          .fontColor('#FFFFFF')
          .backgroundColor('#2B5FBF')
          .borderRadius(8)
          .width(120)
          .height(44)
          .margin({ top: 16, bottom: 32 })
          .onClick(() => {
            this.getUIContext().getRouter().back();
          })
      }
      .width('100%')
      .padding({ top: 32 })
    }
    .width('100%')
    .height('100%')
    .backgroundColor('#F2F3F5')
    .scrollBar(BarState.Auto)
  }
}