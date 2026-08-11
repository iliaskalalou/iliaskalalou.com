# -*- coding: utf-8 -*-
"""
Mount Fuji -- TREATMENT A (ATMOSPHERIC), background layer for a website hero.

  /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
      --python build.py -- --res 2400x1200 --tag final --samples 96

WHY IT LOOKS LIKE THIS
----------------------
The silhouette is not eyeballed. The owner's photograph was fitted with
z = A*exp(-r/L); it gives L/A = 1.572 (rms 5.5 px over 900 px of ridge line)
and a 32.5 deg slope at the summit. That exponential is what makes the flanks
CONCAVE and flare at the base -- a straight cone reads as "generic mountain".
The same photo says the cloud band sits 0.51 of the relief below the summit
and that the visible cone above it is 2.24 x relief wide. Those three numbers
drive the whole composition.

The photograph is a BRIGHT-sky picture; the hero page is #0c0c0c. So the
reference values are transposed by a constant factor (~0.58) into a dark key,
preserving the relationships rather than the absolute levels. Measured from
the photo and kept: the mountain is nearly NEUTRAL/COOL and very low contrast
(snow 133, lit flank 157, shadowed flank 106 -- a 50-value spread), while the
only strongly warm element is the cloud band. That is also the right design
call: the momiji on the right owns the warm end of the palette; if Fuji were
warm brown it would compete with both the tree and a face.

Shading is BAKED PER-VERTEX in numpy (sunset terminator + wrapped Lambert +
cavity + snow + haze) and shown through a pure Emission shader, because
"quiet enough to sit behind a portrait" is a number, not a light rig.

film_transparent -> the sky is a SEPARATE render (fuji_sky.png).
"""

import bpy, sys, os, math, time, subprocess
import numpy as np

# --------------------------------------------------------------------------
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
def arg(name, default):
    return argv[argv.index(name) + 1] if name in argv else default

RES_W, RES_H = [int(v) for v in arg("--res", "1200x600").split("x")]
TAG        = arg("--tag", "prev")
SAMPLES    = int(arg("--samples", "48"))
GRID_SCALE = float(arg("--grid", "1.0"))
DO_POST    = arg("--post", "1") == "1"

HERE = os.path.dirname(os.path.abspath(__file__))

# ---- geometry, from the fit to the reference photograph -------------------
RELIEF   = 3000.0                 # summit above the asymptotic base, metres
L        = 1.572 * RELIEF         # 4716 m  -> 32.5 deg at the summit
CUSP     = 210.0                  # rounds the mathematical apex
CLOUD_FRAC = 0.51                 # cloud band, in reliefs below the summit
CLOUD_Z  = RELIEF * (1.0 - CLOUD_FRAC)      # 1470 m

# ---- framing --------------------------------------------------------------
CONE_WIDTH_FRAC = 0.64            # visible cone as a fraction of frame width
SUMMIT_Y_FRAC   = 0.28            # summit, from the top of the frame
SUMMIT_X_FRAC   = 0.335           # summit, from the left  (portrait centre,
                                  #   momiji right -> Fuji leans left)
CAM_D  = 22000.0
CAM_Z  = 700.0
SENSOR = 36.0

CONE_HALF_W = L * math.log(1.0 / (1.0 - CLOUD_FRAC))     # 3363 m
FRAME_W = (2.0 * CONE_HALF_W) / CONE_WIDTH_FRAC          # 10508 m
FRAME_H = FRAME_W * RES_H / RES_W

SUN_AZ = math.radians(14.0)       # grazing from the right, just behind
SUN_EL = math.radians(7.0)

# sunset terminator: below this the slopes have lost the sun
REACH_LO, REACH_HI = 1450.0, 2150.0
SNOWLINE = RELIEF - 0.20 * RELIEF                        # 2400 m

FOG_NEAR, FOG_FAR = 9000.0, 21000.0   # alpha ramp on camera distance:
                                      # dissolves the near ground, no hard edge

