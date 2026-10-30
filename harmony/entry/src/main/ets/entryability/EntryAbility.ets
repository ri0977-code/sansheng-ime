import { UIAbility, Want } from '@kit.AbilityKit';
import { window } from '@kit.ArkUI';

export default class EntryAbility extends UIAbility {
  /**
   * M2 真机测试开关（只影响调试启动，日常启动仍进 Index）：
   * m2_landscape=1 → 探针页 + 强制横屏；m2_probe=1 → 探针页 + 强制竖屏。
   * M3 新增 m3_probe=1 → 引擎自检页（pages/M3Probe，进页面自动跑用例）。
   */
  private m2Landscape: boolean = false;
  private m2Probe: boolean = false;
  private m3Probe: boolean = false;

  onCreate(want: Want): void {
    const params = want.parameters;
    this.m2Landscape = params?.['m2_landscape'] === '1';
    this.m2Probe = params?.['m2_probe'] === '1';
    this.m3Probe = params?.['m3_probe'] === '1';
    // M4 探针重置开关：m4_phrase_reset=1 → 清掉自造词状态文件，重新走一遍「造词→重启→还在」
    AppStorage.setOrCreate<boolean>('m4PhraseReset', params?.['m4_phrase_reset'] === '1');
  }

  onWindowStageCreate(windowStage: window.WindowStage): void {
    const useProbe: boolean = this.m2Landscape || this.m2Probe;
    let page: string = useProbe ? 'pages/LandscapeProbe' : 'pages/Index';
    if (this.m3Probe) {
      page = 'pages/M3Probe';
    }
    if (useProbe) {
      const orientation: window.Orientation =
        this.m2Landscape ? window.Orientation.LANDSCAPE : window.Orientation.PORTRAIT;
      try {
        windowStage.getMainWindowSync().setPreferredOrientation(orientation);
        console.info(`M2 probe: preferred orientation set to ${orientation}`);
      } catch (e) {
        console.error('M2 probe: setPreferredOrientation failed: ' + JSON.stringify(e));
      }
    }
    windowStage.loadContent(page, (err) => {
      if (err.code) {
        console.error('Failed to load content:', err);
        return;
      }
    });
  }
}
