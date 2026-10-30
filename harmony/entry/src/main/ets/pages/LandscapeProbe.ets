/*
 * 三生输入法 · M2 横屏真机测试页
 * 归属：Qoder（仅测试用，正常启动不会进入本页）。
 *
 * 用途：手机平放时无法物理旋转，由 EntryAbility 读启动参数 m2_landscape
 * 主动把本窗口设为横屏，从而让系统输入法面板进入横屏布局，
 * 验证 H-035（横屏每页 8–10 条候选）与横屏下 9 条候选的显示/翻页。
 *
 * 启动：aa start -b com.sansheng.ime -a EntryAbility --ps m2_landscape 1
 */

@Entry
@Component
struct LandscapeProbe {
  @State content: string = '';

  build() {
    Column({ space: 14 }) {
      Text('M2 横屏候选测试')
        .fontSize(22)
        .fontWeight(FontWeight.Bold)
      Text('点下方输入框后输入 ni / j，观察候选栏是否每页 9 条、候选下方是否显示拼音注释。')
        .fontSize(14)
        .fontColor('#666666')
        .width('92%')
      TextInput({ placeholder: '在此输入（M2 横屏验收）' })
        .id('m2_probe_input')
        .width('92%')
        .height(56)
        .fontSize(18)
        .onChange((value: string) => {
          this.content = value;
        })
      Text('已上屏：' + this.content)
        .fontSize(16)
        .fontColor('#1A7C3E')
        .width('92%')
        .maxLines(3)
    }
    .width('100%')
    .height('100%')
    .padding({ left: 24, right: 24, top: 18 })
    .alignItems(HorizontalAlign.Start)
    .justifyContent(FlexAlign.Start)
  }
}
