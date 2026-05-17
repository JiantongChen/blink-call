<div align="center">
  <img width="100" height="100" src="assets/icons/eye.png" alt="Blink Call icon"/>
  <h1><strong>Blink Call</strong></h1>
  <h3><em>A blink-based calling system for ALS patients, detecting custom blink patterns to trigger hands-free calls.</em></h3>
  <p><strong>English</strong> | <a href="README_zh-CN.md">简体中文</a></p>
</div>

<p align="center">
<img src="https://img.shields.io/badge/Python-3.10%2B-blue">
<img src="https://img.shields.io/badge/Platform-Linux%20%7C%20Windows-orange">
<img src="https://img.shields.io/badge/Type-CLI%20%7C%20GUI-green">
<img src="https://img.shields.io/badge/Status-Active-success">
<img src="https://img.shields.io/badge/License-Public-success">
</p>

## 📘 Overview
**Blink-Call** is an assistive calling system designed for ALS patients. It recognizes user-defined blink patterns from camera input and triggers visible and audio call alerts without requiring speech, hand movement, or physical touch.

### Key Features
- **Minimal interaction**: Only eye blinks are required.
- **Lightweight resource usage**: Runs in a CPU-only environment with less than 500 MB of memory usage.
- **User-friendly features**:
  - Customizable blink patterns, alert audio, volume, and duration.
  - Support for both local and remote camera modes for flexible deployment.
  - One-click model download and update support.
- **Logging and debugging options** for clinical use and algorithm improvement.

---

## ✨ For User
If you want to get started quickly, begin here:

- 📦 **Latest Release ZIP**: [Download the latest release](https://github.com/JiantongChen/blink-call/releases/latest)
- 📖 **User Guide**: *To be added*

> [!NOTE]
> Currently, the software is only available for direct download and use on Windows.

---

## 🔧 For Developer
This project includes developer documentation and setup guidance to help you get started quickly.

### 🚀 Quick Setup & Launch
- See [docs/installation.md](docs/installation.md) for the complete installation guide.
- Start the application:
  ```bash
  python -m blink_call.setup_app
  ```

### 🧭 Changing Model Files

This repository does not handle model training and ONNX model file replacement. Offline training resources for the related models can be found in the following repositories:

- Face Detection: [SCRFD](https://github.com/deepinsight/insightface/tree/master/detection/scrfd)
- 2D Face 106 Keypoint Detection: [SDUNets](https://github.com/deepinsight/insightface/tree/master/alignment/heatmap)
- Eye State Classification: [Project](https://github.com/Ole7755/ViTA)

After obtaining the corresponding ONNX model files, replace the files in the ModelScope model [repository](https://www.modelscope.cn/models/chenjiantong/blink_call_model_files/files).

> [!WARNING]
> Updating ONNX files in the ModelScope model repository will directly affect end users. Please do not modify them without caution.  
> When updating ONNX models, ensure that both file paths and filenames remain exactly the same.

### 📦 Building with Nuitka
After development is completed, the software can be built with Nuitka for standalone distribution. The Nuitka build command is shown below.
```powershell
nuitka ^
  --standalone ^
  --windows-console-mode=disable ^
  --windows-icon-from-ico=assets/icons/app_icon.ico ^
  --enable-plugin=pyside6 ^
  --include-data-file=VERSION=VERSION ^
  --include-data-file=LICENSE=LICENSE ^
  --include-data-dir=assets=assets ^
  --jobs=8 ^
  --output-filename=BlinkCall.exe ^
  blink_call/setup_app.py
```

---

## 📝 License
MIT License. See [LICENSE](LICENSE) for details.
