# 内容闸门「已知坏样本」自测：20 个定向破坏，全部按预期报红

> 2026-10-23 00:34–00:38 · Qoder · 只读测试，未构建、未签名、未装机、未改任何应用代码
> 目的：证明 `scripts/check_app_content.py` 的 16 项断言**不是只会说 PASS**。
> 历史教训：第 ⑨ 项第一版把 DevEco 四宫格判成 PASS（H-097），原因就是检查写完没在坏样本上跑过。

## 0. 底包与工具

| 项 | 值 |
|---|---|
| 底包 | `entry/build/default/outputs/default/entry-default-unsigned.hap`（00:09 构建） |
| 字节 / sha256 | **28,178,736 B** / `6a35196d1e2e85d0dab2a451c245cab372cf590439aaa850d9524b9acc7950ca` |
| 条目数 | 83 |
| 检查器 | `scripts/check_app_content.py`（16 项；13 项恒阻断 + 3 项分级：9b/10 在 `.app` 阻断、裸 HAP WARN；14 恒 WARN） |
| 自测器 | **`scripts/check_app_content_selftest.py`（本次新增）**，默认取上面这份 HAP，逐项做一处定向破坏，比对「预期标记 vs 实际标记」 |
| 产物 | 全部写在系统临时目录，跑完删除 `.hap`，仅留 `selftest-result.json`；不落仓库 |

底包基线：**14/16 通过、阻断 0**，两项 WARN 分别是 ⑨b（`app_icon.png` 48×48 全不透明模板）与 ⑩（`main_pages.json` 仍注册 M3Probe/LandscapeProbe）——与 H-105/H-098 完全一致。

## 1. 用例矩阵（20/20 按预期触发）

| # | 定向破坏 | 期望 | 实测 |
|---|---|---|---|
| 00 | 不改（基线） | 14/16，⑨b⑩ WARN | ✅ 一致 |
| 01 | 塞入 `rawfile/rime/symbols.yaml` | ① FAIL | ✅ 13/16 阻断 1 |
| 02 | `default.yaml` 的 punctuator.symbols 只剩 1 组、half_shape 去掉中文引号 | ②④ FAIL、③ PASS | ✅ 12/16 阻断 2 |
| 03 | `default.yaml` 写成非法 YAML（`punctuator: [`） | ③ FAIL（连带 ②④） | ✅ 11/16 阻断 3 |
| 05 | 删掉 `script_translator@pinyin` | ⑤ FAIL | ✅ 阻断 1 |
| 06 | `import_preset: default` → `symbols` | ⑥ FAIL | ✅ 阻断 1 |
| 07 | 包内 `terms.html` 注入「用户词典与设置保存在应用沙箱」 | ⑦ FAIL | ✅ 阻断 1 |
| 08 | `module.json` 加 `ohos.permission.INTERNET` | ⑧ FAIL | ✅ 阻断 1 |
| 09 | `foreground.png` 换成左右两条竖条（四宫格按行指纹） | ⑨ FAIL | ✅ 阻断 1 |
| 09b | `app_icon.png` 换成已知合格 216px 键帽图 | ⑨b **PASS** | ✅ 15/16 |
| 09b | `app_icon.png` 换成 48×48 全不透明（模板） | ⑨b **WARN** | ✅ 与基线一致 |
| 10 | `main_pages.json` 摘掉两个探针页 | ⑩ **PASS** | ✅ 15/16 |
| 11 | 删除 `rawfile/legal/notice.html` | ⑪ FAIL | ✅ 阻断 1 |
| 12 | `modules.abc` 追加「应用安装目录下的 NOTICE」 | ⑫ FAIL | ✅ 阻断 1 |
| 13 | `modules.abc` 换成 `dummy` | ⑬ FAIL、⑫ PASS | ✅ 阻断 1 |
| 14 | `versionName` 改 `0.9.0` | ⑭ **WARN** | ✅ 13/16 阻断 0 |
| 15 | `deviceTypes` 加 `tablet` | ⑮ FAIL | ✅ 阻断 1 |
| 16 | 只做两处已知修复（合格 app_icon + 摘探针页） | **16/16** | ✅ 16/16 阻断 0 |
| 17 | **把现状 HAP 套壳成 `.app`**（外层 zip 装内层 HAP） | ⑨b⑩ 由 WARN 升为 **FAIL** | ✅ 14/16 阻断 **2** |
| 18 | 修好两项后再套壳成 `.app` | **16/16** | ✅ 16/16 阻断 0 |

## 2. 结论

1. **13 个阻断项每一项都有至少一个坏样本能把它打红**，不存在「写了但永远 PASS」的检查；3 个 WARN 项（9b/10/14）都验证了「坏样本报 WARN、修好后 PASS」双向。
2. **16/16 是可达的**：把当前包里仅有的两处偏差（`app_icon.png` 模板、探针页注册）按 H-105/H-098 改掉，同一底包即 16/16。也就是说这两项就是当前产物层的全部缺口，没有隐藏的第三项。
3. 用例 03 一次破坏触发 ②③④ 三项，是设计上的**共享依赖**（都读 `default.yaml`），不是误报；提审前修 YAML 时按 ③ 的解析错误定位即可。
4. 用例 16 证明「检查器不会因为无关改动误伤」：只换图标、只摘探针页，其它 14 项保持 PASS。
5. **H-115（本轮发现并修复）**：9b/⑩ 原来只报 WARN，而 `release_build.ps1` 只看阻断项 ⇒ **带模板启动图标和探针页的 `.app` 能打印 `RELEASE OK`**。修法是按输入类型分级：裸 HAP 保持 WARN（开发自检要用探针），`.app` 计入阻断。用例 17/18 就是这层的回归：现状壳阻断 2，修好后阻断 0。

## 3. 这套自测证明了什么、没证明什么

**证明**：检查器的判定逻辑在已知坏样本上会响，标记（PASS/FAIL/WARN）与阻断语义一致；修好对应文件后能回到 PASS；`.app` 与裸 HAP 的阻断语义按输入类型正确区分（H-115）。
**没证明**：规则本身的完备性 —— 如果某个新出现的禁用文件不在 16 条规则里，它照样会漏（例如把 `symbols.yaml` 改名为 `symbols2.yaml` 就绕开 ①，因为这不在规则口径内）。这层只能靠 `app-content-checklist.md` 的人工复核与 AGC 实际审核兜底。
**另**：底包是 debug unsigned HAP；提审 `.app` 出件后必须用同一脚本再跑一遍，**包级结论只对那一份 `.app` 有效**。

## 4. 复跑方法

```bash
cd /f/qoderwork/sansheng-ime-harmony
PYTHONIOENCODING=utf-8 python scripts/check_app_content_selftest.py
# 自定义底包 / 保留产物：
PYTHONIOENCODING=utf-8 python scripts/check_app_content_selftest.py --hap <路径> --workdir <目录> --keep
```

退出码：0 = 全部按预期触发；1 = 有检查没响（说明检查器或底包与预期不符，必须先查再提审）。
