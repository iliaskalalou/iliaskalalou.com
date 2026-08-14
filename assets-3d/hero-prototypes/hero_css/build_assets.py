#!/usr/bin/env python3
"""
Asset pipeline for the CSS-3D hero.

Everything the browser pays for is produced here: crop to content, grade,
bake the atmospheric blur (so the runtime needs no CSS filter on a
transform-animated layer), resize with a correct premultiplied filter, then
encode to WebP + AVIF.

Two encoder tricks that matter on foliage with 50% alpha coverage:
  * alpha floor  - the render leaves a dust of alpha 1..14 that is invisible
                   but expensive; snapping it to zero costs ~10% of the file.
  * RGB bleed    - dilate colour outward into transparent pixels so the codec
                   never has to encode a colour cliff at every leaf edge, and
                   so chroma subsampling cannot pull black into the edges.
"""
import os, subprocess
import numpy as np
from PIL import Image, ImageFilter

SRC = "/Users/iliaskalalou/iliaskalalou.com/assets-3d"
LEAF = "/Users/iliaskalalou/iliaskalalou.com/public/leaves"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "a")
os.makedirs(OUT, exist_ok=True)


def resize_rgba(im, w, h):
    a = np.asarray(im, dtype=np.float32) / 255.0
    al = a[:, :, 3:4]
    pm = np.concatenate([a[:, :, :3] * al, al], axis=2)
    pmi = Image.fromarray((pm * 255.0 + 0.5).astype(np.uint8), "RGBA").resize((w, h), Image.LANCZOS)
    b = np.asarray(pmi, dtype=np.float32) / 255.0
    bal = np.clip(b[:, :, 3:4], 1e-5, 1.0)
    return Image.fromarray((np.concatenate(
        [np.clip(b[:, :, :3] / bal, 0, 1), b[:, :, 3:4]], 2) * 255.0 + 0.5).astype(np.uint8), "RGBA")


def blur_rgba(im, radius):
    if radius <= 0:
        return im
    a = np.asarray(im, dtype=np.float32) / 255.0
    al = a[:, :, 3:4]
    pm = np.concatenate([a[:, :, :3] * al, al], axis=2)
    pmi = Image.fromarray((pm * 255.0 + 0.5).astype(np.uint8), "RGBA").filter(
        ImageFilter.GaussianBlur(radius))
    b = np.asarray(pmi, dtype=np.float32) / 255.0
    bal = np.clip(b[:, :, 3:4], 1e-5, 1.0)
    return Image.fromarray((np.concatenate(
        [np.clip(b[:, :, :3] / bal, 0, 1), b[:, :, 3:4]], 2) * 255.0 + 0.5).astype(np.uint8), "RGBA")


def grade(im, gain=1.0, gamma=1.0, sat=1.0, tint=(1.0, 1.0, 1.0)):
    a = np.asarray(im, dtype=np.float32) / 255.0
    rgb = np.clip(a[:, :, :3], 0, 1) ** gamma * gain * np.array(tint, np.float32)
    if sat != 1.0:
        lum = (rgb * np.array([0.2126, 0.7152, 0.0722], np.float32)).sum(2, keepdims=True)
        rgb = lum + (rgb - lum) * sat
    return Image.fromarray((np.concatenate(
        [np.clip(rgb, 0, 1), a[:, :, 3:4]], 2) * 255.0 + 0.5).astype(np.uint8), "RGBA")


def grain(im, amount, seed=7):
    if amount <= 0:
        return im
    rng = np.random.default_rng(seed)
    a = np.asarray(im, dtype=np.float32)
    n = rng.normal(0.0, amount, size=a.shape[:2] + (1,)).astype(np.float32) * (a[:, :, 3:4] / 255.0)
    a[:, :, :3] = np.clip(a[:, :, :3] + n, 0, 255)
    return Image.fromarray(a.astype(np.uint8), "RGBA")


def alpha_floor(im, thr=14, knee=34):
    a = np.asarray(im).astype(np.float32)
    al = a[:, :, 3]
    t = np.clip((al - thr) / (knee - thr), 0, 1)
    a[:, :, 3] = np.where(al <= thr, 0, np.where(al >= knee, al, al * t * t * (3 - 2 * t)))
    return Image.fromarray(a.astype(np.uint8), "RGBA")


def bleed(im, passes=8):
    a = np.asarray(im).astype(np.float32)
    rgb, al = a[:, :, :3].copy(), a[:, :, 3]
    known = (al > 0).astype(np.float32)
    for _ in range(passes):
        wk = np.asarray(Image.fromarray((known * 255).astype(np.uint8)).filter(
            ImageFilter.BoxBlur(1)), dtype=np.float32) / 255.0
        acc = np.zeros_like(rgb)
        for c in range(3):
            acc[:, :, c] = np.asarray(Image.fromarray(
                np.clip(rgb[:, :, c] * known, 0, 255).astype(np.uint8)).filter(
                ImageFilter.BoxBlur(1)), dtype=np.float32)
        m = (known < 0.5) & (wk > 0.01)
        for c in range(3):
            rgb[:, :, c] = np.where(m, acc[:, :, c] / np.maximum(wk, 1e-3), rgb[:, :, c])
        known = np.maximum(known, m.astype(np.float32))
        if known.mean() > 0.999:
            break
    return Image.fromarray(np.concatenate(
        [np.clip(rgb, 0, 255), al[:, :, None]], 2).astype(np.uint8), "RGBA")


