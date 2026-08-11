#!/usr/bin/env python3
"""
Momiji (Acer palmatum) leaf sprite sheet builder for Blender 5.1.

Headless usage:
  /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
      --python build.py -- --mode preview
  ... --mode final

Produces 16 tumbling orientations x 3 colour variants:
  - individual 256x256 transparent PNGs
  - one 1024x1024 4x4 transparent sprite sheet per colour

The 16 orientations advance each Euler angle by an exact integer number of
full turns over the 16 frames, so frame 16 lands back on frame 1: seamless loop.
"""

import bpy
import bmesh
import math
import os
import sys
import random

# --------------------------------------------------------------------------
# paths / args
# --------------------------------------------------------------------------
ROOT = "/private/tmp/claude-501/-Users-iliaskalalou/1bd10a43-69c5-476d-82d4-b393f02194ee/scratchpad/sprites"
DIR_FRAMES = os.path.join(ROOT, "frames")
DIR_SHEETS = os.path.join(ROOT, "sheets")
DIR_PREV = os.path.join(ROOT, "preview")
BLEND = os.path.join(ROOT, "leaf_sprites.blend")

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
MODE = "preview"
TAG = ""
for i, a in enumerate(argv):
    if a == "--mode" and i + 1 < len(argv):
        MODE = argv[i + 1]
    if a == "--tag" and i + 1 < len(argv):
        TAG = argv[i + 1]

for d in (DIR_FRAMES, DIR_SHEETS, DIR_PREV):
    os.makedirs(d, exist_ok=True)

def log(*a):
    print("[leaf]", *a)
    sys.stdout.flush()


# --------------------------------------------------------------------------
# colour helpers
# --------------------------------------------------------------------------
def s2l(c):
    """single sRGB channel 0..1 -> linear"""
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hexlin(h):
    h = h.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    return (s2l(r), s2l(g), s2l(b), 1.0)


def scale_rgb(c, k):
    return (c[0] * k, c[1] * k, c[2] * k, 1.0)


# --------------------------------------------------------------------------
# leaf geometry
# --------------------------------------------------------------------------
# lobe centre angle (deg, measured from +Y, CCW positive), radial length
LOBES = [
    (-123.0, 0.66),
    (-80.0, 0.88),
    (-40.0, 0.97),
    (0.0, 1.00),
    (40.0, 0.97),
    (80.0, 0.88),
    (123.0, 0.66),
]
# Acer palmatum is cut roughly half to two thirds of the way to the petiole and
# its outline is close to circular. Cutting deeper with unequal lobe lengths
# turns it into a cannabis leaf, which is exactly what the first pass produced.
R_SINUS = 0.38          # radius the margin drops to between lobes
LOBE_Q = 0.62           # lobe profile exponent, f(u)=(1-|u|)^q.
                        # q<1 -> corner at the tip (acuminate) and a sharp V sinus.
ACUMEN = 0.13           # extra reach right at the tip -> long drawn-out point
OUTER_HALF = 29.0       # angular half-extent of the outermost lobes on their free side
N_OUT = 1000            # outline samples
RINGS = 7               # radial subdivisions of the blade
TOOTH_LAMBDA = 0.065    # arc length of one serration (fine, not blocky)
TOOTH_AMP = 0.020
# how each lobe lifts or drops, base lobe -> tip lobe -> base lobe
LOBE_TILT = [1.0, -0.55, 0.85, -0.35, 0.90, -0.50, 1.0]
CUP = 0.135
WAVE = 0.090
DROOP = 0.030
SHEAR = 0.060
RNORM = 1.02            # radius that counts as "the rim" for the z profile


def smoothstep(a, b, x):
    if b <= a:
        return 0.0
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def lobe_extents():
    angs = [math.radians(a) for a, _ in LOBES]
    out = []
    for k in range(len(LOBES)):
        dl = (angs[k] - angs[k - 1]) / 2.0 if k > 0 else math.radians(OUTER_HALF)
        dr = (angs[k + 1] - angs[k]) / 2.0 if k < len(LOBES) - 1 else math.radians(OUTER_HALF)
        out.append((angs[k], LOBES[k][1], dl, dr))
    return out


