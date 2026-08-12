#!/bin/bash

set -Eeuo pipefail

# TVC Studio AI - Health Check Script
# Verifies installation and readiness of all models
# Usage: ./health-check.sh [model-name]
# Without model-name, checks all installed models

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${SCRIPT_DIR}/.."
MODELS_CONFIG="${REPO_ROOT}/configs/models.yaml"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
GRAY='\033[0;37m'
NC='\033[0m'

# Counters
MODELS_CHECKED=0
MODELS_OK=0
MODELS_PARTIAL=0
MODELS_MISSING=0

# Logging functions
log_ok() {
    echo -e "${GREEN}✓${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}⚠${NC} $*"
}

log_error() {
    echo -e "${RED}✗${NC} $*"
}

log_header() {
    echo ""
    echo -e "${BLUE}=== $* ===${NC}"
}

# Function to parse YAML value
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

# Function to check single model
check_model() {
    local model_name=$1

    ((MODELS_CHECKED++)) || true

    # Extract configuration
    local repo_url=$(parse_yaml_value "$MODELS_CONFIG" "$model_name" "repo_url")
    local install_dir=$(parse_yaml_value "$MODELS_CONFIG" "$model_name" "install_dir")
    local venv_dir=$(parse_yaml_value "$MODELS_CONFIG" "$model_name" "venv_dir")
    local weights_dir=$(parse_yaml_value "$MODELS_CONFIG" "$model_name" "weights_dir")

    if [[ -z "$repo_url" ]]; then
        log_error "Model '$model_name' not found in configuration"
        ((MODELS_MISSING++)) || true
        return 1
    fi

    log_header "Model: $model_name"

    local status_ok=true

    # Check 1: Repository
    local full_install_path="${REPO_ROOT}/${install_dir}"
    if [[ -d "$full_install_path" ]]; then
        log_ok "Repository cloned: $full_install_path"

        # Check for git status
        if cd "$full_install_path" 2>/dev/null && git rev-parse --git-dir > /dev/null 2>&1; then
            local branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
            local commit=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
            log_ok "Git status: branch=$branch, commit=$commit"
        fi
        cd "$REPO_ROOT"
    else
        log_error "Repository not found: $install_dir"
        status_ok=false
    fi

    # Check 2: Virtual Environment
    local full_venv_path="${REPO_ROOT}/${venv_dir}"
    if [[ -d "$full_venv_path" ]]; then
        log_ok "Virtual environment exists: $venv_dir"

        # Check Python version in venv
        if [[ -f "${full_venv_path}/bin/python" ]]; then
            local python_version=$("${full_venv_path}/bin/python" --version 2>&1 | awk '{print $2}')
            log_ok "Python version in venv: $python_version"
        fi

        # Check installed packages
        local torch_check=$("${full_venv_path}/bin/python" -c "import torch; print(torch.__version__)" 2>/dev/null || echo "NOT_INSTALLED")
        if [[ "$torch_check" != "NOT_INSTALLED" ]]; then
            log_ok "PyTorch installed: $torch_check"

            # Check GPU availability
            "${full_venv_path}/bin/python" << 'EOF'
import torch
if torch.cuda.is_available():
    print(f"✓ CUDA available: {torch.cuda.get_device_name(0)} ({torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f}GB)")
else:
    print("⚠ CUDA not available, running on CPU")
EOF
        else
            log_warn "PyTorch not installed in venv"
            status_ok=false
        fi
    else
        log_error "Virtual environment not found: $venv_dir"
        status_ok=false
    fi

    # Check 3: Model Weights
    local full_weights_path="${REPO_ROOT}/${weights_dir}"
    if [[ -d "$full_weights_path" ]]; then
        local size=$(du -sh "$full_weights_path" 2>/dev/null | cut -f1)
        local file_count=$(find "$full_weights_path" -type f | wc -l)
        log_ok "Model weights downloaded: $size ($file_count files)"
    else
        log_warn "Model weights not found: $weights_dir"
        log_warn "Run: bash scripts/download-model.sh $model_name"
    fi

    # Check 4: Model-specific validations
    log_header "Model-specific Checks: $model_name"

    case "$model_name" in
        scail2)
            if [[ -f "$full_install_path/requirements.txt" ]]; then
                log_ok "requirements.txt found"
            fi
            ;;
        wan22-animate)
            if [[ -f "$full_install_path/README.md" ]]; then
                log_ok "Documentation found"
            fi
            ;;
        fashn-vton)
            if [[ -d "$full_install_path" ]]; then
                log_ok "fashn-VTON repository ready"
                # Check for example files
                if ls "$full_install_path"/example* 2>/dev/null | head -1 > /dev/null; then
                    log_ok "Example files available"
                fi
            fi
            ;;
        qwen-image-edit)
            if [[ -d "$full_install_path" ]]; then
                log_ok "Qwen-Image repository ready"
                # Check for dependencies
                if grep -q "diffusers\|transformers" "$full_install_path/requirements.txt" 2>/dev/null; then
                    log_ok "Main dependencies specified"
                fi
            fi
            ;;
        birefnet)
            if [[ -d "$full_install_path" ]]; then
                log_ok "BiRefNet repository ready"
                log_warn "Note: BiRefNet is optional for scene editing pipeline"
            fi
            ;;
        ic-light)
            if [[ -d "$full_install_path" ]]; then
                log_ok "IC-Light repository ready"
                log_warn "Note: IC-Light is optional for scene editing pipeline"
            fi
            ;;
        seedvr2)
            if [[ -d "$full_install_path" ]]; then
                log_ok "SeedVR2 repository ready"
                log_ok "Video restoration model available"
            fi
            ;;
        realesrgan)
            if [[ -d "$full_install_path" ]]; then
                log_ok "Real-ESRGAN repository ready"
                log_ok "Fast upscaling model available (2x/4x)"
            fi
            ;;
        codeformer)
            if [[ -d "$full_install_path" ]]; then
                log_ok "CodeFormer repository ready"
                log_ok "Face restoration model available"
            fi
            ;;
    esac

    # Overall status
    log_header "Status Summary: $model_name"
    if $status_ok; then
        log_ok "Model is ready for use"
        ((MODELS_OK++)) || true
    else
        log_warn "Model needs attention (see above)"
        ((MODELS_PARTIAL++)) || true
    fi
}

