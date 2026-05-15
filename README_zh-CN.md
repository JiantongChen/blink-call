<div align="center">
  <img width="100" height="100" src="assets/icons/eye.png" alt="眨眼呼叫图标"/>
  <h1><strong>眨眼呼叫</strong></h1>
  <h3><em>一个面向渐冻症患者的眨眼呼叫系统：通过识别自定义眨眼模式，实现无需言语行动的呼叫。</em></h3>
  <p><a href="README.md">English</a> | <strong>简体中文</strong></p>
</div>

<p align="center">
<img src="https://img.shields.io/badge/Python-3.10%2B-blue">
<img src="https://img.shields.io/badge/Platform-Linux%20%7C%20Windows-orange">
<img src="https://img.shields.io/badge/Type-CLI%20%7C%20GUI-green">
<img src="https://img.shields.io/badge/Status-Active-success">
<img src="https://img.shields.io/badge/License-Public-success">
</p>

## 📘 概述
**Blink-Call** 是一个为 ALS（肌萎缩侧索硬化，俗称渐冻症）患者设计的辅助呼叫系统。它可以从摄像头输入中识别用户自定义的眨眼模式，并触发电脑扬声器（或者蓝牙设备）响铃提醒，期间无需说话、手部动作或物理接触。

### 核心特性
- **无需言语行动**：仅需通过眨眼即可操作。
- **轻量资源占用**：可在纯 CPU 环境运行，内存占用低于 500 MB。
- **用户友好**：
  - 支持自定义眨眼模式、提醒音频、音量与持续时间。
  - 同时支持本地摄像头与远程摄像头模式，部署更灵活。
  - 支持一键下载与更新模型。
- 提供**日志与调试选项**，便于现场查看使用与算法改进。

---

## ✨ 用户使用
如果你希望立刻使用软件，请从这里开始：

- 📦 **最新 Release ZIP**：[下载最新版本](https://github.com/JiantongChen/blink-call/releases/latest)
- 📖 **用户指南**：*待补充*

> [!NOTE]
> 当前仅有 Windows 操作系统的软件可直接下载并使用，。

---

## 🔧 开发者指南
本项目提供开发文档与环境配置说明，帮助你快速开始开发。

### 🚀 快速安装与启动
- 完整安装说明见 [docs/installation.md](docs/installation.md)。
- 启动应用：
  ```bash
  python -m blink_call.setup_app
  ```

### 🧭 更换模型文件

本仓库不负责模型训练与 ONNX 模型文件替换。相关模型的离线训练资源可在以下仓库中获取：

- 人脸检测：*待补充*
- 2D 人脸 106 关键点检测：*待补充*
- 眼睛状态分类：[项目地址](https://github.com/Ole7755/ViTA)

获取对应 ONNX 模型文件后，请替换该 ModelScope [模型库](https://www.modelscope.cn/models/chenjiantong/blink_call_model_files/files)中的文件。

> [!WARNING]
> 更新 ModelScope 模型仓库中的 ONNX 文件会直接影响所有用户，请谨慎修改。  
> 更新 ONNX 模型时，请确保文件路径和文件名保持完全一致。

### 📦 使用 Nuitka 打包
开发完成后，可使用 Nuitka 将软件打包为独立分发版本。命令如下：
```powershell
nuitka ^
  --standalone ^
  --windows-console-mode=disable ^
  --windows-icon-from-ico=assets/icons/app_icon.ico ^
  --enable-plugin=pyside6 ^
  --include-data-file=VERSION=VERSION ^
  --include-data-dir=LICENSE=LICENSE ^
  --include-data-dir=assets=assets ^
  --jobs=8 ^
  --output-filename=BlinkCall.exe ^
  blink_call/setup_app.py
```

---

## 📝 许可证
MIT License。详见 [LICENSE](LICENSE)。
