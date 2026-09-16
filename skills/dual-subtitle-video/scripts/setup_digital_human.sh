#!/bin/bash
# ==============================================================================
# setup_digital_human.sh: Setup FasterLivePortrait-MLX / LivePortrait for macOS
# ==============================================================================
set -e

echo "=== Setting up Scheme B: Digital Human Engine for Apple Silicon ==="

# 1. Verify Homebrew and FFmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "⚠️  FFmpeg not found. Installing via Homebrew..."
    brew install ffmpeg
else
    echo "✅ FFmpeg is installed."
fi

# 2. Install MLX Framework for Apple Silicon
echo "📦 Installing MLX and audio packages..."
python3 -m pip install --upgrade pip
python3 -m pip install mlx mlx-metal opencv-python-headless pillow numpy huggingface_hub

# 3. Setup FasterLivePortrait-MLX (Apple Silicon Native)
INSTALL_DIR="$HOME/.cache/fasterliveportrait-mlx"
if [ ! -d "$INSTALL_DIR" ]; then
    echo "📥 Cloning FasterLivePortrait-MLX to $INSTALL_DIR..."
    git clone https://github.com/ivanfioravanti/fasterliveportrait-mlx.git "$INSTALL_DIR"
else
    echo "✅ FasterLivePortrait-MLX repository exists at $INSTALL_DIR"
fi

# 4. Prompt for MLX weights download
echo "💡 To download pre-converted MLX weights from HuggingFace:"
echo "   huggingface-cli download ivanfioravanti/FasterLivePortrait-MLX-weights --local-dir $INSTALL_DIR/pretrained_weights"

echo ""
echo "=== Digital Human Engine setup completed ==="
echo "You can now generate Scheme B videos using:"
echo "python3 skills/dual-subtitle-video/scripts/dual_sub_video.py -i sentences.txt --layout avatar --generate-digital-human"
