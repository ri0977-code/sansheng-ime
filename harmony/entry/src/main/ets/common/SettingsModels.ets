/*
 * 三生输入法 · 设置数据模型（M-061）
 * 归属：CodeArts（鸿蒙 UI）。
 * 定义设置分类、设置项的数据结构。
 *
 * H-240(CodeArts): 按 SETTINGS-CONTRACT.md §3 对齐 12 项契约条目
 * （prefKey/文案/范围/默认值），表外项标 enabledInPanel=false（不删，H-129 口径）。
 */

/** 设置分类 */
export class SettingsCategory {
  id: string = '';
  title: string = '';
  icon: string = '';
  desc: string = '';
}

/** 设置项类型 */
export enum SettingType {
  SWITCH = 'switch',       // 开关
  DROPDOWN = 'dropdown',   // 下拉选择
  SLIDER = 'slider',       // 滑块
  INPUT = 'input',         // 文本输入
  BUTTON = 'button',       // 按钮（操作类）
  NAVIGATION = 'navigation', // 导航到子页面
  GROUP = 'group',         // 分组标题（不可点击）
}

/** 下拉选项 */
export class DropdownOption {
  value: string = '';
  label: string = '';

  constructor(value: string, label: string) {
    this.value = value;
    this.label = label;
  }
}

/** 设置项定义 */
export class SettingItem {
  id: string = '';
  title: string = '';
  type: SettingType = SettingType.SWITCH;
  group: string = '';           // 所属分组（空=不属于任何分组）
  desc: string = '';            // 描述文字
  defaultValue: string = '';    // 默认值（switch: 'true'/'false', dropdown: value, slider: number string）
  options: DropdownOption[] = []; // dropdown 选项
  min: number = 0;              // slider 最小值
  max: number = 100;            // slider 最大值
  step: number = 1;             // slider 步长
  unit: string = '';            // slider 单位（如 'vp', 'ms'）
  danger: boolean = false;      // 是否危险操作（红色按钮）
  prefKey: string = '';         // preferences 存储键名（空=不持久化）
  engineOption: string = '';    // 对应的 Rime 引擎选项名（空=不关联引擎）
  /** H-240(CodeArts): 是否在设置面板上显示——契约 §3 的 12 项=true，表外项=false（H-129 不删） */
  enabledInPanel: boolean = true;
}

// ========== 工厂函数（ArkTS 严格模式：对象字面量必须包含所有属性，用工厂函数填充默认值） ==========

function mkGroup(id: string, title: string): SettingItem {
  const item: SettingItem = new SettingItem();
  item.id = id;
  item.title = title;
  item.type = SettingType.GROUP;
  return item;
}

function mkSwitch(id: string, title: string, defaultValue: string, prefKey: string,
                  group: string = '', desc: string = ''): SettingItem {
  const item: SettingItem = new SettingItem();
  item.id = id;
  item.title = title;
  item.type = SettingType.SWITCH;
  item.group = group;
  item.desc = desc;
  item.defaultValue = defaultValue;
  item.prefKey = prefKey;
  return item;
}

function mkDropdown(id: string, title: string, defaultValue: string,
                    options: DropdownOption[], prefKey: string,
                    group: string = '', desc: string = ''): SettingItem {
  const item: SettingItem = new SettingItem();
  item.id = id;
  item.title = title;
  item.type = SettingType.DROPDOWN;
  item.group = group;
  item.desc = desc;
  item.defaultValue = defaultValue;
  item.options = options;
  item.prefKey = prefKey;
  return item;
}

function mkSlider(id: string, title: string, defaultValue: string,
                  min: number, max: number, step: number, unit: string,
                  prefKey: string, group: string = '', desc: string = ''): SettingItem {
  const item: SettingItem = new SettingItem();
  item.id = id;
  item.title = title;
  item.type = SettingType.SLIDER;
  item.group = group;
  item.desc = desc;
  item.defaultValue = defaultValue;
  item.min = min;
  item.max = max;
  item.step = step;
  item.unit = unit;
  item.prefKey = prefKey;
  return item;
}

function mkInput(id: string, title: string, defaultValue: string, prefKey: string,
                 group: string = '', desc: string = ''): SettingItem {
  const item: SettingItem = new SettingItem();
  item.id = id;
  item.title = title;
  item.type = SettingType.INPUT;
  item.group = group;
  item.desc = desc;
  item.defaultValue = defaultValue;
  item.prefKey = prefKey;
  return item;
}

