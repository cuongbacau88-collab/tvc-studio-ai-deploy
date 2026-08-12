#!/bin/bash

set -Eeuo pipefail

# TVC Studio AI - Preflight Checks Script
# Verifies GPU, CUDA, VRAM, RAM, disk space, and Python version

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Counters for warnings and errors
WARNINGS=0
ERRORS=0

log_info() {
    echo -e "${GREEN}✓${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}⚠${NC} $*"
    ((WARNINGS++)) || true
}

log_error() {
    echo -e "${RED}✗${NC} $*"
    ((ERRORS++)) || true
}

log_header() {
    echo ""
    echo -e "${BLUE}=== $* ===${NC}"
}

# Main checks
log_header "TVC Studio AI - Preflight System Checks"

# Check 1: Python Version
log_header "Python Version"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
    MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

    log_info "Python version: $PYTHON_VERSION"

    if [[ "$MAJOR" -lt 3 ]] || [[ "$MAJOR" -eq 3 && "$MINOR" -lt 10 ]]; then
        log_error "Python 3.10+ required, but found $PYTHON_VERSION"
    elif [[ "$MAJOR" -eq 3 && "$MINOR" -gt 13 ]]; then
        log_warn "Python $PYTHON_VERSION might not be fully tested with TVC Studio AI"
    else
        log_info "Python version is compatible"
    fi
else
    log_error "Python3 not found"
fi

# Check 2: NVIDIA GPU
log_header "NVIDIA GPU"
if command -v nvidia-smi &> /dev/null; then
    log_info "nvidia-smi found"

    GPU_COUNT=$(nvidia-smi --list-gpus | wc -l)
    log_info "Number of GPUs detected: $GPU_COUNT"

    # Multi-GPU readiness
    if [[ $GPU_COUNT -gt 1 ]]; then
        log_info "Multi-GPU system detected (FSDP + Ulysses support available)"
    fi

    # Get GPU details
    nvidia-smi --query-gpu=name,memory.total,driver_version,compute_cap \
        --format=csv,noheader,nounits | while IFS=',' read -r name memory driver compute; do
        log_info "GPU: $name | VRAM: ${memory%.*} MB | Driver: $driver | Compute: $compute"
    done

    # Check VRAM
    log_header "GPU Memory"
    TOTAL_VRAM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | awk '{sum+=$1} END {print sum}')
    AVAILABLE_VRAM=$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits | awk '{sum+=$1} END {print sum}')

    log_info "Total VRAM: $((TOTAL_VRAM / 1024)) GB"
    log_info "Available VRAM: $((AVAILABLE_VRAM / 1024)) GB"

    if [[ $TOTAL_VRAM -lt 6144 ]]; then
        log_warn "Total VRAM is less than 6GB. Performance may be degraded."
    fi

    if [[ $AVAILABLE_VRAM -lt 4096 ]]; then
        log_warn "Available VRAM is less than 4GB. Some models may not run."
    fi
else
    log_warn "nvidia-smi not found. GPU support not available."
    log_warn "Install NVIDIA driver and CUDA Toolkit for GPU acceleration."
fi

# Check 3: CUDA
log_header "CUDA Toolkit & PyTorch"
if command -v nvcc &> /dev/null; then
    CUDA_VERSION=$(nvcc --version | grep -oP 'release \K[0-9.]+' || echo "unknown")
    log_info "CUDA Toolkit version: $CUDA_VERSION"
else
    log_warn "CUDA Toolkit (nvcc) not found. This is optional but recommended."
fi

# Check PyTorch CUDA compatibility
if python3 -c "import torch" 2>/dev/null; then
    TORCH_CUDA=$(python3 -c "import torch; print(torch.version.cuda)" 2>/dev/null || echo "None")
    TORCH_VERSION=$(python3 -c "import torch; print(torch.__version__)" 2>/dev/null || echo "unknown")
    log_info "PyTorch installed: $TORCH_VERSION (CUDA: $TORCH_CUDA)"

    # Check if CUDA versions match
    if [[ "$CUDA_VERSION" != "unknown" ]] && [[ "$TORCH_CUDA" != "None" ]]; then
        SYSTEM_CUDA_MAJOR=$(echo "$CUDA_VERSION" | cut -d. -f1)
        TORCH_CUDA_MAJOR=$(echo "$TORCH_CUDA" | cut -d. -f1)
        if [[ "$SYSTEM_CUDA_MAJOR" != "$TORCH_CUDA_MAJOR" ]]; then
            log_warn "CUDA version mismatch: PyTorch ($TORCH_CUDA) vs System ($CUDA_VERSION)"
        else
            log_info "CUDA versions compatible"
        fi
    fi
