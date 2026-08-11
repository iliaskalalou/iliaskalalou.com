# -*- coding: utf-8 -*-
"""
Authored 2D cloud band: density + illumination, baked to a PNG that drives the
volume in build.py.

Procedural 3D noise inside the volume kept integrating along the view ray into a
flat horizontal smear.  Painting the band in 2D and extruding it along the view
axis gives exact control of what this treatment depends on: a defined bumpy top
edge, real gaps, a band that concentrates where the mountain is and dies away
before the right of the frame, and light that strikes from the left and below.

  R channel = density
  G channel = illumination

Run directly to write previews:  python3 cloudmap.py
"""
import numpy as np


def _blur(a, rx, rz):
    """separable box blur, run twice -> near-gaussian"""
    out = a
    for _ in range(2):
        if rz > 0:
            k = np.ones(2 * rz + 1) / (2 * rz + 1)
            out = np.apply_along_axis(lambda m: np.convolve(m, k, 'same'), 0, out)
        if rx > 0:
            k = np.ones(2 * rx + 1) / (2 * rx + 1)
            out = np.apply_along_axis(lambda m: np.convolve(m, k, 'same'), 1, out)
    return out


def _fbm2(X, Z, rng, octaves=5, base=6.0, aspect=3.0):
    out = np.zeros_like(X)
    amp, freq, norm = 1.0, 1.0, 0.0
    for _ in range(octaves):
        fx, fz = base * freq / aspect, base * freq
        ph = rng.uniform(0, 2 * np.pi, 6)
        out += amp * (
            np.sin(fx * X + ph[0] + 0.9 * np.sin(fz * Z + ph[1]))
            * np.cos(fz * Z + ph[2] + 0.9 * np.sin(fx * X + ph[3]))
            + 0.6 * np.sin(1.7 * fx * X + ph[4]) * np.cos(1.3 * fz * Z + ph[5]))
        norm += amp * 1.6
        amp *= 0.52
        freq *= 2.07
    return out / norm