def radius_at(phi, ext):
    """polar margin function: max over lobes of a petal profile riding on R_SINUS"""
    best = 0.0
    for a, L, dl, dr in ext:
        d = phi - a
        half = dr if d >= 0 else dl
        u = abs(d) / half
        if u >= 1.0:
            continue
        f = ((1.0 - u) ** LOBE_Q) * (1.0 + ACUMEN * math.exp(-((u / 0.18) ** 2)))
        r = R_SINUS + (L - R_SINUS) * f
        if r > best:
            best = r
    return max(best, 0.0)


def build_outline():
    """Return (smooth, serrated) margin point lists, swept CCW."""
    ext = lobe_extents()
    phi_max = math.radians(126.0 + OUTER_HALF) - 1e-4
    phis = [(-phi_max + (2 * phi_max) * (j / (N_OUT - 1))) for j in range(N_OUT)]
    rs = [radius_at(p, ext) for p in phis]

    # base cartesian: direction d(phi) = (-sin phi, cos phi) so phi=0 -> +Y, CCW
    pts = [(-r * math.sin(p), r * math.cos(p)) for p, r in zip(phis, rs)]

    # arc length
    s = [0.0]
    for j in range(1, N_OUT):
        dx = pts[j][0] - pts[j - 1][0]
        dy = pts[j][1] - pts[j - 1][1]
        s.append(s[-1] + math.hypot(dx, dy))
    total = s[-1]
    lam = TOOTH_LAMBDA

    out = []
    for j in range(N_OUT):
        jm = max(0, j - 1)
        jp = min(N_OUT - 1, j + 1)
        tx = pts[jp][0] - pts[jm][0]
        ty = pts[jp][1] - pts[jm][1]
        tl = math.hypot(tx, ty) or 1e-9
        # outward normal for a CCW traversal
        nx, ny = ty / tl, -tx / tl

        # heading outward toward a lobe tip, or inward toward a sinus?
        outward = (rs[jp] - rs[jm]) >= 0.0

        q = (s[j] / lam) % 1.0
        prim = (q ** 1.7) if outward else ((1.0 - q) ** 1.7)
        q2 = (s[j] / (lam / 2.5)) % 1.0
        sec = (q2 ** 1.5) if outward else ((1.0 - q2) ** 1.5)
        shape = prim + 0.30 * sec

        fade = smoothstep(R_SINUS * 1.02, R_SINUS * 1.35, rs[j])
        size = max(0.55, min(1.0, rs[j] / 0.75))
        disp = TOOTH_AMP * shape * fade * size

        out.append((pts[j][0] + nx * disp, pts[j][1] + ny * disp))
    log("outline: %d pts, arc %.3f, tooth wavelength %.4f" % (N_OUT, total, lam))
    return pts, out


_TILT_ANGS = [math.radians(a) for a, _ in LOBES]


def lobe_tilt(phi):
    """Smooth C1 interpolation of LOBE_TILT across the lobe midrib angles, so the
    blade folds along the veins the way a real curled leaf does (extrema sit on
    the midribs, crossings sit in the sinuses) instead of on an arbitrary sine."""
    if phi <= _TILT_ANGS[0]:
        return LOBE_TILT[0]
    if phi >= _TILT_ANGS[-1]:
        return LOBE_TILT[-1]
    for k in range(len(_TILT_ANGS) - 1):
        a0, a1 = _TILT_ANGS[k], _TILT_ANGS[k + 1]
        if a0 <= phi <= a1:
            t = (phi - a0) / (a1 - a0)
            t = 0.5 - 0.5 * math.cos(math.pi * t)      # cosine ease -> C1
            return LOBE_TILT[k] * (1 - t) + LOBE_TILT[k + 1] * t
    return 0.0


def leaf_z(x, y):
    rr = math.hypot(x, y)
    t = min(1.0, rr / RNORM)
    phi = math.atan2(-x, y)          # inverse of d(phi)
    z = CUP * (t ** 2.0)
    z += WAVE * (t ** 1.7) * lobe_tilt(phi)
    z -= DROOP * (t ** 1.4) * math.cos(phi)
    z += SHEAR * x * t
    return z


def vein_value(x, y):
    """1 near a lobe midrib / the blade base, 0 elsewhere"""
    best = 0.0
    r = math.hypot(x, y)
    for a_deg, _L in LOBES:
        a = math.radians(a_deg)
        dx, dy = -math.sin(a), math.cos(a)
        proj = x * dx + y * dy
        if proj <= 0:
            d = r
        else:
            d = math.hypot(x - proj * dx, y - proj * dy)
        v = math.exp(-((d / 0.030) ** 2))
        if v > best:
            best = v
    best = max(best, math.exp(-((r / 0.075) ** 2)))
    return best