function mkButton(id: string, title: string, desc: string = '',
                  danger: boolean = false, group: string = ''): SettingItem {
  const item: SettingItem = new SettingItem();
  item.id = id;
  item.title = title;
  item.type = SettingType.BUTTON;
  item.group = group;
  item.desc = desc;
  item.danger = danger;
  return item;
}

function mkNavigation(id: string, title: string, desc: string = '',
                      group: string = ''): SettingItem {
  const item: SettingItem = new SettingItem();
  item.id = id;
  item.title = title;
  item.type = SettingType.NAVIGATION;
  item.group = group;
  item.desc = desc;
  return item;
}

/** H-240(CodeArts): 标记表外项 enabledInPanel=false（不删，H-129 口径） */
function disabled(item: SettingItem): SettingItem {
  item.enabledInPanel = false;
  return item;
}

/** 所有分类的设置项定义 */
export function getSettingsForCategory(categoryId: string): SettingItem[] {
  switch (categoryId) {
    case 'global':
      return getGlobalSettings();
    case 'im':
      return getImSettings();
    case 'addon':
      return getAddonSettings();
    case 'platform':
      return getPlatformSettings();
    case 'theme':
      return getThemeSettings();
    case 'keyboard':
      return getKeyboardSettings();
    case 'candidate':
      return getCandidateSettings();

    case 'advanced':
      return getAdvancedSettings();
    default:
      return [];
  }
}

// ========== 全局选项 ==========
// H-240(CodeArts): 全部表外项，enabledInPanel=false
function getGlobalSettings(): SettingItem[] {
  return [
    mkGroup('g_hotkey', '快捷键'),
    disabled(mkSwitch('g_switch_key_rotation', '按住切换键的修饰键时进行轮换切换', 'true',
             'global_switch_key_rotation', 'hotkey')),
    disabled(mkSwitch('g_skip_first_im', '轮换输入法时跳过第一个输入法', 'false',
             'global_skip_first_im', 'hotkey')),
    disabled(mkSlider('g_hotkey_timeout', '触发修饰键快捷键的时限', '250',
             100, 1000, 50, 'ms', 'global_hotkey_timeout', 'hotkey')),
    mkGroup('g_behavior', '行为'),
    disabled(mkSwitch('g_default_active_im', '默认激活输入法', 'false',
             'global_default_active_im', 'behavior')),
    disabled(mkDropdown('g_reset_on_refocus', '重新聚焦时重置状态', 'no',
             [new DropdownOption('no', '否'), new DropdownOption('yes', '是')],
             'global_reset_on_refocus', 'behavior')),
    disabled(mkDropdown('g_share_state', '共享输入状态', 'all',
             [new DropdownOption('all', '所有'), new DropdownOption('program', '程序'),
              new DropdownOption('no', '否')],
             'global_share_state', 'behavior')),
    // H-240(CodeArts): g_show_preedit 是旧键名，契约 §3-12 用 show_preedit（在虚拟键盘节）
    disabled(mkSwitch('g_show_preedit', '在程序中显示预编辑文本', 'true',
             'global_show_preedit', 'behavior')),
    disabled(mkSwitch('g_show_im_info', '切换输入法时显示输入法信息', 'true',
             'global_show_im_info', 'behavior')),
    disabled(mkSwitch('g_show_im_info_focus', '在焦点更改时显示输入法信息', 'false',
             'global_show_im_info_focus', 'behavior')),
    disabled(mkSwitch('g_compact_im_info', '显示紧凑的输入法信息', 'true',
             'global_compact_im_info', 'behavior')),
    disabled(mkSwitch('g_show_first_im_info', '显示第一个输入法的信息', 'true',
             'global_show_first_im_info', 'behavior')),
    // H-240(CodeArts): g_default_page_size 是旧键名，契约 §3-4 用 page_size（在候选窗口节）
    disabled(mkInput('g_default_page_size', '缺省每页候选词', '5',
            'global_default_page_size', 'behavior')),
    disabled(mkSwitch('g_allow_in_password', '允许在密码框中使用输入法', 'false',
             'global_allow_in_password', 'behavior')),
    disabled(mkSwitch('g_show_preedit_password', '输入密码时显示预编辑文本', 'false',
             'global_show_preedit_password', 'behavior')),
    disabled(mkSlider('g_save_data_interval', '保存用户数据的时间间隔', '30',
             5, 120, 5, '分钟', 'global_save_data_interval', 'behavior')),
  ];
}

