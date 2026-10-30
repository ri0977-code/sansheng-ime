# H-096 键盘布局收口 · 一次交付清单（M6 唯一剩闸门 · 2026-10-23 12:5x）

> **用法**：这是 CodeArts 下一轮（布局收口那次）**一次性交齐**的清单。7 项齐了我才打提审包、跑 16 项内容闸门、重拍 5 张商店截图；缺一项我就打回，**别一件一个包来回装**。
> 依据：`docs/ISSUES.md` H-096（交付判据①②③④）＋ M-133（五件收口）＋ H-098／H-147。

## 一、布局本身（H-096，你在跟主人改的那条）
- [ ] **A. 报改动清单**：每个视觉决策对应 H-096 哪条已知问题（键帽间距/高度、底栏比例、横屏候选区挤压、符号面板贴合、展开网格分隔）。
- [ ] **B. 交付行带全量信息**（WIP 一行）：构建产物全名 ＋ `unsigned` 字节数（**debug 与 release 两个，带 B 标记**）＋ `signed` 字节数＋sha256 前 12 位（我按规矩只比字节数、不比 hash）。
- [ ] **C. 竖屏／横屏各 3 张对照截图**（主键盘、候选展开网格、符号面板），与 `docs/evidence/2026-10-22/m5-50*` 基线**同角度**（我 12:5x 会重出 720×1280）。
- [ ] **D. 四条不许回归**（真机我验）：九键严格 3×3、26 键数字直出、候选左右滑翻页、Shift 有可见态。
- [ ] **E. 主人点头**：截图主人看过确认（这是 H-096 判据④，我不能替你签这格）。

## 二、随同批带出的 5 件收口（M-133，别单独改一版）
- [ ] **F. 摘两个调试探针页（H-098）**：`main_pages.json` 删掉 `pages/M3Probe`、`pages/LandscapeProbe` 两行（页面文件可留、路由不注册即可）。
- [ ] **G. 包内图标换含环源图（H-147，D-022）**：用 `python scripts/make_store_icon.py` 出的 512/1024 件覆盖 `entry/.../app_icon.png` 与 `AppScope/.../foreground.png`（或把 nova6 那张 192 件等比放大）。我 12:5x 复量判据：gold 像素覆盖率回到 ≈15.4%（含外环）——现在包内是缺环版，覆盖率对不上。
- [ ] **H. 退 `module.json5` 的 `ohos.entry.mainability` metadata**（11:06 之前加的；现在 `ohos.want.action.home` 已是文档要求的入口条件，这条要么退、要么加一行注释说清为什么留）。
- [ ] **I. 改 `KeyboardIndex.ets:1005` 注释**（现注释写「短按展开/长按折叠」，代码是单击折叠，二者相反）。
- [ ] **J. 12:14 那版（625a805）补两个 unsigned 字节数**：debug＋release，带 B 标记（我 12:5x 还没独立复现那版）。

## 三、我这边收口的固定动作（你交齐 7 项后，顺序是死的）
1. 独立全量重编，比你报的 **unsigned 字节数**（一致才继续，不一致写 MAILBOX 停手）；
2. `sign.ps1`＋`install.ps1` **同一 HAP 只装一次**；
3. 装机跑 **16 项内容检查**（构建绿≠验收过；⑨b/⑩ 在 `.app` 上是阻断项）；
4. 重拍 5 张商店截图（720×1280，`make_store_shots.py`）；
5. 打 release 提审 `.app`，过 16/16 才交你提审。

## 判「交齐」的标准
上面 7 格全勾、且 B/G/J 的字节数我独立重编对上，才算 H-096＋H-098＋H-147 一起收口；缺任何一格我打回。**在此之前不出包、不拍商店截图、不装机跑回归。**

---

## 七、一条命令全查（14:2x 起）

```bash
python scripts/check_closure_items.py            # 查六件，逐件给结论
python scripts/check_closure_items.py --strict     # 任一件未过 exit 1，可当提交前闸门
```

**14:2x 实测（当前树）六项全 FAIL**：探针页仍注册两页；`app_icon.png` gold=0.100/fill=0.617/环厚=0.0127；`foreground.png` gold=0.130/fill=0.633/环厚=0.0039；`module.json5:47` metadata 无保留理由注释；`KeyboardIndex.ets:1005` 旧注释；反斜杠仍打顿号。

判据阈值（基准＝nova6 真源 `res/mipmap-xxxhdpi/ic_launcher.png`）：gold 覆盖率 ≈0.15、内容占比 ≈0.77、外环厚 ≈0.026×边长。

## 八、现成补丁 + 交付行模板（14:4x 起，照着抄）

五件不用手改，跑脚本（默认 dry-run，`--apply` 才落盘、自动 `.bak-<时间戳>` 备份）：

```bash
python scripts/apply_closure_fixes.py            # 先看每处 old/new
python scripts/apply_closure_fixes.py --apply    # 落盘
python scripts/check_closure_items.py            # 改完验收，应全 OK
```

交付行照这个格式写（WIP 表格 9 格，`本机构建` 四个字别省 —— 本机有 271,577 B CRLF 漂移，
换目录构建会小这么多，所以字节数只在同一台机器、同一工作区里比对，M-143）：

```
| W-2xx | 2026-10-23 15:0x | CodeArts | H-096 | READY | `entry/src/main/ets/pages/KeyboardIndex.ets`, `AppScope/resources/base/media/foreground.png` | 本批改动一句话说明。本批 unsigned 28,xxx,xxx B / signed 28,xxx,xxx B（**本机构建**），已装 Mate80 | Qoder 复验：真机三条 | 待 Qoder 读 |
```

我收到后的固定动作（第三节）：独立全量重编 → 只比 unsigned 字节数 → sign+install 一次 → 16 项内容闸门 → 重拍 5 张商店截图 → 打 release `.app`。
