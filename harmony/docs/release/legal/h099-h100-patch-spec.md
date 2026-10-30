# H-099 / H-100 落地补丁说明（给 CodeArts，2026-10-22 19:8x · Qoder）

**只涉及两个文件**：`entry/src/main/ets/pages/LegalPage.ets`（3 行）与 `entry/src/main/ets/pages/AboutPage.ets`（加 1 个按钮 + 改 1 句 + 加 1 组条目）。
页面素材 `rawfile/legal/notice.html`（73,388 B，NOTICE 全文 + 11 份许可全文 + 目录锚点）已经就绪，**不要自己写**。

---

## 一、`LegalPage.ets`：让它能加载 `notice.html`

现在只认两档（实测行号）：

```ts
// 第 29 行附近
if (params !== undefined && params !== null && params.doc === 'terms') {
  this.doc = 'terms';
}
// 第 35-36 行
return this.doc === 'terms' ? 'resource://rawfile/legal/terms.html'
  : 'resource://rawfile/legal/privacy.html';
```

**改法**（保持现有两档行为不变，只增加第三档）：

```ts
// 第 29 行附近：把单条件改成白名单
const d = params?.doc;
if (d === 'terms' || d === 'notice') {
  this.doc = d;
}

// 第 35-36 行：用映射代替三元
private docUrl(): string {
  const map: Record<string, string> = {
    privacy: 'resource://rawfile/legal/privacy.html',
    terms:   'resource://rawfile/legal/terms.html',
    notice:  'resource://rawfile/legal/notice.html',
  };
  return map[this.doc] ?? map.privacy;
}
```

**注意**：顶栏那两个「隐私政策 / 用户协议」切换按钮在 `doc === 'notice'` 时应当**都不高亮**（现有三元会把它落到 privacy 的高亮态，
造成「正文是许可声明、按钮亮着隐私政策」的矛盾，正是 H-073 修过的那类问题）。把两处条件改成：
`this.doc === 'privacy'` / `this.doc === 'terms'` 已经是精确比较，**不用改**——只要确认没有 `!==` 的兜底分支即可。

---

## 二、`AboutPage.ets`：加按钮 + 改一句 + 加一组条目

### 2.1 「完整许可声明」按钮（替换第 353 行那句死指路）

现在（`:345-357`）：

```ts
Column({ space: 8 }) {
  Text('完整许可声明') ... .width('100%')
  Text('完整的第三方软件与数据许可声明请查看应用安装目录下的 NOTICE 文件及 LICENSES/ 目录。')
    .fontSize(14).fontColor('#1A1C1E').width('100%')
}
```

**改成**：

```ts
Column({ space: 8 }) {
  Text('完整许可声明')
    .fontSize(18).fontWeight(FontWeight.Bold).fontColor('#1A1C1E').width('100%')
  Text('本页下面是摘要；完整正文（NOTICE 与全部第三方许可全文）可在应用内直接阅读。')
    .fontSize(14).fontColor('#1A1C1E').width('100%')
  Button('查看完整许可声明')
    .fontSize(15).fontColor('#2B5FBF').backgroundColor('#FFFFFF')
    .borderRadius(8).width('100%').height(42)
    .onClick(() => {
      this.openLegal('notice');
    })
}
```

> `openLegal(doc)` 现有实现不用改，它把 `doc` 原样传给 `pages/LegalPage` 的 `LegalRouteParams`。

### 2.2 词库来源补 LGPL 主码表（H-100）

在 `:194-209` 那段 `rime-wubi86-jidian` **之后、`rime-pinyin-simp` 之前**插入一组：

```ts
// 86 五笔主码表（LGPL-3.0）——与上面的极点权重层分开列
Row({ space: 8 }) {
  Text('rime-wubi（86 五笔主码表）')
    .fontSize(14).fontWeight(FontWeight.Bold).fontColor('#1A1C1E').layoutWeight(1)
  Text('LGPL-3.0')
    .fontSize(12).fontColor('#2B5FBF')
}
.width('100%')
Text('五笔主码表本体；极点权重与补充词条见上一项（Apache-2.0）')
  .fontSize(12).fontColor('#8A8F99').width('100%')
```

**为什么必须分开列**：上一项 `rime-wubi86-jidian` 是 Apache-2.0 的**权重与补充词条层**；
主码表 `wubi86.dict.yaml`（2.29 MB，`rawfile/rime/` 下）是 **LGPL-3.0**。混成一项会让用户以为整个五笔码表是 Apache 的。

---

## 二·五、还有第三处：键盘内「关于」浮层（我第一版漏了）

`AboutPage.ets` 改完后我跑核验脚本，第 12 项仍然 FAIL。原因是**同一句话在第二个地方还有一份**：

```
entry/src/main/ets/pages/KeyboardIndex.ets:1282
        // 完整声明指引
        Text('完整许可声明请查看应用安装目录下的 NOTICE 文件。')
          .fontSize(12)
          .fontColor(FG_HINT)
          .width('100%')
```

这是键盘里长按 `?123` 弹出的 `AboutPanel()` 浮层（`showAbout`，`:1140` 方法、`:2088` 渲染），
不是 `AboutPage`。**两处都是用户真的会看到的**，必须一起改。

**改法**（保持浮层轻量，不塞长按钮）：

```ts
        // 完整声明指引（H-099：改成指向应用内可读的许可声明页）
        Text('完整许可声明：首页「关于」→「查看完整许可声明」')
          .fontSize(12)
          .fontColor(FG_HINT)
          .width('100%')
          .onClick(() => {
            this.showAbout = false;
            this.getUIContext().getRouter().pushUrl({
              url: 'pages/LegalPage',
              params: new LegalRouteParams('notice')
            });
          })
```

若嫌浮层里跳页突兀，**最小改法是只改文案**（不提「安装目录」），跳转留给首页「关于」页——
两种都接受，判据是包内 `modules.abc` 不再含「应用安装目录下的 NOTICE」。

---

## 三、验收（我做，你不用管）

出包后我跑 `python scripts/check_app_content.py`，其中三项专门盯这两单：

- 第 11 项：包里有 `rawfile/legal/notice.html` 且含 Apache / LGPL / MIT 全文；
- 第 12 项：`modules.abc` 里不再有「应用安装目录下的 NOTICE」——**这一项会同时扫 AboutPage 与 KeyboardIndex 的 AboutPanel**，两处都得改；
- 第 13 项：`modules.abc` 里有 `LGPL-3.0` 与「五笔主码表」。

三项全绿才算 H-099 / H-100 关闭。

---

## 四、不影响的东西

- **不需要 bump `DATA_VERSION`**：`rawfile/legal/` 不经过 Rime 释放清单（H-091 那个坑的边界就在这）。
- **不需要改 `SHARED_FILES`**：`rawfile` 整棵树进包。
- **不需要新增权限**：Web 只加载 `resource://rawfile/`，无网络请求。
