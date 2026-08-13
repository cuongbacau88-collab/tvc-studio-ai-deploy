# TVC Studio AI - Deployment Repository

Deployment automation and setup scripts for **TVC Studio AI**, a comprehensive AI platform integrating:

**Core Video Generation:**
- **SCAIL-2** (zai-org/SCAIL-2): Semantic control for image-to-video synthesis
- **Wan2.2** (Wan-AI/Wan2.2-Animate-14B): Advanced video generation and animation

**Image Services:**
- **Fashn Virtual Try-On 1.5**: Virtual clothing try-on
- **Qwen-Image-Edit-2511**: Scene and background editing with optional BiRefNet & IC-Light pipeline
- **SeedVR2**: High-quality video restoration
- **Real-ESRGAN**: Fast 2x/4x image upscaling
- **CodeFormer**: Blind face restoration with identity preservation

This repository provides a complete installation framework for Ubuntu 22.04 and 24.04, with automatic GPU detection, isolated Python environments per model, and safe model downloading. Each model runs in its own virtual environment to avoid conflicts.

---

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Quick Start](#quick-start)
3. [Installation Steps](#installation-steps)
4. [Core Models Installation](#core-models-installation-scail-2-wan22)
5. [Optional AI Services](#optional-ai-services)
6. [Configuration](#configuration)
7. [Model Management](#model-management)
8. [System Verification](#system-verification)
9. [Troubleshooting](#troubleshooting)
10. [Repository Structure](#repository-structure)
11. [Updating Models](#updating-models)
12. [Advanced Pipelines](#advanced-pipelines)

---

## System Requirements

### Hardware Minimum
- **GPU**: NVIDIA GPU with compute capability 7.0+ (RTX 2070 or better)
- **VRAM**: 6GB GPU memory (8GB+ recommended)
- **RAM**: 8GB system memory (16GB+ recommended)
- **Storage**: 100GB+ free disk space for models and working data

### Operating System
- Ubuntu 22.04 LTS or Ubuntu 24.04 LTS
- Other Linux distributions may work but are not officially supported

### Software Requirements
- Python 3.10 or 3.11 (3.12+ not tested)
- NVIDIA Driver 520+
- CUDA Toolkit 11.8+ (optional but recommended)
- Git

---

## Quick Start

### Step 1: Clone This Repository
```bash
git clone https://github.com/your-org/tvc-studio-ai-deploy.git
cd tvc-studio-ai-deploy
```

### Step 2: Run Preflight Checks
```bash
bash scripts/preflight.sh
```
This verifies your system has the necessary hardware and software.

### Step 3: Install TVC Studio AI
```bash
bash install.sh
```
The installation script will:
- Check system requirements
- Install system dependencies
- Clone SCAIL-2 and Wan2.2 repositories
- Create isolated Python virtual environments
- Install PyTorch and dependencies
- Generate `.env` configuration file

### Step 4: Download Models (Optional)
```bash
# Activate appropriate environment first
source venv/scail2/bin/activate
# or
source venv/wan22/bin/activate

# Run model downloader
bash scripts/download-models.sh
```

### Step 5: Verify Installation
```bash
bash scripts/preflight.sh
```
Run this again to confirm all components are working.

---

## Core Models Installation (SCAIL-2, Wan2.2)

The `install.sh` script installs the core video generation models: SCAIL-2 and Wan2.2-Animate-14B with their own isolated Python environments.

No additional action needed for core models after running `install.sh`.

---

## Optional AI Services

After core installation, you can add specialized AI services for image editing, enhancement, and restoration:

### A. Virtual Try-On (Clothing)
```bash
# Install Fashn Virtual Try-On 1.5
bash scripts/install-model.sh fashn-vton

# Download weights
bash scripts/download-model.sh fashn-vton

# Verify installation
bash scripts/health-check.sh fashn-vton
```

### B. Scene & Background Editing
```bash
# Basic: Qwen-Image-Edit only
bash scripts/install-model.sh qwen-image-edit
bash scripts/download-model.sh qwen-image-edit

# Advanced: With background removal and lighting sync
bash scripts/install-model.sh qwen-image-edit
bash scripts/install-model.sh birefnet
bash scripts/install-model.sh ic-light
bash scripts/download-model.sh qwen-image-edit
bash scripts/download-model.sh birefnet
bash scripts/download-model.sh ic-light
```

### C. Image & Video Enhancement

```bash
# High-quality video restoration
bash scripts/install-model.sh seedvr2
bash scripts/download-model.sh seedvr2

# Fast 2x/4x upscaling
bash scripts/install-model.sh realesrgan
bash scripts/download-model.sh realesrgan

# Face restoration
bash scripts/install-model.sh codeformer
bash scripts/download-model.sh codeformer
```

### Health Check All Services
```bash
# Check all models
bash scripts/health-check.sh

# Check specific model
bash scripts/health-check.sh fashn-vton
bash scripts/health-check.sh qwen-image-edit
bash scripts/health-check.sh seedvr2
bash scripts/health-check.sh realesrgan
bash scripts/health-check.sh codeformer
```

---

## Installation Steps

### Detailed Installation Process

#### 1. System Preparation
```bash
# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install NVIDIA drivers if not present
sudo apt-get install -y nvidia-driver-535
sudo nvidia-smi  # Verify installation
```

#### 2. Clone and Install
```bash
# Set environment variables (optional)
export PYTHON_VERSION=3.11
export ALLOW_FLASHATTENTION=1  # Set to 1 to enable FlashAttention

# Run installation
bash install.sh
```

#### 3. Configuration
```bash
# Copy and customize environment file
cp .env.example .env
nano .env  # Edit with your settings
```

#### 4. Model Download
```bash
# Load preflight before downloading to ensure connectivity
bash scripts/preflight.sh

# Download models interactively
bash scripts/download-models.sh
```

### Environment Variables

#### Installation-Time Variables
- `PYTHON_VERSION`: Python version to use (default: 3.11)
- `ALLOW_FLASHATTENTION`: Enable FlashAttention (0 or 1, default: 0)

#### Runtime Variables (in `.env` file)
- `MODELS_DIR`: Directory for model downloads
- `SCAIL2_MODEL_PATH`: Path to SCAIL-2 model
- `WAN22_MODEL_PATH`: Path to Wan2.2 model
- `OUTPUT_DIR`: Output directory for generated videos
- `GPU_INDEX`: GPU index to use (0, 1, etc.)

---

## Configuration

### .env File

Copy `.env.example` to `.env` and customize:

```bash
cp .env.example .env
```

**Important**: Never commit `.env` to version control. It's already listed in `.gitignore`.

### Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `PYTHON_VERSION` | 3.11 | Python version for venv |
| `ALLOW_FLASHATTENTION` | 0 | Enable optimized attention (experimental) |
| `MODELS_DIR` | ./models | Model storage directory |
| `OUTPUT_DIR` | ./outputs | Output directory for results |
| `GPU_INDEX` | 0 | GPU device index to use |
| `AUTO_LOAD_MODELS` | false | Auto-load models on startup |
| `LOG_LEVEL` | INFO | Logging verbosity |

### Advanced Configuration

For CUDA-specific settings:
```bash
# In .env or shell
export CUDA_VISIBLE_DEVICES=0
export CUDA_LAUNCH_BLOCKING=1
```

For multiple GPUs:
```bash
export CUDA_VISIBLE_DEVICES=0,1  # Use GPUs 0 and 1
```

---

## Model Management

### Automatic Model Download

Use the interactive model downloader:
```bash
bash scripts/download-models.sh
```

Menu options:
1. **SCAIL-2**: Download SCAIL-2 model (~2-4 GB)
2. **Wan2.2-Animate-14B**: Download Wan2.2 model (~28 GB)
3. **Both**: Download both models sequentially
4. **Exit**: Cancel

### Manual Model Download

If the automatic downloader fails, download manually:

```bash
# Using huggingface-cli
huggingface-cli download zai-org/SCAIL-2 --repo-type model --local-dir ./models/scail2

huggingface-cli download Wan-AI/Wan2.2-Animate-14B --repo-type model --local-dir ./models/wan22-animate
```

### Model Paths

After downloading, verify paths in `.env`:
- SCAIL-2: `./models/scail2`
- Wan2.2: `./models/wan22-animate`

---

## System Verification

### Preflight Checks

The `preflight.sh` script verifies:

✓ Python version (3.10+)
✓ NVIDIA GPU presence and capability
✓ CUDA Toolkit installation
✓ System RAM and VRAM
✓ Disk space availability
✓ Required system tools
✓ Network connectivity

**Run anytime:**
```bash
bash scripts/preflight.sh
```

### Typical Output
```
=== TVC Studio AI - Preflight System Checks ===

=== Python Version ===
✓ Python version: 3.11.5
  Python version is compatible

=== NVIDIA GPU ===
✓ nvidia-smi found
✓ Number of GPUs detected: 1
✓ GPU: NVIDIA RTX 3090 | VRAM: 24576 MB | Driver: 535.104.05 | Compute: 8.6

...

=== Preflight Check Summary ===
✓ No critical errors found. System is ready for installation!
```

### Common Issues

| Issue | Solution |
|-------|----------|
| `nvidia-smi not found` | Install NVIDIA driver: `sudo apt-get install nvidia-driver-535` |
| `Python 3.10+ not found` | Install: `sudo apt-get install python3.11` |
| `Insufficient disk space` | Free up space or use external storage |
| `Low VRAM warning` | Use smaller batch sizes or optimize model loading |

---

## Troubleshooting

### Installation Issues

#### Error: "Failed to clone repository"
```bash
# Check git and network
git clone https://github.com/zai-org/SCAIL-2.git
# If SSL errors occur, try:
git config --global http.sslVerify false
```

#### Error: "Python module not found"
```bash
# Verify venv is activated
source venv/scail2/bin/activate
# Reinstall dependencies
pip install -r ../repos/SCAIL-2/requirements.txt
```

#### Error: "CUDA out of memory"
```bash
# Reduce batch size in .env
BATCH_SIZE=1

# Or enable CPU mode (if supported)
CUDA_VISIBLE_DEVICES=  # Empty disables GPU
```

### GPU Issues

#### GPU not detected
```bash
# Check NVIDIA drivers
nvidia-smi

# If not found, install drivers
sudo apt-get install nvidia-driver-535
sudo reboot
```

#### CUDA version mismatch
```bash
# Check installed CUDA
nvcc --version

# Check PyTorch CUDA compatibility
python -c "import torch; print(torch.__version__)"
```

### Model Download Issues

#### Timeout downloading large models
```bash
# Resume interrupted download (automatic retry)
bash scripts/download-models.sh

# For Hugging Face CLI with resume
huggingface-cli download --resume-download ...
```

#### Authentication required
```bash
# Set Hugging Face token (for private models)
export HF_TOKEN="YOUR_HUGGING_FACE_TOKEN"
bash scripts/download-models.sh
```

### Disk Space Issues

#### Insufficient space for models
```bash
# Check available space
df -h

# Clean up old models
rm -ri -- ./models/old-model

# Use external storage
mkdir /mnt/external/models
ln -s /mnt/external/models ./models
```

---

## Repository Structure

```
tvc-studio-ai-deploy/
├── install.sh                  # Main installation script
├── .env.example               # Environment configuration template
├── .gitignore                 # Git ignore rules
├── README.md                  # This file
├── scripts/
│   ├── preflight.sh           # System verification checks
│   └── download-models.sh     # Interactive model downloader
├── configs/                   # Configuration files (future)
├── workflows/                 # Workflow definitions (future)
├── repos/                     # Cloned source repositories
│   ├── SCAIL-2/               # SCAIL-2 source (cloned during install)
│   └── Wan2.2/                # Wan2.2 source (cloned during install)
├── venv/                      # Python virtual environments
│   ├── scail2/                # SCAIL-2 venv
│   └── wan22/                 # Wan2.2 venv
├── models/                    # Downloaded model weights
│   ├── scail2/
│   └── wan22-animate/
├── outputs/                   # Generated results
├── logs/                      # Application logs
└── weights/                   # Additional weights storage
```

**Important**:
- `.env` file is created during installation (not in repo)
- `repos/`, `venv/`, `models/`, `outputs/` are in `.gitignore`
- Do not commit model files, weights, or personal configuration

---

## Updating Models

### Update Model Repositories

After initial installation, update source repositories:

```bash
# Update SCAIL-2
cd repos/SCAIL-2
git pull origin main
cd ../..

# Update Wan2.2
cd repos/Wan2.2
git pull origin main
cd ../..
```

### Download Updated Model Weights

New model versions are released on Hugging Face:

```bash
# Re-run download script
bash scripts/download-models.sh

# Select the models to update (will overwrite if directory exists)
```

### Backup Old Models

Before updating, backup existing models:

```bash
# Backup SCAIL-2
mv models/scail2 models/scail2.backup

# Download new version
bash scripts/download-models.sh

# If issues occur, restore backup
mv models/scail2.backup models/scail2
```

---

## Advanced Usage

### Custom Model Paths

Modify `.env` to use custom paths:
```bash
SCAIL2_MODEL_PATH=/custom/path/to/scail2
WAN22_MODEL_PATH=/custom/path/to/wan22-animate
```

### Disable FlashAttention

By default, FlashAttention installation is skipped. To enable:

```bash
# During installation
ALLOW_FLASHATTENTION=1 bash install.sh

# Or manually install
source venv/scail2/bin/activate
pip install flash-attn
```

### Multi-GPU Setup

Configure for multiple GPUs:

```bash
# In .env
CUDA_VISIBLE_DEVICES=0,1,2,3
GPU_INDEX=0  # Primary GPU for coordination
```

### Monitoring Installation

Monitor the installation progress in real-time:

```bash
# In another terminal
tail -f install.log

# (This requires modification of install.sh to log output)
```

---

## Support and Contribution

### Reporting Issues

If you encounter problems:

1. Run `bash scripts/preflight.sh` to collect diagnostics
2. Check the troubleshooting section above
3. Review installation logs for error messages
4. Create an issue with:
   - System specs (GPU, RAM, OS version)
   - Preflight output
   - Error messages and logs

### Contributing

Improvements welcome! To contribute:

1. Test your changes on Ubuntu 22.04/24.04
2. Ensure scripts have `set -Eeuo pipefail`
3. Add error handling and helpful messages
4. Update this README with any new features

---

## License

This deployment repository is provided as-is. Please refer to the licenses of SCAIL-2 and Wan2.2 for their respective terms.

---

## Resources

### Model Documentation
- [SCAIL-2 GitHub](https://github.com/zai-org/SCAIL-2)
- [Wan2.2 GitHub](https://github.com/Wan-Video/Wan2.2)
- [Hugging Face SCAIL-2](https://huggingface.co/zai-org/SCAIL-2)
- [Hugging Face Wan2.2](https://huggingface.co/Wan-AI/Wan2.2-Animate-14B)

### System Resources
- [NVIDIA CUDA Installation Guide](https://docs.nvidia.com/cuda/cuda-installation-guide-linux/)
- [PyTorch Installation](https://pytorch.org/get-started/locally/)
- [Ubuntu Community Help](https://help.ubuntu.com/)

### Useful Commands

```bash
# Check NVIDIA GPU status
nvidia-smi -l 1  # Refresh every 1 second

# Activate SCAIL-2 environment
source venv/scail2/bin/activate

# Activate Wan2.2 environment
source venv/wan22/bin/activate

# Run system checks
bash scripts/preflight.sh

# Download models
bash scripts/download-models.sh

# Check available disk space
df -h .

# Monitor system resources
top  # Or 'htop' if installed
```

---

## Advanced Pipelines

Combine multiple models for sophisticated workflows:

### Pipeline 1: Fashion E-Commerce
```
Product Image
  → Fashn Virtual Try-On
  → Real-ESRGAN (2x upscale)
  → Final Product Preview
```

**Resources**: ~10GB VRAM
**Time**: 2-3 seconds total
**Use Case**: Try-on then upscale for display

### Pipeline 2: Content Enhancement
```
User Photo
  → Fashn Virtual Try-On (new outfit)
  → CodeFormer (face restoration, fidelity=0.85)
  → Real-ESRGAN (upscale 4x)
  → Final Enhanced Content
```

**Resources**: ~12GB VRAM
**Time**: 5-8 seconds total
**Use Case**: Social media content

### Pipeline 3: Professional Scene Editing
```
Base Photo
  → BiRefNet (extract subject)
  → Qwen-Image-Edit (new background from prompt)
  → IC-Light (synchronize lighting)
  → SeedVR2 (final restoration)
  → Final Professional Image
```

**Resources**: ~20GB VRAM
**Time**: 30-50 seconds total
**Use Case**: Professional photo editing, advertising

### Pipeline 4: Video Generation to Broadcast
```
Image or Prompt
  → Wan2.2-Animate (generate video)
  → SeedVR2 (restore quality 4x)
  → Final Broadcast-Quality Video
```

**Resources**: ~24GB VRAM
**Time**: 2-3 minutes per 4-second video
**Use Case**: Video content creation

### Pipeline 5: Portrait Enhancement
```
Portrait Photo
  → CodeFormer (face restoration, fidelity=0.5)
  → IC-Light (lighting adjustment)
  → Real-ESRGAN (upscale 2x)
  → Final Professional Portrait
```

**Resources**: ~8GB VRAM
**Time**: 3-5 seconds total
**Use Case**: Professional photography

### Model Configuration and Resource Management

**Key Principles:**
1. **Each model has isolated venv** - No dependency conflicts
2. **Sequential GPU usage** - One model active at a time in API mode
3. **Configurable model selection** - Enable only needed models
4. **Health checks available** - Verify each model before using

**Configuration:**
```yaml
# Edit configs/models.yaml to enable/disable models
enabled: true    # Set to false to skip in health checks
min_vram_gb: 8   # Minimum GPU memory required
task_type: "image-editing"  # For API routing
```

**Monitoring:**
```bash
# Check which models are available and healthy
bash scripts/health-check.sh

# Monitor GPU during execution
nvidia-smi -l 1  # Refresh every 1 second
```

---

**Last Updated**: 2026-08-13
**Maintained for Ubuntu 22.04 LTS and 24.04 LTS**


## Phase 4A authenticated GPU API

All non-health API calls use server-to-server authentication with the
Authorization Bearer header and X-Owner-ID. The service token must stay on trusted
servers and must never be sent to browser JavaScript or HTML.

Protected endpoints include uploads, jobs, cancellation, results, output downloads,
queue inspection, and model discovery. POST /v1/uploads accepts a raw request body
with X-Filename and an allowed image, video, or audio Content-Type. POST /v1/jobs
requires non-empty owner_id and client_job_id, and owner_id must match X-Owner-ID.

Reusing the same owner_id and client_job_id returns the existing in-memory job and
does not enqueue it again. Uploads, jobs, cancellation, result metadata, and output
downloads are owner-isolated. Restart persistence is intentionally deferred.
