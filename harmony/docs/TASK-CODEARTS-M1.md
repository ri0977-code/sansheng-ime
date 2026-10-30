# M1 任务书 · 键盘壳 + IME 接入（CodeArts）

> 只在 `docs/HANDOFF.md` 写明「M1 可以开始」后执行。否则只读文档，不动代码。
> 使用 CodeArts 的 **「鸿蒙开发」** 专属 agent；工作区必须是 `F:\qoderwork\sansheng-ime-harmony`。
> 参考壳源码已就位：`F:\qoderwork\_ref_hMixedKeyboard\entry\src\main\ets\inputmethod\`
> （`HMixedService.ets`、`model/MixedController.ets`、`pages/KeyboardIndex.ets`、`model/DictEngine.ets`）。可借鉴面板生命周期/resize/按键路由，不整包照搬。
> 该项目是 Apache-2.0：若复制其代码片段，保留版权头，并在交接报告里注明来源文件。

## 0. 你的角色

你是这个项目的鸿蒙 UI 负责人。你只做 **输入法扩展 + 键盘面板 + 候选栏 + 按键交互**，接 Qoder 提供的 mock 引擎。**不要接真 Rime，不要改 native/数据/构建配置。**

## 1. 开工前必读

1. `AGENTS.md`
2. `docs/PROGRESS.md`
3. `docs/HANDOFF.md`（确认文件归属与当前交接）
4. `docs/ISSUES.md`
5. `docs/INTERFACE.md`
6. `docs/BUILD.md`
7. `docs/OPEN-SOURCE.md`（复用规则与 hMixedKeyboard 移植边界）

## 2. 目标（M1）

在真机上做出一个**能用的最小键盘**：

- 系统输入法列表里能添加「三生输入法」；
- 切换到它，键盘面板弹出；
- 在备忘录里能输入字母、数字、空格、回车、退格；
- 候选栏显示 mock 候选（你/尼/泥/呢/你好 + comment）；
- 点候选能把词上屏；
- 横竖屏切换不崩，键盘不遮输入框。

**不要求**真的出 Rime 候选；那是 M2。

### 开源优先

- **不要从零画键盘**：先移植 `F:\qoderwork\_ref_hMixedKeyboard` 的 IME 服务、面板控制器、键盘面板，替换 `DictEngine` 为 `EngineProvider`。复用边界见 `docs/OPEN-SOURCE.md`。
- 开工前用半天调研可复用的开源键盘/皮肤（Gitee/GitHub），把「项目、许可证、可复用文件、结论」追加到 `docs/OPEN-SOURCE.md`。
- 只接受 Apache-2.0/MIT/BSD；GPL/AGPL/无 LICENSE 只参考交互，不复制代码。
- 复制代码必须保留版权头，并在 M1 交接报告里注明来源文件。

## 3. 交付物

| # | 文件 / 产物 | 说明 |
|---|---|---|
| 1 | `entry/src/main/ets/inputmethod/InputMethodService.ets` | 实现 `InputMethodExtensionAbility`：onCreate/onBind/onUnbind；创建并管理 panel；接输入事件 |
| 2 | `entry/src/main/ets/pages/KeyboardIndex.ets` | 键盘面板 UI：候选栏 + QWERTY + 数字/符号 + 功能键 |
| 3 | `entry/src/main/ets/inputmethod/**` 下的组件/控制器 | 按键布局、状态、面板尺寸、配色等，按需拆分 |
| 4 | `entry/src/main/resources/base/media/keyboard/**` | 键盘图标/资源（新建） |
| 5 | 可编译 HAP | `entry\build\default\outputs\default\entry-default-unsigned.hap` |
| 6 | `docs/HANDOFF.md` / `docs/ISSUES.md` 更新 | 写清构建结果、真机结果、未完成项 |
| 7 | `docs/OPEN-SOURCE.md` 追加调研结果 | 开源键盘/皮肤候选、许可证、采用结论 |

可以改 `entry/src/main/resources/base/profile/input_method_config.json`（子类型/语言），但**不要改 `module.json5`**；确实需要时写变更请求。

## 4. 必须遵守的接口

只通过 `EngineProvider.get()` 拿引擎，不要直接 import `libfanxing_rime.so`。

```ts
import { EngineProvider } from '../engine/EngineProvider';
import { RimeContext } from '../engine/RimeEngine';

const engine = EngineProvider.get();
await engine.init(getContext(this).filesDir + '/rime');
const ctx: RimeContext = engine.processKey('n');
// ctx.preedit / ctx.candidates[].text + comment / ctx.page
// 如果 ctx.commitText 有值，立刻 insertText(ctx.commitText)
const committed: string = engine.selectCandidate(index);
```

- mock 引擎已经就位（`entry/src/main/ets/engine/MockRimeEngine.ets`），**不要修改 engine 目录**。
- 候选的 `comment` 是三向反查注解，有就显示在候选词旁边。
- 翻页键调用 `engine.flipPage(1/-1)`；删除调用 `engine.deleteBackward()`；清空调用 `engine.clear()`。
- 中文/英文、简繁开关调用 `engine.setOption('ascii_mode'|'zh_trad', boolean)`（mock 只打日志，先把 UI 状态做好）。

## 5. IME 实现要点

- `InputMethodExtensionAbility` 的 `onCreate` 里拿 `InputMethodExtensionContext`，创建面板；`onBind` 里建立 `InputClient`。
- 面板：先 `panel.setUiContent('pages/KeyboardIndex')`，**再** `panel.resize(width, height)`。顺序反了会踩旧项目记录过的 vp 坑。
- 尺寸：用 `display`/`window` 拿屏幕宽高，按 vp 计算；手机竖屏键盘高度建议 38%–45% 屏高，横屏另算。
- 上屏：`inputClient.insertText(text)`；退格用 `inputClient.deleteBackward()` 或发送按键事件；回车/空格按 `commitText` 或编辑器行为处理。
- 键盘收起/切换：调用 panel 的 hide/显示接口；不要直接销毁 ability。
- 防止崩溃：所有 `inputClient` 调用判空；panel 生命周期与 ability 解绑时清理监听。
- 不要用 `any`、不要 `@ts-ignore`、不要硬编码设备路径；ArkTS 严格类型。
- 目标 API 22，设备 API 26；只用公开 IME Kit/ArkUI API。API 不确定就查官方文档并编译验证，不要猜。

## 6. 验收

### 构建

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build.ps1
```

必须通过，并在 `HANDOFF.md` 写产物路径 + 大小。

### 真机（有设备时）

- [ ] `scripts/install.ps1` 安装成功
- [ ] 设置 → 系统 → 语言与输入法 → 输入法，能添加「三生输入法」
- [ ] 切换到三生输入法，键盘弹出
- [ ] 备忘录输入 `nihao`，候选栏出现 mock 候选
- [ ] 点「你好」上屏
- [ ] 退格、空格、回车、数字、符号都正常
- [ ] 横竖屏切换不崩，键盘不遮输入框

没有设备就只做构建，明确写「未装机验证」，不要写「已通过」。

## 7. 禁止事项

1. 不改 `entry/src/main/cpp/**`、`entry/src/main/ets/engine/**`、`fanxing_rime_har/**`。
2. 不改包名 `com.sansheng.ime`、不改签名、不碰 `sign/**`。
3. 不改根 `build-profile.json5`、`oh-package.json5`、`entry/build-profile.json5`、`entry/oh-package.json5`。
4. 不加第三方依赖（要加先写变更请求）。
5. 不复制旧目录的 `deploy.bat` / 旧测试页的原生 import。
6. 不提交 git、不写密钥、不删除旧文件。
7. 不在没跑构建的情况下交接。
8. 不引入 GPL/AGPL/无许可证代码，不整包照搬社区项目。

## 8. 完成后报告格式

在 `docs/HANDOFF.md` 追加：

```markdown
### YYYY-MM-DD · CodeArts → Qoder（M1 完成）

- 完成：
- 未完成 / 阻塞：
- 改动文件：
- 构建：命令 + 成功/失败 + HAP 路径 + 大小
- 真机：设备/系统/现象（或「未装机」）
- 新增/关闭问题：H-xxx
- 下一步（给 Qoder）：
```

然后给主人一段不超过 10 行的摘要：做了什么、能不能装、卡在哪、下一步。
