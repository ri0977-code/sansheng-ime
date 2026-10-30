/*
 * 三生输入法 · 设置分类页（M-061）
 * 归属：CodeArts（鸿蒙 UI）。
 * 根据路由参数 categoryId 动态渲染对应分类的设置项。
 * 支持的设置项类型：Switch / Dropdown / Slider / Input / Button / Navigation / Group
 */
import preferences from '@ohos.data.preferences';
import {
  SettingItem, SettingType, DropdownOption, getSettingsForCategory
} from '../common/SettingsModels';

const PREF_STORE: string = 'sansheng_prefs';

/** 路由参数 */
class CategoryRouteParams {
  categoryId: string = '';
  categoryTitle: string = '';
}

@Entry
@Component
struct SettingsCategoryPage {
  @State categoryId: string = '';
  @State categoryTitle: string = '';
  @State settings: SettingItem[] = [];
  @State prefStore: preferences.Preferences | undefined = undefined;
  // 所有设置项的当前值缓存（key = prefKey 或 id）
  @State valueCache: Record<string, string> = {};

  aboutToAppear(): void {
    // 从路由参数获取分类信息
    const params = this.getUIContext().getRouter().getParams() as CategoryRouteParams;
    if (params !== undefined && params !== null) {
      this.categoryId = params.categoryId ?? '';
      this.categoryTitle = params.categoryTitle ?? '';
    }
    this.settings = getSettingsForCategory(this.categoryId);
    this.initPrefs();
  }

  private async initPrefs(): Promise<void> {
    try {
      const ctx: Context = this.getUIContext().getHostContext() as Context;
      if (ctx === undefined || ctx === null) {
        this.loadDefaults();
        return;
      }
      this.prefStore = await preferences.getPreferences(ctx, PREF_STORE);
      this.loadValues();
    } catch (e) {
      this.loadDefaults();
    }
  }

  /** 从 preferences 加载所有设置项的值 */
  private loadValues(): void {
    const cache: Record<string, string> = {};
    for (const item of this.settings) {
      const key = item.prefKey || item.id;
      if (key.length > 0 && item.type !== SettingType.GROUP &&
          item.type !== SettingType.NAVIGATION && item.type !== SettingType.BUTTON) {
        try {
          const val: preferences.ValueType = this.prefStore?.getSync(key, item.defaultValue) ?? item.defaultValue;
          cache[key] = String(val);
        } catch (e) {
          cache[key] = item.defaultValue;
        }
      }
    }
    this.valueCache = cache;
  }

  /** 无 preferences 时用默认值填充 */
  private loadDefaults(): void {
    const cache: Record<string, string> = {};
    for (const item of this.settings) {
      const key = item.prefKey || item.id;
      if (key.length > 0 && item.type !== SettingType.GROUP &&
          item.type !== SettingType.NAVIGATION && item.type !== SettingType.BUTTON) {
        cache[key] = item.defaultValue;
      }
    }
    this.valueCache = cache;
  }

  /** 保存某个设置项的值到 preferences */
  private async saveValue(key: string, value: string): Promise<void> {
    try {
      if (this.prefStore !== undefined && key.length > 0) {
        await this.prefStore.put(key, value);
        await this.prefStore.flush();
      }
    } catch (e) {
      // 静默失败
    }
    // 更新缓存
    const newCache: Record<string, string> = {};
    const keys: string[] = Object.keys(this.valueCache);
    for (let i: number = 0; i < keys.length; i++) {
      newCache[keys[i]] = this.valueCache[keys[i]];
    }
    newCache[key] = value;
    this.valueCache = newCache;
  }

  /** 获取某个设置项的当前值 */
  private getValue(item: SettingItem): string {
    const key = item.prefKey || item.id;
    return this.valueCache[key] ?? item.defaultValue;
  }