// ========== 输入法 ==========
// H-240(CodeArts): 全部表外项，enabledInPanel=false
function getImSettings(): SettingItem[] {
  return [
    mkGroup('im_group', '输入法设置'),
    disabled(mkDropdown('im_lang_switch_behavior', '语言切换键行为', 'next',
             [new DropdownOption('next', '切换至下一个输入法'),
              new DropdownOption('prev', '切换至上一个输入法'),
              new DropdownOption('dialog', '显示输入法选择对话框')],
             'im_lang_switch_behavior')),
    disabled(mkDropdown('im_space_long_press', '空格键长按行为', 'none',
             [new DropdownOption('none', '无'),
              new DropdownOption('rotate', '轮换输入法'),
              new DropdownOption('toggle', '在当前和第一个输入法之间切换'),
              new DropdownOption('dialog', '显示输入法选择对话框')],
             'im_space_long_press')),
    disabled(mkSwitch('im_space_swipe_cursor', '划动空格键以移动光标', 'true',
             'im_space_swipe_cursor')),
    disabled(mkNavigation('im_manage_table', '管理码表输入法', '查看和管理已安装的码表输入法')),
    disabled(mkNavigation('im_pinyin_dict', '拼音词库', '管理拼音词库')),
    disabled(mkNavigation('im_quickphrase', '快速输入编辑器', '编辑快速输入短语')),
  ];
}

// ========== 附加组件 ==========
// H-240(CodeArts): 全部表外项，enabledInPanel=false
function getAddonSettings(): SettingItem[] {
  return [
    mkGroup('addon_group', '附加组件'),
    disabled(mkNavigation('addon_list', '附加组件列表', '启用或禁用附加组件')),
    disabled(mkNavigation('addon_configure', '配置附加组件', '进入附加组件配置页面')),
  ];
}

// ========== 平台（原 Android 分类） ==========
// H-240(CodeArts): 全部表外项，enabledInPanel=false
function getPlatformSettings(): SettingItem[] {
  return [
    mkGroup('p_group', '平台设置'),
    disabled(mkSwitch('p_show_lang_switch', '显示语言切换键', 'true',
             'platform_show_lang_switch')),
    disabled(mkSwitch('p_swipe_symbol', '划动输入标点符号及数字', 'false',
             'platform_swipe_symbol')),
    disabled(mkDropdown('p_space_long_press', '空格键长按行为', 'none',
             [new DropdownOption('none', '无'),
              new DropdownOption('rotate', '轮换输入法'),
              new DropdownOption('toggle', '切换'),
              new DropdownOption('dialog', '选择对话框')],
             'platform_space_long_press')),
    disabled(mkSwitch('p_space_swipe_cursor', '划动空格键以移动光标', 'true',
             'platform_space_swipe_cursor')),
    disabled(mkDropdown('p_punct_position', '标点位置', 'none',
             [new DropdownOption('none', '无'),
              new DropdownOption('top_right', '右上'),
              new DropdownOption('bottom', '底部（仅限竖屏）')],
             'platform_punct_position')),
    disabled(mkSwitch('p_reset_keyboard', '焦点改变时切换回键盘', 'false',
             'platform_reset_keyboard')),
    disabled(mkSwitch('p_num_row_password', '输入密码时在工具栏上显示数字行', 'false',
             'platform_num_row_password')),
    disabled(mkSwitch('p_inline_suggestions', '显示内嵌自动填充建议', 'false',
             'platform_inline_suggestions')),
  ];
}

// ========== 主题 ==========
// H-240(CodeArts): 全部表外项，enabledInPanel=false
function getThemeSettings(): SettingItem[] {
  return [
    mkGroup('t_group', '主题'),
    disabled(mkSwitch('t_follow_system', '跟随系统夜间模式', 'true',
             'theme_follow_system')),
    disabled(mkDropdown('t_light_theme', '亮色模式主题', 'default',
             [new DropdownOption('default', '默认')],
             'theme_light')),
    disabled(mkDropdown('t_dark_theme', '暗色模式主题', 'default_dark',
             [new DropdownOption('default_dark', '默认暗色')],
             'theme_dark')),
    disabled(mkSwitch('t_dark_keys', '暗色按键', 'false',
             'theme_dark_keys')),
    disabled(mkDropdown('t_navbar_bg', '导航栏背景', 'none',
             [new DropdownOption('none', '无背景'),
              new DropdownOption('keyboard_color', '跟随键盘背景色'),
              new DropdownOption('keyboard_image', '键盘背景图片')],
             'theme_navbar_bg')),
  ];
}

