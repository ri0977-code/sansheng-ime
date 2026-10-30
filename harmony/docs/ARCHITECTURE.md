# 架构说明

## 1. 分层

```text
┌─────────────────────────────────────────────────────┐
│ InputMethodExtensionAbility（CodeArts）              │
│   ├─ KeyboardPanel / KeyboardIndex（ArkUI）          │
│   ├─ 候选栏（text + comment）                         │
│   └─ InputClient（insertText / delete / 光标）        │
├─────────────────────────────────────────────────────┤
│ EngineProvider + RimeEngine 接口（Qoder）             │
│   ├─ M1: MockRimeEngine（假候选，先把 UI 跑通）       │
│   └─ M2: RimeEngineImpl（NAPI 适配）                  │
├─────────────────────────────────────────────────────┤
│ libfanxing_rime.so（Qoder 重写 NAPI）                 │
│   └─ librime.a + liblua.a + libopencc.a +            │
│      libleveldb.a + libmarisa.a + libyaml-cpp.a      │
├─────────────────────────────────────────────────────┤
│ 电脑版资产（Qoder 移植）                              │
│   schema / 12 级 Lua 滤镜 / 词库闭包 / OpenCC 数据     │
└─────────────────────────────────────────────────────┘
```

## 2. 职责边界

| 层 | 谁负责 | 说明 |
|---|---|---|
| IME 扩展、面板、键盘、候选栏 | CodeArts | 只依赖 `RimeEngine` 接口，不直接 import NAPI |
| 接口、Provider、mock、真实现 | Qoder | 换实现时 UI 不动 |
| C++ / NAPI / 链接 | Qoder | 复用上游静态库，重写桥 |
| 词库/滤镜/OpenCC | Qoder | 从电脑版 1.9.8 的 release 配置移植 |
| 构建/签名/装机/版本 | Qoder | 统一脚本，单一出口 |

## 3. 数据流

```text
按键 → KeyboardIndex → engine.processKey(key)
     → RimeContext{preedit, candidates[text, comment], page}
     → 候选栏渲染
点选 → engine.selectCandidate(index) → committed text
     → InputClient.insertText(committed)
```

引擎初始化：

```text
EntryAbility / InputMethodService
  → EngineProvider.get().init(filesDir + '/rime')
  → 首次把 rawfile/rime 铺到沙盒（M3）
  → librime setup + initialize + start_maintenance
  → 就绪后可 processKey
```

## 4. 为什么走 HAR 路线

- 上游已完成 librime + Lua + OpenCC + LevelDB + marisa + yaml-cpp + glog 到 OHOS 的交叉编译（arm64-v8a，API 22）。
- 电脑版的五笔/拼音/中英/简繁/三向反查/自造词/自调频都依赖 Rime 配置与 Lua 滤镜，复用引擎可以原样搬；用 ArkTS 重写引擎是重复造轮子。
- 代价：依赖上游预编译库；API 22 在鸿蒙 7 上已实测可加载（闸门②）；只有 arm64。

## 5. 上游约束

- 目标：`targetSdkVersion` / `compatibleSdkVersion` = `6.0.2(22)`；设备 API 26 已实测加载。
- ABI：仅 `arm64-v8a`，模拟器 x86_64 不可用。
- 上游 NAPI 只有 5 个 Demo 级接口，必须重写（见 `ISSUES.md` H-008）。
- 上游 `build-profile.json5` 里带作者自己的签名路径/密钥，**不要使用**；我们的签名在本地 `sign/`。
- 许可：根 LICENSE 是 MIT，`fanxing_rime_har` 包声明 Apache-2.0，发布前核实（H-007）。

## 6. 数据移植（M3）

- 源：`F:\workbuddywork\三生输入法\packaging\release\config\`（1.9.8 发布版口径）。
- 目标：`entry/src/main/resources/rawfile/rime/`，首启复制到 `filesDir/rime`。
- 内容：`wubi_pinyin.schema.yaml` / `.custom.yaml`、12 级 Lua 滤镜、39 个 Lua 模块、15 份 dict.yaml、OpenCC `s2t.json` + 字典、数据 txt。
- 复用安卓版的闭包校验思路：从 schema 的 `dictionary` + `import_tables` 做 BFS，避免漏词库。
- 真机验收：五笔、拼音、中英混输、简繁、三向反查、自造词、自调频。

## 7. 已知风险

| 风险 | 应对 |
|---|---|
| IME 面板生命周期/resize 坑 | 先 `setUiContent` 再 `resize`；参考官方 Sample / hMixedKeyboard |
| 首次部署耗时 | M3 做进度提示；启动维护异步 |
| `.so` 体积大（20MB+） | 接受；后续可裁剪链接 |
| 上游库长期维护 | 保留源码副本与构建说明；必要时自行重编 |
| 真机只有一台 | 每次改动小步提交，保留可回滚 HAP |
