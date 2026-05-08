"""Pad / fit an image to a multi-platform blog cover ratio (default 16:9).

跨平台（微信公众号 / 掘金 / CSDN）通用封面比例：
- **16:9**（≈ 1.778） 横向流程图、对比图、时间线 —— 默认推荐
- **1:1**            视觉海报、概念图、文字主标题、中心放射构图

各平台都会按自己规范自动截取缩略图，给个常见的横向或方形比例即可。
旧的 2.35:1 规则（仅针对公众号头条）已废弃。

Usage:
    # 16:9 横向（默认）
    python3 tools/fit_wechat_cover.py <path/to/cover.png> [--width 1920]

    # 1:1 方形
    python3 tools/fit_wechat_cover.py <path/to/cover.png> --ratio 1 --width 1500

    # 仍需 2.35:1（极少数场景）
    python3 tools/fit_wechat_cover.py <path/to/cover.png> --ratio 2.35 --width 2350

工具仅做白底 letterbox，保留原构图、不裁切、不拉伸。
"""
import argparse
import sys
from pathlib import Path

from PIL import Image


def fit_cover(src: Path, dst: Path, target_ratio: float = 16 / 9, target_width: int | None = None,
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
    ap = argparse.ArgumentParser(description="Fit image to a blog cover ratio (default 16:9).")
    ap.add_argument("src", type=Path, help="source image path")
    ap.add_argument("--dst", type=Path, default=None, help="output path (default: overwrite src)")
    ap.add_argument("--ratio", type=float, default=16 / 9,
                    help="target ratio (default 1.778 = 16:9). Common: 1.778, 1.0, 2.35")
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