# ---- palette (sRGB 0-255) -- reference values x ~0.58 ---------------------
# Stated as FINAL screen colours and interpolated, not as albedo x light:
# the product has to land on a number, and a linear-space albedo does not.
C_ROCK_DARK = ( 18,  26,  45)   # rock below the terminator: indigo shadow
C_ROCK_LIT  = ( 86,  73,  69)   # rock in the last grazing sun: barely warm
C_SNOW_DARK = ( 38,  46,  62)
C_SNOW_LIT  = (132, 124, 124)   # NOT white -- reference snow reads 133/255
C_ABYSS     = ( 10,  12,  19)   # what the base falls to, ~= page background
RIM         = (150,  84,  38)
HAZE        = ( 34,  42,  62)

C_CLOUD_WARM = (188, 128,  98)
C_CLOUD_MID  = (100,  80,  82)
C_CLOUD_DARK = ( 34,  40,  58)
C_MIST       = ( 24,  32,  50)

S_ZENITH  = (14, 18, 31)
S_MID     = (24, 30, 46)
S_HORIZON = (42, 43, 54)
S_EMBER   = ( 68, 38, 17)
S_BELOW   = (10, 10, 13)


def srgb2lin(c):
    c = np.asarray(c, dtype=np.float64) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


# --------------------------------------------------------------------------
def _fade(t):
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def vnoise2(u, v, nu, nv, seed):
    rng = np.random.default_rng(seed)
    g = (rng.random((nu, nv)).astype(np.float32) * 2.0 - 1.0)
    uu = u * nu; vv = v * nv
    i0 = np.floor(uu).astype(np.int64); j0 = np.floor(vv).astype(np.int64)
    fu = _fade(uu - i0).astype(np.float32); fv = _fade(vv - j0).astype(np.float32)
    i0m = np.mod(i0, nu); i1m = np.mod(i0 + 1, nu)
    j0m = np.mod(j0, nv); j1m = np.mod(j0 + 1, nv)
    a = g[i0m, j0m]; b = g[i1m, j0m]; c = g[i0m, j1m]; d = g[i1m, j1m]
    return (a * (1 - fu) + b * fu) * (1 - fv) + (c * (1 - fu) + d * fu) * fv


def fbm(u, v, nu, nv, octaves, seed, lac_u=2.0, lac_v=1.7, gain=0.5):
    out = np.zeros_like(u, dtype=np.float32); amp = 1.0; tot = 0.0
    cu, cv = float(nu), float(nv)
    for o in range(octaves):
        out += amp * vnoise2(u, v, max(2, int(round(cu))), max(2, int(round(cv))), seed + 977 * o)
        tot += amp; amp *= gain; cu *= lac_u; cv *= lac_v
    return out / tot