def build_leaf_mesh(name="MomijiLeaf"):
    smooth, serrated = build_outline()
    verts = []
    faces = []
    veins = []
    rads = []          # 0 at the petiole attachment, 1 out at the margin

    # centre vertex
    verts.append((0.0, 0.0, leaf_z(0.0, 0.0)))
    veins.append(1.0)
    rads.append(0.0)

    ring_start = []
    for k in range(1, RINGS + 1):
        rho = k / RINGS
        # Serration belongs to the margin only. Scaling the toothed outline
        # inward turns every tooth into a radial crease across the whole blade
        # and the leaf shades like a palm frond.
        w = 1.0 if k == RINGS else (0.30 if k == RINGS - 1 else 0.0)
        ring_start.append(len(verts))
        for (bx, by), (tx_, ty_) in zip(smooth, serrated):
            px = bx + w * (tx_ - bx)
            py = by + w * (ty_ - by)
            x, y = px * rho, py * rho
            verts.append((x, y, leaf_z(x, y)))
            veins.append(vein_value(x, y))
            rads.append(min(1.0, math.hypot(x, y) / RNORM))

    r0 = ring_start[0]
    for j in range(N_OUT - 1):
        faces.append((0, r0 + j, r0 + j + 1))
    for k in range(RINGS - 1):
        a, b = ring_start[k], ring_start[k + 1]
        for j in range(N_OUT - 1):
            faces.append((a + j, b + j, b + j + 1, a + j + 1))

    # ---- petiole (stem) --------------------------------------------------
    M, S = 9, 8
    pet_start = len(verts)
    rings = []
    for m in range(M + 1):
        t = m / M
        cx = 0.045 * (t ** 2)
        cy = -0.02 - 0.30 * t
        cz = -0.012 - 0.055 * t + 0.03 * (t ** 2)
        rad = 0.023 * (1.0 - 0.42 * t)
        idx = []
        for sN in range(S):
            psi = 2 * math.pi * sN / S
            idx.append(len(verts))
            verts.append((cx + rad * math.cos(psi), cy, cz + rad * math.sin(psi)))
            veins.append(1.0)
            rads.append(0.0)
        rings.append(idx)
    for m in range(M):
        for sN in range(S):
            s2 = (sN + 1) % S
            faces.append((rings[m][sN], rings[m][s2], rings[m + 1][s2], rings[m + 1][sN]))
    faces.append(tuple(rings[M]))                 # far cap, outward -Y
    faces.append(tuple(reversed(rings[0])))       # base cap
    log("petiole verts %d..%d" % (pet_start, len(verts) - 1))

    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    me.validate(verbose=False)

    attr = me.attributes.new(name="vein", type='FLOAT', domain='POINT')
    for i, v in enumerate(veins):
        attr.data[i].value = v
    attr = me.attributes.new(name="rad", type='FLOAT', domain='POINT')
    for i, v in enumerate(rads):
        attr.data[i].value = v

    for p in me.polygons:
        p.use_smooth = True

    log("mesh: %d verts, %d faces, %d tris" % (len(me.vertices), len(me.polygons), len(me.loop_triangles)))
    return me


def min_enclosing_radius(coords, iters=900):
    """Badoiu-Clarkson: returns (centre, radius) of a near-minimal enclosing ball."""
    cx = sum(c[0] for c in coords) / len(coords)
    cy = sum(c[1] for c in coords) / len(coords)
    cz = sum(c[2] for c in coords) / len(coords)
    for i in range(1, iters + 1):
        # farthest point
        bd, bp = -1.0, coords[0]
        for c in coords:
            d = (c[0] - cx) ** 2 + (c[1] - cy) ** 2 + (c[2] - cz) ** 2
            if d > bd:
                bd, bp = d, c
        k = 1.0 / (i + 1)
        cx += (bp[0] - cx) * k
        cy += (bp[1] - cy) * k
        cz += (bp[2] - cz) * k
    R = max(math.sqrt((c[0] - cx) ** 2 + (c[1] - cy) ** 2 + (c[2] - cz) ** 2) for c in coords)
    return (cx, cy, cz), R


