# third_party

This directory contains standalone, offline research and training code that is **not part of the main application runtime**.

It exists to support algorithm development, experimentation, and model training for the production system, but is intentionally separated from the software application layer.

---

## Overview

`third_party/` serves as a **research and training sandbox** for core computer vision algorithms used in the application, including:

- Face detection
- Facial landmark regression
- Glasses state classification

It is completely decoupled from the runtime application and is used exclusively for model development and experimentation.

---

## Key Characteristics

- Fully offline training environment
- Independent of production inference code
- May include third-party research repositories or adapted implementations
- Used for model experimentation, benchmarking, and validation
- Outputs are typically exported to formats such as ONNX for deployment

---

## Relationship to the Main Application

Models trained in this directory are typically exported to a format suitable for inference:

```

third_party/ (training & research)
↓
export (ONNX / other formats)
↓
main application (inference runtime)

```

The main application is designed for:

- Inference and deployment
- Model loading (e.g., ONNX models)
- User-facing functionality
- Real-time processing

In contrast, `third_party/` is:

- **Standalone**
- **Offline**
- **Research-oriented**
- **Training-focused**

Code in this directory is **not required for running the application** and should not be imported directly by production modules.

---

## Important Notes

- Do NOT assume code in this directory is production-safe or optimized.
- Dependencies in this folder may differ from the main application requirements.
- This directory may include experimental or unstable implementations.
- Only exported models (e.g., ONNX files) are intended for use in production.