def sstep(a, b, x):
    t = np.clip((x - a) / (b - a + 1e-12), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


# --------------------------------------------------------------------------
def build_grid_mesh(name, co, nx, ny, rgba, origin=(0.0, 0.0, 0.0)):
    co = co - np.asarray(origin, dtype=np.float64)[None, :]
    me = bpy.data.meshes.new(name)
    me.vertices.add(co.shape[0])
    me.vertices.foreach_set("co", co.astype(np.float32).ravel())
    i = np.arange(nx - 1, dtype=np.int64)[None, :]
    j = np.arange(ny - 1, dtype=np.int64)[:, None]
    v00 = (j * nx + i).ravel()
    quads = np.stack([v00, v00 + 1, v00 + 1 + nx, v00 + nx], axis=1).astype(np.int64)
    nf = quads.shape[0]
    me.loops.add(nf * 4)
    me.loops.foreach_set("vertex_index", quads.ravel())
    me.polygons.add(nf)
    me.polygons.foreach_set("loop_start", np.arange(0, nf * 4, 4, dtype=np.int64))
    me.update(calc_edges=True)
    col = me.color_attributes.new(name="col", type='FLOAT_COLOR', domain='POINT')
    col.data.foreach_set("color", np.ascontiguousarray(rgba, dtype=np.float32).ravel())
    ob = bpy.data.objects.new(name, me)
    ob.location = origin                   # EEVEE sorts blended objects by origin
    bpy.context.collection.objects.link(ob)
    return ob


def emission_material(name, backface_cull, method='BLENDED'):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    mx  = nt.nodes.new("ShaderNodeMixShader")
    tr  = nt.nodes.new("ShaderNodeBsdfTransparent")
    em  = nt.nodes.new("ShaderNodeEmission")
    at  = nt.nodes.new("ShaderNodeAttribute")
    at.attribute_type = 'GEOMETRY'; at.attribute_name = "col"
    em.inputs["Strength"].default_value = 1.0
    nt.links.new(at.outputs["Color"], em.inputs["Color"])
    nt.links.new(at.outputs["Alpha"], mx.inputs["Fac"])
    nt.links.new(tr.outputs["BSDF"], mx.inputs[1])
    nt.links.new(em.outputs["Emission"], mx.inputs[2])
    nt.links.new(mx.outputs["Shader"], out.inputs["Surface"])
    mat.surface_render_method = method
    mat.use_backface_culling = backface_cull
    return mat


# ==========================================================================
# TERRAIN
# ==========================================================================
def build_terrain(cam_pos):
    t0 = time.time()
    EXT = 11800.0
    nx = int(1900 * GRID_SCALE); ny = int(1250 * GRID_SCALE)
    xs = np.linspace(-EXT, EXT, nx)
    ys = np.linspace(-13500.0, 1900.0, ny)
    X, Y = np.meshgrid(xs, ys, indexing='xy')

    r = np.hypot(X, Y); th = np.arctan2(Y, X)
    u = ((th + math.pi) / (2.0 * math.pi)).astype(np.float32)
    vr = ((np.log(np.clip(r, 250.0, 30000.0)) - math.log(250.0)) /
          (math.log(30000.0) - math.log(250.0))).astype(np.float32)

    # --- concave exponential profile, slightly asymmetric -----------------
    Lm = L * (1.0 + 0.050 * np.sin(th + 0.8) + 0.026 * np.sin(2 * th - 0.4)
                  + 0.014 * np.sin(3 * th + 1.9))
    A = RELIEF / math.exp(-CUSP / L)
    zb = A * np.exp(-np.sqrt(r * r + CUSP * CUSP) / Lm)
    z = zb.copy()

    # --- summit crown: shallow crater with an irregular rim ---------------
    rim_n = fbm(u, np.full_like(u, 0.3, dtype=np.float32), 13, 2, 3, 4401)
    rim_r = 370.0
    z += (46.0 + 40.0 * rim_n) * np.exp(-((r - rim_r) / 195.0) ** 2)
    z += -155.0 * np.clip(1.0 - (r / (rim_r * 1.02)) ** 2, 0.0, 1.0) ** 0.6

    # --- erosion gullies radiating down the cone --------------------------
    # the angular coordinate is warped first, otherwise the grooves comb the
    # cone in perfectly straight rays and it reads as fur
    uw = np.mod(u + 0.013 * fbm(u, vr, 5, 4, 3, 8123), 1.0).astype(np.float32)
    gr = fbm(uw, vr, 44, 3, 5, 1201, lac_u=2.0, lac_v=1.5)
    g1 = (1.0 - np.abs(gr)) ** 3.0
    gr2 = fbm(uw, vr, 95, 4, 3, 7717, lac_u=2.0, lac_v=1.55)
    g2 = (1.0 - np.abs(gr2)) ** 3.0
    env_g = sstep(950.0, 1900.0, zb) * (1.0 - sstep(2760.0, 3020.0, zb))
    z -= (40.0 * g1 + 15.0 * g2) * env_g

    # --- broad ridges + grain ---------------------------------------------
    z += fbm(u, vr, 15, 5, 5, 3313, lac_u=2.0, lac_v=1.9) * 62.0 * \
         sstep(500.0, 1500.0, zb) * (1.0 - sstep(2880.0, 3080.0, zb))
    z += fbm(u, vr, 180, 24, 3, 9091) * 9.0 * sstep(300.0, 900.0, zb)

    # low shoulder on the right flank -- breaks the symmetry
    z += 130.0 * np.exp(-(((X - 5000.0) ** 2 + (Y - 2400.0) ** 2) / (3000.0 ** 2)))

    summit = float(z.max())

    # --- derivatives -------------------------------------------------------
    dx = xs[1] - xs[0]; dy = ys[1] - ys[0]
    gx = np.gradient(z, dx, axis=1); gy = np.gradient(z, dy, axis=0)
    ln = np.sqrt(gx * gx + gy * gy + 1.0)
    nxv, nyv, nzv = -gx / ln, -gy / ln, 1.0 / ln

    lap = np.zeros_like(z)
    lap[1:-1, 1:-1] = (z[1:-1, 2:] + z[1:-1, :-2] + z[2:, 1:-1] + z[:-2, 1:-1]
                       - 4.0 * z[1:-1, 1:-1])
    cav = np.clip(lap / 18.0, -1.0, 1.0)

    # --- snow: altitude driven, irregular line, gullies eat into it -------
    snow_z = (SNOWLINE + 150.0 * fbm(u, vr, 7, 2, 3, 5501)
              + 330.0 * (g1 - 0.20) + 120.0 * g2)
    snow = sstep(-120.0, 150.0, z - snow_z)
    snow *= sstep(0.50, 0.80, nzv)
    snow *= 1.0 - 0.72 * sstep(0.22, 0.78, g1)     # bare rock in the gullies
    snow *= 1.0 - 0.30 * sstep(0.30, 0.85, g2)
    snow = np.clip(snow, 0.0, 1.0)

    # --- light -------------------------------------------------------------
    S = np.array([math.cos(SUN_EL) * math.cos(SUN_AZ),
                  math.cos(SUN_EL) * math.sin(SUN_AZ),
                  math.sin(SUN_EL)])
    lam = nxv * S[0] + nyv * S[1] + nzv * S[2]
    wrapped = np.clip((lam + 1.00) / 2.00, 0.0, 1.0) ** 0.85
    reach = sstep(REACH_LO, REACH_HI, z)          # the sunset terminator
    direct = wrapped * reach
    shade = 1.0 - 0.30 * np.clip(cav, 0.0, 1.0) + 0.13 * np.clip(-cav, 0.0, 1.0)
    # very slight skylight variation so the shadowed slab is not a flat plate
    shade *= 0.93 + 0.10 * np.clip(0.5 + 0.5 * nzv, 0.0, 1.0)

    # "earth shadow" rising up the base. COLOUR and ALPHA collapse on the SAME
    # ramp: a partially-covered silhouette pixel then carries page-background
    # colour, so the antialiased rim along the flank cannot show as a bright
    # ray across the cloud band (it did, for four iterations).
    fade = sstep(1150.0, 2100.0, z)
    deep = (1.0 - fade)[..., None]
    rockd = srgb2lin(C_ROCK_DARK)[None, None, :] * (1 - deep) + srgb2lin(C_ABYSS)[None, None, :] * deep
    snowd = srgb2lin(C_SNOW_DARK)[None, None, :] * (1 - deep) + srgb2lin(C_ABYSS)[None, None, :] * deep
    d3 = direct[..., None]
    rockc = rockd + (srgb2lin(C_ROCK_LIT)[None, None, :] - rockd) * d3
    snowc = snowd + (srgb2lin(C_SNOW_LIT)[None, None, :] - snowd) * d3
    col = rockc + (snowc - rockc) * snow[..., None]
    col *= shade[..., None]
    col += srgb2lin(RIM)[None, None, :] * ((np.clip(lam, 0.0, 1.0) ** 4.0) * reach)[..., None] * 0.55

    # --- atmospheric perspective (upper cone only; the base is already dark)
    hz = np.clip((RELIEF + 150.0 - z) / (RELIEF + 150.0 - 300.0), 0.0, 1.0)
    hmix = ((0.10 + 0.24 * hz ** 1.4) * (1.0 - deep[..., 0]))[..., None]
    col = col * (1.0 - hmix) + srgb2lin(HAZE)[None, None, :] * hmix

    # --- alpha: distance fog, so the near ground melts away, no hard edge --
    d = np.sqrt((X - cam_pos[0]) ** 2 + (Y - cam_pos[1]) ** 2 + (z - cam_pos[2]) ** 2)
    alpha = 0.97 * sstep(FOG_NEAR, FOG_FAR, d)
    alpha *= 0.03 + 0.97 * fade

    rgba = np.concatenate([np.clip(col, 0.0, 4.0), alpha[..., None]], -1).reshape(-1, 4)
    co = np.stack([X.ravel(), Y.ravel(), z.ravel()], 1)
    ob = build_grid_mesh("Fuji", co, nx, ny, rgba)
    # DITHERED, not BLENDED: the cone is edge-on at its own silhouette, so
    # blended fragments stack there and spike alpha (measured 0.42 against 0.16
    # one pixel below) -- a bright rim tracing the whole flank. Dithered
    # transparency writes depth, so each pixel is shaded once.
    ob.data.materials.append(emission_material("M_Fuji", backface_cull=True, method='DITHERED'))
    print("[terrain] %d verts  summit %.0fm  %.1fs" % (co.shape[0], summit, time.time() - t0))
    return ob, summit


# ==========================================================================
# CLOUD BAND  (Rc, z_lo, z_hi, seed, bright, alpha, detail, warm)
# ==========================================================================
SHEETS = [
    (4200.0, 1330.0, 2130.0, 21, 0.74, 0.78, 1.00, 1.00),
    (5600.0, 1200.0, 2000.0, 57, 1.00, 0.92, 1.25, 1.00),
    (7200.0, 1080.0, 1880.0, 93, 0.84, 0.66, 1.60, 0.88),
    (9600.0,  380.0, 1700.0, 131, 0.30, 0.24, 0.55, 0.26),   # faint cool veil
]


def build_sheet(Rc, z_lo, z_hi, seed, bright, alpha_s, detail, warm, idx):
    ns = max(80, int(2000 * GRID_SCALE)); nv = max(24, int(240 * GRID_SCALE))
    XSPAN = 10000.0
    S_, W_ = np.meshgrid(np.linspace(-1, 1, ns), np.linspace(0, 1, nv), indexing='xy')
    xw = S_ * XSPAN
    Wd = Rc * 1.15
    yw = -Rc / (1.0 + (xw / Wd) ** 2)
    zw = z_lo + (z_hi - z_lo) * W_
    zw -= 170.0 * (1.0 - 1.0 / (1.0 + (xw / (Wd * 1.6)) ** 2))
    _u0 = (S_ * 0.5 + 0.5).astype(np.float32)
    zw += 150.0 * fbm(_u0, np.full_like(_u0, 0.5), 4, 2, 3, seed + 401)

    un = (S_ * 0.5 + 0.5).astype(np.float32)
    vn = W_.astype(np.float32)
    n_low = fbm(un, vn, max(3, int(10 * detail)), 2, 3, seed + 11, lac_v=1.5)
    n_mid = fbm(un, vn, max(4, int(30 * detail)), 5, 5, seed + 31, lac_v=1.7)
    n_hi  = fbm(un, vn, max(6, int(84 * detail)), 14, 4, seed + 71, lac_v=1.8)

    top = 0.66 + 0.36 * n_low + 0.20 * n_mid
    bot = 0.09 + 0.15 * np.clip(0.5 + 0.7 * n_low, 0.0, 1.0) + 0.07 * n_mid
    dens = sstep(top, top - 0.19, vn)
    dens *= sstep(bot - 0.07, bot + 0.20, vn)
    dens *= (0.62 + 0.38 * np.clip(0.5 + 0.62 * n_mid, 0.0, 1.0))
    dens *= (0.80 + 0.20 * np.clip(0.5 + 0.5 * n_hi, 0.0, 1.0))
    dens *= 0.50 + 0.50 * np.clip(0.5 + 0.8 * fbm(un, np.full_like(un, 0.5), 5, 2, 2, seed + 5), 0, 1)
    dens *= sstep(0.0, 0.09, un) * (1.0 - sstep(0.91, 1.0, un))
    a = np.clip(dens, 0.0, 1.0) ** 1.05 * alpha_s

    # colour: warm where the band crosses the cone, cooling to the right.
    # Brightness keys on rel = height WITHIN the cloud mass, not on the sheet:
    # keying it on the sheet puts the glow exactly where there is no density.
    rel = np.clip(vn / np.clip(top, 0.15, 1.4), 0.0, 1.0)
    lz = np.exp(-((xw - 300.0) / 5200.0) ** 2) * 0.90 + 0.10
    lz *= 1.0 - 0.35 * sstep(2500.0, 9000.0, xw)      # dim the momiji side
    lz *= 0.78 + 0.22 * np.clip(0.5 + 0.5 * n_low, 0.0, 1.0)
    wf = np.clip((0.42 + 0.58 * rel) * lz * bright * warm, 0.0, 1.0)

    cw = srgb2lin(C_CLOUD_WARM); cm = srgb2lin(C_CLOUD_MID)
    cd = srgb2lin(C_CLOUD_DARK if idx < 3 else C_MIST)
    t1 = np.clip(wf * 2.0, 0, 1)[..., None]; t2 = np.clip(wf * 2.0 - 1.0, 0, 1)[..., None]
    col = cd[None, None, :] + (cm - cd)[None, None, :] * t1 + (cw - cm)[None, None, :] * t2
    crest = sstep(0.62, 1.0, rel) * lz * warm
    col += cw[None, None, :] * (crest ** 2.0)[..., None] * 0.26 * bright

    rgba = np.concatenate([np.clip(col, 0.0, 4.0), a[..., None]], -1).reshape(-1, 4)
    co = np.stack([xw.ravel(), yw.ravel(), zw.ravel()], 1)
    org = (0.0, -Rc * 0.70, 0.5 * (z_lo + z_hi))
    ob = build_grid_mesh("Cloud%d" % idx, co, ns, nv, rgba, origin=org)
    ob.data.materials.append(emission_material("M_Cloud%d" % idx, backface_cull=False))
    print("[cloud%d] a_max %.2f  a_mean %.3f" % (idx, a.max(), a.mean()))
    return ob


# ==========================================================================
# SKY (separate layer)
# ==========================================================================
def build_sky(cam, horiz_ndc):
    nxp, nyp = 300, 160
    d = 1400.0
    hw = d * (FRAME_W * 0.5 / CAM_D)
    hh = hw * RES_H / RES_W
    PX, PY = np.meshgrid(np.linspace(-1, 1, nxp), np.linspace(-1, 1, nyp), indexing='xy')

    # Stated directly as a vertical ramp of screen colours, keyed on the
    # fraction from the top of the frame. A big soft ember blob was the first
    # attempt: it washed the lower right of the hero to ~75/255 and would have
    # eaten both the portrait and the body text. This stays under 60 everywhere
    # except a narrow, contained band at the cloud line.
    f = (1.0 - PY) * 0.5                                # 0 = top, 1 = bottom
    stops = np.array([0.00, 0.34, 0.52, 0.62, 0.78, 1.00])
    ramp = np.array([(12, 15, 26), (18, 22, 35), (26, 29, 39),
                     (28, 30, 39), (14, 15, 21), (10, 10, 13)], dtype=float)
    col = np.stack([np.interp(f, stops, srgb2lin(ramp[:, k])) for k in range(3)], -1)

    # contained sunset ember, low and right -- the warm side of the brief
    g = np.exp(-((PX - 0.42) ** 2) / 0.48) * np.exp(-((f - 0.575) / 0.115) ** 2)
    col += srgb2lin(S_EMBER)[None, None, :] * (g ** 1.15)[..., None]

    un = (PX * .5 + .5).astype(np.float32); vn = (PY * .5 + .5).astype(np.float32)
    wisp = np.clip(fbm(un, vn, 10, 6, 4, 606, lac_v=2.4), 0, 1) ** 2.4
    col += (wisp * np.exp(-((f - 0.30) / 0.20) ** 2))[..., None] * \
           srgb2lin((22, 24, 30))[None, None, :]

    rgba = np.concatenate([np.clip(col, 0, 4), np.ones_like(PX)[..., None]], -1).reshape(-1, 4)
    loc = np.stack([(PX * hw).ravel(), (PY * hh).ravel(), np.full(PX.size, -d)], 1)
    M = np.array(cam.matrix_world)
    co = (loc @ M[:3, :3].T) + M[:3, 3][None, :]
    ob = build_grid_mesh("Sky", co, nxp, nyp, rgba)
    ob.data.materials.append(emission_material("M_Sky", backface_cull=False))
    return ob


# ==========================================================================
def setup_render():
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE'
    sc.render.resolution_x = RES_W; sc.render.resolution_y = RES_H
    sc.render.resolution_percentage = 100
    im = sc.render.image_settings
    im.file_format = 'PNG'; im.color_mode = 'RGBA'; im.color_depth = '8'; im.compression = 15
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'
    sc.eevee.taa_render_samples = SAMPLES
    sc.eevee.use_shadows = False
    w = bpy.data.worlds.new("W"); w.use_nodes = True
    bg = w.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0, 0, 0, 1); bg.inputs[1].default_value = 0.0
    sc.world = w