// ========== 虚拟键盘 ==========
// H-240(CodeArts): 契约 §3 的 8 项（KBD_KEYS）enabledInPanel=true，其余 false
function getKeyboardSettings(): SettingItem[] {
  return [
    mkGroup('k_layout', '布局'),
    // §3-1: kbd_height_pct — 键盘高度百分比，滑条 80–120(%), 默认 100
    mkSlider('k_height_pct', '键盘高度百分比', '100',
             80, 120, 5, '%', 'kbd_height_pct', 'layout'),
    disabled(mkSlider('k_bottom_padding', '键盘底部边距', '0',
             0, 30, 1, 'vp', 'kbd_bottom_padding', 'layout')),
    disabled(mkSlider('k_side_padding', '键盘两侧边距', '0',
             0, 30, 1, 'vp', 'kbd_side_padding', 'layout')),
    mkGroup('k_keys', '按键'),
    // §3-3: key_font_size — 键面字母字号，滑条 16–26(vp), 默认 20
    mkSlider('k_font_size', '键面字母字号', '20',
             16, 26, 1, 'vp', 'key_font_size', 'keys'),
    // §3-6: key_long_press_delay — 长按触发时长，滑条 300–700(ms), 默认 450
    mkSlider('k_long_press_delay', '长按触发时长', '450',
             300, 700, 25, 'ms', 'key_long_press_delay', 'keys'),
    disabled(mkSlider('k_radius', '按键圆角半径', '8',
             0, 20, 1, 'vp', 'kbd_radius', 'keys')),
    disabled(mkSlider('k_h_margin', '按键横向边距', '3',
             0, 10, 0.5, 'vp', 'kbd_h_margin', 'keys')),
    disabled(mkSlider('k_v_margin', '按键纵向边距', '3',
             0, 10, 0.5, 'vp', 'kbd_v_margin', 'keys')),
    disabled(mkSwitch('k_border', '启用按键边框', 'false',
             'kbd_border', 'keys')),
    // §3-7: popup_on_key_press — 按键时弹出字符，开关, 默认 开
    mkSwitch('k_popup', '按键时弹出字符', 'true',
             'popup_on_key_press', 'keys'),
    disabled(mkSwitch('k_expand_area', '将按键范围扩展至边缘', 'false',
             'kbd_expand_area', 'keys')),
    disabled(mkSwitch('k_uppercase', '键盘字母保持大写', 'false',
             'kbd_uppercase', 'keys')),
    disabled(mkSwitch('k_disable_anim', '禁用动画', 'false',
             'kbd_disable_anim', 'keys')),
    mkGroup('k_feedback', '反馈'),
    // §3-5: kbd_haptic — 按键时振动，开关, 默认 开
    mkSwitch('k_haptic', '按键时振动', 'true',
             'kbd_haptic', 'feedback'),
    disabled(mkSwitch('k_haptic_up', '按键松开时振动', 'false',
             'kbd_haptic_up', 'feedback')),
    disabled(mkSwitch('k_haptic_repeat', '重复按键时的振动反馈', 'true',
             'kbd_haptic_repeat', 'feedback')),
    disabled(mkSlider('k_haptic_amplitude', '按键振动幅度', '50',
             1, 255, 1, '', 'kbd_haptic_amplitude', 'feedback')),
    disabled(mkSlider('k_haptic_duration', '按键振动时长', '20',
             5, 100, 5, 'ms', 'kbd_haptic_duration', 'feedback')),
    disabled(mkSwitch('k_sound', '按键音', 'false',
             'kbd_sound', 'feedback')),
    disabled(mkSlider('k_sound_volume', '按键音音量', '50',
             0, 100, 5, '%', 'kbd_sound_volume', 'feedback')),
    mkGroup('k_toolbar', '工具栏'),
    // §3-11: expand_toolbar_by_default — 默认展开工具栏，开关, 默认 关
    mkSwitch('k_expand_toolbar', '默认展开工具栏', 'false',
             'expand_toolbar_by_default', 'toolbar'),
    mkGroup('k_gesture', '手势'),
    // §3-10: space_swipe_step — 空格划动移光标步长，滑条 5–20(vp/格), 默认 10
    mkSlider('k_space_swipe_step', '空格划动移光标步长', '10',
             5, 20, 1, 'vp', 'space_swipe_step', 'gesture'),
    // §3-12: show_preedit — 显示编码行，开关, 默认 开
    mkSwitch('k_show_preedit', '显示编码行', 'true',
             'show_preedit', 'gesture'),
  ];
}

