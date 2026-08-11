# -*- coding: utf-8 -*-
"""Post pass: atmospheric softening + gentle bloom, then contact sheets.

Run automatically by build.py.  System python3 (numpy + PIL).
    python3 post.py <tag>
"""
import sys, os
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
TAG = sys.argv[1] if len(sys.argv) > 1 else "prev"

BG = np.array([0x0c, 0x0c, 0x0c], dtype=np.float64) / 255.0

SOFT_SIGMA_REL = 0.00045     # blur sigma as a fraction of image width
BLOOM_AMOUNT   = 0.16
BLOOM_THRESH   = 0.34
BLOOM_SIGMA_REL = 0.020


def gblur(a, sigma):
    if sigma < 0.35:
        return a
    rad = int(np.ceil(3.0 * sigma))
    x = np.arange(-rad, rad + 1, dtype=np.float64)
    k = np.exp(-x * x / (2.0 * sigma * sigma))
    k /= k.sum()
    out = np.zeros_like(a)
    pad = np.pad(a, ((rad, rad), (0, 0), (0, 0)), mode='edge')
    for i, w in enumerate(k):
        out += w * pad[i:i + a.shape[0]]
    a2 = out
    out = np.zeros_like(a2)
    pad = np.pad(a2, ((0, 0), (rad, rad), (0, 0)), mode='edge')
    for i, w in enumerate(k):
        out += w * pad[:, i:i + a.shape[1]]
    return out


def gblur_fast(a, sigma, ds=6):
    """Large-radius blur via downsample -> blur -> upsample."""
    h, w = a.shape[:2]
    hh, ww = max(2, h // ds), max(2, w // ds)
    small = np.asarray(Image.fromarray(np.clip(a * 255, 0, 255).astype(np.uint8))
                       .resize((ww, hh), Image.BILINEAR)).astype(np.float64) / 255.0
    small = gblur(small, sigma / ds)
    big = np.asarray(Image.fromarray(np.clip(small * 255, 0, 255).astype(np.uint8))
                     .resize((w, h), Image.BILINEAR)).astype(np.float64) / 255.0
    return big


def load(p):
    im = Image.open(p).convert("RGBA")
    return np.asarray(im).astype(np.float64) / 255.0


def save(a, p):
    Image.fromarray(np.clip(a * 255.0 + 0.5, 0, 255).astype(np.uint8)).save(p)
    print("[post]", p)


def soften_rgba(a):
    """Blur in premultiplied space so the alpha edge does not halo."""
    rgb = a[..., :3]
    al = a[..., 3:4]
    pm = np.concatenate([rgb * al, al], axis=-1)
    sig = SOFT_SIGMA_REL * a.shape[1]
    pm = gblur(pm, sig)
    al2 = np.clip(pm[..., 3:4], 0.0, 1.0)
    rgb2 = np.where(al2 > 1e-4, pm[..., :3] / np.maximum(al2, 1e-4), 0.0)
    return np.concatenate([np.clip(rgb2, 0, 1), al2], axis=-1)


def bloom_rgba(a):
    rgb = a[..., :3]
    al = a[..., 3:4]
    pm = rgb * al
    lum = pm @ np.array([0.2126, 0.7152, 0.0722])
    mask = np.clip((lum - BLOOM_THRESH) / (1.0 - BLOOM_THRESH), 0.0, 1.0)[..., None]
    src = pm * mask
    src4 = np.concatenate([src, np.zeros_like(al)], axis=-1)
    b = gblur_fast(src4, BLOOM_SIGMA_REL * a.shape[1])[..., :3]
    pm2 = pm + b * BLOOM_AMOUNT
    al2 = np.clip(al + b.mean(axis=-1, keepdims=True) * BLOOM_AMOUNT * 0.55, 0.0, 1.0)
    rgb2 = np.where(al2 > 1e-4, pm2 / np.maximum(al2, 1e-4), 0.0)
    return np.concatenate([np.clip(rgb2, 0, 1), al2], axis=-1)


def over(fg, bg_rgb):
    al = fg[..., 3:4]
    return fg[..., :3] * al + bg_rgb * (1.0 - al)


def main():
    raw = os.path.join(HERE, "raw_%s.png" % TAG)
    rawsky = os.path.join(HERE, "raw_sky_%s.png" % TAG)
    if not os.path.exists(raw):
        print("missing", raw); return

    a = load(raw)
    a = soften_rgba(a)
    a = bloom_rgba(a)
    out_name = "fuji_final.png" if TAG == "final" else "preview_%s.png" % TAG
    save(a, os.path.join(HERE, out_name))

    flat = over(a, BG[None, None, :])
    save(np.concatenate([flat, np.ones_like(a[..., 3:4])], axis=-1),
         os.path.join(HERE, "check_on_bg_%s.png" % TAG))

    if os.path.exists(rawsky):
        s = load(rawsky)
        s3 = gblur(s[..., :3], 0.0006 * s.shape[1])
        sky = np.concatenate([np.clip(s3, 0, 1), np.ones_like(s[..., 3:4])], axis=-1)
        sky_name = "fuji_sky.png" if TAG == "final" else "preview_sky_%s.png" % TAG
        save(sky, os.path.join(HERE, sky_name))
        comp = over(a, sky[..., :3])
        save(np.concatenate([comp, np.ones_like(a[..., 3:4])], axis=-1),
             os.path.join(HERE, "check_with_sky_%s.png" % TAG))


main()