def setup_camera(summit_z):
    cd = bpy.data.cameras.new("Cam")
    cd.sensor_fit = 'HORIZONTAL'; cd.sensor_width = SENSOR
    hfov = 2.0 * math.atan((FRAME_W * 0.5) / CAM_D)
    cd.lens = (SENSOR * 0.5) / math.tan(hfov * 0.5)
    cd.clip_start = 10.0; cd.clip_end = 400000.0
    cam = bpy.data.objects.new("Cam", cd)
    bpy.context.collection.objects.link(cam)
    half_h = FRAME_H * 0.5
    axis_z = summit_z - (0.5 - SUMMIT_Y_FRAC) * FRAME_H
    pitch = math.atan2(axis_z - CAM_Z, CAM_D)
    cam_x = (0.5 - SUMMIT_X_FRAC) * FRAME_W
    cam.location = (cam_x, -CAM_D, CAM_Z)
    cam.rotation_euler = (math.pi * 0.5 + pitch, 0.0, 0.0)
    bpy.context.scene.camera = cam
    bpy.context.view_layer.update()          # cam.matrix_world is stale without this
    vhalf = math.atan(half_h / CAM_D)
    horiz_ndc = -pitch / vhalf                     # eye level in NDC
    print("[cam] lens %.1fmm pitch %.2fdeg x %.0f frame %.0fx%.0fm horiz_ndc %.3f"
          % (cd.lens, math.degrees(pitch), cam_x, FRAME_W, FRAME_H, horiz_ndc))
    return cam, horiz_ndc


def render_to(path, transparent):
    sc = bpy.context.scene
    sc.render.film_transparent = transparent
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


def main():
    t0 = time.time()
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    setup_render()

    cam_pos = ((0.5 - SUMMIT_X_FRAC) * FRAME_W, -CAM_D, CAM_Z)
    terrain, summit = build_terrain(cam_pos)
    cam, horiz = setup_camera(summit)
    clouds = [build_sheet(*s, i) for i, s in enumerate(SHEETS)]
    sky = build_sky(cam, horiz)

    sky.hide_render = True
    render_to(os.path.join(HERE, "raw_%s.png" % TAG), True)
    sky.hide_render = False
    terrain.hide_render = True
    for c in clouds:
        c.hide_render = True
    render_to(os.path.join(HERE, "raw_sky_%s.png" % TAG), False)
    terrain.hide_render = False
    for c in clouds:
        c.hide_render = False
    sky.hide_render = True

    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "fuji.blend"))
    print("[done] %.1fs" % (time.time() - t0))

    if DO_POST and os.path.exists(os.path.join(HERE, "post.py")):
        subprocess.run(["/usr/bin/env", "python3", os.path.join(HERE, "post.py"), TAG], check=False)


main()