# --------------------------------------------------------------------------
# material
# --------------------------------------------------------------------------
def sock(node, name, typ):
    for s in node.inputs:
        if s.name == name and s.type == typ:
            return s
    raise KeyError("no input %r/%r on %s; have %s"
                   % (name, typ, node.bl_idname, [(s.name, s.type) for s in node.inputs]))


# Each variant carries its own warm tints. Sharing one amber tint across all
# three pulled crimson up to hue 16 and made it indistinguishable from ember:
# the additive glow terms dominate the pigment on a near-black background.
VARIANTS = {
    "crimson": {"ramp": ("#7E120F", "#B31E14", "#C22615"),
                "rim": "#BC2A10", "trans": "#D42A10", "emit": "#DC300F"},
    "ember":   {"ramp": ("#93300B", "#C1440E", "#DA6A22"),
                "rim": "#F0812A", "trans": "#FF7A1E", "emit": "#FF7A16"},
    "amber":   {"ramp": ("#BE6E20", "#E08D3C", "#F0BE72"),
                "rim": "#FBB25C", "trans": "#FFAE48", "emit": "#FFAB3E"},
}


def build_material(name):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (900, 0)

    oinfo = nt.nodes.new("ShaderNodeObjectInfo")
    oinfo.location = (-1000, 300)

    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.location = (-820, 300)
    ramp.name = "LeafRamp"
    el = ramp.color_ramp.elements
    while len(el) > 2:
        el.remove(el[-1])
    el[0].position = 0.0
    el[1].position = 1.0
    el.new(0.5)
    ramp.color_ramp.interpolation = 'LINEAR'
    nt.links.new(oinfo.outputs["Random"], ramp.inputs["Fac"])

    vein = nt.nodes.new("ShaderNodeAttribute")
    vein.location = (-1000, -100)
    vein.attribute_name = "vein"

    veinfac = nt.nodes.new("ShaderNodeMath")
    veinfac.location = (-820, -100)
    veinfac.operation = 'MULTIPLY'
    veinfac.inputs[1].default_value = 0.60
    nt.links.new(vein.outputs["Fac"], veinfac.inputs[0])

    veinmix = nt.nodes.new("ShaderNodeMix")
    veinmix.location = (-600, 200)
    veinmix.data_type = 'RGBA'
    veinmix.blend_type = 'MULTIPLY'
    veinmix.name = "VeinMix"
    nt.links.new(veinfac.outputs[0], sock(veinmix, "Factor", 'VALUE'))
    nt.links.new(ramp.outputs["Color"], sock(veinmix, "A", 'RGBA'))
    sock(veinmix, "B", 'RGBA').default_value = (0.62, 0.46, 0.42, 1.0)

    LEAF = next(o for o in veinmix.outputs if o.type == 'RGBA')

    # --- radial backlight gradient: cool crimson core -> hot amber rim, which
    # is what the reference photograph does (thin outer blade transmits more).
    radat = nt.nodes.new("ShaderNodeAttribute")
    radat.location = (-1000, -280)
    radat.attribute_name = "rad"

    radpow = nt.nodes.new("ShaderNodeMath")
    radpow.location = (-820, -280)
    radpow.operation = 'POWER'
    radpow.inputs[1].default_value = 1.9
    nt.links.new(radat.outputs["Fac"], radpow.inputs[0])

    rimfac = nt.nodes.new("ShaderNodeMath")
    rimfac.location = (-660, -280)
    rimfac.operation = 'MULTIPLY'
    rimfac.inputs[1].default_value = 0.28
    nt.links.new(radpow.outputs[0], rimfac.inputs[0])

    rimmix = nt.nodes.new("ShaderNodeMix")
    rimmix.location = (-440, 200)
    rimmix.data_type = 'RGBA'
    rimmix.blend_type = 'MIX'
    rimmix.name = "RimMix"
    nt.links.new(rimfac.outputs[0], sock(rimmix, "Factor", 'VALUE'))
    nt.links.new(LEAF, sock(rimmix, "A", 'RGBA'))
    sock(rimmix, "B", 'RGBA').default_value = hexlin("#F0812A")
    LEAF = next(o for o in rimmix.outputs if o.type == 'RGBA')

    # ...and a darker, denser core where the blade is thick and doubled over
    coref = nt.nodes.new("ShaderNodeMath")
    coref.location = (-660, -420)
    coref.operation = 'SUBTRACT'
    coref.inputs[0].default_value = 1.0
    nt.links.new(radat.outputs["Fac"], coref.inputs[1])

    corep = nt.nodes.new("ShaderNodeMath")
    corep.location = (-520, -420)
    corep.operation = 'POWER'
    corep.inputs[1].default_value = 2.2
    nt.links.new(coref.outputs[0], corep.inputs[0])

    corem = nt.nodes.new("ShaderNodeMath")
    corem.location = (-380, -420)
    corem.operation = 'MULTIPLY'
    corem.inputs[1].default_value = 0.28
    nt.links.new(corep.outputs[0], corem.inputs[0])

    coremix = nt.nodes.new("ShaderNodeMix")
    coremix.location = (-250, 200)
    coremix.data_type = 'RGBA'
    coremix.blend_type = 'MULTIPLY'
    coremix.name = "CoreMix"
    nt.links.new(corem.outputs[0], sock(coremix, "Factor", 'VALUE'))
    nt.links.new(LEAF, sock(coremix, "A", 'RGBA'))
    sock(coremix, "B", 'RGBA').default_value = (0.62, 0.40, 0.36, 1.0)
    LEAF = next(o for o in coremix.outputs if o.type == 'RGBA')

    # opaque side
    pr = nt.nodes.new("ShaderNodeBsdfPrincipled")
    pr.location = (-300, 400)
    nt.links.new(LEAF, pr.inputs["Base Color"])
    pr.inputs["Roughness"].default_value = 0.72
    pr.inputs["Specular IOR Level"].default_value = 0.10
    pr.inputs["Sheen Weight"].default_value = 0.08
    pr.inputs["Sheen Roughness"].default_value = 0.35
    pr.inputs["Sheen Tint"].default_value = hexlin("#FFC58A")

    # translucent side (light coming through from behind)
    tlcol = nt.nodes.new("ShaderNodeMix")
    tlcol.location = (-500, -30)
    tlcol.data_type = 'RGBA'
    tlcol.blend_type = 'MIX'
    tlcol.name = "TransColor"
    sock(tlcol, "Factor", 'VALUE').default_value = 0.30
    nt.links.new(LEAF, sock(tlcol, "A", 'RGBA'))
    sock(tlcol, "B", 'RGBA').default_value = hexlin("#FF7A1E")
    TLC = next(o for o in tlcol.outputs if o.type == 'RGBA')

    tl = nt.nodes.new("ShaderNodeBsdfTranslucent")
    tl.location = (-300, -40)
    nt.links.new(TLC, tl.inputs["Color"])

    mixs = nt.nodes.new("ShaderNodeMixShader")
    mixs.location = (200, 150)
    mixs.inputs[0].default_value = 0.45
    nt.links.new(pr.outputs["BSDF"], mixs.inputs[1])
    nt.links.new(tl.outputs["BSDF"], mixs.inputs[2])

    # rim glow
    fres = nt.nodes.new("ShaderNodeFresnel")
    fres.location = (-500, -320)
    fres.inputs["IOR"].default_value = 1.65

    fm = nt.nodes.new("ShaderNodeMath")
    fm.location = (-320, -320)
    fm.operation = 'MULTIPLY'
    fm.inputs[1].default_value = 1.38
    nt.links.new(fres.outputs["Fac"], fm.inputs[0])

    fa = nt.nodes.new("ShaderNodeMath")
    fa.location = (-150, -320)
    fa.operation = 'ADD'
    fa.inputs[1].default_value = 0.07
    nt.links.new(fm.outputs[0], fa.inputs[0])

    radglow = nt.nodes.new("ShaderNodeMath")
    radglow.location = (-150, -430)
    radglow.operation = 'MULTIPLY'
    radglow.inputs[1].default_value = 0.55
    nt.links.new(radpow.outputs[0], radglow.inputs[0])

    fa2 = nt.nodes.new("ShaderNodeMath")
    fa2.location = (10, -360)
    fa2.operation = 'ADD'
    fa2.name = "EmitStrength"
    nt.links.new(fa.outputs[0], fa2.inputs[0])
    nt.links.new(radglow.outputs[0], fa2.inputs[1])

    emcol = nt.nodes.new("ShaderNodeMix")
    emcol.location = (-320, -520)
    emcol.data_type = 'RGBA'
    emcol.blend_type = 'MIX'
    emcol.name = "EmitColor"
    sock(emcol, "Factor", 'VALUE').default_value = 0.22
    nt.links.new(LEAF, sock(emcol, "A", 'RGBA'))
    sock(emcol, "B", 'RGBA').default_value = hexlin("#FF7A16")
    EMC = next(o for o in emcol.outputs if o.type == 'RGBA')

    em = nt.nodes.new("ShaderNodeEmission")
    em.location = (60, -420)
    nt.links.new(EMC, em.inputs["Color"])
    nt.links.new(fa2.outputs[0], em.inputs["Strength"])

    add = nt.nodes.new("ShaderNodeAddShader")
    add.location = (500, 0)
    nt.links.new(mixs.outputs[0], add.inputs[0])
    nt.links.new(em.outputs[0], add.inputs[1])
    nt.links.new(add.outputs[0], out.inputs["Surface"])
    return mat


