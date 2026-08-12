#!/bin/bash

set -Eeuo pipefail

# TVC Studio AI - Individual Model Installation Script
# Installs a specific model with its own Python virtual environment
# Usage: ./install-model.sh <model-name> [--flashattention]
# Example: ./install-model.sh fashn-vton --flashattention

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${SCRIPT_DIR}/.."

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
ENABLE_FLASHATTENTION=0
MODELS_CONFIG="${REPO_ROOT}/configs/models.yaml"

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

log_header() {
    echo ""
    echo -e "${BLUE}=== $* ===${NC}"
}

# Error handler
trap 'log_error "Installation failed at line $LINENO."' ERR

# Parse arguments
if [[ $# -lt 1 ]]; then
    log_error "Usage: $0 <model-name> [--flashattention]"
    echo ""
    echo "Available models:"
    echo "  - scail2"
    echo "  - wan22-animate"
    echo "  - fashn-vton"
    echo "  - qwen-image-edit"
    echo "  - birefnet"
    echo "  - ic-light"
    echo "  - seedvr2"
    echo "  - realesrgan"
    echo "  - codeformer"
    exit 1
fi

MODEL_NAME="$1"
shift || true

# Parse flags
while [[ $# -gt 0 ]]; do
    case "$1" in
        --flashattention)
            ENABLE_FLASHATTENTION=1
            shift
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

log_header "TVC Studio AI - Model Installation"
log_info "Model: $MODEL_NAME"

# Function to parse YAML value (simple parser)
parse_yaml_value() {
    local file=$1
    local section=$2
    local key=$3

    grep -A 100 "^  $section:" "$file" | \
        grep "    $key:" | \
        head -1 | \
        sed "s/.*: //" | \
        sed 's/"//g' | \
        sed "s/'//g" || echo ""
}

# Check if model exists in config
if ! grep -q "^  $MODEL_NAME:" "$MODELS_CONFIG"; then
    log_error "Model '$MODEL_NAME' not found in $MODELS_CONFIG"
    exit 1
fi

# Extract model configuration from models.yaml
REPO_URL=$(parse_yaml_value "$MODELS_CONFIG" "$MODEL_NAME" "repo_url")
INSTALL_DIR=$(parse_yaml_value "$MODELS_CONFIG" "$MODEL_NAME" "install_dir")
VENV_DIR=$(parse_yaml_value "$MODELS_CONFIG" "$MODEL_NAME" "venv_dir")
MIN_VRAM=$(parse_yaml_value "$MODELS_CONFIG" "$MODEL_NAME" "min_vram_gb")
PYTHON_VERSION=$(parse_yaml_value "$MODELS_CONFIG" "$MODEL_NAME" "python_version")

if [[ -z "$REPO_URL" ]]; then
    log_error "Could not parse configuration for model: $MODEL_NAME"
    exit 1
fi

log_info "Repository: $REPO_URL"
log_info "Install directory: $INSTALL_DIR"
log_info "Virtual environment: $VENV_DIR"
log_info "Minimum VRAM required: ${MIN_VRAM}GB"

# Check for GPU memory if available
if command -v nvidia-smi &> /dev/null; then
    AVAILABLE_VRAM=$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits | head -1)
    AVAILABLE_VRAM_GB=$((AVAILABLE_VRAM / 1024))
    log_info "Available GPU VRAM: ${AVAILABLE_VRAM_GB}GB"

    if [[ $AVAILABLE_VRAM_GB -lt $MIN_VRAM ]]; then
        log_warn "Available VRAM (${AVAILABLE_VRAM_GB}GB) is less than recommended (${MIN_VRAM}GB)"
        read -p "Continue anyway? (y/n): " continue_choice
        if [[ "$continue_choice" != "y" && "$continue_choice" != "Y" ]]; then
            log_error "Installation cancelled."
            exit 1
        fi
    fi
fi

# Step 1: Clone repository
log_header "Cloning Repository"

FULL_INSTALL_PATH="${REPO_ROOT}/${INSTALL_DIR}"

if [[ -d "$FULL_INSTALL_PATH" ]]; then
    log_warn "Directory $FULL_INSTALL_PATH already exists."
    read -p "Update existing repository? (y/n): " update_choice
    if [[ "$update_choice" == "y" || "$update_choice" == "Y" ]]; then
        log_info "Pulling latest changes..."
        cd "$FULL_INSTALL_PATH"
        git pull origin main || git pull || true
        cd "$REPO_ROOT"
    fi
else
    mkdir -p "$(dirname "$FULL_INSTALL_PATH")"
    log_info "Cloning from $REPO_URL..."
    git clone "$REPO_URL" "$FULL_INSTALL_PATH" || {
        log_error "Failed to clone repository."
        exit 1
    }
    log_info "Repository cloned successfully."
fi

# Step 2: Create virtual environment
log_header "Setting up Python Virtual Environment"

FULL_VENV_PATH="${REPO_ROOT}/${VENV_DIR}"

if [[ -d "$FULL_VENV_PATH" ]]; then
    log_warn "Virtual environment already exists at $FULL_VENV_PATH"
    read -p "Recreate venv? (y/n): " recreate_choice
    if [[ "$recreate_choice" == "y" || "$recreate_choice" == "Y" ]]; then
        log_info "Removing old venv..."
            [[ -n "$FULL_VENV_PATH" && "$FULL_VENV_PATH" == "$REPO_ROOT"/* && "$FULL_VENV_PATH" != "$REPO_ROOT" ]] || { log_error "Unsafe venv path: $FULL_VENV_PATH"; exit 1; }
        rm -rf "$FULL_VENV_PATH"
    else
        log_info "Using existing venv."
    fi
fi

if [[ ! -d "$FULL_VENV_PATH" ]]; then
    log_info "Creating Python $PYTHON_VERSION virtual environment..."
    python3 -m venv "$FULL_VENV_PATH" || {
        log_error "Failed to create virtual environment."
        exit 1
    }
    log_info "Virtual environment created."
fi

# Step 3: Activate venv and upgrade pip
log_header "Upgrading pip and setuptools"
source "${FULL_VENV_PATH}/bin/activate"

pip install --upgrade pip setuptools wheel -q 2>&1 | tail -1 || true
log_info "pip upgraded"

# Step 4: Install PyTorch
log_header "Installing PyTorch"
if command -v nvidia-smi &> /dev/null; then
    log_info "GPU detected. Installing CUDA-enabled PyTorch..."
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118 -q 2>&1 | tail -1
else
    log_warn "No GPU detected. Installing CPU-only PyTorch..."
    pip install torch torchvision torchaudio -q 2>&1 | tail -1
fi
log_info "PyTorch installed"

# Step 5: Install model requirements
log_header "Installing Model Dependencies"

if [[ -f "${FULL_INSTALL_PATH}/requirements.txt" ]]; then
    log_info "Installing requirements from $INSTALL_DIR/requirements.txt..."
    pip install -r "${FULL_INSTALL_PATH}/requirements.txt" -q 2>&1 | tail -1 || {
        log_warn "Some requirements failed to install. Continuing..."
    }
    log_info "Requirements installed"
else
    log_warn "No requirements.txt found in $INSTALL_DIR"
fi

# Step 6: Install FlashAttention if requested
log_header "Flash Attention Setup"
if [[ $ENABLE_FLASHATTENTION -eq 1 ]]; then
    log_info "Installing FlashAttention..."
    pip install flash-attn -q 2>&1 | tail -1 || {
        log_warn "FlashAttention installation failed. Continuing without it."
    }
    log_info "FlashAttention installation complete"
else
    log_info "FlashAttention not enabled. Set --flashattention flag to enable."
fi

# Step 7: Verify installation
log_header "Verifying Installation"

# Try importing torch
python -c "import torch; print(f'PyTorch version: {torch.__version__}')" && \
    log_info "✓ PyTorch verified" || \
    log_warn "PyTorch import failed"

# Try importing model-specific packages
case "$MODEL_NAME" in
    fashn-vton)
        python -c "import diffusers" 2>/dev/null && log_info "✓ Diffusers verified" || log_warn "Diffusers not found"
        ;;
    qwen-image-edit)
        python -c "import transformers" 2>/dev/null && log_info "✓ Transformers verified" || log_warn "Transformers not found"
        ;;
    realesrgan)
        python -c "import cv2" 2>/dev/null && log_info "✓ OpenCV verified" || log_warn "OpenCV not found"
        ;;
esac

deactivate

# Step 8: Create environment-specific activation script
log_header "Creating Activation Script"

ACTIVATE_SCRIPT="${REPO_ROOT}/activate-${MODEL_NAME}.sh"
cat > "$ACTIVATE_SCRIPT" << EOF
#!/bin/bash
# Activation script for $MODEL_NAME
source "\$(dirname "\${BASH_SOURCE[0]}")/${VENV_DIR}/bin/activate"
export TVC_ACTIVE_MODEL="$MODEL_NAME"
echo "Activated: $MODEL_NAME"
EOF

chmod +x "$ACTIVATE_SCRIPT"
log_info "Created activation script: $ACTIVATE_SCRIPT"

# Summary
log_header "Installation Complete"
log_info "Model: $MODEL_NAME"
log_info "Install directory: $FULL_INSTALL_PATH"
log_info "Virtual environment: $FULL_VENV_PATH"
echo ""
echo "Next steps:"
echo "1. Activate the environment:"
echo "   source $ACTIVATE_SCRIPT"
echo ""
echo "2. Download model weights:"
echo "   bash scripts/download-model.sh $MODEL_NAME"
echo ""
echo "3. Test the model (check documentation for specific commands)"
echo ""
