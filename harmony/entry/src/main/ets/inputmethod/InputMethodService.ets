/*
 * 三生输入法 · IME 扩展服务（M1 键盘壳）
 * 归属：CodeArts（鸿蒙 UI）。
 * 生命周期与面板接入借鉴自 nanaseyuu/hMixedKeyboard (Apache-2.0) 的 HMixedService.ets，
 * 本项目裁剪为「只转调键盘控制器」，不引入其字典引擎。
 */
import { InputMethodExtensionAbility } from '@kit.IMEKit';
import { Want } from '@kit.AbilityKit';
import { keyboardController } from './KeyboardController';

const TAG: string = 'SSInputMethodService';

export default class InputMethodService extends InputMethodExtensionAbility {
  onCreate(want: Want): void {
    console.info(`${TAG} onCreate, ability: ${want.abilityName ?? ''}`);
    keyboardController.onCreate(this.context);
  }

  onDestroy(): void {
    console.info(`${TAG} onDestroy`);
    keyboardController.onDestroy();
  }
}