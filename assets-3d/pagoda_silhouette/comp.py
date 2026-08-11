"""Composite the RGBA render over the page background #0c0c0c, optionally beside
the momiji card so the two warm masses can be compared for loudness."""
import sys, os
from PIL import Image, ImageStat
import numpy as np

BG = (12, 12, 12)

def over(path, out, w=None):
    im = Image.open(path).convert("RGBA")
    if w:
        h = int(im.height * w / im.width)
        im = im.resize((w, h), Image.LANCZOS)
    bg = Image.new("RGBA", im.size, BG + (255,))
    bg.alpha_composite(im)
    bg.convert("RGB").save(out)
    a = np.asarray(im)[..., 3].astype(np.float32) / 255.0
    rgb = np.asarray(bg.convert("RGB")).astype(np.float32)
    lum = rgb @ np.array([0.2126, 0.7152, 0.0722])
    print(f"{os.path.basename(path)}  size={im.size}  cover={a.mean():.3f}  "
          f"mean_lum={lum.mean():.1f}  p99_lum={np.percentile(lum,99):.1f}  "
          f"max_lum={lum.max():.1f}  frac_lum>40={np.mean(lum>40):.4f}")
    return bg


def side_by_side(pag, tree, out):
    H = 900
    a = Image.open(pag).convert("RGBA")
    b = Image.open(tree).convert("RGBA")
    a = a.resize((int(a.width * H / a.height), H), Image.LANCZOS)
    b = b.resize((int(b.width * H / b.height), H), Image.LANCZOS)
    canvas = Image.new("RGBA", (a.width + b.width + 80, H), BG + (255,))
    canvas.alpha_composite(a, (0, 0))
    canvas.alpha_composite(b, (a.width + 80, 0))
    canvas.convert("RGB").save(out)
    print("wrote", out)


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[0] == "pair":
        side_by_side(args[1], args[2], args[3])
    else:
        over(args[0], args[1], int(args[2]) if len(args) > 2 else None)
