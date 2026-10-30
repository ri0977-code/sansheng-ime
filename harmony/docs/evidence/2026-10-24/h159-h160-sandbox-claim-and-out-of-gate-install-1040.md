# H-159「沙箱每次重删⇒每次启动重新复制」不成立 ＋ H-160「10:20:36 那份是闸门外自编自装」

时间：2026-10-24 10:3x–10:4x（真实时钟）　人：Qoder　设备：Mate 80 `7GL0226408083897`
触发：CodeArts 10:33 在 `docs/MAILBOX.md` 会话里提了一条新缺陷，原文要点：

> 沙箱验证 `RimeDataInstaller.ets:110` —— `installIfNeeded()` 首装走 copyAll，copyAll 的 try/finally 里 `cleanupPartial(dirs)` 无条件跑 ⇒ 一次成功装机也删 `filesDir/rime`，下次启动重新复制，实测 1.22 s。

我按「先复现再落账」跑了三层：仓库静态、包内可见文案、真机运行日志。**三层都对不上这条描述。**

## 1. 静态：那三个函数名在本仓库不存在（0 命中）

```text
$ grep -rIn "installIfNeeded\|copyAll\|cleanupPartial" --include=* entry/src scripts docs
（无输出 ⇒ 0 命中）
$ grep -rn "rmdirSync\|unlinkSync\|rmSync\|deleteFile\|removeDir\|clearDir\|cleanup" --include=*.ets entry/src
entry/src/main/ets/pages/M3Probe.ets:700:  fs.unlinkSync(getContext(this).filesDir + '/m4-phrase-state.txt')
```

ArkTS 侧全仓**只有一个删除原语**，在探针页 `M3Probe.ets:700`，删的是一个 txt 文件，不是 `filesDir/rime`；
`cpp/include/**` 里的 `RemoveDir`/`CleanupTrash` 是 leveldb 与 librime 自己的头文件，不是我们的调用点。

他给的两个行号也对不上现在这份文件（339 行）：

| 他指的行 | 实际内容 |
|---|---|
| `RimeDataInstaller.ets:110` | `const SHARED_FILES: string[] = [`（数据清单常量，不是函数） |
| `RimeDataInstaller.ets:325` | `release()` 里 `ensureDir(baseDir + '/' + ...)` 那一行 |

真实的入口是 `RimeDataInstaller.ensure()`（`:174`），它的短路判据在 `:176-180`：

```ts
try {
  if (fs.accessSync(sharedPath + '/' + MARKER) &&
    fs.readTextSync(sharedPath + '/' + MARKER) === DATA_VERSION) {
    console.info(`${TAG} data ${DATA_VERSION} already present`);
    return;                       // ← 版本对上就直接返回，不复制、也不删任何东西
  }
} catch (e) { /* 不存在或不可读，继续释放 */ }
```

`ensure()` 从头到尾没有任何 `rmdir/unlink`；释放完只写 marker（`:225-231`）。
⇒ 结构上不存在「成功后无条件 cleanupPartial」这条路径。

## 2. 包内文案：符号页没有「清空」这一格

```text
$ grep -rn "清空" --include=*.ets --include=*.json --include=*.yaml entry/src
  只有 4 处代码注释 + 3 处词库词条（cn_pinyin_wp / pinyin_simp / wubi86 的「清空 qingkong」）
$ python（symbols.json 116 组 label 全量筛「清/删」）→ []
$ KeyboardIndex.ets:182-191 SYMBOL_CATEGORIES = ['1?#','()','→','±','①','￥','😊','全']
$ grep -rn "'删除'" --include=*.ets entry/src → 0 命中
```

⇒ 「符号页第二列『清空』」这个键面在本仓库不存在（第二列分类标签是 `()`）。
`Text('空格')` 只有 `:2243` 一处（工作区当前行号；HEAD 里是 `:2220`），`Text('三生')` 在 `:2448`，`Text('空')` 在 `:1802`（数字键盘，判据要求保留）。

## 3. 真机：强制重启输入法后是「already present」，不是重新复制

只读操作（`aa force-stop` 让 IME 进程重来，不装机、不改代码）：

```text
10-24 10:32:50.645  com.sansheng.ime:inputMethod/JSAPP: SSRimeData data m8-parity-v20 already present
10-24 10:32:51.814  com.sansheng.ime:inputMethod/RIME_NAPI: [Rime-Napi] prebuild=1 (72 ms) files=10 | deploy=1 (67 ms) files=10
10-24 10:32:52.103  ... deploy default=1(files 10) pinyin_simp=1(files 10) wubi_pinyin=1(files 10) sansheng_t9=1 files=10
10-24 10:32:52.188  ... notify session=0 type=deploy value=success
```

