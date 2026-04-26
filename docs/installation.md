# Installation on Linux/Windows

This guide will help you quickly set up the development environment for the **blink-call** project on Linux/Windows.

## 1. Clone the Repository
```bash
git clone https://github.com/JiantongChen/blink-call.git
cd blink-call
```

## 2. Install Dependencies

### 2.1 If Linux
```bash
# default conda environment name -> blink_call
./setup_conda.sh [--name]

conda activate blink-call
```

### 2.2 If Windows
```powershell
# Create Conda Environment
conda create -n blink_call python=3.10
conda activate blink_call
pip install --upgrade pip

# Install main project
pip install -e .
```

## 3. Install Git Hooks (Just for developer)

```bash
# Git hooks help ensure code formatting and checks before committing.
pre-commit install
```