  build() {
    Column() {
      // 顶栏
      Row() {
        Text('‹')
          .fontSize(22)
          .fontColor('#2B5FBF')
          .width(40)
          .textAlign(TextAlign.Center)
          .onClick(() => {
            this.getUIContext().getRouter().back();
          })

        Text(this.categoryTitle)
          .fontSize(20)
          .fontWeight(FontWeight.Bold)
          .fontColor('#1A1C1E')
          .layoutWeight(1)
      }
      .width('100%')
      .height(56)
      .padding({ left: 4, right: 20 })
      .alignItems(VerticalAlign.Center)
      .backgroundColor('#FFFFFF')

      Divider().color('#E4E7EC')

      // 设置项列表
      Scroll() {
        Column({ space: 0 }) {
          ForEach(this.settings, (item: SettingItem) => {
            this.SettingItemBuilder(item)
          }, (item: SettingItem) => `setitem_${item.id}`)
        }
        .width('100%')
      }
      .width('100%')
      .layoutWeight(1)
      .scrollBar(BarState.Auto)
    }
    .width('100%')
    .height('100%')
    .backgroundColor('#F2F3F5')
  }

  // ========== 设置项渲染 ==========

  @Builder
  SettingItemBuilder(item: SettingItem) {
    if (item.type === SettingType.GROUP) {
      // 分组标题
      Row() {
        Text(item.title)
          .fontSize(14)
          .fontWeight(FontWeight.Bold)
          .fontColor('#8A8F99')
      }
      .width('100%')
      .padding({ left: 20, right: 20, top: 16, bottom: 8 })
      .backgroundColor('#F2F3F5')
    } else {
      // 可交互的设置项
      Column() {
        if (item.type === SettingType.SWITCH) {
          this.SwitchItem(item)
        } else if (item.type === SettingType.DROPDOWN) {
          this.DropdownItem(item)
        } else if (item.type === SettingType.SLIDER) {
          this.SliderItem(item)
        } else if (item.type === SettingType.INPUT) {
          this.InputItem(item)
        } else if (item.type === SettingType.BUTTON) {
          this.ButtonItem(item)
        } else if (item.type === SettingType.NAVIGATION) {
          this.NavigationItem(item)
        }
      }
      .width('100%')
    }
  }

  @Builder
  SwitchItem(item: SettingItem) {
    Row() {
      Text(item.title)
        .fontSize(16)
        .fontColor('#1A1C1E')
        .layoutWeight(1)

      Toggle({ type: ToggleType.Switch, isOn: this.getValue(item) === 'true' })
        .onChange((isOn: boolean) => {
          this.saveValue(item.prefKey || item.id, isOn ? 'true' : 'false');
        })
        .selectedColor('#2B5FBF')
        .width(48)
        .height(28)
    }
    .width('100%')
    .height(56)
    .padding({ left: 20, right: 20 })
    .alignItems(VerticalAlign.Center)
    .backgroundColor('#FFFFFF')
  }

  @Builder
  DropdownItem(item: SettingItem) {
    Row() {
      Text(item.title)
        .fontSize(16)
        .fontColor('#1A1C1E')
        .layoutWeight(1)

      // 当前值显示
      Text(this.getDropdownLabel(item))
        .fontSize(14)
        .fontColor('#8A8F99')
        .margin({ right: 8 })

      Text('›')
        .fontSize(16)
        .fontColor('#C0C4CC')
    }
    .width('100%')
    .height(56)
    .padding({ left: 20, right: 20 })
    .alignItems(VerticalAlign.Center)
    .backgroundColor('#FFFFFF')
    .onClick(() => {
      // 弹出选择对话框
      this.showDropdownDialog(item);
    })
  }

  @Builder
  SliderItem(item: SettingItem) {
    Column({ space: 4 }) {
      Row() {
        Text(item.title)
          .fontSize(16)
          .fontColor('#1A1C1E')
          .layoutWeight(1)

        Text(`${this.getValue(item)}${item.unit}`)
          .fontSize(14)
          .fontColor('#2B5FBF')
      }
      .width('100%')

      Slider({
        value: parseFloat(this.getValue(item)),
        min: item.min,
        max: item.max,
        step: item.step,
        style: SliderStyle.OutSet
      })
        .width('100%')
        .height(36)
        .selectedColor('#2B5FBF')
        .trackThickness(4)
        .onChange((value: number, mode: SliderChangeMode) => {
          if (mode === SliderChangeMode.End) {
            const intVal: number = item.step >= 1 ? Math.round(value) : Math.round(value * 10) / 10;
            this.saveValue(item.prefKey || item.id, String(intVal));
          }
        })
    }
    .width('100%')
    .padding({ left: 20, right: 20, top: 12, bottom: 12 })
    .backgroundColor('#FFFFFF')
  }

