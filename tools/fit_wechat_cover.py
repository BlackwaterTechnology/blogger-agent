"""Pad / fit an image to WeChat Official Account cover spec (2.35:1).

WeChat 公众号头图（headline cover）要求 2.35:1，否则编辑器会报
"2.35:1 cover specifications abnormal. Recrop"。本工具用白底 letterbox
把任意比例的图压成 2.35:1，保留原构图，不做任何裁剪/拉伸。

Usage:
    python3 tools/fit_wechat_cover.py <path/to/cover.png> [--ratio 2.35] [--width 2350]

默认 width=2350（高分屏友好，公众号显示约 750–900px 宽，2.5x 缩放仍清晰）。
"""
import argparse
import sys
from pathlib import Path

from PIL import Image


def fit_cover(src: Path, dst: Path, target_ratio: float = 2.35, target_width: int | None = None,
              bg: tuple[int, int, int] = (255, 255, 255)) -> None:
    img = Image.open(src).convert("RGB")
    w, h = img.size
    cur_ratio = w / h

    if target_width is None:
        # 不强制目标宽度，按现有宽度补 padding 到目标比例
        if cur_ratio > target_ratio:
            new_w = w
            new_h = round(w / target_ratio)
        elif cur_ratio < target_ratio:
            new_w = round(h * target_ratio)
            new_h = h
        else:
            img.save(dst); return
    else:
        # 强制目标宽度，按比例算高，再把原图等比缩放到能放下，居中贴上
        new_w = target_width
        new_h = round(target_width / target_ratio)
        # 等比缩放原图，使其在 new_w x new_h 画布内（不裁切）
        scale = min(new_w / w, new_h / h)
        sw, sh = round(w * scale), round(h * scale)
        img = img.resize((sw, sh), Image.LANCZOS)
        w, h = sw, sh

    canvas = Image.new("RGB", (new_w, new_h), bg)
    pad_x = (new_w - w) // 2
    pad_y = (new_h - h) // 2
    canvas.paste(img, (pad_x, pad_y))
    canvas.save(dst, optimize=True)
    print(f"{src} ({img.size if target_width else (w, h)}) → {dst} ({canvas.size}), ratio={canvas.size[0]/canvas.size[1]:.3f}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Fit image to WeChat cover spec (default 2.35:1).")
    ap.add_argument("src", type=Path, help="source image path")
    ap.add_argument("--dst", type=Path, default=None, help="output path (default: overwrite src)")
    ap.add_argument("--ratio", type=float, default=2.35, help="target ratio (default 2.35)")
    ap.add_argument("--width", type=int, default=None,
                    help="target absolute width; if set, image is scaled to fit a (width × width/ratio) canvas")
    args = ap.parse_args()

    src = args.src
    if not src.exists():
        print(f"source not found: {src}", file=sys.stderr); sys.exit(1)
    dst = args.dst or src
    fit_cover(src, dst, target_ratio=args.ratio, target_width=args.width)


if __name__ == "__main__":
    main()
