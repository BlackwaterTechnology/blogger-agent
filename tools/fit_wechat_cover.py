import argparse
from PIL import Image
import os

def fit_cover(src, dst, ratio, width, bg_color):
    img = Image.open(src)
    src_w, src_h = img.size
    
    target_w = width
    target_h = int(width / ratio)
    
    # Scale image to fit within target dimensions
    scale = min(target_w / src_w, target_h / src_h)
    new_w = int(src_w * scale)
    new_h = int(src_h * scale)
    img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    # Create background
    new_img = Image.new("RGB", (target_w, target_h), bg_color)
    
    # Paste centered
    offset_x = (target_w - new_w) // 2
    offset_y = (target_h - new_h) // 2
    new_img.paste(img, (offset_x, offset_y))
    
    new_img.save(dst)
    print(f"Saved letterboxed image to {dst}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("src")
    parser.add_argument("-o", "--output", required=True)
    parser.add_argument("--ratio", type=float, default=1.778)
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--bg", default="white")
    args = parser.parse_args()
    
    fit_cover(args.src, args.output, args.ratio, args.width, args.bg)