def set_variant(mat, key):
    spec = VARIANTS[key]
    nodes = mat.node_tree.nodes
    dark, base, bright = spec["ramp"]
    el = nodes["LeafRamp"].color_ramp.elements
    el[0].color = hexlin(dark)
    el[1].color = hexlin(base)
    el[2].color = hexlin(bright)
    sock(nodes["RimMix"], "B", 'RGBA').default_value = hexlin(spec["rim"])
    sock(nodes["TransColor"], "B", 'RGBA').default_value = hexlin(spec["trans"])
    sock(nodes["EmitColor"], "B", 'RGBA').default_value = hexlin(spec["emit"])


# --------------------------------------------------------------------------
# scene
# --------------------------------------------------------------------------
N_FRAMES = 16
PHASE = 0.25          # sub-frame offset so no frame is exactly degenerate edge-on
WOBBLE = 0.42         # radians of Y-axis wobble amplitude


def frame_rotation(i):
    """Seamless loop: every angle advances a whole number of turns over 16 frames."""
    th = 2.0 * math.pi * (i + PHASE) / N_FRAMES
    rx = th                                # 1 full tumble  -> edge-on twice
    ry = WOBBLE * math.sin(th)             # periodic wobble, no net turn
    rz = 2.0 * th                          # 2 spins: at 1 it cancels the tumble
    return (rx, ry, rz)


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def build_scene():
    clear_scene()
    sc = bpy.context.scene

    me = build_leaf_mesh()

    # ---- single-user object first: thickness must be applied before we share
    # the mesh across the 16 frame objects (modifiers can't be applied to
    # multi-user data). An edge-on frame must be a real sliver, not a
    # vanishing zero-thickness plane.
    ob0 = bpy.data.objects.new("Leaf_00", me)
    sc.collection.objects.link(ob0)
    bpy.context.view_layer.objects.active = ob0
    for o in bpy.context.selected_objects:
        o.select_set(False)
    ob0.select_set(True)
    m = ob0.modifiers.new("Solidify", 'SOLIDIFY')
    m.thickness = 0.006
    m.offset = 0.0
    # even offset divides by cos(angle) at sharp corners and fires long spikes
    # out of every serration tip and sinus. The blade is near planar, so a plain
    # vertex-normal offset already gives even thickness.
    m.use_even_offset = False
    if hasattr(m, "thickness_clamp"):
        m.thickness_clamp = 1.0
    bpy.ops.object.modifier_apply(modifier=m.name)
    log("after solidify: %d verts, %d faces" % (len(me.vertices), len(me.polygons)))
    log("attributes now: %s" % [a.name for a in me.attributes])

    coords = [tuple(v.co) for v in me.vertices]
    centre, R = min_enclosing_radius(coords)
    log("pivot %.4f %.4f %.4f  enclosing radius %.4f" % (centre[0], centre[1], centre[2], R))
    for v in me.vertices:
        v.co = (v.co[0] - centre[0], v.co[1] - centre[1], v.co[2] - centre[2])

    mat = build_material("MomijiLeaf")
    me.materials.append(mat)

    leaves = [ob0]
    for i in range(1, N_FRAMES):
        ob = bpy.data.objects.new("Leaf_%02d" % i, me)
        sc.collection.objects.link(ob)
        leaves.append(ob)
    for i, ob in enumerate(leaves):
        ob.rotation_mode = 'XYZ'
        ob.rotation_euler = frame_rotation(i)
        ob.visible_shadow = False

    cell = 2.0 * R * 1.16
    log("cell ortho scale %.4f" % cell)

    cam_data = bpy.data.cameras.new("Cam")
    cam_data.type = 'ORTHO'
    cam_data.ortho_scale = cell
    cam_data.clip_start = 0.5
    cam_data.clip_end = 60.0
    cam = bpy.data.objects.new("Cam", cam_data)
    cam.location = (0, 0, 10)
    cam.rotation_euler = (0, 0, 0)
    sc.collection.objects.link(cam)
    sc.camera = cam

    # --- lights: SUNs only, so a leaf's lighting is identical in every grid cell
    def sun(name, rot_deg, energy, colour):
        d = bpy.data.lights.new(name, 'SUN')
        d.energy = energy
        d.color = hexlin(colour)[:3]
        d.angle = math.radians(6.0)
        o = bpy.data.objects.new(name, d)
        o.rotation_euler = tuple(math.radians(x) for x in rot_deg)
        sc.collection.objects.link(o)
        return o

    # key: from behind the leaf, shining toward camera -> backlit glow
    sun("KeyBack", (152, 0, -28), 5.2, "#FFB877")
    # warm three-quarter from front upper right, gives the surface some form
    sun("FrontWarm", (48, 0, 145), 2.70, "#FFE0BC")
    # cool fill from front lower left, keeps the shadow side from going flat black
    sun("CoolFill", (-58, 0, -30), 0.35, "#A9C2E2")

    world = bpy.data.worlds.new("W")
    sc.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = hexlin("#2A1206")
    bg.inputs["Strength"].default_value = 0.20

    # --- render settings
    sc.render.engine = 'BLENDER_EEVEE'
    sc.render.film_transparent = True
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA'
    sc.render.image_settings.color_depth = '8'
    sc.render.dither_intensity = 0.4
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'
    sc.eevee.use_shadows = False      # no self-shadowing -> clean translucency
    sc.eevee.taa_render_samples = 64
    log("engine=%s view=%s" % (sc.render.engine, sc.view_settings.view_transform))

    return sc, leaves, cam, mat, cell


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------
def render_to(sc, path, res_x, res_y):
    sc.render.resolution_x = res_x
    sc.render.resolution_y = res_y
    sc.render.resolution_percentage = 100
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    log("wrote", path, os.path.exists(path))


