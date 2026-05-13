#!/usr/bin/env python3
"""
Seedance 2.0 Watermark Remover
================================
Removes the "AI生成" (AI-Generated) watermark added by Seedance 2.0 video generation.

Works on any corner-positioned watermark — auto-detects which corner it's in.

Pipeline:
  1. Sample ~60 frames and compute a mean frame — static watermarks become visible
  2. Auto-detect the watermark corner using Canny edge density × temporal stability
     (static watermarks score high; moving content like people/water scores low)
  3. Build a precise text mask via Canny edge detection on the watermark region
  4. Remove watermark using OpenCV TELEA inpainting (fast, no GPU required)
     or optionally an AI model (LaMa / MAT) via iopaint
  5. Reassemble frames + original audio with ffmpeg

Usage:
  python watermark_remover.py input.mp4
  python watermark_remover.py input.mp4 -o clean.mp4
  python watermark_remover.py input.mp4 -r 10,5,120,60                  # manual region x,y,w,h
  python watermark_remover.py input.mp4 --model lama                    # LaMa inpainting
  python watermark_remover.py input.mp4 --model mat --patch-pad 80      # MAT (best on stylized bgs)

Requirements:
  pip install opencv-python-headless numpy
  pip install iopaint torch  # only if using --model lama or --model mat
  ffmpeg must be installed and on PATH
"""

import cv2
import numpy as np
import subprocess
import sys
import os
import argparse
import tempfile
import shutil


