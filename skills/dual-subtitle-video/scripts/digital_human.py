#!/usr/bin/env python3
"""Standalone CLI Tool to generate Digital Human Talking Head videos for Scheme B.

Usage:
  python3 skills/dual-subtitle-video/scripts/digital_human.py \
    --source path/to/avatar.png \
    --audio path/to/speech.mp3 \
    --output path/to/avatar_talking.mp4 \
    --driver auto  # or mlx, pytorch, cloud, template
"""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.blogger.core.digital_human import get_digital_human_driver


def main():
    parser = argparse.ArgumentParser(description="Generate digital human talking video from portrait image and audio (Scheme B).")
    parser.add_argument("--source", "-s", required=True, help="Path to source portrait image (PNG/JPG).")
    parser.add_argument("--audio", "-a", required=True, help="Path to driving speech audio (MP3/WAV).")
    parser.add_argument("--output", "-o", required=True, help="Output MP4 path for the talking head video.")
    parser.add_argument(
        "--driver", "-d",
        default="auto",
        choices=["auto", "mlx", "fasterliveportrait", "pytorch", "liveportrait", "cloud", "template"],
        help="Digital human driver engine (default: auto).",
    )
    parser.add_argument("--fps", type=int, default=25, help="Video frame rate (default: 25).")

    args = parser.parse_args()

    src_p = Path(args.source).resolve()
    audio_p = Path(args.audio).resolve()
    out_p = Path(args.output).resolve()

    if not src_p.exists():
        print(f"Error: source image not found at '{src_p}'", file=sys.stderr)
        sys.exit(1)
    if not audio_p.exists():
        print(f"Error: driving audio not found at '{audio_p}'", file=sys.stderr)
        sys.exit(1)

    driver = get_digital_human_driver(args.driver)
    print(f"Selected Digital Human Driver: {driver.name}")

    try:
        res = driver.generate(
            source_image=src_p,
            driving_audio=audio_p,
            output_video=out_p,
            fps=args.fps,
        )
        print(f"✅ Digital human video generated successfully: {res}")
    except Exception as e:
        print(f"❌ Error generating digital human video: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