def layout_grid(leaves, cell):
    for i, ob in enumerate(leaves):
        r, c = divmod(i, 4)
        ob.location = ((c - 1.5) * cell, (1.5 - r) * cell, 0.0)
        ob.hide_render = False


def layout_single(leaves, idx):
    for i, ob in enumerate(leaves):
        ob.location = (0, 0, 0)
        ob.hide_render = (i != idx)


def main():
    sc, leaves, cam, mat, cell = build_scene()

    if MODE == "preview":
        sfx = ("_" + TAG) if TAG else ""
        set_variant(mat, "ember")
        # a) flat-on single leaf, big, to judge the silhouette
        sc.eevee.taa_render_samples = 32
        layout_single(leaves, 0)
        leaves[0].rotation_euler = (0, 0, 0)
        cam.data.ortho_scale = cell
        render_to(sc, os.path.join(DIR_PREV, "prev_shape%s.png" % sfx), 512, 512)
        leaves[0].rotation_euler = frame_rotation(0)
        # b) the whole 4x4 tumble sheet, small
        layout_grid(leaves, cell)
        cam.data.ortho_scale = cell * 4.0
        render_to(sc, os.path.join(DIR_PREV, "prev_sheet%s.png" % sfx), 640, 640)
        bpy.ops.wm.save_as_mainfile(filepath=BLEND)
        log("PREVIEW DONE")
        return

    # ---- final
    sc.eevee.taa_render_samples = 64
    for key in VARIANTS:
        set_variant(mat, key)
        outdir = os.path.join(DIR_FRAMES, key)
        os.makedirs(outdir, exist_ok=True)
        cam.data.ortho_scale = cell
        for i in range(N_FRAMES):
            layout_single(leaves, i)
            render_to(sc, os.path.join(outdir, "leaf_%s_%02d.png" % (key, i)), 256, 256)
        layout_grid(leaves, cell)
        cam.data.ortho_scale = cell * 4.0
        render_to(sc, os.path.join(DIR_SHEETS, "momiji_leaf_sheet_%s.png" % key), 1024, 1024)

    set_variant(mat, "ember")
    layout_grid(leaves, cell)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)
    log("FINAL DONE")


main()
