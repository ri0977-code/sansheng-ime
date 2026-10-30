import { RimeEngine } from './RimeEngine';
import { MockRimeEngine } from './MockRimeEngine';
import { RealRimeEngine } from './RealRimeEngine';

/**
 * 引擎单例入口。
 * M2 起默认返回真 Rime；若 native 初始化失败，键盘 UI 会在日志里报错，
 * 但不会崩（`KeyboardController.initEngine` 已 catch）。
 * `set()` 仍可用于测试时换回 MockRimeEngine。
 * 归属：Qoder。
 */
export class EngineProvider {
  private static instance: RimeEngine | null = null;

  static get(): RimeEngine {
    if (EngineProvider.instance === null) {
      EngineProvider.instance = new RealRimeEngine();
    }
    return EngineProvider.instance;
  }

  static set(engine: RimeEngine): void {
    EngineProvider.instance = engine;
  }
}
