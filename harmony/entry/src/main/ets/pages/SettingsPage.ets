/*
 * 三生输入法 · 设置主页（M-061）
 * 归属：CodeArts（鸿蒙 UI）。
 * 照安卓版 12 分类结构，适配鸿蒙平台。
 * 分类：全局选项 / 输入法 / 附加组件 / Android→平台 / 主题 / 虚拟键盘 /
 *       候选窗口 / 高级
 * （Fcitx 守护程序分类不适用鸿蒙，已删）
 */
import bundleManager from '@ohos.bundle.bundleManager';
import { SettingsCategory } from '../common/SettingsModels';

@Entry
@Component
struct SettingsPage {
  @State versionName: string = '1.0.0';

  // 8 分类（1.0.0 发布版：剪贴板/表情/插件因与隐私申报口径冲突已移除）
  private categories: SettingsCategory[] = [
    { id: 'global', title: '全局选项', icon: '🌐', desc: '快捷键、行为、候选词数' },
    { id: 'im', title: '输入法', icon: '⌨️', desc: '语言切换、空格长按、拼音词库' },
    { id: 'addon', title: '附加组件', icon: '🧩', desc: '附加组件启用与配置' },
    { id: 'platform', title: '平台', icon: '📱', desc: '平台特定设置' },
    { id: 'theme', title: '主题', icon: '🎨', desc: '亮色暗色、按键颜色' },
    { id: 'keyboard', title: '虚拟键盘', icon: '🎹', desc: '键盘高度、边距、振动、按键音' },
    { id: 'candidate', title: '候选窗口', icon: '📝', desc: '字体大小、边距、展开样式' },
    { id: 'advanced', title: '高级', icon: '⚙️', desc: '日志、关于' },
  ];

  aboutToAppear(): void {
    try {
      bundleManager.getBundleInfoForSelf(bundleManager.BundleFlag.GET_BUNDLE_INFO_DEFAULT)
        .then((info: bundleManager.BundleInfo) => {
          if (info.versionName !== undefined && info.versionName.length > 0) {
            this.versionName = info.versionName;
          }
        })
        .catch(() => {});
    } catch (e) {}
  }

  build() {
    Column() {
      // 顶栏
      Row() {
        Text('设置')
          .fontSize(22)
          .fontWeight(FontWeight.Bold)
          .fontColor('#1A1C1E')
        Text(`v${this.versionName}`)
          .fontSize(13)
          .fontColor('#8A8F99')
          .margin({ left: 8 })
      }
      .width('100%')
      .padding({ left: 20, right: 20, top: 16, bottom: 12 })
      .alignItems(VerticalAlign.Center)

      Divider().color('#E4E7EC')

      // 分类列表
      List({ space: 0 }) {
        ForEach(this.categories, (cat: SettingsCategory) => {
          ListItem() {
            Row() {
              Text(cat.icon)
                .fontSize(22)
                .width(40)
                .textAlign(TextAlign.Center)

              Column({ space: 2 }) {
                Text(cat.title)
                  .fontSize(16)
                  .fontWeight(FontWeight.Medium)
                  .fontColor('#1A1C1E')
                Text(cat.desc)
                  .fontSize(12)
                  .fontColor('#8A8F99')
              }
              .layoutWeight(1)
              .alignItems(HorizontalAlign.Start)

              Text('›')
                .fontSize(18)
                .fontColor('#C0C4CC')
                .width(24)
                .textAlign(TextAlign.Center)
            }
            .width('100%')
            .height(64)
            .padding({ left: 16, right: 16 })
            .alignItems(VerticalAlign.Center)
            .onClick(() => {
              this.getUIContext().getRouter().pushUrl({
                url: 'pages/SettingsCategoryPage',
                params: { categoryId: cat.id, categoryTitle: cat.title }
              });
            })
          }
        }, (cat: SettingsCategory) => `setcat_${cat.id}`)
      }
      .width('100%')
      .layoutWeight(1)
      .divider({ strokeWidth: 0.5, color: '#E4E7EC', startMargin: 56, endMargin: 16 })
    }
    .width('100%')
    .height('100%')
    .backgroundColor('#F2F3F5')
  }
}