// ========== 候选窗口 ==========
// H-240(CodeArts): 契约 §3 的 4 项（CAND_KEYS）enabledInPanel=true，其余 false
function getCandidateSettings(): SettingItem[] {
  return [
    mkGroup('c_group', '候选窗口'),
    // §3-2: cand_font_size — 候选词字号，滑条 14–22(vp), 默认 18
    mkSlider('c_font_size', '候选词字号', '18',
             14, 22, 1, 'vp', 'cand_font_size', 'group'),
    // §3-4: page_size — 每页候选词数，单选 3/5/7/9, 默认 5
    mkDropdown('c_page_size', '每页候选词数', '5',
               [new DropdownOption('3', '3'),
                new DropdownOption('5', '5'),
                new DropdownOption('7', '7'),
                new DropdownOption('9', '9')],
               'page_size', 'group'),
    // §3-8: undo_stack_limit — 可撤销步数，滑条 5–30, 默认 10
    mkSlider('c_undo_stack_limit', '可撤销步数', '10',
             5, 30, 1, '步', 'undo_stack_limit', 'group'),
    // §3-9: grid_page_size — 展开网格每页条数，滑条 20–80, 默认 50
    mkSlider('c_grid_page_size', '展开网格每页条数', '50',
             20, 80, 5, '条', 'grid_page_size', 'group'),
    disabled(mkSwitch('c_show', '显示候选窗口', 'true',
             'cand_show', 'group')),
    disabled(mkDropdown('c_orientation', '候选词列表方向', 'horizontal',
             [new DropdownOption('horizontal', '横向'),
              new DropdownOption('vertical', '纵向')],
             'cand_orientation', 'group')),
    disabled(mkSlider('c_padding', '候选词边距', '8',
             0, 20, 1, 'vp', 'cand_padding', 'group')),
    disabled(mkSlider('c_window_padding', '候选窗口边距', '4',
             0, 20, 1, 'vp', 'cand_window_padding', 'group')),
    disabled(mkSlider('c_min_width', '候选窗口最小宽度', '0',
             0, 200, 10, 'vp', 'cand_min_width', 'group')),
    disabled(mkSlider('c_radius', '候选窗口圆角半径', '8',
             0, 20, 1, 'vp', 'cand_radius', 'group')),
    disabled(mkDropdown('c_horizontal_style', '横向候选词样式', 'always_fill',
             [new DropdownOption('always_fill', '总是填充宽度'),
              new DropdownOption('as_needed', '按需填充宽度'),
              new DropdownOption('never_fill', '从不填充宽度')],
             'cand_horizontal_style', 'group')),
    disabled(mkDropdown('c_expanded_style', '展开候选词样式', 'flex',
             [new DropdownOption('flex', '弹性盒'),
              new DropdownOption('table', '表格')],
             'cand_expanded_style', 'group')),
    disabled(mkSlider('c_grid_span', '表格样式展开候选词列数', '4',
             2, 8, 1, '列', 'cand_grid_span', 'group')),
  ];
}

// ========== 高级 ==========
// H-240(CodeArts): 全部表外项，enabledInPanel=false
function getAdvancedSettings(): SettingItem[] {
  return [
    mkGroup('a_group', '高级'),
    disabled(mkSwitch('a_verbose_log', '详细记录日志', 'false',
             'adv_verbose_log')),
    disabled(mkNavigation('a_real_time_logs', '实时日志', '查看实时日志输出')),
    disabled(mkNavigation('a_crash_logs', '崩溃日志', '查看崩溃日志')),
    disabled(mkButton('a_reload_config', '重载配置', '重新加载 Rime 配置')),
    disabled(mkNavigation('a_about', '关于', '版本信息、许可证、第三方声明')),
  ];
}