else
    log_info "PyTorch not yet installed (will be installed during setup)"
fi

# Check 4: System RAM
log_header "System Memory"
if [[ -f /proc/meminfo ]]; then
    TOTAL_RAM=$(grep MemTotal /proc/meminfo | awk '{print $2}')
    AVAILABLE_RAM=$(grep MemAvailable /proc/meminfo | awk '{print $2}')

    log_info "Total RAM: $((TOTAL_RAM / 1024 / 1024)) GB"
    log_info "Available RAM: $((AVAILABLE_RAM / 1024 / 1024)) GB"

    if [[ $TOTAL_RAM -lt 8388608 ]]; then
        log_warn "Total RAM is less than 8GB. Consider upgrading for better performance."
    fi

    if [[ $AVAILABLE_RAM -lt 4194304 ]]; then
        log_warn "Available RAM is less than 4GB. Close other applications or optimize system."
    fi
else
    log_warn "Could not read memory information from /proc/meminfo"
fi

# Check 5: Disk Space
log_header "Disk Space"
REPO_DIR="${SCRIPT_DIR}/.."
if [[ -d "$REPO_DIR" ]]; then
    DISK_AVAILABLE=$(df "$REPO_DIR" | tail -1 | awk '{print $4}')
    DISK_USED=$(df "$REPO_DIR" | tail -1 | awk '{print $3}')
    DISK_TOTAL=$(df "$REPO_DIR" | tail -1 | awk '{print $2}')
    DISK_PERCENT=$(df "$REPO_DIR" | tail -1 | awk '{print $5}' | sed 's/%//')

    log_info "Filesystem: $(df "$REPO_DIR" | tail -1 | awk '{print $1}')"
    log_info "Total: $((DISK_TOTAL / 1024 / 1024)) GB"
    log_info "Used: $((DISK_USED / 1024 / 1024)) GB"
    log_info "Available: $((DISK_AVAILABLE / 1024 / 1024)) GB"
    log_info "Usage: ${DISK_PERCENT}%"

    if [[ $DISK_AVAILABLE -lt 104857600 ]]; then
        log_error "Disk space is critically low (< 100GB available). Models require significant space."
    elif [[ $DISK_AVAILABLE -lt 52428800 ]]; then
        log_warn "Available disk space is less than 50GB. Models may not fit."
    fi

    if [[ $DISK_PERCENT -gt 80 ]]; then
        log_warn "Disk usage is above 80%. Consider cleaning up."
    fi
else
    log_warn "Repository directory not found: $REPO_DIR"
fi

# Check 6: System Information
log_header "System Information"
if [[ -f /etc/os-release ]]; then
    source /etc/os-release
    log_info "OS: $PRETTY_NAME"

    if [[ "$ID" != "ubuntu" ]]; then
        log_warn "This script is optimized for Ubuntu 22.04/24.04. Your OS is: $PRETTY_NAME"
    fi
else
    log_warn "Could not read OS information"
fi

KERNEL_VERSION=$(uname -r)
log_info "Kernel: $KERNEL_VERSION"

# Check 7: Required tools
log_header "Required Tools"
REQUIRED_TOOLS=("git" "wget" "curl" "gcc" "make")
for tool in "${REQUIRED_TOOLS[@]}"; do
    if command -v "$tool" &> /dev/null; then
        VERSION=$("$tool" --version 2>&1 | head -1 | grep -oP '[\d.]+' | head -1 || echo "unknown")
        log_info "$tool: found (version: $VERSION)"
    else
        log_error "$tool: not found"
    fi
done

# Check 8: Network connectivity
log_header "Network Connectivity"
if timeout 2 curl -s https://www.google.com &> /dev/null || \
   timeout 2 curl -s https://huggingface.co &> /dev/null; then
    log_info "Internet connectivity: OK"
else
    log_warn "Could not verify internet connectivity. You may not be able to download models."
fi

# Summary
log_header "Preflight Check Summary"
if [[ $ERRORS -eq 0 ]]; then
    log_info "No critical errors found. System is ready for installation!"
    echo ""
    if [[ $WARNINGS -gt 0 ]]; then
        echo -e "${YELLOW}Warnings: $WARNINGS${NC}"
        echo "Please review the warnings above and consider the recommendations."
    fi
    exit 0
else
    echo ""
    echo -e "${RED}Errors: $ERRORS${NC}"
    if [[ $WARNINGS -gt 0 ]]; then
        echo -e "${YELLOW}Warnings: $WARNINGS${NC}"
    fi
    echo ""
    echo "Please fix the errors above before proceeding with installation."
    exit 1
fi
