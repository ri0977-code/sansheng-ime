# 19:34:30 独立复算构建：BUILD FAILED（我踩了在途文件，非 CodeArts 缺陷）

命令：`powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build.ps1`
完整原始日志 2,536 行（148,917 B）本地留存 `docs/evidence/2026-10-22/build-verify-190x.log`；`.log` 扩展名被 `.gitignore` 忽略，故此处只存判定所需摘录（已去 ANSI 色码）。

- 失败任务：`default@CompileArkTS`
- 错误总数：**594** 条，全部为 `arkts-no-standalone-this`（`10605093`）
- 首错：`entry/src/main/ets/pages/KeyboardIndex.ets:1617:13`
- 判定依据：`KeyboardIndex.ets` mtime **19:35:05**、102,072 B；提交态 `3c94d66` 为 86,750 B / 2,154 行；工作区较提交态 **+431 行 / −35 行**
  ⇒ 构建时 CodeArts 正在写该文件（半保存状态：`:1584-1585` 出现游离 `})` / `}`，`:1540` 起 `@Builder` 掉到 0 列，`struct KeyboardIndex` 被提前闭合，其后的 builder 变成「stand-alone function」，所以一个语法缺口炸出 594 个 `this` 错误）。
- 结论：**违反本轮约束④（构建前等 mtime ≥ 120 s）的是我**，本条不作为任何 H 项的证据；等他本轮报数并停手 ≥120 s 后我再复算，逐字节一致才签名装机。

## 前 12 条错误原文

    Error Message: Using "this" inside stand-alone functions is not supported (arkts-no-standalone-this) At File: F:/qoderwork/sansheng-ime-harmony/entry/src/main/ets/pages/KeyboardIndex.ets:1617:13
    Error Message: Using "this" inside stand-alone functions is not supported (arkts-no-standalone-this) At File: F:/qoderwork/sansheng-ime-harmony/entry/src/main/ets/pages/KeyboardIndex.ets:1618:13
    Error Message: Using "this" inside stand-alone functions is not supported (arkts-no-standalone-this) At File: F:/qoderwork/sansheng-ime-harmony/entry/src/main/ets/pages/KeyboardIndex.ets:1620:13
    Error Message: Using "this" inside stand-alone functions is not supported (arkts-no-standalone-this) At File: F:/qoderwork/sansheng-ime-harmony/entry/src/main/ets/pages/KeyboardIndex.ets:1621:39
    Error Message: Using "this" inside stand-alone functions is not supported (arkts-no-standalone-this) At File: F:/qoderwork/sansheng-ime-harmony/entry/src/main/ets/pages/KeyboardIndex.ets:1622:13
    Error Message: Using "this" inside stand-alone functions is not supported (arkts-no-standalone-this) At File: F:/qoderwork/sansheng-ime-harmony/entry/src/main/ets/pages/KeyboardIndex.ets:1643:13
    Error Message: Using "this" inside stand-alone functions is not supported (arkts-no-standalone-this) At File: F:/qoderwork/sansheng-ime-harmony/entry/src/main/ets/pages/KeyboardIndex.ets:1645:13
    Error Message: Using "this" inside stand-alone functions is not supported (arkts-no-standalone-this) At File: F:/qoderwork/sansheng-ime-harmony/entry/src/main/ets/pages/KeyboardIndex.ets:1661:40
    Error Message: Using "this" inside stand-alone functions is not supported (arkts-no-standalone-this) At File: F:/qoderwork/sansheng-ime-harmony/entry/src/main/ets/pages/KeyboardIndex.ets:1662:41
    Error Message: Using "this" inside stand-alone functions is not supported (arkts-no-standalone-this) At File: F:/qoderwork/sansheng-ime-harmony/entry/src/main/ets/pages/KeyboardIndex.ets:1668:17
    Error Message: Using "this" inside stand-alone functions is not supported (arkts-no-standalone-this) At File: F:/qoderwork/sansheng-ime-harmony/entry/src/main/ets/pages/KeyboardIndex.ets:1670:37
    Error Message: Using "this" inside stand-alone functions is not supported (arkts-no-standalone-this) At File: F:/qoderwork/sansheng-ime-harmony/entry/src/main/ets/pages/KeyboardIndex.ets:1672:19

## 构建尾部判定行原文

```
> hvigor ERROR: Failed :entry:default@CompileArkTS...
> hvigor ERROR: ArkTS Compiler Error
FAILURE: Build completed with 1 failure.
Execution failed for task 'default@CompileArkTS'.
> hvigor ERROR: BUILD FAILED in 5 s 660 ms
hvigor failed with exit code -1
+   throw "hvigor failed with exit code $exitCode"
+ CategoryInfo          : OperationStopped: (hvigor failed with exit code -1:String) [], RuntimeException
+ FullyQualifiedErrorId : hvigor failed with exit code -1
```
