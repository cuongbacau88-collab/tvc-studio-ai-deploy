# TVC Studio AI - Model Matrix Reference

Complete specifications for all available AI models in TVC Studio AI deployment.

---

## Table of Contents

1. [Video Generation Models](#section-1-video-generation)
2. [Image Editing & Transformation](#section-2-image-editing)
3. [Image & Video Enhancement](#section-3-enhancement)
4. [Resource Comparison](#resource-comparison)
5. [Licensing Notes](#licensing-notes)
6. [Combining Models](#combining-models)

---

## Section 1: Video Generation

### SCAIL-2 (Semantic Control Image-to-Video)

**Purpose**: Convert static images to videos with semantic control over motion, composition, and semantics.

**Repository**: https://github.com/zai-org/SCAIL-2
**Hugging Face**: https://huggingface.co/zai-org/SCAIL-2
**Virtual Environment**: `venv/scail2`

**Task Type**: `video-generation`

#### Input
- Static image (JPEG, PNG)
- Optional: Text prompt for semantic guidance
- Optional: Motion mask or control signals

#### Output
- Video file (MP4 or other format)
- Configurable frame rate and duration

#### Hardware Requirements
| Spec | Minimum | Recommended |
|------|---------|-------------|
| VRAM | 6GB | 8GB |
| RAM | 8GB | 16GB |
| Disk | 5GB | 10GB |
| GPU | RTX 2070 | RTX 3080+ |

#### Performance
- Average inference time: 30-60 seconds for 4-second video (1080p)
- Batch processing: Not supported (single video at a time)
- Real-time capable: No

#### Special Features
- Semantic control over video content
- Customizable motion intensity
- Support for various aspect ratios

#### License
⚠️ **IMPORTANT**: Check the model card at https://huggingface.co/zai-org/SCAIL-2 for licensing terms. The weights and model may have restrictions on commercial use.

#### Setup
```bash
bash scripts/install-model.sh scail2
source venv/scail2/bin/activate
bash scripts/download-model.sh scail2
```

---

### Wan2.2-Animate-14B

**Purpose**: Advanced video generation and animation from images or text prompts.

**Repository**: https://github.com/Wan-Video/Wan2.2
**Hugging Face**: https://huggingface.co/Wan-AI/Wan2.2-Animate-14B
**Virtual Environment**: `venv/wan22`

**Task Type**: `video-generation`

#### Input
- Static image (JPEG, PNG) OR
- Text prompt describing desired animation/video
- Optional: Animation style guide
- Optional: Character/object reference

#### Output
- Animated video (MP4)
- Configurable resolution (up to 2K)
- Configurable duration and frame rate

#### Hardware Requirements
| Spec | Minimum | Recommended |
|------|---------|-------------|
| VRAM | 8GB | 16GB |
| RAM | 16GB | 24GB |
| Disk | 15GB | 30GB |
| GPU | RTX 3080 | RTX 4090 / A100 |

#### Performance
- Average inference time: 60-120 seconds for 4-second video (1080p)
- Batch processing: Limited (sequential processing)
- Real-time capable: No

#### Special Features
- Large model (14B parameters) for superior quality
- Supports both image and text-to-video
- Multiple animation styles
- Character consistency across frames

#### License
⚠️ **IMPORTANT**: Check https://huggingface.co/Wan-AI/Wan2.2-Animate-14B for model licensing. Commercial use may require explicit permission.

#### Setup
```bash
bash scripts/install-model.sh wan22-animate
source venv/wan22/bin/activate
bash scripts/download-model.sh wan22-animate
```

---

## Section 2: Image Editing & Transformation

### Fashn Virtual Try-On 1.5

**Purpose**: Virtual clothing try-on system allowing users to see how garments fit and look on people.

**Repository**: https://github.com/fashn-AI/fashn-vton-1.5
**Hugging Face**: https://huggingface.co/fashn-ai/fashn-vton-1.5
**Virtual Environment**: `venv/fashn-vton`

**Task Type**: `image-editing`

#### Input
- Person image (JPEG, PNG) - full body or upper body
- Garment image (JPEG, PNG) - flat lay or worn
- Optional: Garment category (shirt, pants, dress, etc.)

#### Output
- Person wearing the garment (JPEG, PNG)
- Same dimensions as input person image

#### Hardware Requirements
| Spec | Minimum | Recommended |
|------|---------|-------------|
| VRAM | 4GB | 6GB |
| RAM | 8GB | 12GB |
| Disk | 2GB | 4GB |
| GPU | GTX 1660 | RTX 2080+ |

#### Performance
- Average inference time: 2-5 seconds per try-on
- Batch processing: Supported (multiple garments per person)
- Real-time capable: Yes (with optimization)

#### Special Features
- Fast inference for interactive use
- Maintains person's pose and proportions
- Works with various clothing types
- Lightweight model for edge deployment

#### Typical Use Cases
- E-commerce virtual try-on
- Fashion app integration
- Personal styling assistant
- Inventory visualization

#### License
⚠️ **Commercial use**: Review https://huggingface.co/fashn-ai/fashn-vton-1.5 for licensing. Some models require academic or non-commercial use.

#### Setup
```bash
bash scripts/install-model.sh fashn-vton
source venv/fashn-vton/bin/activate
bash scripts/download-model.sh fashn-vton
```

---

### Qwen-Image-Edit-2511

**Purpose**: Edit scenes and backgrounds in images using text prompts and reference images.

**Repository**: https://github.com/QwenLM/Qwen-Image
**Hugging Face**: https://huggingface.co/Qwen/Qwen-Image-Edit-2511
**Virtual Environment**: `venv/qwen-image-edit`

**Task Type**: `image-editing`

#### Input
- Base image (JPEG, PNG)
- Text prompt describing desired edits
- Optional: Reference image for style/content
- Optional: Segmentation mask

#### Output
- Edited image with modified background/scene
- Same resolution as input (or configurable)

#### Hardware Requirements
| Spec | Minimum | Recommended |
|------|---------|-------------|
| VRAM | 8GB | 12GB |
| RAM | 12GB | 16GB |
| Disk | 8GB | 16GB |
| GPU | RTX 3080 | RTX 4090 |

#### Performance
- Average inference time: 10-30 seconds
- Batch processing: Not supported
- Real-time capable: No

#### Special Features
- Text-guided image editing
- Reference-based style transfer
- Scene and background manipulation
- Support for complex prompts

#### Optional Pipeline: Advanced Scene Editing

For more control, use as part of a pipeline:

```
BiRefNet (background removal)
         ↓
Qwen-Image-Edit (scene generation)
         ↓
IC-Light (lighting synchronization)
```

This three-stage pipeline allows:
1. Extract subject from background
2. Generate new background matching prompt
3. Synchronize lighting to make result photorealistic

#### License
⚠️ **Qwen models**: Check https://huggingface.co/Qwen/ for licensing terms. Qwen models often allow commercial use under certain conditions.

#### Setup (Basic)
```bash
bash scripts/install-model.sh qwen-image-edit
source venv/qwen-image-edit/bin/activate
bash scripts/download-model.sh qwen-image-edit
```

#### Setup (Advanced Pipeline with BiRefNet + IC-Light)
```bash
# Install all three models
bash scripts/install-model.sh qwen-image-edit
bash scripts/install-model.sh birefnet
bash scripts/install-model.sh ic-light

# Activate shared environment
source venv/qwen-image-edit/bin/activate

# Download all models
bash scripts/download-model.sh qwen-image-edit
bash scripts/download-model.sh birefnet
bash scripts/download-model.sh ic-light
```

---

### BiRefNet (Background Removal)

**Purpose**: Remove or extract background from images using bilateral reference filtering.

**Repository**: https://github.com/ZhengPeng7/BiRefNet
**Hugging Face**: https://huggingface.co/ZhengPeng7/BiRefNet
**Virtual Environment**: `venv/qwen-image-edit` (shared)

**Task Type**: `image-preprocessing`
**Usage Context**: Optional step in scene editing pipeline

#### Input
- Image (JPEG, PNG) with subject and background

#### Output
- Foreground/background segmentation mask
- Extracted subject with transparent background
- Binary or soft mask

#### Hardware Requirements
| Spec | Minimum | Recommended |
|------|---------|-------------|
| VRAM | 2GB | 4GB |
| RAM | 4GB | 8GB |
| Disk | 500MB | 1GB |
| GPU | GTX 1050 | GTX 1660+ |

#### Performance
- Average inference time: 1-3 seconds
- Batch processing: Supported
- Real-time capable: Yes

#### Typical Use Cases
- Preprocessing for scene editing
- Background removal for product photos
- Silhouette extraction
- Subject isolation

#### Note
BiRefNet is **optional** - you can use Qwen-Image-Edit alone. Use BiRefNet when you need explicit background removal before scene editing.

#### License
⚠️ Check https://huggingface.co/ZhengPeng7/BiRefNet for license details.

---

### IC-Light (Intelligent Color Light)

**Purpose**: Synchronize and adjust lighting in images to ensure photorealistic results after scene editing.

**Repository**: https://github.com/lllyasviel/IC-Light
**Hugging Face**: https://huggingface.co/lllyasviel/ic-light-unet
**Virtual Environment**: `venv/qwen-image-edit` (shared)

**Task Type**: `image-enhancement`
**Usage Context**: Final step in scene editing pipeline

#### Input
- Edited image from Qwen-Image-Edit
- Original lighting information
- Target lighting direction (optional)

#### Output
- Image with synchronized lighting
- Consistent shadows and highlights
- Photorealistic lighting

#### Hardware Requirements
| Spec | Minimum | Recommended |
|------|---------|-------------|
| VRAM | 3GB | 6GB |
| RAM | 6GB | 12GB |
| Disk | 1GB | 2GB |
| GPU | GTX 1660 | RTX 3070+ |

#### Performance
- Average inference time: 5-10 seconds
- Batch processing: Supported
- Real-time capable: Partial (with optimization)

#### Typical Use Cases
- Lighting correction after scene editing
- Shadow/highlight adjustment
- Consistency across multi-edited images
- Photorealism enhancement

#### Note
IC-Light is **optional** - completes the scene editing pipeline for photorealistic results. Use alone for lighting-only adjustments.

#### License
⚠️ Check https://github.com/lllyasviel/IC-Light for licensing terms.

---

## Section 3: Image & Video Enhancement

### SeedVR2 (Video Restoration)

**Purpose**: High-quality video restoration and super-resolution with artifact removal.

**Repository**: https://github.com/IceClear/SeedVR2
**Hugging Face**: https://huggingface.co/IceClear/SeedVR2
**Virtual Environment**: `venv/seedvr2`

**Task Type**: `video-enhancement`

#### Input
- Video file (MP4, AVI, WebM)
- Supported resolutions: SD to 1080p

#### Output
- Enhanced video (MP4)
- 2x-4x resolution improvement
- Artifact and noise reduced

#### Hardware Requirements
| Spec | Minimum | Recommended |
|------|---------|-------------|
| VRAM | 6GB | 12GB |
| RAM | 12GB | 24GB |
| Disk | Variable | 50GB+ |
| GPU | RTX 3080 | RTX 4090 |

#### Performance
- Frame processing: 5-15 seconds per frame (1080p)
- Batch processing: Supported (sequential frames)
- Real-time capable: No (post-processing tool)

#### Special Features
- Temporal consistency (smooth across frames)
- Artifact removal
- Adaptive upscaling
- High-quality restoration

#### Typical Use Cases
- Restore old/low-quality videos
- Professional video enhancement
- Archive digitization
- Quality improvement for AI generation output

#### Quality vs Speed
- **Best Quality**: Use full model with 4x upscaling
- **Balanced**: 2x upscaling with standard model
- **Fast**: Consider Real-ESRGAN for quick upscaling

#### License
⚠️ Check https://huggingface.co/IceClear/SeedVR2 for licensing information.

#### Setup
```bash
bash scripts/install-model.sh seedvr2
source venv/seedvr2/bin/activate
bash scripts/download-model.sh seedvr2
```

---

### Real-ESRGAN (Fast Upscaling)

**Purpose**: Fast image and video upscaling (2x/4x) with face enhancement capabilities.

**Repository**: https://github.com/xinntao/Real-ESRGAN
**Hugging Face**: https://huggingface.co/xinntao/Real-ESRGAN
**Virtual Environment**: `venv/realesrgan`

**Task Type**: `image-enhancement`

#### Input
- Image (JPEG, PNG) or video
- Supported resolutions: Any (scales adaptively)

#### Output
- Upscaled image (2x or 4x resolution)
- Reduced noise and artifacts
- Optional face enhancement

#### Hardware Requirements
| Spec | Minimum | Recommended |
|------|---------|-------------|
| VRAM | 3GB | 6GB |
| RAM | 4GB | 8GB |
| Disk | 500MB | 2GB |
| GPU | GTX 1050 Ti | RTX 2070+ |

#### Performance
- Speed: 0.2-1 second per image (2x upscale, 1080p)
- Batch processing: Highly efficient (GPU batch)
- Real-time capable: Yes (with optimization)

#### Upscaling Models Available
| Model | Speed | Quality | Use Case |
|-------|-------|---------|----------|
| `RealESRGAN_x2plus` | Very Fast | Good | 2x upscaling |
| `RealESRGAN_x4plus` | Fast | Excellent | 4x upscaling |
| `RealESRGAN_x4plus_anime_6B` | Fast | Good | Anime/illustration |
| `GFPGANv1.3` | Medium | Excellent | Face restoration |

#### Special Features
- Lightweight model
- Anime support
- Face enhancement option
- Real-time processing

#### Typical Use Cases
- Quick image upscaling
- Batch image enhancement
- Web integration
- Real-time processing pipelines

#### Quality Comparison: SeedVR2 vs Real-ESRGAN
- **SeedVR2**: Superior quality, slower, video-optimized
- **Real-ESRGAN**: Fast, good quality, image-optimized

#### License
⚠️ Check https://github.com/xinntao/Real-ESRGAN for licensing. Real-ESRGAN is generally MIT-licensed allowing commercial use.

#### Setup
```bash
bash scripts/install-model.sh realesrgan
source venv/realesrgan/bin/activate
bash scripts/download-model.sh realesrgan
```

---

### CodeFormer (Face Restoration)

**Purpose**: Blind face restoration using code guidance, restoring faces to high quality while preserving identity.

**Repository**: https://github.com/sczhou/CodeFormer
**Hugging Face**: https://huggingface.co/sczhou/codeformer
**Virtual Environment**: `venv/codeformer`

**Task Type**: `image-restoration`

#### Input
- Image (JPEG, PNG) containing faces
- Fidelity parameter: 0.0 (higher quality) to 1.0 (preserve identity)
- Default: 0.85 (balanced)

#### Output
- Restored face image
- Improved clarity and details
- Configurable identity preservation

#### Hardware Requirements
| Spec | Minimum | Recommended |
|------|---------|-------------|
| VRAM | 2GB | 4GB |
| RAM | 4GB | 8GB |
| Disk | 500MB | 1GB |
| GPU | GTX 1050 | GTX 1660+ |

#### Performance
- Speed: 0.5-2 seconds per image
- Batch processing: Supported
- Real-time capable: Yes

#### Fidelity Parameter Guidance
| Fidelity | Effect | Use Case |
|----------|--------|----------|
| 0.0 | Maximum enhancement | Artistic/creative |
| 0.5 | Balanced | General restoration |
| 0.85 | Identity-preserving (default) | Legal/ID documents |
| 1.0 | Minimal change | Preservation focus |

#### Special Features
- Blind restoration (no ground truth needed)
- Identity control via fidelity parameter
- Face quality improvement
- Lightweight and fast

#### Typical Use Cases
- Restore old photo faces
- Enhance video call quality
- Face detail enhancement
- Identity document improvement

#### Identity Preservation
⚠️ **Default fidelity is 0.85** to limit identity changes. This is important for:
- Legal/official document use
- Privacy-sensitive applications
- Authentication scenarios

Increase fidelity toward 1.0 if preserving exact identity is critical.

#### License
⚠️ **IMPORTANT**: Check https://github.com/sczhou/CodeFormer for licensing. CodeFormer may have restrictions on commercial use without modification.

#### Setup
```bash
bash scripts/install-model.sh codeformer
source venv/codeformer/bin/activate
bash scripts/download-model.sh codeformer
```

---

## Resource Comparison

### VRAM Usage Summary

```
Video Generation (Most Demanding):
├── Wan2.2-Animate: 8-16GB
├── SCAIL-2: 6-8GB
│
Image Editing & Enhancement (Medium):
├── Qwen-Image-Edit: 8-12GB
├── IC-Light: 3-6GB
├── BiRefNet: 2-4GB
├── SeedVR2: 6-12GB
├── Real-ESRGAN: 3-6GB
│
Lightweight (Real-Time Capable):
├── Fashn-VTON: 4-6GB
└── CodeFormer: 2-4GB
```

### Inference Speed Ranking

| Model | Type | Speed | Note |
|-------|------|-------|------|
| CodeFormer | Face | 0.5-2s | Fastest |
| Real-ESRGAN | Upscale | 0.2-1s | Fast batch |
| BiRefNet | Segmentation | 1-3s | Fast |
| Fashn-VTON | Try-on | 2-5s | Real-time possible |
| IC-Light | Lighting | 5-10s | Medium |
| Qwen-Image-Edit | Edit | 10-30s | Medium-Slow |
| SeedVR2 | Restoration | 5-15s/frame | Slow (quality) |
| SCAIL-2 | Video | 30-60s | Slow (generation) |
| Wan2.2 | Video | 60-120s | Slowest |

### Disk Space Requirements

```
Video Generation:
├── Wan2.2-Animate: ~14GB
└── SCAIL-2: ~4GB

Image Editing:
├── Qwen-Image-Edit: ~10GB
├── BiRefNet: ~200MB
└── IC-Light: ~1GB

Enhancement:
├── SeedVR2: ~5GB
├── Real-ESRGAN: ~500MB
└── CodeFormer: ~300MB

Total Installed (all models): ~50GB
Total with dependencies: ~60GB+
```

---

## Licensing Notes

### ⚠️ IMPORTANT LICENSING INFORMATION

This deployment repository does NOT claim commercial rights to any model weights. **You are responsible for:**

1. **Reviewing each model's license** before commercial deployment
2. **Understanding usage restrictions** for each model
3. **Obtaining proper licenses** if required by model authors
4. **Respecting intellectual property rights** of model creators

### Model License Categories

| Model | Category | Status | Check |
|-------|----------|--------|-------|
| SCAIL-2 | Research | ⚠️ Unclear | https://huggingface.co/zai-org/SCAIL-2 |
| Wan2.2 | Research | ⚠️ Unclear | https://huggingface.co/Wan-AI/Wan2.2-Animate-14B |
| Fashn-VTON | Commercial | ⚠️ Mixed | https://huggingface.co/fashn-ai/fashn-vton-1.5 |
| Qwen-Image-Edit | Research | ✓ Allowed* | https://huggingface.co/Qwen/ |
| BiRefNet | Academic | ⚠️ Check | https://huggingface.co/ZhengPeng7/BiRefNet |
| IC-Light | Research | ⚠️ Check | https://github.com/lllyasviel/IC-Light |
| SeedVR2 | Research | ⚠️ Check | https://huggingface.co/IceClear/SeedVR2 |
| Real-ESRGAN | MIT License | ✓ Allowed | https://github.com/xinntao/Real-ESRGAN |
| CodeFormer | Research | ⚠️ Check | https://github.com/sczhou/CodeFormer |

*Qwen models often allow commercial use under attribution

### Recommended Pre-Deployment Checks

Before deploying any model commercially:

```bash
# 1. Read model card on Hugging Face
# https://huggingface.co/<model-name>

# 2. Check repository README
cd repos/<model-repo>
cat README.md  # Look for license section

# 3. Review LICENSE file
cat LICENSE

# 4. Contact authors if unclear
# Check GitHub issues for licensing questions
```

### Safe Commercial Use

Generally safe for commercial deployment:
- **Real-ESRGAN**: MIT License ✓
- **Qwen models**: With attribution ✓
- Others: Requires explicit verification ⚠️

---

## Combining Models

### Recommended Pipelines

#### Pipeline 1: Fashion E-Commerce
```
Product Image → Fashn-VTON → Real-ESRGAN → Final Preview
```
- User selects garment
- Virtual try-on applied
- Quick upscaling for display
- Fast, suitable for web

#### Pipeline 2: Content Enhancement
```
User Photo → Fashn-VTON → CodeFormer → Real-ESRGAN → Final Content
```
- Virtual clothing try-on
- Face restoration
- Quality upscaling
- Balanced quality/speed

#### Pipeline 3: Professional Scene Editing
```
Base Photo → BiRefNet → Qwen-Image-Edit → IC-Light → SeedVR2
```
- Extract subject
- Generate new background
- Synchronize lighting
- Final restoration
- Highest quality, slowest

#### Pipeline 4: Video Generation to Enhancement
```
Image → Wan2.2-Animate → SeedVR2 → Final Video
```
- Generate video from image
- High-quality restoration
- Optimal quality result

#### Pipeline 5: Face Enhancement Focus
```
Portrait → CodeFormer (fidelity=0.5) → IC-Light → Real-ESRGAN
```
- Restore face details
- Adjust lighting
- Upscale image
- Professional portrait result

### Pipeline Execution Model

⚠️ **IMPORTANT**: Current architecture assumes sequential execution.

```
GPU Queue (TVC Studio AI API):
  Task 1 (Wan2.2-Animate) [RUNNING]
       ↓
  Task 2 (Real-ESRGAN) [WAITING]
       ↓
  Task 3 (CodeFormer) [WAITING]
```

Each GPU task runs exclusively to avoid CUDA memory conflicts.

---

## Resource Allocation Guidelines

### Single GPU Deployment (< 12GB)
- **Best Fit**: Lightweight models
- Models: Fashn-VTON, CodeFormer, Real-ESRGAN, BiRefNet
- Pipelines: Fashion try-on, Quick enhancement
- Concurrent: Single model active

### Dual GPU Deployment (16GB+ each)
- **Best Fit**: Balanced pipeline
- Model Split: One GPU per major model type
- Pipelines: Scene editing, Video generation
- Concurrent: Two independent models

### Enterprise GPU Deployment (24GB+ with batch)
- **Best Fit**: Full pipeline
- All models available
- Sequential queueing
- Concurrent: Preprocessing while generating

---

**Last Updated**: 2026-08-13
**Scope**: TVC Studio AI Deployment Reference
**Note**: Licensing information subject to change. Always verify with official model sources.
