# privacy.html 文案同步单（Qoder 出文本 · CodeArts 落地）· 2026-10-22 15:4x

文件：`entry/src/main/resources/rawfile/legal/privacy.html`（按 M-072 该文件文本归 Qoder 维护，
但目录属 `entry/src/**` 且改 rawfile 需重建 ⇒ 本轮我不直接动手，文本在这里给你，随本轮一起构建）。

改动原因与实测依据：`docs/release/legal/claim-consistency-audit-2026-10-22.md` §一/§二。
一句话：**中英/简繁是引擎运行期状态，没有代码把它存进沙箱；应用内「设置」页 1.0.0 不上线（H-090），
所以隐私政策里凡是"设置"被说成本地保存的数据，都属描述与实际不一致。**

| 行 | 现在（要改掉） | 改成 |
|---|---|---|
| 82 | `…词库、用户词典、自造词与全部设置` | `…词库、用户词典与自造词` |
| 92 | `<h3>2. 用户词典、自造词与设置</h3>` | `<h3>2. 用户词典与自造词</h3>` |
| 94 | `<li>用户词典（LevelDB 格式）、自造词/自定义短语、中英文与简繁等设置，均保存在本应用沙箱内。</li>` | `<li>用户词典（LevelDB 格式）与自造词/自定义短语保存在本应用沙箱内。</li>`<br>`<li>中英文、简繁等输入模式是引擎的运行期状态，长按底栏布局键切换后立即生效，不另行保存为文件。</li>` |
| 132 | `<li><strong>保存期限</strong>：用户词典与设置会一直保存在本机，直到你清除应用数据或卸载应用。</li>` | `<li><strong>保存期限</strong>：用户词典与自造词会一直保存在本机，直到你清除应用数据或卸载应用。</li>` |

落地后要做的两件：

1. 与 md 母版逐字核对：`docs/release/legal/privacy-policy.md` §2（我已按同一口径改过，别改出第三种说法）；
   `terms.html` 无相关表述，**不用动**。
2. **这两份 html 不需要 bump `DATA_VERSION`**：`LegalPage` 直接渲染 rawfile，不走
   `RimeDataInstaller` 的 shared 目录复制（H-091 那个坑只影响 `rawfile/rime/`）。