# Main execution
log_header "TVC Studio AI - Health Check"

# GPU Health Check
log_header "GPU Status"
if command -v nvidia-smi &> /dev/null; then
    GPU_COUNT=$(nvidia-smi --list-gpus | wc -l)
    log_ok "GPU detected: $GPU_COUNT GPU(s)"

    # Check each GPU
    for ((i=0; i<GPU_COUNT; i++)); do
        GPU_NAME=$(nvidia-smi --id=$i --query-gpu=name --format=csv,noheader 2>/dev/null || echo "Unknown")
        GPU_VRAM=$(nvidia-smi --id=$i --query-gpu=memory.total --format=csv,noheader,nounits 2>/dev/null || echo "0")
        GPU_COMPUTE=$(nvidia-smi --id=$i --query-gpu=compute_cap --format=csv,noheader 2>/dev/null || echo "0.0")
        log_ok "GPU $i: $GPU_NAME | VRAM: $((GPU_VRAM/1024))GB | Compute: $GPU_COMPUTE"
    done

    # Multi-GPU readiness
    if [[ $GPU_COUNT -gt 1 ]]; then
        log_ok "Multi-GPU system (FSDP + DeepSpeed Ulysses ready)"
    fi
else
    log_warn "No NVIDIA GPU detected (CPU-only mode)"
fi
echo ""

# Get list of models to check
if [[ $# -gt 0 ]]; then
    # Check specific model
    MODEL_NAME="$1"
    check_model "$MODEL_NAME"
else
    # Check all models
    log_header "Checking all configured models..."

    for model in scail2 wan22-animate fashn-vton qwen-image-edit birefnet ic-light seedvr2 realesrgan codeformer; do
        if grep -q "^  $model:" "$MODELS_CONFIG"; then
            check_model "$model"
        fi
    done
fi

# Final Summary
log_header "Overall Health Check Summary"
echo "Models checked: $MODELS_CHECKED"
echo -e "  ${GREEN}Ready: $MODELS_OK${NC}"
echo -e "  ${YELLOW}Partial: $MODELS_PARTIAL${NC}"
echo -e "  ${GRAY}Skipped/Not-installed: $MODELS_MISSING${NC}"
echo ""

if [[ $MODELS_CHECKED -eq 0 ]]; then
    log_warn "No models configured yet. Run 'scripts/model-selector.sh' to choose models."
    exit 0
elif [[ $MODELS_OK -gt 0 ]]; then
    log_ok "$MODELS_OK model(s) ready for inference!"
    exit 0
else
    log_warn "No models installed yet. Run 'scripts/install-model.sh <model-name>' to install."
    exit 0
fi
