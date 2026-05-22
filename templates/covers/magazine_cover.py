import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.patches import Rectangle, Circle
import os

# Set font for macOS
mpl.rcParams["font.sans-serif"] = [
    "Hiragino Sans GB", "Heiti TC", "Songti SC", "PingFang SC", "Arial Unicode MS"
]
mpl.rcParams["axes.unicode_minus"] = False

def create_magazine_cover():
    # 16:9 ratio for WeChat cover (1920x1080)
    fig = plt.figure(figsize=(19.2, 10.8), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_axis_off()

    # --- Background ---
    # Deep "Wealth" Blue
    bg_color = "#102A43"  # Deep blue
    accent_color = "#F0B429" # Gold/Yellow for contrast
    text_white = "#F0F4F8"
    
    ax.add_patch(Rectangle((0, 0), 1, 1, color=bg_color, transform=ax.transAxes))

    # --- Decorative Elements ---
    # Add a gold accent strip on the left
    ax.add_patch(Rectangle((0, 0), 0.05, 1, color=accent_color, transform=ax.transAxes))
    
    # Add some abstract circles
    ax.add_patch(Circle((0.9, 0.1), 0.3, color="#243B53", alpha=0.5, transform=ax.transAxes))
    ax.add_patch(Circle((0.95, 0.05), 0.15, color=accent_color, alpha=0.2, transform=ax.transAxes))

    # --- Text ---
    # Title - Big and Bold
    ax.text(0.12, 0.65, "你的房子", fontsize=90, fontweight='bold', color=text_white, transform=ax.transAxes)
    ax.text(0.12, 0.48, "正在榨干你", fontsize=90, fontweight='bold', color=accent_color, transform=ax.transAxes)
    
    # Subtitle
    ax.text(0.12, 0.35, "——《穷爸爸与富爸爸》深度复盘", fontsize=40, color="#BCCCDC", transform=ax.transAxes)
    
    # Brand/Series
    ax.text(0.12, 0.15, "G E M I N I   C O A C H   |   财 务 思 维 系列", fontsize=25, color="#829AB1", transform=ax.transAxes)

    # Save
    output_path = "cover-magazine.png"
    plt.savefig(output_path, facecolor=bg_color, bbox_inches='tight', pad_inches=0)
    print(f"Professional cover saved to {output_path}")

if __name__ == "__main__":
    create_magazine_cover()
