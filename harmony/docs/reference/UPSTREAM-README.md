# HarmonyOS NEXT Rime Engine (Pure Harmony)

全球首个将 Rime 输入法引擎完美移植至 HarmonyOS NEXT (纯血鸿蒙) 的高性能开源核心库。

## 🚀 架构概览
![系统架构图](docs/image_f94439.png)

## 核心技术价值
* **纯血鸿蒙底座**：原生支持 HarmonyOS NEXT，非兼容模式。
* **极速引擎**：深度优化交叉编译，集成 `liblua` 与 `OpenCC`，性能达瞬时响应。
* **高可拓展性**：提供标准 NAPI 桥接层，赋能开发者构建顶级输入法应用。

---

## 🌟 体验繁星不语输入法
本项目核心驱动了【繁星不语输入法】，欢迎前往华为应用市场体验完整功能：
[**点击此处前往华为应用市场下载【繁星不语输入法】**](https://appgallery.huawei.com/app/detail?id=com.fanxing.voice&channelId=SHARE&source=appshare)

---

## 如何集成 (Integration)

1. **编译模块**：
   在 DevEco Studio 中选择 `fanxing_rime_har` 模块，执行 `Build -> Make Module 'fanxing_rime_har'`。

2. **引用库文件**：
   获取编译产物 `fanxing_rime_har.har`（路径：`fanxing_rime_har/build/default/outputs/default/`），放置于目标工程的 `libs/` 目录下。

3. **配置依赖**：
   在目标项目的 `oh-package.json5` 中声明：
   
       "dependencies": {
         "fanxing_rime_har": "file:./libs/fanxing_rime_har.har"
       }

4. **初始化引擎**：
   通过 NAPI 接口 `initEngine` 传入沙盒路径完成引擎异步点火。

## 许可证 (License)
本项目采用 MIT 协议开源。这意味着您可以免费在个人或商业项目中使用本引擎，但请在项目代码中保留原作者的版权声明。