def vgrad(im, start, end, floor):
    """Multiply RGB by a vertical ramp from 1.0 at `start` (fraction of the
    height) down to `floor` at `end`. Sinks a trunk or a base into the dark
    without touching alpha, so the silhouette survives."""
    a = np.asarray(im, dtype=np.float32)
    h = a.shape[0]
    y = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    t = np.clip((y - start) / max(end - start, 1e-6), 0, 1)
    k = 1.0 - (1.0 - floor) * (t * t * (3 - 2 * t))
    a[:, :, :3] *= k[:, :, None]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGBA")


def bbox_alpha(im, thr=2):
    a = np.asarray(im)[:, :, 3]
    c = np.nonzero(a.max(0) > thr)[0]
    r = np.nonzero(a.max(1) > thr)[0]
    return int(c.min()), int(r.min()), int(c.max()) + 1, int(r.max()) + 1


rows = []


def encode(im, name, webp_q, alpha_q=62, avif_q=None, avif_qa=70):
    png = os.path.join(OUT, name + ".png")
    im.save(png)
    webp = os.path.join(OUT, name + ".webp")
    subprocess.run(["cwebp", "-q", str(webp_q), "-alpha_q", str(alpha_q), "-m", "6",
                    "-sharp_yuv", "-metadata", "none", png, "-o", webp],
                   check=True, capture_output=True)
    av = 0
    if avif_q is not None:
        avif = os.path.join(OUT, name + ".avif")
        subprocess.run(["avifenc", "-s", "4", "-q", str(avif_q), "--qalpha", str(avif_qa),
                        "-j", "all", png, avif], check=True, capture_output=True)
        av = os.path.getsize(avif)
    os.remove(png)
    rows.append((name, im.size, os.path.getsize(webp), av))


# ---------------------------------------------------------------- momiji ----
# Re-rendered from tree.blend at a 1.34x wider FOV (rerender_tree.py) so the
# canopy no longer touches the frame. The far-right 12% is dropped: it is the
# one flank that still clips, and it sits off the right of the viewport.
tree = Image.open(os.path.join(HERE, "tree_margin.png")).convert("RGBA")
tree = tree.crop((0, 220, int(1716 * 0.88), 2144))
# Four cuts, chosen by srcset: the byte cost of a retina-sharp momiji falls
# only on the screens that can show it.
for tag, W, q in (("tree", 800, 50), ("tree_2x", 1000, 54),
                  ("tree_sm", 430, 56), ("tree_md", 620, 54)):
    r = resize_rgba(tree, W, round(tree.size[1] * W / tree.size[0]))
    r = grade(r, gain=0.86, gamma=1.07, sat=1.00)
    r = vgrad(r, 0.60, 1.00, 0.34)      # the trunk sinks into the ground haze
    r = bleed(alpha_floor(r))
    encode(r, tag, q, alpha_q=62)

# ---------------------------------------------------------------- pagoda ----
pag = Image.open(os.path.join(SRC, "pagoda_dusk/pagoda_final.png")).convert("RGBA")
x0, y0, x1, y1 = bbox_alpha(pag)
pag = pag.crop((max(0, x0 - 6), max(0, y0 - 6), min(pag.size[0], x1 + 6), min(pag.size[1], y1 + 6)))
PW = 560
p = resize_rgba(pag, PW, round(pag.size[1] * PW / pag.size[0]))
p = blur_rgba(p, 0.65)                                   # mid distance
p = grade(p, gain=0.80, gamma=1.13, sat=0.70, tint=(0.95, 0.98, 1.11))
p = grain(bleed(alpha_floor(p, 8, 24)), 1.4, seed=11)
encode(p, "pagoda", 76, alpha_q=70, avif_q=48, avif_qa=72)

# ------------------------------------------------------------------ fuji ----
fj = Image.open(os.path.join(SRC, "fuji_minimal/fuji_final.png")).convert("RGBA")
FW = 1500
f = resize_rgba(fj, FW, round(fj.size[1] * FW / fj.size[0]))
f = blur_rgba(f, 2.5)                                   # kilometres of air
f = grade(f, gain=0.74, gamma=1.24, sat=0.66, tint=(0.94, 0.97, 1.12))
f = grain(f, 2.2, seed=3)                               # kills 8-bit banding
encode(f, "fuji", 72, alpha_q=70, avif_q=48, avif_qa=70)

# ----------------------------------------------------------- leaf sheets ----
# 1024 -> 512 (128px cells). Largest leaf ever drawn is 130 device px at
# 1440x900 / DPR 1.5, so a 128px cell is 1:1 and 1024 was 4x wasted bytes.
for nm in ("ember", "crimson", "amber"):
    im = Image.open(os.path.join(LEAF, "momiji_leaf_sheet_%s.png" % nm)).convert("RGBA")
    s = resize_rgba(im, 512, 512)
    s = bleed(alpha_floor(s, 6, 20), passes=6)
    encode(s, "leaf_" + nm, 78, alpha_q=76)

tw = ta = 0
print("\n%-10s %-12s %10s %10s" % ("asset", "size", "webp", "avif"))
for n, sz, w, a in rows:
    print("%-10s %-12s %10d %10d" % (n, "%dx%d" % sz, w, a))
    tw += w
    ta += a
print("%-10s %-12s %10d %10d" % ("SUM", "", tw, ta))
