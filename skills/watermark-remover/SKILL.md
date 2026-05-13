name: watermark-remover
description: Automatically remove watermarks (specifically ByteDance Seedance 2.0 "AI生成") from videos using intelligent corner detection and AI inpainting (TELEA, LaMa, MAT). Activates on intent to "remove watermark", "clean video", or "delete AI tag from video".

# Watermark Remover Skill

This skill provides an automated way to strip static watermarks from video files, optimized for Seedance 2.0 output.

## Installation

### 1. Download Script
```bash
curl -L -o watermark_remover.py https://raw.githubusercontent.com/xilu0/seedance-2.0-watermark-remover/main/watermark_remover.py
```

### 2. Install Core Dependencies
Requires `ffmpeg` installed on your system.
```bash
pip install opencv-python numpy
```

### 3. (Optional) AI Models for High Quality
For better results using `lama` or `mat` models:
```bash
pip install torch iopaint
```

## When This Skill Activates

**Intent detection:** Recognize requests like:
- "Remove the watermark from this video"
- "Clean up the 'AI生成' tag from my clip"
- "Delete the watermark in input.mp4"
- "Can you get rid of the watermark in the corner of this video?"

## Usage Guide

### Basic Usage (Fast)
Uses the TELEA method (OpenCV-based, no GPU needed).
```bash
python watermark_remover.py path/to/video.mp4
```

### High Quality (AI-powered)
Requires `torch` and `iopaint`.
```bash
# Using LaMa model (Best for photographic content)
python watermark_remover.py path/to/video.mp4 --model lama

# Using MAT model (Best for stylized/textured content)
python watermark_remover.py path/to/video.mp4 --model mat
```

### Advanced Options
- `--output`: Specify output filename (defaults to `input_no_wm.mp4`).
- `--debug`: Save the detected mask as an image for verification.
- `--temp`: Custom temporary directory for frame processing.

## Autonomy Rules

**Run automatically (no confirmation):**
- Checking if a file exists.
- Running with default settings (TELEA) for small files (<10MB).
- Checking for dependencies (`ffmpeg`, `cv2`).

**Ask before running:**
- Processing large video files (>10MB).
- Using AI models (`--model lama/mat`) as they download weights (~100MB+).
- Overwriting existing files.

## Troubleshooting

- **FFmpeg not found**: Ensure `ffmpeg` is in your PATH.
- **Out of memory**: If using LaMa/MAT on large videos, ensure enough RAM/VRAM is available.
- **Detection failure**: Use `--debug` to see if the script correctly identifies the watermark corner.
