"""
Chureito-style five-storey pagoda  --  TREATMENT B : BACKLIT SILHOUETTE
=====================================================================
Left-hand hero element for a very dark editorial page (#0c0c0c).

Design brief distilled:
  * the five upswept eave curves (sori) ARE the subject; everything else is filler
  * near-black mass, read almost entirely by a thin warm rim on the silhouette
  * quieter and darker than the momiji tree on the right; must never out-shout it
  * a whisper of vermilion only where the low key light pools on the right flank

Run:
  /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
      --python build.py -- --out preview_01.png --w 700 --h 950 --samples 24
"""

import bpy, bmesh, math, sys, os, argparse
from mathutils import Vector

# ----------------------------------------------------------------------------
# PALETTE  (site palette: bg #0c0c0c, ember #C1440E, amber #E08D3C,
#           faded gold #8C6A3F, text #ededed)
# ----------------------------------------------------------------------------
def srgb(hexstr):
    """hex -> linear rgb tuple"""
    h = hexstr.lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255.0
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return tuple(out)

BG          = srgb("#0c0c0c")
EMBER       = srgb("#C1440E")
AMBER       = srgb("#E08D3C")
GOLD        = srgb("#8C6A3F")
VERMILION   = srgb("#D8442A")

# the body of the building: warm charcoal, barely above the page background
TIMBER_DARK = srgb("#171210")
TILE_DARK   = srgb("#12141a")   # roof surface, a touch cooler than the timber
BRONZE_DARK = srgb("#251a10")
PLASTER_DK  = srgb("#1c1a18")

# rim colours
RIM_ROOF    = AMBER
RIM_TIMBER  = EMBER
RIM_METAL   = srgb("#D9903F")
RIM_BRACKET = srgb("#D9A874")   # the white-tipped masu blocks

# ----------------------------------------------------------------------------
# STRUCTURE PARAMETERS
# ----------------------------------------------------------------------------
N_TIERS       = 5

W1            = 2.00     # half-width of the lowest roof, at the eave mid-point
TAPER         = 0.876    # each roof above is this fraction of the one below
EAVE_Z1       = 2.06     # height of the lowest eave mid-point
GAP1          = 1.24     # vertical distance eave(i) -> eave(i+1)
GAP_TAPER     = 0.945

BODY_FRAC     = 0.400    # body half-width / roof half-width
BALC_FRAC     = 1.58     # balcony half-width / body half-width
PLINTH_Z      = 0.44

# --- the single most important shape in the model : the eave curve ----------
ROOF_SMIN     = 0.30     # roof starts at this fraction of the half-width
ROOF_HPEAK    = 0.425    # peak height above the eave, as fraction of half-width
ROOF_PROFILE  = 1.46     # >1 : steep at the ridge, flattening toward the eave
SWEEP         = 0.168    # corner lift, as fraction of half-width  (sori)
SWEEP_U_A     = 0.30     # the gentle sag across the middle  (u^1.3)
SWEEP_U_B     = 0.55     # the main acceleration        (u^2.6)
SWEEP_U_C     = 0.15     # the last curl at the very tip (u^6)
SWEEP_S_POW   = 1.55     # how fast the lift dies away toward the ridge
FLARE         = 0.028    # corners also push OUT in plan, not only up
ROOF_THICK    = 0.047    # eave fascia depth -> this is the band the rim rides on
ROOF_THICK_IN = 0.48     # thickness multiplier up at the ridge (thin) vs eave (thick)

RING_N        = 30       # rings across the roof slope
SIDE_N        = 26       # samples per side of the square ring

BRACKETS      = True
BRACKET_S     = 0.948    # where the dotted row of masu sits, along the slope
BRACKET_STEP  = 0.086    # spacing between blocks, world units
BRACKET_W     = 0.030
BRACKET_H     = 0.044

HIPS          = True     # the four diagonal ridge tiles
HIP_W         = 0.075
HIP_H         = 0.055

# --- sorin (bronze finial) --------------------------------------------------
SORIN_RINGS   = 9
SORIN_MAST_R  = 0.030
SORIN_H       = 1.60

# ----------------------------------------------------------------------------
# LIGHT / LOOK
# ----------------------------------------------------------------------------
KEY_DIR       = Vector((0.60, 0.74, 0.31)).normalized()   # object -> key light
KEY_COLOR     = srgb("#FF8A3C")
KEY_POWER     = 520.0
POOL_COLOR    = srgb("#C1440E")
POOL_POWER    = 34.0
AMBIENT       = (0.0045, 0.0060, 0.0095)                  # cold, nearly nothing

RIM_LO        = 0.815    # colour-ramp start : lower = fatter rim
RIM_HI        = 0.998
DIR_MIN       = 0.055    # rim strength on faces turned away from the key
FADE_LO       = 0.78     # world Z where the building starts to exist
FADE_HI       = 3.05     # world Z where it is at full strength
ALPHA_LO      = 0.42     # below this the building is fully transparent
ALPHA_HI      = 1.80     # above this it is fully opaque
FADE_FLOOR    = 0.045

