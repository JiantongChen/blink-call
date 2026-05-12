<div align="center">

<img width="100" height="100" src="assets/icons/eye.png" alt="pencil-tip"/>

<h1><strong>Blink Call</strong></h1>

<h3><em>A blink-based calling system for ALS patients, detecting custom blink patterns to trigger hands-free calls.</em></h3>

</div>

<p align="center">
<a><img src="https://img.shields.io/badge/Python-3.10%2B-blue"></a>
<a><img src="https://img.shields.io/badge/Platform-Linux%20%7C%20Windows-orange"></a>
<a><img src="https://img.shields.io/badge/Type-CLI%20%7C%20GUI-green"></a>
<a><img src="https://img.shields.io/badge/Status-Active-success"></a>
<a><img src="https://img.shields.io/badge/License-Public-success"></a>
</p>

---

# 📘 Overview

**Blink-Call** is an assistive communication system designed for ALS patients, enabling hands-free emergency calling through customized blink pattern detection.

The system captures real-time video streams, performs lightweight blink recognition, and triggers a call signal when predefined eye-blink behaviors are detected. It is designed to run in low-interaction environments where users have limited or no motor or verbal capability.

---

# ✨ For User

## Model Assets

The runtime eye-state classifier uses an ONNX model file that is not stored in
Git because it is too large for normal repository storage. Download the model
asset from the project cloud drive and place it in the expected local path
before running blink detection.

See: **[`docs/model_assets.md`](docs/model_assets.md)**

---


# ✨ For Developer

## 🧭 Project Structure

```
./
├── assets/
│   ├── icons/
...
├── README.md
├── requirements.txt
├── setup_conda.sh*
├── setup.py
└── VERSION

```

## 🔧 Installation

See: **[`docs/installation.md`](docs/installation.md)**

## 🧠 Model Assets

See: **[`docs/model_assets.md`](docs/model_assets.md)** for the required ONNX
runtime model and optional training checkpoints.

---

## 🚀 Quick Start

### 📟 **Method 1 : Using Scripts (CLI Mode)**

### 🖥️ **Method 2 : Using the GUI Application**
