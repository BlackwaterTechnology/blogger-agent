#!/usr/bin/env python3
"""Dual-Tier Subtitle Video Generator CLI Script.

Standalone runner for generating lightweight language learning videos with two-tier subtitles.
Supports:
1. Direct MP4 generation: -i sentences.txt -o video.mp4
2. Full payload generation compatible with publish-video: --payload-dir videos/<topic>/
3. Direct multi-platform publishing: --platform wechat_video,wechat_channels,bilibili
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

# Add repository root to sys.path so it works whether run from root or anywhere
repo_root = Path(__file__).resolve().parents[3]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))
src_path = repo_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

try:
    from blogger.core.dual_sub_video import (
        create_dual_sub_payload,
        generate_dual_subtitle_video,
        generate_video_cover,
        generate_video_payload_md,
    )
except ImportError:
    from src.blogger.core.dual_sub_video import (
        create_dual_sub_payload,
        generate_dual_subtitle_video,
        generate_video_cover,
        generate_video_payload_md,
    )


def main():
    parser = argparse.ArgumentParser(description="Generate dual-tier subtitle videos and payloads for language learning.")
    parser.add_argument("-i", "--input", required=True, help="Path to input text file containing sentences (sentences.txt).")
    parser.add_argument("-o", "--output", help="Destination path for generated MP4 video file.")
    parser.add_argument("--payload-dir", help="Directory for assembling standard video payload (videos/<topic>/).")
    parser.add_argument("--cover", help="Destination path for generated 16:9 cover image (cover.png).")
    parser.add_argument("--voice", default="en-US-JennyNeural", help="Edge-TTS voice name (default: en-US-JennyNeural).")
    parser.add_argument("--level", default="a2", choices=["a2", "b1", "b2", "c1", "A2", "B1", "B2", "C1"], help="CEFR English level (a2, b1, b2, c1; default: a2).")
    parser.add_argument("--rate", help="Edge-TTS speech rate (defaults to level preset, e.g. -12%% for A2, -6%% for B1).")
    parser.add_argument("--pitch", default="+2Hz", help="Edge-TTS speech pitch (default: +2Hz).")
    parser.add_argument("--title", default="English Listening Practice", help="Title displayed on top header and metadata.")
    parser.add_argument("--tag", help="Badge tag on top left (defaults to level preset, e.g. A2 · ELEMENTARY).")
    parser.add_argument("--subtitle", help="Subtitle on cover image (defaults to level preset).")
    parser.add_argument("--desc", help="Description / summary for payload.md (strictly 60-120 characters).")
    parser.add_argument("--collection", default="软件教程", help="Collection matching blogger.toml (default: '软件教程').")
    parser.add_argument("--author", default="Blogger Agent", help="Author name in payload.md.")
    parser.add_argument("--notes", help="Optional markdown text containing key vocabulary and learning notes.")
    parser.add_argument(
        "--platform",
        help="Optional target platform(s) to publish to immediately (e.g. wechat_video,wechat_channels,bilibili).",
    )
    parser.add_argument(
        "--no-publish",
        action="store_true",
        help="Dry run for publishing (fills dialog but skips final submit).",
    )
    parser.add_argument(
        "--bg-image",
        help="Path to custom ambient background image (or auto-detected from payload dir).",
    )
    parser.add_argument(
        "--bg-blur",
        type=int,
        default=3,
        help="Gaussian blur radius for ambient background (default: 3).",
    )
    parser.add_argument(
        "--bg-alpha",
        type=float,
        default=0.20,
        help="Dark overlay alpha for ambient background (default: 0.20).",
    )
    args = parser.parse_args()

    input_file = Path(args.input).resolve()
    if not input_file.exists():
        print(f"Error: input file '{input_file}' does not exist.", file=sys.stderr)
        sys.exit(1)

    try:
        desc_text = args.desc or f"Master English listening with {args.title}, featuring dual-tier subtitles and context stream."

        if args.payload_dir:
            payload_p = Path(args.payload_dir).resolve()
            payload_p.mkdir(parents=True, exist_ok=True)
            print(f"Assembling standard video payload in: {payload_p} ...")

            result = create_dual_sub_payload(
                payload_dir=payload_p,
                sentences_path=input_file,
                title=args.title,
                desc=desc_text,
                collection=args.collection,
                voice=args.voice,
                rate=args.rate,
                pitch=args.pitch,
                tag=args.tag,
                subtitle=args.subtitle,
                author=args.author,
                notes=args.notes,
                bg_image=args.bg_image,
                level=args.level.lower(),
                bg_blur=args.bg_blur,
                bg_alpha=args.bg_alpha,
            )

            print(f"Video created:   {result['video_path']}")
            print(f"Cover created:   {result['cover_path']}")
            print(f"Payload created: {result['payload_md']}")
            target_payload_md = result["payload_md"]

        else:
            # Standalone output mode
            if not args.output:
                output_mp4 = input_file.with_name(f"{input_file.stem}_dual_sub.mp4")
            else:
                output_mp4 = Path(args.output).resolve()

            cover_path = Path(args.cover).resolve() if args.cover else None

            out = generate_dual_subtitle_video(
                input_path=input_file,
                output_mp4=output_mp4,
                voice=args.voice,
                rate=args.rate,
                pitch=args.pitch,
                title=args.title,
                tag=args.tag,
                cover_path=cover_path,
                subtitle=args.subtitle,
                bg_image=args.bg_image,
                level=args.level.lower(),
                bg_blur=args.bg_blur,
                bg_alpha=args.bg_alpha,
            )
            print(f"Video generated successfully: {out}")
            if cover_path and cover_path.exists():
                print(f"Cover generated: {cover_path}")
            target_payload_md = None

        # Publishing flow if requested
        if args.platform and args.platform.lower() != "none":
            if not target_payload_md or not target_payload_md.exists():
                # If generated standalone, create a temporary payload.md in output parent directory
                parent_dir = (Path(args.output) if args.output else input_file).parent
                target_payload_md = generate_video_payload_md(
                    payload_dir=parent_dir,
                    title=args.title,
                    desc=desc_text,
                    collection=args.collection,
                    author=args.author,
                    video_filename=(Path(args.output) if args.output else input_file.with_suffix(".mp4")).name,
                    sentences_path=input_file,
                )

            print(f"Initiating publication to platforms ({args.platform}) via blogger CLI...")
            pub_cmd = [
                sys.executable,
                "-m",
                "blogger.cli",
                "publish",
                "--payload",
                str(target_payload_md),
                "--platform",
                args.platform,
            ]
            if args.no_publish:
                pub_cmd.append("--no-publish")

            pub_res = subprocess.run(pub_cmd)
            if pub_res.returncode != 0:
                print(f"Publishing failed with exit code {pub_res.returncode}", file=sys.stderr)
                sys.exit(pub_res.returncode)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