VIEW_TRANSFORM = "AgX"
VIEW_LOOK      = "AgX - Medium Contrast"
EXPOSURE       = 0.0

# --- camera -----------------------------------------------------------------
CAM_LENS      = 58.0
CAM_Z         = 0.72     # below the building : the upward view gives it presence
CAM_YAW       = 7.0     # degrees off dead-on, so the roofs read as 3D forms
FRAME_FILL    = 0.915
FRAME_CENTER  = 0.507

HALO          = True     # let the bloom bleed into the alpha channel
GLARE_SIZE    = 8
GLARE_STR     = 0.38
GLARE_THRESH  = 0.30
HALO_K        = 0.55


# ============================================================================
# helpers
# ============================================================================
def wipe():
    for coll in (bpy.data.objects, bpy.data.meshes, bpy.data.materials,
                 bpy.data.lights, bpy.data.cameras, bpy.data.node_groups):
        for item in list(coll):
            coll.remove(item)


def new_obj(name, verts, faces, mat):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.validate()
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    if mat:
        ob.data.materials.append(mat)
    return ob


def box(cx, cy, cz, hx, hy, hz):
    """returns (verts, faces) for an axis aligned box"""
    v = [(cx - hx, cy - hy, cz - hz), (cx + hx, cy - hy, cz - hz),
         (cx + hx, cy + hy, cz - hz), (cx - hx, cy + hy, cz - hz),
         (cx - hx, cy - hy, cz + hz), (cx + hx, cy - hy, cz + hz),
         (cx + hx, cy + hy, cz + hz), (cx - hx, cy + hy, cz + hz)]
    f = [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1),
         (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
    return v, f


def merge(parts):
    verts, faces = [], []
    for v, f in parts:
        o = len(verts)
        verts += list(v)
        faces += [tuple(i + o for i in fc) for fc in f]
    return verts, faces


# ============================================================================
# THE EAVE CURVE
# ============================================================================
def unit_ring(n_side):
    """CCW points on the perimeter of the unit square, chebyshev radius 1."""
    pts = []
    for k in range(4):
        for j in range(n_side):
            t = j / n_side
            if k == 0:   a, b = -1 + 2 * t, -1.0
            elif k == 1: a, b = 1.0, -1 + 2 * t
            elif k == 2: a, b = 1 - 2 * t, 1.0
            else:        a, b = -1.0, 1 - 2 * t
            pts.append((a, b))
    return pts


def sweep_profile(u):
    """how much the eave lifts, as a function of the distance to the corner."""
    return (SWEEP_U_A * u ** 1.3 + SWEEP_U_B * u ** 2.6
            + SWEEP_U_C * u ** 6.0)


def roof_point(a, b, s, W, hroof, eave_z):
    """(a,b) on the unit square perimeter, s = chebyshev radius fraction."""
    u = min(abs(a), abs(b))
    fl = 1.0 + FLARE * sweep_profile(u) * s ** 2.2
    x = a * s * W * fl
    y = b * s * W * fl
    z = eave_z + hroof * (1.0 - s) ** ROOF_PROFILE \
              + SWEEP * W * (s ** SWEEP_S_POW) * sweep_profile(u)
    return x, y, z, u


def build_roof(idx, W, eave_z, mat, mat_eave=None, mat_under=None):
    hpeak = ROOF_HPEAK * W
    hroof = hpeak / (1.0 - ROOF_SMIN) ** ROOF_PROFILE
    ring = unit_ring(SIDE_N)
    P = len(ring)

    verts, weights = [], []
    for i in range(RING_N + 1):
        t = i / RING_N
        t = 1.0 - (1.0 - t) ** 1.7          # cluster the rings near the eave
        s = ROOF_SMIN + (1.0 - ROOF_SMIN) * t
        for (a, b) in ring:
            x, y, z, u = roof_point(a, b, s, W, hroof, eave_z)
            verts.append((x, y, z))
            weights.append(t ** 0.6)

    faces = []
    for i in range(RING_N):
        for j in range(P):
            j2 = (j + 1) % P
            faces.append((i * P + j, i * P + j2, (i + 1) * P + j2, (i + 1) * P + j))

    ob = new_obj(f"roof_{idx}", verts, faces, mat)
    # slot 0 = top surface, 1 = eave fascia (solidify rim), 2 = underside
    if mat_eave is not None:
        ob.data.materials.append(mat_eave)
    if mat_under is not None:
        ob.data.materials.append(mat_under)

    vg = ob.vertex_groups.new(name="eave")
    for vi, w in enumerate(weights):
        vg.add([vi], w, 'REPLACE')

    sol = ob.modifiers.new("sol", 'SOLIDIFY')
    sol.thickness = ROOF_THICK
    sol.offset = -1.0
    sol.use_rim = True
    sol.use_even_offset = False
    sol.vertex_group = "eave"
    sol.thickness_vertex_group = ROOF_THICK_IN
    if mat_eave is not None:
        # the fascia band generated by solidify gets its own material: this is
        # the bright continuous line that draws the eave curve
        sol.material_offset_rim = 1
    if mat_under is not None:
        # seen from below, the underside IS most of the roof. it must stay
        # near-black or the silhouette dies.
        sol.material_offset = 2

    bpy.context.view_layer.objects.active = ob
    try:
        bpy.ops.object.shade_auto_smooth(angle=math.radians(38))
    except Exception:
        for p in ob.data.polygons:
            p.use_smooth = True
    return ob, hroof, hpeak


def build_hips(idx, W, eave_z, mat):
    """four diagonal ridge tiles - they make the hipped roof read as a solid."""
    hpeak = ROOF_HPEAK * W
    hroof = hpeak / (1.0 - ROOF_SMIN) ** ROOF_PROFILE
    parts = []
    for (sa, sb) in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        rows = []
        n = 26
        for i in range(n + 1):
            t = i / n
            t = 1.0 - (1.0 - t) ** 1.7
            s = ROOF_SMIN + (1.0 - ROOF_SMIN) * t
            x, y, z, u = roof_point(sa * 1.0, sb * 1.0, s, W, hroof, eave_z)
            # perpendicular to the diagonal, in plan
            px, py = -sb * 0.7071, sa * 0.7071
            w = HIP_W * (0.55 + 0.45 * t)
            h = HIP_H * (0.6 + 0.4 * t)
            rows.append([
                (x - px * w, y - py * w, z - 0.012),
                (x + px * w, y + py * w, z - 0.012),
                (x + px * w * 0.55, y + py * w * 0.55, z + h),
                (x - px * w * 0.55, y - py * w * 0.55, z + h),
            ])
        v, f = [], []
        for r in rows:
            v += r
        for i in range(n):
            o, o2 = i * 4, (i + 1) * 4
            for k in range(4):
                k2 = (k + 1) % 4
                f.append((o + k, o + k2, o2 + k2, o2 + k))
        f.append((0, 1, 2, 3))
        o = n * 4
        f.append((o + 3, o + 2, o + 1, o + 0))
        parts.append((v, f))
    return new_obj(f"hips_{idx}", *merge(parts), mat)


def build_brackets(idx, W, eave_z, mat):
    """the dense dotted row of white-tipped masu blocks under each eave."""
    hpeak = ROOF_HPEAK * W
    hroof = hpeak / (1.0 - ROOF_SMIN) ** ROOF_PROFILE
    s = BRACKET_S
    # walk the ring at fine resolution, drop a block every BRACKET_STEP
    fine = unit_ring(240)
    pts = []
    for (a, b) in fine:
        x, y, z, u = roof_point(a, b, s, W, hroof, eave_z)
        pts.append((x, y, z))
    parts, acc = [], 1e9
    for i in range(len(pts)):
        p, q = pts[i], pts[(i + 1) % len(pts)]
        d = math.dist(p, q)
        acc += d
        if acc >= BRACKET_STEP:
            acc = 0.0
            # thickness of the roof shell at this s
            th = ROOF_THICK * (ROOF_THICK_IN + (1 - ROOF_THICK_IN) * (s ** 0.6))
            cz = p[2] - th - BRACKET_H * 0.5 + 0.012
            parts.append(box(p[0], p[1], cz, BRACKET_W, BRACKET_W, BRACKET_H * 0.5))
    return new_obj(f"brackets_{idx}", *merge(parts), mat)


# ============================================================================
# BODY / BALCONY / PLINTH / SORIN
# ============================================================================
def build_body(idx, B, z0, z1, mat):
    parts = []
    cz, hz = (z0 + z1) * 0.5, (z1 - z0) * 0.5
    parts.append(box(0, 0, cz, B, B, hz))
    # four corner posts, very slightly proud : gives vertical rim lines
    p = B * 0.040
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts.append(box(sx * B, sy * B, cz, p, p, hz))
    return new_obj(f"body_{idx}", *merge(parts), mat)


def roof_z_mid(r, W, eave_z):
    """height of the roof surface (edge mid-line, u=0) at plan radius r."""
    hpeak = ROOF_HPEAK * W
    hroof = hpeak / (1.0 - ROOF_SMIN) ** ROOF_PROFILE
    s = min(1.0, max(ROOF_SMIN, r / W))
    return eave_z + hroof * (1.0 - s) ** ROOF_PROFILE


def build_balcony(idx, B, z, mat):
    B2 = B * BALC_FRAC
    parts = []
    parts.append(box(0, 0, z + 0.030, B2, B2, 0.030))          # deck
    rail_h = 0.255
    t = 0.026
    for lev, hh in ((z + rail_h, 0.026), (z + rail_h * 0.52, 0.016)):
        for sgn in (-1, 1):
            parts.append(box(0, sgn * B2, lev, B2 + t, t, hh))
            parts.append(box(sgn * B2, 0, lev, t, B2 + t, hh))
    # posts
    n = 7
    for k in range(n + 1):
        f = -1 + 2 * k / n
        for sgn in (-1, 1):
            parts.append(box(f * B2, sgn * B2, z + rail_h * 0.55, 0.016, 0.016, rail_h * 0.55))
            parts.append(box(sgn * B2, f * B2, z + rail_h * 0.55, 0.016, 0.016, rail_h * 0.55))
    return new_obj(f"balcony_{idx}", *merge(parts), mat)


def build_plinth(B, mat):
    parts = []
    parts.append(box(0, 0, PLINTH_Z * 0.5, B * 1.62, B * 1.62, PLINTH_Z * 0.5))
    parts.append(box(0, 0, PLINTH_Z + 0.055, B * 1.30, B * 1.30, 0.055))
    return new_obj("plinth", *merge(parts), mat)


def build_sorin(z0, mat):
    """
    Sorin, bottom to top: roban (square block), fukubachi (bowl), ukebana,
    then nine kurin rings threaded on a slender mast, suien (four flame
    blades), ryusha and the hoju jewel.  Kept fine and dense: at hero scale
    it must read as a ribbed bronze thread, never as a coil spring.
    """
    parts = []

    def tube(zc, r_bot, r_top, h, seg=24, cap=False):
        """open (or capped) truncated cone shell, centred on zc, half-height h"""
        v, f = [], []
        for i in range(seg):
            a = 2 * math.pi * i / seg
            ca, sa = math.cos(a), math.sin(a)
            v += [(ca * r_bot, sa * r_bot, zc - h), (ca * r_top, sa * r_top, zc + h)]
        for i in range(seg):
            j = (i + 1) % seg
            f.append((i * 2, j * 2, j * 2 + 1, i * 2 + 1))
        if cap:
            v.append((0, 0, zc - h)); v.append((0, 0, zc + h))
            cb, ct = len(v) - 2, len(v) - 1
            for i in range(seg):
                j = (i + 1) % seg
                f.append((cb, j * 2, i * 2))
                f.append((ct, i * 2 + 1, j * 2 + 1))
        return v, f

    def annulus(zc, ri, ro, t, seg=32):
        """a closed flat ring -- reads as a clean disc, not as a spiral"""
        v, f = [], []
        for i in range(seg):
            a = 2 * math.pi * i / seg
            ca, sa = math.cos(a), math.sin(a)
            v += [(ca * ri, sa * ri, zc - t), (ca * ro, sa * ro, zc - t),
                  (ca * ro, sa * ro, zc + t), (ca * ri, sa * ri, zc + t)]
        for i in range(seg):
            j = (i + 1) % seg
            o, q = i * 4, j * 4
            f += [(o + 0, q + 0, q + 1, o + 1),
                  (o + 1, q + 1, q + 2, o + 2),
                  (o + 2, q + 2, q + 3, o + 3),
                  (o + 3, q + 3, q + 0, o + 0)]
        return v, f

    z = z0
    parts.append(box(0, 0, z + 0.048, 0.150, 0.150, 0.048))      # roban
    z += 0.096
    parts.append(tube(z + 0.060, 0.132, 0.062, 0.060, 28))       # fukubachi
    z += 0.120
    parts.append(annulus(z + 0.012, 0.030, 0.115, 0.012, 32))    # ukebana
    z += 0.030

    mast_top = z0 + SORIN_H
    parts.append(tube((z + mast_top - 0.16) * 0.5 + 0.08, SORIN_MAST_R,
                      SORIN_MAST_R * 0.8,
                      (mast_top - 0.16 - z) * 0.5, 16, cap=True))

    # kurin : nine rings, tightly stacked and tapering
    span = (mast_top - 0.30) - z
    for k in range(SORIN_RINGS):
        t = k / max(1, SORIN_RINGS - 1)
        rz = z + 0.045 + span * t
        ro = 0.106 * (1.0 - 0.28 * t)
        parts.append(annulus(rz, SORIN_MAST_R * 1.30, ro, 0.0105, 32))

    # suien : four slender flame blades, thin plates seen mostly edge on
    sz = z + 0.045 + span + 0.085
    for k in range(4):
        a = math.pi * 0.25 + math.pi * 0.5 * k
        ca, sa = math.cos(a), math.sin(a)
        prof = [(0.022, -0.075), (0.105, -0.030), (0.118, 0.055), (0.062, 0.115),
                (0.022, 0.085)]
        v, f = [], []
        for (r, dz) in prof:
            v.append((ca * r - sa * 0.007, sa * r + ca * 0.007, sz + dz))
        for (r, dz) in prof:
            v.append((ca * r + sa * 0.007, sa * r - ca * 0.007, sz + dz))
        n = len(prof)
        f.append(tuple(range(n)))
        f.append(tuple(reversed(range(n, 2 * n))))
        for i in range(n):
            j = (i + 1) % n
            f.append((i, j, n + j, n + i))
        parts.append((v, f))

    parts.append(annulus(mast_top - 0.145, 0.020, 0.062, 0.011, 28))   # ryusha
    parts.append(tube(mast_top - 0.105, 0.024, 0.014, 0.030, 16))

    # hoju : the jewel
    v, f = [], []
    seg, rings = 18, 9
    R = 0.043
    for i in range(rings + 1):
        th = math.pi * i / rings
        for j in range(seg):
            ph = 2 * math.pi * j / seg
            v.append((R * math.sin(th) * math.cos(ph),
                      R * math.sin(th) * math.sin(ph),
                      mast_top - 0.062 + R * 1.25 * math.cos(th)))
    for i in range(rings):
        for j in range(seg):
            j2 = (j + 1) % seg
            f.append((i * seg + j, i * seg + j2, (i + 1) * seg + j2, (i + 1) * seg + j))
    parts.append((v, f))
    parts.append(tube(mast_top - 0.010, 0.014, 0.001, 0.022, 12))      # tip

    ob = new_obj("sorin", *merge(parts), mat)
    bpy.context.view_layer.objects.active = ob
    try:
        bpy.ops.object.shade_auto_smooth(angle=math.radians(30))
    except Exception:
        pass
    return ob


# ============================================================================
# MATERIALS
# ============================================================================
def make_mat(name, base, rim_col, rim_str, rim_lo=RIM_LO, rim_hi=RIM_HI,
             metallic=0.0, rough=0.62, dir_min=DIR_MIN,
             base_emit=0.0, base_dir_min=0.42, fade=True, dir_vec=None,
             x_emit=None, x_col=None, spec=0.35):
    """
    Every surface is the same idea:
        emission = ( base_emit * soft_directional        <- the continuous line
                   + rim_ramp(facing) * rim_str * dir )  <- the grazing rim
                   * height_fade
    and the diffuse base colour is crushed toward black near the ground so the
    building dissolves into the page instead of ending in a black tombstone.
    """
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.surface_render_method = 'DITHERED'
    nt = mat.node_tree
    nt.nodes.clear()

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    emis = nt.nodes.new("ShaderNodeEmission")
    add = nt.nodes.new("ShaderNodeAddShader")
    lw = nt.nodes.new("ShaderNodeLayerWeight")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    dot = nt.nodes.new("ShaderNodeVectorMath")
    mrd = nt.nodes.new("ShaderNodeMapRange")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    mrz = nt.nodes.new("ShaderNodeMapRange")
    m1 = nt.nodes.new("ShaderNodeMath")
    m2 = nt.nodes.new("ShaderNodeMath")
    mbase = nt.nodes.new("ShaderNodeMix")

    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metallic
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = spec

    lw.inputs["Blend"].default_value = 0.5
    ramp.color_ramp.interpolation = 'EASE'
    ramp.color_ramp.elements[0].position = rim_lo
    ramp.color_ramp.elements[0].color = (0, 0, 0, 1)
    ramp.color_ramp.elements[1].position = rim_hi
    ramp.color_ramp.elements[1].color = (1, 1, 1, 1)

    dot.operation = 'DOT_PRODUCT'
    dot.inputs[1].default_value = tuple(dir_vec if dir_vec else KEY_DIR)
    mrd.clamp = True
    mrd.inputs["From Min"].default_value = -1.0
    mrd.inputs["From Max"].default_value = 1.0
    mrd.inputs["To Min"].default_value = dir_min
    mrd.inputs["To Max"].default_value = 1.0

    mrz.clamp = True
    mrz.inputs["From Min"].default_value = FADE_LO
    mrz.inputs["From Max"].default_value = FADE_HI
    mrz.inputs["To Min"].default_value = FADE_FLOOR
    mrz.inputs["To Max"].default_value = 1.0

    m1.operation = 'MULTIPLY'
    m2.operation = 'MULTIPLY'
    m2.inputs[1].default_value = rim_str

    mbase.data_type = 'RGBA'
    mbase.inputs[6].default_value = (base[0] * 0.10, base[1] * 0.10, base[2] * 0.10, 1)
    mbase.inputs[7].default_value = (*base, 1)

    L = nt.links.new
    L(lw.outputs["Facing"], ramp.inputs["Factor"])
    L(geo.outputs["Normal"], dot.inputs[0])
    L(dot.outputs["Value"], mrd.inputs["Value"])
    L(geo.outputs["Position"], sep.inputs["Vector"])
    L(sep.outputs["Z"], mrz.inputs["Value"])
    L(ramp.outputs["Color"], m1.inputs[0])
    L(mrd.outputs["Result"], m1.inputs[1])
    L(m1.outputs["Value"], m2.inputs[0])
    L(mrz.outputs["Result"], mbase.inputs[0])
    L(mbase.outputs[2], bsdf.inputs["Base Color"])

    # --- the continuous line term: a soft directional wash, no fresnel -------
    mrs = nt.nodes.new("ShaderNodeMapRange")
    mrs.clamp = True
    mrs.inputs["From Min"].default_value = -1.0
    mrs.inputs["From Max"].default_value = 1.0
    mrs.inputs["To Min"].default_value = base_dir_min
    mrs.inputs["To Max"].default_value = 1.0
    L(dot.outputs["Value"], mrs.inputs["Value"])
    mb = nt.nodes.new("ShaderNodeMath"); mb.operation = 'MULTIPLY'
    mb.inputs[1].default_value = base_emit
    L(mrs.outputs["Result"], mb.inputs[0])

    tot = nt.nodes.new("ShaderNodeMath"); tot.operation = 'ADD'
    L(m2.outputs["Value"], tot.inputs[0])
    L(mb.outputs["Value"], tot.inputs[1])

    # --- the pool of vermilion: a purely positional gradient on the lit
    # flank. driving it off world X rather than off a lamp means it can never
    # blow out into cream, and it stays a whisper.
    if x_emit:
        lo, hi, xs = x_emit
        mrx = nt.nodes.new("ShaderNodeMapRange")
        mrx.clamp = True
        mrx.inputs["From Min"].default_value = lo
        mrx.inputs["From Max"].default_value = hi
        mrx.inputs["To Min"].default_value = 0.0
        mrx.inputs["To Max"].default_value = 1.0
        L(sep.outputs["X"], mrx.inputs["Value"])
        px = nt.nodes.new("ShaderNodeMath"); px.operation = 'POWER'
        px.inputs[1].default_value = 2.2
        L(mrx.outputs["Result"], px.inputs[0])
        mxs = nt.nodes.new("ShaderNodeMath"); mxs.operation = 'MULTIPLY'
        mxs.inputs[1].default_value = xs
        L(px.outputs["Value"], mxs.inputs[0])
        # its own colour, mixed into the emission tint by how strong it is
        emix = nt.nodes.new("ShaderNodeMix"); emix.data_type = 'RGBA'
        emix.inputs[6].default_value = (*rim_col, 1)
        emix.inputs[7].default_value = (*(x_col or rim_col), 1)
        L(px.outputs["Value"], emix.inputs[0])
        L(emix.outputs[2], emis.inputs["Color"])
        tot2 = nt.nodes.new("ShaderNodeMath"); tot2.operation = 'ADD'
        L(tot.outputs["Value"], tot2.inputs[0])
        L(mxs.outputs["Value"], tot2.inputs[1])
        tot = tot2

    # everything fades toward the base
    m3 = nt.nodes.new("ShaderNodeMath"); m3.operation = 'MULTIPLY'
    L(tot.outputs["Value"], m3.inputs[0])
    L(mrz.outputs["Result"], m3.inputs[1])

    emis.inputs["Color"].default_value = (*rim_col, 1)
    L(m3.outputs["Value"], emis.inputs["Strength"])
    L(bsdf.outputs["BSDF"], add.inputs[0])
    L(emis.outputs["Emission"], add.inputs[1])

    # --- alpha fade: the bottom of the building dissolves into the page -----
    if fade:
        tr = nt.nodes.new("ShaderNodeBsdfTransparent")
        mx = nt.nodes.new("ShaderNodeMixShader")
        mra = nt.nodes.new("ShaderNodeMapRange")
        mra.clamp = True
        mra.inputs["From Min"].default_value = ALPHA_LO
        mra.inputs["From Max"].default_value = ALPHA_HI
        mra.inputs["To Min"].default_value = 0.0
        mra.inputs["To Max"].default_value = 1.0
        L(sep.outputs["Z"], mra.inputs["Value"])
        L(mra.outputs["Result"], mx.inputs[0])
        L(tr.outputs["BSDF"], mx.inputs[1])
        L(add.outputs["Shader"], mx.inputs[2])
        L(mx.outputs["Shader"], out.inputs["Surface"])
    else:
        L(add.outputs["Shader"], out.inputs["Surface"])
    return mat


# ============================================================================
# SCENE
# ============================================================================
def build_scene():
    wipe()
    sc = bpy.context.scene

    # roof surface : essentially black, a whisper of grazing rim only
    m_tile    = make_mat("tile",    TILE_DARK,   RIM_ROOF,    2.4, rim_lo=0.905, rough=0.52)
    # the eave fascia : THE line. constant emission so it survives being seen
    # broadside from below, plus a grazing kick where it turns away
    m_eave    = make_mat("eave",    TILE_DARK,   RIM_ROOF,    1.5, rim_lo=0.80,
                         base_emit=1.18, base_dir_min=0.58, rough=0.45)
    m_timber  = make_mat("timber",  srgb("#100b09"), RIM_TIMBER, 2.2, rim_lo=0.905,
                         base_emit=0.045, base_dir_min=0.0, rough=0.70)
    m_bracket = make_mat("bracket", PLASTER_DK,  RIM_BRACKET, 0.45, rim_lo=0.74,
                         base_emit=0.145, base_dir_min=0.30, rough=0.75)
    # the underside of every eave: black, save for whatever the low warm pool
    # light chooses to touch on the right flank
    # a whisper of vermilion, painted by direction rather than by a lamp so it
    # can never blow out: only undersides turned right-and-down get anything
    m_under   = make_mat("under",   srgb("#120904"), EMBER, 0.22, rim_lo=0.93,
                         rough=0.92, spec=0.02, x_emit=(0.55, 2.20, 0.21), x_col=EMBER)
    m_hip     = make_mat("hip",     TILE_DARK,   RIM_ROOF,    2.8, rim_lo=0.80, rough=0.50)
    m_metal   = make_mat("metal",   BRONZE_DARK, RIM_METAL,   1.7, rim_lo=0.60,
                         base_emit=0.26, base_dir_min=0.24,
                         metallic=0.85, rough=0.40, dir_min=0.15, spec=0.25)
    m_stone   = make_mat("stone",   srgb("#141414"), GOLD,     0.60, rim_lo=0.92, rough=0.85)

    # ---- tier table --------------------------------------------------------
    Ws, Zs = [], []
    z = EAVE_Z1
    g = GAP1
    for i in range(N_TIERS):
        Ws.append(W1 * TAPER ** i)
        Zs.append(z)
        z += g
        g *= GAP_TAPER

    top_of_last = 0.0
    for i in range(N_TIERS):
        W, ez = Ws[i], Zs[i]
        B = W * BODY_FRAC
        z_lo = PLINTH_Z if i == 0 else Zs[i - 1]
        z_hi = ez + ROOF_HPEAK * W + 0.02
        build_body(i, B, z_lo, z_hi, m_timber)
        build_roof(i, W, ez, m_tile, m_eave, m_under)
        if HIPS:
            build_hips(i, W, ez, m_hip)
        if BRACKETS:
            build_brackets(i, W, ez, m_bracket)
        if i < N_TIERS - 1:
            # the balcony of the storey above sits on this roof's slope
            Bn = Ws[i + 1] * BODY_FRAC
            deck_r = Bn * BALC_FRAC
            deck_z = roof_z_mid(deck_r, W, ez) + 0.055
            build_balcony(i, Bn, deck_z, m_timber)
        top_of_last = ez + ROOF_HPEAK * W

    build_plinth(W1 * BODY_FRAC, m_stone)
    build_sorin(top_of_last - 0.02, m_metal)

    # ---- lights ------------------------------------------------------------
    def lamp(name, kind, loc, energy, color, size=2.0, angle=None):
        d = bpy.data.lights.new(name, kind)
        d.energy = energy
        d.color = color
        if kind == 'AREA':
            d.size = size
        if kind == 'SUN' and angle is not None:
            d.angle = angle
        o = bpy.data.objects.new(name, d)
        o.location = loc
        bpy.context.collection.objects.link(o)
        return o

    def aim(o, target):
        d = Vector(target) - o.location
        o.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()

    key = lamp("key", 'AREA', (9.0, 16.0, 3.4), KEY_POWER, KEY_COLOR, size=10.0)
    aim(key, (0, 0, 4.4))

    pool = lamp("pool", 'AREA', (8.5, 2.0, 2.2), POOL_POWER, POOL_COLOR, size=6.0)
    aim(pool, (0.6, 0, 2.6))

    top = lamp("toprim", 'AREA', (4.0, 9.0, 12.5), 620.0, srgb("#FFB169"), size=7.0)
    aim(top, (0, 0, 7.6))

    fill = lamp("fill", 'AREA', (-10.0, -7.0, 4.0), 95.0, srgb("#38506E"), size=12.0)
    aim(fill, (0, 0, 4.0))

    w = bpy.data.worlds.new("w")
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (*AMBIENT, 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = 1.0
    sc.world = w

    # ---- camera ------------------------------------------------------------
    cd = bpy.data.cameras.new("cam")
    cd.lens = CAM_LENS
    cam = bpy.data.objects.new("cam", cd)
    bpy.context.collection.objects.link(cam)
    sc.camera = cam
    return cam


# ============================================================================
# FRAMING
# ============================================================================
def frame_camera(cam, res_x, res_y):
    from bpy_extras.object_utils import world_to_camera_view
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = res_x, res_y
    dep = bpy.context.evaluated_depsgraph_get()

    pts = []
    for ob in bpy.context.scene.objects:
        if ob.type != 'MESH':
            continue
        obe = ob.evaluated_get(dep)
        for c in obe.bound_box:
            pts.append(obe.matrix_world @ Vector(c))

    az = math.radians(CAM_YAW)
    dist = 16.0
    tz = 4.5
    tx = 0.0
    for _ in range(30):
        cam.location = Vector((math.sin(az) * dist, -math.cos(az) * dist, CAM_Z))
        d = Vector((tx, 0, tz)) - cam.location
        cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
        bpy.context.view_layer.update()
        ys = [world_to_camera_view(sc, cam, p).y for p in pts]
        xs = [world_to_camera_view(sc, cam, p).x for p in pts]
        y0, y1 = min(ys), max(ys)
        x0, x1 = min(xs), max(xs)
        hgt = y1 - y0
        wid = x1 - x0
        need = max(hgt / FRAME_FILL, wid / 0.92)
        dist *= need
        # recentre
        span = dist * 36.0 / cam.data.lens
        tz += (((y0 + y1) * 0.5) - FRAME_CENTER) * span * 0.90
        tx += (((x0 + x1) * 0.5) - 0.5) * span * 0.90 * (res_x / res_y)
    print(f"[frame] dist={dist:.2f} tz={tz:.2f} tx={tx:.2f} "
          f"y=({y0:.3f},{y1:.3f}) x=({x0:.3f},{x1:.3f})")


# ============================================================================
# RENDER
# ============================================================================
def setup_render(res_x, res_y, samples, out):
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE'
    sc.render.film_transparent = True
    sc.render.resolution_x, sc.render.resolution_y = res_x, res_y
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA'
    sc.render.image_settings.color_depth = '8'
    sc.render.filepath = os.path.abspath(out)

    ee = sc.eevee
    ee.taa_render_samples = samples
    ee.use_shadows = True
    ee.shadow_ray_count = 2
    ee.shadow_step_count = 6
    ee.use_raytracing = True

    sc.view_settings.view_transform = VIEW_TRANSFORM
    try:
        sc.view_settings.look = VIEW_LOOK
    except Exception:
        pass
    sc.view_settings.exposure = EXPOSURE

    # ---- compositor : bloom on the rim, optionally bleeding into alpha -----
    ng = bpy.data.node_groups.new("comp", "CompositorNodeTree")
    ng.interface.new_socket("Image", in_out='OUTPUT', socket_type='NodeSocketColor')
    n = ng.nodes
    rl = n.new("CompositorNodeRLayers")
    gl = n.new("CompositorNodeGlare")
    go = n.new("NodeGroupOutput")
    try:
        gl.inputs['Type'].default_value = 'Bloom'
    except Exception as e:
        print("glare type:", e)
    gl.inputs['Quality'].default_value = 'High'
    gl.inputs['Threshold'].default_value = GLARE_THRESH
    gl.inputs['Size'].default_value = GLARE_SIZE
    gl.inputs['Strength'].default_value = GLARE_STR
    ng.links.new(rl.outputs['Image'], gl.inputs['Image'])

    if HALO:
        bw = n.new("CompositorNodeRGBToBW")
        mul = n.new("ShaderNodeMath"); mul.operation = 'MULTIPLY'
        mul.inputs[1].default_value = HALO_K
        sa = n.new("CompositorNodeSetAlpha")
        ao = n.new("CompositorNodeAlphaOver")
        ng.links.new(gl.outputs['Glare'], bw.inputs['Image'])
        ng.links.new(bw.outputs['Val'], mul.inputs[0])
        ng.links.new(gl.outputs['Glare'], sa.inputs['Image'])
        ng.links.new(mul.outputs['Value'], sa.inputs['Alpha'])
        ng.links.new(sa.outputs['Image'], ao.inputs['Background'])
        ng.links.new(gl.outputs['Image'], ao.inputs['Foreground'])
        ng.links.new(ao.outputs['Image'], go.inputs[0])
    else:
        ng.links.new(gl.outputs['Image'], go.inputs[0])
    sc.compositing_node_group = ng


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="preview.png")
    ap.add_argument("--w", type=int, default=700)
    ap.add_argument("--h", type=int, default=950)
    ap.add_argument("--samples", type=int, default=24)
    ap.add_argument("--blend", default="")
    a = ap.parse_args(argv)

    cam = build_scene()
    setup_render(a.w, a.h, a.samples, a.out)
    frame_camera(cam, a.w, a.h)
    if a.blend:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(a.blend))
    bpy.ops.render.render(write_still=True)
    print("[done]", a.out)


main()