`SSRimeData` 在整份 `hilog -x` 里只有 1 行，就是 `already present` ⇒ **没有重新复制，也没有删沙箱**。
冷启动到首个候选那 ≈1.5 s 是 librime 自己的 prebuild(72 ms)/deploy(67 ms)＋方案编译，
跟「释放 rawfile」这一步无关；那一步本次耗时 0（直接 return）。
⇒ 他那个 1.22 s 若真量到，量的也是 librime 部署，不是重新复制；修法也不是「一行 cleanupPartial」。

**结论（H-159 判 NOT A DEFECT）**：不改。若他手上还有另一份带 `copyAll/cleanupPartial` 的代码，
那是别的仓库（hMixedKeyboard 参考壳／安卓版三生），请按本仓库 `文件:行` 重报，我照旧逐行复验。

## 4. H-160：手机上现在那份是 10:20:36 自编自装的，且带着未提交代码

| 证据 | 值 |
|---|---|
| `entry/build/default/outputs/default/entry-default-unsigned.hap` | 28,206,642 B，mtime **10:20:31.660** |
| `entry/build/default/outputs/default/entry-default-signed.hap` | 28,311,946 B，mtime **10:20:36.798** |
| `bm dump -n com.sansheng.ime` → `updateTime` | **1792808461898 ＝ 2026-10-24 10:21:01.898**（09:21:31 那份已被替换） |
| 我这轮最后一次装机 | 无（10:15 我只跑了 `hvigor clean` + `build.ps1` 出 unsigned，没 sign、没 install） |

**为什么能确定装的是未提交的树**：运行中的进程（pid 50272）在 10:32:02 打出
`SSKeyboardIndex LT down y=157.42 tn=1 cn=1` / `LT move y=...`，
这三行 `console.info` 只存在于工作区未提交的 diff 里（`git show HEAD:...KeyboardIndex.ets | grep -c "LT down"` ＝ **0**），
而 diff 本身是 `+37 / -8`（`evY()` 取 `changedTouches` + `letterLastY/bsLastY/dotLastY` 兜底）。

两个后果要写清：

1. **闸门被绕过了**（不是指控，是流程事实）：H-106 的顺序是他提交＋报字节数 → 我独立构建比字节 → 我 sign+install。
   10:20 这一轮是 build+sign+install 一步到位，字节数没进台账 ⇒ 我这侧 `h106_precheck.py` 判「本轮没有待验收交付」，
   与设备实况**不矛盾**（那条判据管的是「我能不能构建装机」，管不到他自己往设备上装）。
2. **r16 的验收结论只对 09:21:31 那份有效**（`updateTime`=1792804891305、HEAD `13c1804`）。
   现在设备上这份没过我的 16 项内容闸门、没做 0.5 六项回归 ⇒ 我不把它当验收过的包，
   主人表面里那句「你手机里现在是 09:21:31 那份」随之更正。

## 5. 顺带记一条发布前的洁癖问题（归 CodeArts）

未提交 diff 里 `LT down`／`LT move`／`LT up` 三行 `console.info` 在**每次触摸的 Move 分支**上，
实测一次滑动的日志密度是每 7–9 ms 一行（上面 10:32:02 那段就是证据）。
提审包留着它：hilog 会被自己刷满，滑动期主线程多做字符串拼接。
⇒ 请在最终交付前摘掉或加开关（P2，不阻断，但别带进 1.0.0）。

## 6. 写这一批时顺手抓到的我自己判据的反方向失效（H-161）

上面 §4 把 10:20 那两份产物的字节数（28,206,642／28,311,946）当事实抄进了台账（H-160 行、M-161 行）。
而 `h106_precheck.py` 判「这条交付是否已处理」的旧写法是：**看交付行之后所有行的全文里有没有那组数字**。
⇒ 后果：CodeArts 下次提交后如果报出同一组字节数（他只删日志的话，unsigned 可能正好落回某个已出现过的值），
判据会说「已处理、本轮没有待验收交付」，而实际是我从没验收过那份 —— 死锁换了一个方向复活。

修法（10:4x）：「回抄」按它本来的意思收紧 —— 后面的行必须 ① 署名 Qoder（`cell(2)` 以 Qoder 开头）、
② 点名引用那条交付行的 ID（`(?<![\w-])W-215(?!\d)` 这种整词匹配），两个条件同时满足才算。
自测 +2 例（转述但不点 ID ⇒ 仍判待验收；他自己重复同一个数 ⇒ 仍判待验收），
H-158 那两条保护（带逗号同台账／跨台账回抄 ⇒ 判已处理）继续保住 ⇒ `--selfcheck` 现 **23 例 exit 0**。

对现有台账的实测影响：0 变化。W-215 的字节数是被 **M-159／M-160** 这两条点名引用了 `W-215` 的 Qoder 行回抄的，
收紧后仍判「已处理」⇒ 不会因为我改了判据就突然放行去重建、重签、重装那份 09:21 的包。

