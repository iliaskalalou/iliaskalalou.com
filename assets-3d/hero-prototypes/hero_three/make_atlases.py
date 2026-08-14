#!/usr/bin/env python3
"""Build the two texture atlases the browser actually downloads.

1. leaf_atlas   -- the four momiji foliage-card cluster atlases packed 2x2.
                   One texture => the whole canopy is ONE draw call.
2. sprite_atlas -- the three 4x4 tumbling-leaf sheets packed into one grid,
                   downscaled to the largest size ever drawn on screen.

Straight (unassociated) alpha in, straight alpha out, but every resample is
done PREMULTIPLIED so transparent black never bleeds into the leaf edges.
"""
import os, subprocess, sys
from PIL import Image

SRC_CLUSTER = "/Users/iliaskalalou/iliaskalalou.com/assets-3d/momiji/atlas/cluster_%d.png"
SRC_SHEET = [
    "/Users/iliaskalalou/iliaskalalou.com/public/leaves/momiji_leaf_sheet_ember.png",
    "/Users/iliaskalalou/iliaskalalou.com/public/leaves/momiji_leaf_sheet_crimson.png",
    "/Users/iliaskalalou/iliaskalalou.com/public/leaves/momiji_leaf_sheet_amber.png",
]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets")          # the .webp the browser downloads
TMP = os.path.join(ROOT, "build")           # the intermediate .png, never shipped
os.makedirs(OUT, exist_ok=True)
os.makedirs(TMP, exist_ok=True)


def resize_straight(im, size):
    """Resample RGBA that carries STRAIGHT alpha without dark fringing."""
    import numpy as np
    im = im.convert("RGBA")
    arr = np.asarray(im).astype("float32") / 255.0
    al = arr[..., 3:4]
    arr[..., :3] *= al
    pm = Image.fromarray((arr * 255.0 + 0.5).astype("uint8"), "RGBA")
    pm = pm.resize(size, Image.LANCZOS)
    arr = np.asarray(pm).astype("float32") / 255.0
    al = arr[..., 3:4]
    safe = np.where(al > 1e-4, al, 1.0)
    arr[..., :3] = np.clip(arr[..., :3] / safe, 0.0, 1.0)
    arr[..., 3:4] = al
    return Image.fromarray((arr * 255.0 + 0.5).astype("uint8"), "RGBA")


def webp(png_path, quality=88, lossless=False, alpha_q=100, outdir=None):
    out = os.path.join(outdir or os.path.dirname(png_path),
                       os.path.basename(png_path)[:-4] + ".webp")
    cmd = ["cwebp", "-quiet", "-alpha_q", str(alpha_q), "-metadata", "none"]
    if lossless:
        cmd += ["-lossless", "-z", "9"]
    else:
        cmd += ["-q", str(quality), "-m", "6", "-af"]
    cmd += [png_path, "-o", out]
    subprocess.run(cmd, check=True)
    return out


# ---------------------------------------------------------------- leaf atlas
CELL = int(sys.argv[1]) if len(sys.argv) > 1 else 512
atlas = Image.new("RGBA", (CELL * 2, CELL * 2), (0, 0, 0, 0))
for i in range(4):
    im = Image.open(SRC_CLUSTER % i)
    im = resize_straight(im, (CELL, CELL))
    col, row = i % 2, i // 2          # PIL row 0 == TOP
    atlas.paste(im, (col * CELL, row * CELL))
p = os.path.join(TMP, "leaf_atlas.png")
atlas.save(p)
w = webp(p, quality=78, alpha_q=70, outdir=OUT)
print("leaf_atlas   %dx%d  png=%d  webp=%d" % (CELL * 2, CELL * 2,
      os.path.getsize(p), os.path.getsize(w)))

# -------------------------------------------------------------- sprite atlas
SC = int(sys.argv[2]) if len(sys.argv) > 2 else 128
COLS, ROWS = 8, 6                      # 48 cells = 3 sheets x 16 frames
sprite = Image.new("RGBA", (COLS * SC, ROWS * SC), (0, 0, 0, 0))
for s, path in enumerate(SRC_SHEET):
    sheet = Image.open(path).convert("RGBA")
    src_cell = sheet.width // 4
    for f in range(16):
        sx, sy = (f % 4) * src_cell, (f // 4) * src_cell
        cellim = sheet.crop((sx, sy, sx + src_cell, sy + src_cell))
        cellim = resize_straight(cellim, (SC, SC))
        idx = s * 16 + f
        sprite.paste(cellim, ((idx % COLS) * SC, (idx // COLS) * SC))
p = os.path.join(TMP, "sprite_atlas.png")
sprite.save(p)
w = webp(p, quality=82, alpha_q=100, outdir=OUT)
print("sprite_atlas %dx%d  png=%d  webp=%d" % (COLS * SC, ROWS * SC,
      os.path.getsize(p), os.path.getsize(w)))
