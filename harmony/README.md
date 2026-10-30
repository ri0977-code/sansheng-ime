# 三生输入法 · 鸿蒙版

这是三生输入法鸿蒙版的**唯一正式工程目录**。旧目录 `F:\codeartswork` 只作归档，不再修改。

## 当前状态

- 阶段：**M1 真机首测部分通过**，进入 M1.1 手机键盘补全（横屏、九宫格、完整符号页）
- 基线：`6d504a6` / `v0.1.0-baseline`；M1：`8c8d625` / `v0.2.0-shell`（构建 + 签名均通过）
- 引擎：复用 `chuanis/harmonyos-next-rime-har` 的预编译 `librime.a`（含 Lua、OpenCC、LevelDB、marisa、yaml-cpp、glog）
- 闸门：调试签名输入法进系统列表 ✅；API 22 引擎库在鸿蒙 7 加载 ✅（2026-10-19，Mate 80 真机，用户参与验证）
- 现在能跑的：Mate 80 已可安装/启用并弹出竖屏键盘，mock 候选与基础按键链路已通；横屏、T9 和完整符号页仍未完成
- 下一步：Qoder 已修数字/`-`/`=`/符号直接上屏；CodeArts 修横屏、九宫格、分类符号页 → M2 真引擎接通（Qoder）→ M3 词库/滤镜移植

## 文档索引

| 文档 | 用途 |
|---|---|
| [PROGRESS.md](docs/PROGRESS.md) | 工程进度表：里程碑、当前状态、下一步、阻塞 |
| [VERSION_LOG.md](docs/VERSION_LOG.md) | 版本演进表：每个可安装版本的构建、真机结果、产物 |
| [ISSUES.md](docs/ISSUES.md) | 问题清单：编号、状态、归属、证据 |
| [HANDOFF.md](docs/HANDOFF.md) | 交接台：文件归属、当前交接、交接模板 |
| [MAILBOX.md](docs/MAILBOX.md) | Agent 信箱：双方开工先读、收工先写，不靠主人传话 |
| [INTERFACE.md](docs/INTERFACE.md) | UI 与引擎的接口契约（v0.1） |
| [BUILD.md](docs/BUILD.md) | 构建、签名、装机、真机测试步骤 |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | 架构与数据流 |
| [TASK-CODEARTS-M1.md](docs/TASK-CODEARTS-M1.md) | 给 CodeArts 的 M1 任务书 |
| [OPEN-SOURCE.md](docs/OPEN-SOURCE.md) | 开源复用规则、许可证门槛、候选清单 |
| [reference/HAR-集成方案-2026-10-19.md](docs/reference/HAR-集成方案-2026-10-19.md) | 2026-10-19 的 HAR 路线评估原文 |

## 构建

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build.ps1
```

产物：`entry\build\default\outputs\default\entry-default-unsigned.hap`

## 协作规则（摘要）

1. **唯一仓库**：只改 `F:\qoderwork\sansheng-ime-harmony`；旧目录只读。
2. **单一写入者**：同一时间只有一个 agent 改同一批文件；按 [HANDOFF.md](docs/HANDOFF.md) 的归属表执行。
3. **交接必须过构建**：构建不过，不交接。
4. **文档没记等于没发生**：每次交接更新进度/问题/版本记录，写清证据路径。
5. **不提交密钥**：`sign/`、口令、证书、`agconnect-services.json` 全部本地保留，已 gitignore。
6. **不删旧成果**：只复制、不搬空；旧目录保留作回滚基线。
7. **开源优先**：键盘、面板、皮肤先复用许可证兼容的开源实现；复用前登记到 [OPEN-SOURCE.md](docs/OPEN-SOURCE.md)。

## 上游与许可

- 引擎来源：`chuanis/harmonyos-next-rime-har`（上游根 LICENSE 为 MIT，`fanxing_rime_har` 包内标注 Apache-2.0，已记入问题清单待核）
- 上游 README 存档：[docs/reference/UPSTREAM-README.md](docs/reference/UPSTREAM-README.md)
- 本工程保留上游版权与许可声明；第三方签名密钥与本工程无关，未使用。
