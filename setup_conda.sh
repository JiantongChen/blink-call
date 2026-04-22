#!/bin/bash
set -o pipefail

# Default environment name and project root path
ENV_NAME="blink_call"
PROJECT_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

# Parsing command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --name)
            if [[ -n "$2" ]]; then
                ENV_NAME="$2"
                shift 2
            else
                echo "❌ --name requires an argument"
                exit 1
            fi
            ;;
        *)
            echo "❌ Unknown argument: $1"
            exit 1
            ;;
    esac
done

# Initialize conda
if ! command -v conda &> /dev/null; then
    echo "❌ Conda is not installed or not in PATH"
    exit 1
fi

source $(conda info --base)/etc/profile.d/conda.sh

# Create the environment (skip if it already exists).
if conda info --envs | grep -q "^$ENV_NAME\s"; then
    echo "⚠️  Conda environment '$ENV_NAME' already exists. Skipping creation."
else
    echo "📦 Creating conda environment '$ENV_NAME' with Python 3.10..."
    conda create -y -n "$ENV_NAME" python=3.10 || {
        echo "❌ Failed to create conda environment '$ENV_NAME'" >&2
        exit 1
    }
fi

# Activate the environment
conda activate "$ENV_NAME"

# Install dependencies
echo -e "\n📦 Installing project dependencies..."

pip install --upgrade pip

cd "$PROJECT_ROOT"
pip install -e . || {
    echo -e "❌ \033[1;31mFailed to install blink_call dependencies\033[0m" >&2
    exit 1
}

echo -e "\n✅ Setup completed successfully in conda environment '$ENV_NAME'!"
echo -e "\n📌 To activate your environments, run:\nconda activate $ENV_NAME"