def _ss(a, b, t):
    t = np.clip((t - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def cloud_map(W=1800, H=560, seed=5, aspect=6.84):
    """float RGB (H, W, 3); row 0 = top of the volume box, x = -1 .. +1.

    `aspect` is box_half_x / box_half_z of the volume this map drives.  Puff
    widths are given in local x and heights in local z, so without it every
    cloud comes out ~7x too flat and the band reads as smooth dunes."""
    rng = np.random.default_rng(seed)
    xs = np.linspace(-1.0, 1.0, W)
    zs = np.linspace(1.0, -1.0, H)
    X, Z = np.meshgrid(xs, zs)

    # ---- centreline ---------------------------------------------------------
    base = (0.00
            + 0.105 * np.sin(2.30 * xs + 0.55)
            + 0.055 * np.sin(4.70 * xs - 1.30)
            + 0.028 * np.sin(9.10 * xs + 2.40))

    # ---- bumpy top: overlapping cumulus puffs -------------------------------
    top = base + 0.035
    for _ in range(170):                                     # cauliflower
        c = rng.uniform(-1.15, 1.15)
        w = np.exp(rng.uniform(np.log(0.005), np.log(0.022)))
        top = np.maximum(top, base + aspect * w * rng.uniform(0.45, 0.95)
                         * np.exp(-((xs - c) / w) ** 2))
    for _ in range(58):                                      # main puffs
        c = rng.uniform(-1.15, 1.15)
        w = np.exp(rng.uniform(np.log(0.018), np.log(0.085)))
        top = np.maximum(top, base + aspect * w * rng.uniform(0.30, 0.68)
                         * np.exp(-((xs - c) / w) ** 2))
    for c, w, r in ((-0.52, 0.062, 0.72), (-0.22, 0.048, 0.60),
                    (0.02, 0.056, 0.66), (0.26, 0.043, 0.55)):
        top = np.maximum(top, base + aspect * w * r * np.exp(-((xs - c) / w) ** 2))

    # gaps thin the band instead of slicing vertical slots through it
    for c, w, d in ((-0.335, 0.048, 0.84), (-0.055, 0.030, 0.62),
                    (0.135, 0.052, 0.78), (-0.62, 0.038, 0.58)):
        top = base + (top - base) * (1.0 - d * np.exp(-((xs - c) / w) ** 2))

    # the mass itself tapers away toward the right, not just its brightness
    env_t = np.clip(_ss(-1.06, -0.80, xs) * (1.0 - _ss(-0.02, 0.34, xs)), 0, 1)
    top = base + (top - base) * (0.10 + 0.90 * env_t)

    bot = (base - 0.098 - 0.040 * np.sin(3.3 * xs + 0.9)
           - 0.022 * np.sin(7.7 * xs - 2.1) - 0.016 * np.sin(17.3 * xs + 0.4)
           - 0.010 * np.sin(31.0 * xs - 1.7))

    TOP = np.broadcast_to(top, (H, W))
    BOT = np.broadcast_to(bot, (H, W))

    soft_t = 0.022 + 0.022 * np.abs(np.sin(5.0 * X))
    dens = _ss(0.0, 1.0, (TOP - Z) / soft_t) * _ss(-0.090, 0.030, Z - BOT)

    n1 = _fbm2(X, Z, rng, octaves=5, base=9.0, aspect=2.6)
    dens *= np.clip(0.70 + 0.50 * (n1 * 0.5 + 0.5), 0, 1.25)

    # ---- envelope: dense across the mountain, gone before the right edge ----
    # visible window in these coordinates is roughly x = -0.43 .. +0.63
    env = np.clip(_ss(-1.00, -0.72, xs) * (1.0 - _ss(0.05, 0.36, xs)), 0, 1)
    dens *= np.broadcast_to(env, (H, W))

    # ---- wisps trailing below ----------------------------------------------
    below = np.clip(BOT - Z, 0, None)
    n2 = _fbm2(X * 1.6, Z * 0.8, rng, octaves=4, base=15.0, aspect=5.0)
    wisp = np.exp(-below / 0.085) * np.clip(n2 * 0.5 + 0.40, 0, 1) * (Z < BOT)
    dens = np.clip(dens + 0.20 * wisp * np.broadcast_to(env, (H, W)), 0, 1)

    # ---- illumination -------------------------------------------------------
    # treat the density field as a surface: light arrives from the left and from
    # below (the sun is under the horizon), so the left/under faces of every
    # puff glow and the light dies as it works up into the mass.
    k = W / 1800.0                      # blur radii are in pixels
    d_s = _blur(dens, int(round(5 * k)), int(round(3 * k)))
    gz, gx = np.gradient(d_s)
    gz = -gz                      # row 0 is the top, so flip to make +z = up
    g = np.sqrt(gx ** 2 + gz ** 2) + 1e-6
    Lx, Lz = -0.95, 0.30      # sunset light comes in almost horizontally
    lit = np.clip(-(gx * Lx + gz * Lz) / g, 0, 1) ** 1.15
    surf = np.clip(g / (np.percentile(g, 99.5) + 1e-6), 0, 1) ** 0.60
    surf = _blur(surf, int(round(6 * k)), int(round(4 * k)))

    # as in the reference: the band is brightest just under its lit top edge
    # and its underside sinks into blue shadow
    down = np.clip(TOP - Z, 0, None)
    base_glow = 0.16 + 0.58 * np.exp(-down / 0.150)
    illum = dens * (base_glow + 1.70 * lit * surf)
    illum *= np.broadcast_to(1.25 - 0.80 * _ss(-0.95, 0.60, xs), (H, W))
    illum = _blur(illum, int(round(3 * k)), int(round(2 * k)))

    out = np.zeros((H, W, 3), dtype=np.float32)
    out[..., 0] = np.clip(dens, 0, 1)
    out[..., 1] = np.clip(illum, 0, 1)
    return out


if __name__ == "__main__":
    from PIL import Image
    m = cloud_map()
    Image.fromarray((m * 255).astype(np.uint8)).save("cloudmap_preview.png")
    look = np.zeros(m.shape)
    look[..., 0] = m[..., 1] * 0.90
    look[..., 1] = m[..., 1] * 0.52
    look[..., 2] = m[..., 1] * 0.36
    look += m[..., 0][..., None] * np.array([0.012, 0.014, 0.020])
    Image.fromarray((np.clip(look, 0, 1) ** (1 / 2.2) * 255).astype(np.uint8)).save(
        "cloudmap_look.png")
    print("dens: mean %.3f p99 %.2f   illum: mean %.3f p99 %.2f max %.2f"
          % (m[..., 0].mean(), np.percentile(m[..., 0], 99),
             m[..., 1].mean(), np.percentile(m[..., 1], 99), m[..., 1].max()))
