# H-149 / H-098 探针页摘除：包级复测（2026-10-24 00:12，Qoder）

## 为什么测

`docs/ISSUES.md` 的 H-149 写着「提审 `.app` 只差第 ⑩ 项一件 —— 15/16、唯一红项是⑩，
摘掉 `main_pages.json` 两条路由就 16/16」（13:4x 的结论）。CodeArts 已在 `b5fda68`
从路由里摘掉两个探针页，但我此后没有在**包上**复核过这一项。本文件把「源码里改了」
和「包里确实没有」分开量一次。

纪律：不签名、不装机、不碰 `sign/**`；只读盘上已有的包。

## 被测对象（实测）

| 对象 | 字节 | mtime | 说明 |
|---|---|---|---|
| `entry/build/default/outputs/default/entry-default-unsigned.hap` | 28,199,141 | 2026-10-24 00:05 | CodeArts 本机构建，含 d3840eb（H-155 手势层） |
| `entry/build/default/outputs/default/entry-default-signed.hap` | 28,302,843 | 2026-10-24 00:06 | 同一棵树签名产物（**未安装**） |
| `%TEMP%\dryrun-sansheng.app` | 10,758,974 | 本次现场生成 | 把 signed HAP 放进一个 zip、内层命名 `entry-default.hap`；仅用于让闸门走 `.app` 分支（⑩ 在 `.app` 口径才是阻断项） |

`.app` 壳是临时件，测完即删；不进仓库、不冒充提审件。

## 源码侧

```
entry/src/main/resources/base/profile/main_pages.json  118 B
{"src": ["pages/Index","pages/KeyboardIndex","pages/AboutPage","pages/LegalPage"]}   ← 4 页，无 M3Probe/LandscapeProbe
```

（`pages/M3Probe.ets`、`pages/LandscapeProbe.ets` 文件仍在源码树，按 H-098 的修法「页面文件可留，路由不注册即可」——见文末取舍。）

## 包内实物

直接从 unsigned HAP 里取，不看工作树：

```
81 resources/base/profile/main_pages.json
{"src":["pages/Index","pages/KeyboardIndex","pages/AboutPage","pages/LegalPage"]}
```

`.app` 壳内层是 signed HAP，同一路径同一内容（内层解包读到的就是上面这 81 B）。

## 闸门结果

```
python scripts/check_app_content.py entry/build/default/outputs/default/entry-default-unsigned.hap
→ [PASS] 10. 提审包不含调试探针页   未注册
→ 结果: 15/16 通过；阻断项未过 1 个

python scripts/check_app_content.py %TEMP%\dryrun-sansheng.app
→ [PASS] 10. 提审包不含调试探针页   未注册
→ 结果: 15/16 通过；阻断项未过 1 个
```

`.app` 口径下 ⑩ 是**阻断项**（`check_app_content.py:471-479`：只有 `.app` 才 `blk=True`），
两次都 PASS ⇒ H-149 的「差 2 行」已经闭合。

## 唯一红项换了：⑪（不是 ⑩）

两份输入的红项都是第 ⑪ 项，原因是我自己 00:1x 的声明层改动：

| | 包内 | 当前源文件 |
|---|---|---|
| `legal/notice.html` | 77,148 B | **77,255 B** |
| `rime/README.md` | 7,433 B | 7,433 B（已同步） |

00:05 构建时 `README` 已是新版、`notice.html` 停在我中途那版（77,148 B）；
之后 NOTICE 定稿到 24,855 B，重生成得 77,255 B，尚未进包。
⇒ **下次构建 rawfile 只多 +107 B**（77,255 − 77,148），⑪ 自动转绿。
（M-152 里写的「+2,594 B」是相对 00:05 **之前**那份包的合计，两个数指的不是同一基线。）

## 结论

1. **H-149 闭合**：提审 `.app` 口径下第 ⑩ 项 PASS，探针页路由不再随包。
2. **H-098 可闭合**（提审目标达成），但它的第 ② 条判据「开发包仍可用启动参数进入」与修法
   「路由不注册」互斥：路由一摘，任何构建都进不去探针页。提审优先，接受这个损失；
   以后要自检时临时把两行路由加回去再构建，不动页面文件。
3. 下一份包的闸门预期：⑩ 保持绿，⑪ 因 notice.html 已重生成而转绿 ⇒ **16/16**，
   前提是 H-154 三处（P1-1/P1-2/P2-1）不再引入新的红项。

## 复现命令

```bash
cd /f/qoderwork/sansheng-ime-harmony
python scripts/check_app_content.py entry/build/default/outputs/default/entry-default-unsigned.hap
python - <<'PY'
import zipfile, os, tempfile
hap = "entry/build/default/outputs/default/entry-default-signed.hap"
out = os.path.join(tempfile.gettempdir(), "dryrun-sansheng.app")
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("entry-default.hap", open(hap, "rb").read())
print(out)
PY
python scripts/check_app_content.py "%TEMP%/dryrun-sansheng.app"
```

## 附：同轮源码级闸门（构建前快检，2026-10-24 00:18）

```
python scripts/check_app_content.py --source
→ [PASS] 10. 提审包不含调试探针页   未注册
→ [PASS] 11. ... notice.html 77255 B：许可全文齐、且等于当前 NOTICE+LICENSES/ 现场重生成的结果
→ 结果: 16/16 通过；阻断项未过 0 个
```

含义：上一份包唯一的红灯（⑪）在源码侧已经是绿的，**只要下次构建把当前 rawfile 打进包，
⑩/⑪ 都应转绿，预期 16/16**。注意源码级 9／9b 报的是 1024 源图、包内是 512（hvigor 重编码），
图标几何仍以包内实量为准（本文件上半节与 `h147-icon-w209-closure-0014.md`）。