def _auto_detect(frames, mean_frame, width, height):
    """
    Scan the four corners for the watermark.

    Scoring: edge_density × temporal_stability
      - edge_density: fraction of Canny edge pixels in mean frame (text has crisp edges)
      - temporal_stability: 1 / (1 + temporal_std) — static watermarks score high,
        moving content (people, water, foliage) scores low

    Uses tight corner regions (8 % h × 12 % w) so dynamic content inside larger
    corners does not dilute the watermark signal.
    """
    stack = np.stack(frames, axis=0)
    std_map = np.std(stack, axis=0).mean(axis=2)

    corner_h = max(60, int(height * 0.08))
    corner_w = max(120, int(width * 0.12))
    corners = [
        (0,            0,            corner_h,        corner_w),
        (0,            width-corner_w, corner_h,      width),
        (height-corner_h, 0,         height,          corner_w),
        (height-corner_h, width-corner_w, height,     width),
    ]

    best, best_score = None, 0
    for r1, c1, r2, c2 in corners:
        roi_gray = cv2.cvtColor(mean_frame[r1:r2, c1:c2], cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(roi_gray, 20, 60)
        edge_density = edges.mean() / 255.0
        temporal_std = std_map[r1:r2, c1:c2].mean()
        stability = 1.0 / (1.0 + temporal_std)
        score = edge_density * stability

        if score > best_score and edge_density > 0.002:
            ys, xs = np.where(edges > 0)
            if len(xs) > 20:
                best_score = score
                pad = 8
                x = max(0, c1 + int(xs.min()) - pad)
                y = max(0, r1 + int(ys.min()) - pad)
                w = min(width  - x, int(xs.max() - xs.min()) + 1 + 2 * pad)
                h = min(height - y, int(ys.max() - ys.min()) + 1 + 2 * pad)
                best = (x, y, w, h)

    return best


def _build_mask(mean_frame_bgr, region_xywh, frame_shape):
    """
    Build a sparse text mask using Canny edge detection on the mean frame.
    Canny traces only the sharp letter strokes, avoiding over-masking uniform sky/backgrounds.
    Falls back to full-rect if Canny finds nothing (very faint watermark).
    """
    x, y, w, h = region_xywh
    H, W = frame_shape[:2]
    roi_gray = cv2.cvtColor(mean_frame_bgr[y:y+h, x:x+w], cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(roi_gray, 30, 80)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    dilated = cv2.dilate(edges, kernel, iterations=1)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(dilated)
    clean = np.zeros_like(dilated)
    for i in range(1, n):
        if stats[i, cv2.CC_STAT_AREA] >= 100:
            clean[labels == i] = 255
    if clean.sum() == 0:
        clean = np.full((h, w), 255, dtype=np.uint8)
    mask = np.zeros((H, W), dtype=np.uint8)
    mask[y:y+h, x:x+w] = clean
    return mask


def _inpaint_telea(frame_bgr, mask):
    """Fast OpenCV TELEA inpainting — no GPU needed, works great on uniform backgrounds."""
    return cv2.inpaint(frame_bgr, mask, inpaintRadius=5, flags=cv2.INPAINT_TELEA)


def _inpaint_ai(model, frame_bgr, mask, region_xywh, pad=20):
    """AI inpainting via iopaint (LaMa / MAT / etc).

    pad: padding (px) around the watermark region fed to the model. Use a
    very large value (e.g. 9999) to feed the whole frame for maximum context.
    """
    from iopaint.schema import InpaintRequest, HDStrategy
    x, y, w, h = region_xywh
    Hf, Wf = frame_bgr.shape[:2]
    x0, y0 = max(0, x - pad), max(0, y - pad)
    x1, y1 = min(Wf, x + w + pad), min(Hf, y + h + pad)
    patch_bgr  = frame_bgr[y0:y1, x0:x1]
    patch_mask = mask[y0:y1, x0:x1]
    patch_rgb  = cv2.cvtColor(patch_bgr, cv2.COLOR_BGR2RGB)
    cfg = InpaintRequest(
        hd_strategy=HDStrategy.ORIGINAL,
        hd_strategy_crop_margin=32,
        hd_strategy_crop_trigger_size=800,
        hd_strategy_resize_limit=1280,
    )
    result = model(patch_rgb, patch_mask, cfg)
    if result.dtype != np.uint8:
        result = np.clip(result, 0, 255).astype(np.uint8)
    result_bgr = cv2.cvtColor(result, cv2.COLOR_RGB2BGR)
    out = frame_bgr.copy()
    out[y0:y1, x0:x1] = result_bgr
    return out


_AI_MODELS = {"lama", "mat"}


def remove_watermark(input_path, output_path, manual_region=None,
                     model_name="telea", patch_pad=20):
    cap = cv2.VideoCapture(input_path)
    total  = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps    = cap.get(cv2.CAP_PROP_FPS)
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"Video: {width}x{height} @ {fps:.2f} fps | {total} frames")

    # ── sample frames → mean frame ────────────────────────────────────────────
    print("Sampling frames for watermark detection...")
    sample_frames = []
    step = max(1, total // 60)
    for i in range(0, total, step):
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        ret, f = cap.read()
        if ret:
            sample_frames.append(f.astype(np.float32))
        if len(sample_frames) >= 60:
            break

    if not sample_frames:
        print("Error: could not read any frames.")
        cap.release()
        return False

    mean_frame = np.mean(np.stack(sample_frames), axis=0).astype(np.uint8)

    # ── detect / use manual region ────────────────────────────────────────────
    if manual_region:
        x, y, w, h = manual_region
        print(f"Using manual region: x={x} y={y} w={w} h={h}")
    else:
        region = _auto_detect(sample_frames, mean_frame, width, height)
        if region is None:
            print("Error: auto-detection failed. Try -r x,y,w,h to specify the region manually.")
            cap.release()
            return False
        x, y, w, h = region
        print(f"Detected watermark region: x={x} y={y} w={w} h={h}")

    mask = _build_mask(mean_frame, (x, y, w, h), (height, width))
    print(f"Mask: {int(mask.sum() // 255)} pixels")

    # ── load AI model if requested ────────────────────────────────────────────
    ai_model = None
    if model_name in _AI_MODELS:
        try:
            import torch
            import iopaint.const
            iopaint.const.MPS_UNSUPPORT_MODELS = [
                m for m in iopaint.const.MPS_UNSUPPORT_MODELS if m != model_name
            ]
            if model_name == "lama":
                from iopaint.model import LaMa as _ModelCls
            elif model_name == "mat":
                from iopaint.model import MAT as _ModelCls
        except ImportError:
            print(f"Error: --model {model_name} requires  pip install torch iopaint")
            cap.release()
            return False
        if torch.cuda.is_available():
            device = torch.device("cuda")
        elif torch.backends.mps.is_available():
            os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")
            device = torch.device("mps")
        else:
            device = torch.device("cpu")
        print(f"Loading {model_name.upper()} on {device}...")
        ai_model = _ModelCls(device)

    # ── process frames ────────────────────────────────────────────────────────
    if ai_model is not None:
        method = f"{model_name.upper()} (patch_pad={patch_pad})"
    else:
        method = "OpenCV TELEA"
    print(f"Inpainting {total} frames with {method} (streaming to ffmpeg)...")

    # Stream raw BGR frames straight into ffmpeg via stdin so we don't need
    # ~10 GB of temp PNGs on disk for long videos.
    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo",
        "-pix_fmt", "bgr24",
        "-s", f"{width}x{height}",
        "-r", str(fps),
        "-i", "-",                 # video from stdin
        "-i", input_path,          # audio source
        "-map", "0:v", "-map", "1:a?",
        "-c:v", "libx264", "-crf", "18", "-preset", "fast",
        "-pix_fmt", "yuv420p",
        "-c:a", "copy",
        "-movflags", "+faststart",
        output_path,
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    ret_code = 1
    stderr_tail = b""
    try:
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        for i in range(total):
            ret, frame = cap.read()
            if not ret:
                break
            if ai_model is not None:
                result = _inpaint_ai(ai_model, frame, mask, (x, y, w, h), pad=patch_pad)
            else:
                result = _inpaint_telea(frame, mask)
            try:
                proc.stdin.write(result.tobytes())
            except BrokenPipeError:
                # ffmpeg died; fall through to wait/stderr capture
                break
            if (i + 1) % 30 == 0 or i == total - 1:
                print(f"  {i+1}/{total}", end="\r", flush=True)
        cap.release()
        print()
        try:
            proc.stdin.close()
        except Exception:
            pass
        ret_code = proc.wait()
        try:
            stderr_tail = proc.stderr.read()[-2000:]
        except Exception:
            pass
    finally:
        if ai_model is not None:
            del ai_model
        if proc.poll() is None:
            proc.kill()

    if ret_code == 0:
        in_mb  = os.path.getsize(input_path)  / 1024 / 1024
        out_mb = os.path.getsize(output_path) / 1024 / 1024
        print(f"\nDone.  {in_mb:.1f} MB  →  {out_mb:.1f} MB")
        print(f"Output: {output_path}")
        return True
    else:
        print(f"Error: ffmpeg reassembly failed (exit {ret_code}).")
        if stderr_tail:
            print(stderr_tail.decode(errors="replace"))
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Remove Seedance 2.0 'AI生成' watermark from videos."
    )
    parser.add_argument("input",           help="Input video file")
    parser.add_argument("-o", "--output",  help="Output path (default: <input>_clean.mp4)")
    parser.add_argument(
        "-r", "--region",
        help="Manual watermark region as x,y,w,h — skips auto-detection",
    )
    parser.add_argument(
        "--model",
        choices=["telea", "lama", "mat"],
        default="telea",
        help="Inpainting backend. telea = OpenCV (fast, no GPU). "
             "lama / mat = AI models via iopaint (better quality on natural backgrounds; "
             "auto-selects CUDA / Apple MPS / CPU). Default: telea",
    )
    parser.add_argument(
        "--patch-pad",
        type=int,
        default=20,
        help="Padding (px) around the mask region fed to the AI model. "
             "Larger = more context, slower. Use a very large value (e.g. 9999) "
             "to feed the entire frame. Ignored for --model telea. Default: 20",
    )
    parser.add_argument(
        "--lama",
        action="store_true",
        help="Deprecated alias for --model lama (kept for backwards compatibility)",
    )
    args = parser.parse_args()
    if args.lama and args.model == "telea":
        args.model = "lama"

    if not os.path.exists(args.input):
        print(f"Error: file not found: {args.input}")
        sys.exit(1)

    output = args.output or os.path.splitext(args.input)[0] + "_clean.mp4"

    region = None
    if args.region:
        try:
            region = tuple(int(v) for v in args.region.split(","))
            assert len(region) == 4
        except Exception:
            print("Error: --region must be four comma-separated integers: x,y,w,h")
            sys.exit(1)

    ok = remove_watermark(
        args.input, output,
        manual_region=region,
        model_name=args.model,
        patch_pad=args.patch_pad,
    )
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