  @Builder
  InputItem(item: SettingItem) {
    Row() {
      Text(item.title)
        .fontSize(16)
        .fontColor('#1A1C1E')
        .layoutWeight(1)

      TextInput({ text: this.getValue(item) })
        .fontSize(14)
        .fontColor('#2B5FBF')
        .width(80)
        .height(36)
        .backgroundColor('#F2F3F5')
        .borderRadius(6)
        .type(InputType.Number)
        .onChange((text: string) => {
          this.saveValue(item.prefKey || item.id, text);
        })
    }
    .width('100%')
    .height(56)
    .padding({ left: 20, right: 20 })
    .alignItems(VerticalAlign.Center)
    .backgroundColor('#FFFFFF')
  }

  @Builder
  ButtonItem(item: SettingItem) {
    Row() {
      Text(item.title)
        .fontSize(16)
        .fontColor(item.danger ? '#E53935' : '#1A1C1E')
        .layoutWeight(1)

      if (item.desc.length > 0) {
        Text(item.desc)
          .fontSize(12)
          .fontColor('#8A8F99')
          .margin({ right: 8 })
      }
    }
    .width('100%')
    .height(56)
    .padding({ left: 20, right: 20 })
    .alignItems(VerticalAlign.Center)
    .backgroundColor('#FFFFFF')
    .onClick(() => {
      if (item.danger) {
        this.showConfirmDialog(item);
      } else {
        this.executeButtonAction(item);
      }
    })
  }

  @Builder
  NavigationItem(item: SettingItem) {
    Row() {
      Text(item.title)
        .fontSize(16)
        .fontColor('#1A1C1E')
        .layoutWeight(1)

      if (item.desc.length > 0) {
        Text(item.desc)
          .fontSize(12)
          .fontColor('#8A8F99')
          .margin({ right: 8 })
      }

      Text('›')
        .fontSize(16)
        .fontColor('#C0C4CC')
    }
    .width('100%')
    .height(56)
    .padding({ left: 20, right: 20 })
    .alignItems(VerticalAlign.Center)
    .backgroundColor('#FFFFFF')
    .onClick(() => {
      this.navigateFromItem(item);
    })
  }

  // ========== 辅助方法 ==========

  /** 获取下拉选项的显示标签 */
  private getDropdownLabel(item: SettingItem): string {
    const currentValue: string = this.getValue(item);
    for (const opt of item.options) {
      if (opt.value === currentValue) {
        return opt.label;
      }
    }
    return currentValue;
  }

  /** 弹出下拉选择对话框 */
  private showDropdownDialog(item: SettingItem): void {
    // 使用 AlertDialog 弹出选项列表
    const currentValue: string = this.getValue(item);
    const labels: string[] = item.options.map((opt: DropdownOption) => opt.label);

    // ArkTS 严格模式：用 SelectDialog 或自定义弹层
    // 这里用简单的 AlertDialog 实现
    AlertDialog.show({
      title: item.title,
      message: '',
      primaryButton: {
        value: '取消',
        action: () => {}
      },
      secondaryButton: {
        value: '确定',
        action: () => {}
      }
    });
    // TODO: 改用自定义弹层实现选项列表（AlertDialog 不支持列表选择）
    // 暂时用 promptAction.showActionMenu 替代
  }

  /** 弹出确认对话框（危险操作） */
  private showConfirmDialog(item: SettingItem): void {
    AlertDialog.show({
      title: item.title,
      message: item.desc || '确认执行此操作？',
      primaryButton: {
        value: '取消',
        action: () => {}
      },
      secondaryButton: {
        value: '确定',
        action: () => {
          this.executeButtonAction(item);
        }
      }
    });
  }

  /** 执行按钮操作 */
  private executeButtonAction(item: SettingItem): void {
    // 根据按钮 id 执行对应操作
    switch (item.id) {

      case 'a_reload_config':
        console.info('SettingsPage: reload rime config');
        break;
      default:
        break;
    }
  }

  /** 导航到子页面 */
  private navigateFromItem(item: SettingItem): void {
    switch (item.id) {
      case 'a_about':
        this.getUIContext().getRouter().pushUrl({ url: 'pages/AboutPage' });
        break;
      default:
        // 其他导航项暂未实现子页面
        break;
    }
  }
}