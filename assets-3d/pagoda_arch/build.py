"""
Chureito-style five-storey pagoda (忠霊塔) — architectural treatment.
Blender 5.1.2, headless.

    /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
        --python build.py -- --preview --out preview_01.png

All shape / palette / lighting knobs are named constants at the top of the file.
Detail comes from instanced repeated elements (rafters, bracket blocks,
balusters), never from subdividing.
"""

import bpy, bmesh, math, sys, os
from mathutils import Vector, Matrix

# ---------------------------------------------------------------------------
# 0. CLI
# ---------------------------------------------------------------------------
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
QUALITY = "final" if "--final" in argv else "preview"
DIAG = "--diag" in argv          # flat-lit orthographic elevation, shape check only
OUT = "render.png"
if "--out" in argv:
    OUT = argv[argv.index("--out") + 1]
HERE = os.path.dirname(os.path.abspath(__file__))
OUT_PATH = OUT if os.path.isabs(OUT) else os.path.join(HERE, OUT)
BLEND_PATH = os.path.join(HERE, "pagoda.blend")

# ---------------------------------------------------------------------------
# 1. PALETTE  (sRGB hex — the *albedo*. Dusk lighting takes it much darker.)
#    Deliberately several stops below full-daylight vermilion #D8442A:
#    the building must sit behind the momiji, not beside it.
# ---------------------------------------------------------------------------
HEX_TIMBER      = "9C3520"   # muted vermilion — reads oxblood in shade
HEX_TIMBER_DEEP = "6A2416"   # under-structure, rafter sides
HEX_PLASTER     = "6E6455"   # wall panels
HEX_SOFFIT      = "B0A38C"   # eave underside: stays pale so the rafters
                             # read as DARK stripes on a light field, the
                             # way the photograph reads at dusk
HEX_BRACKET     = "CBBBA0"   # white-tipped bracket blocks
HEX_TILE        = "616B63"   # green-grey tile field
HEX_COPPER      = "6C7660"   # patinated copper eave band
HEX_STONE       = "504D49"   # podium
HEX_BRONZE      = "8A6E42"   # sorin finial (metallic)
HEX_DOOR        = "832C1A"

# Vertical albedo fade: the foot of the building sinks toward the page black.
Z_FADE_LO, Z_FADE_HI = -3.3, 6.0
Z_FADE_MIN = 0.30

# ---------------------------------------------------------------------------
# 2. ARCHITECTURE
# ---------------------------------------------------------------------------
TIERS = 5
ROOF_W0 = 4.35                 # half-width of the bottom eave (axis-aligned)
ROOF_TAPER = 0.900             # each tier's eave relative to the one below
EAVE_Z = [0.00, 3.29, 6.18, 8.92, 11.51]     # eave height, mid-side (lowest pt)

ROOF_RISE = 0.43               # apex height above eave, as fraction of half-width
ROOF_THICK = 0.20              # tile slab thickness (solidify)

# --- sori: the single most important shape in the model -------------------
SWEEP = 0.135                  # corner lift above mid-eave, x half-width
SWEEP_POW = 2.80               # >2 keeps the eave line flat mid-side, flicks at corner
CORNER_EXT = 0.055             # diagonal splay of the corner wing
CORNER_EXT_POW = 3.4
# radial profile control values (fractions of the apex->eave drop)
PROF_C1 = 0.66                 # steep descent off the ridge
PROF_C2 = 0.070                # negative-going tail => eave flicks UP at the tip

ROOF_SEG_SIDE = 20             # ring samples per side
ROOF_SEG_RAD = 10              # apex -> eave rings

# --- hip ridge + corner rafter -------------------------------------------
HIP_SEGS = 8
HIP_W, HIP_H, HIP_LIFT = 0.075, 0.058, 0.045

# --- fascia beam (茅負 kayaoi) — the eave's defining edge ------------------
FASCIA_SEGS = 26               # samples per side
FASCIA_H = 0.135               # half-height (deep board)
FASCIA_T = 0.062               # half-thickness
FASCIA_IN = 0.055              # pulled inboard of the tile edge

# --- rafters (垂木) -------------------------------------------------------
RAFTER_SPACING = 0.175         # absolute, so upper roofs read finer
RAFTER_W = 0.036
RAFTER_H = 0.045
RAFTER_T_IN = 0.42             # inner terminus, fraction of eave radius
RAFTER_SEGS = 3                # must follow the concave soffit, not chord it
CORNER_S = 0.70                # |s| beyond this the rafters fan radially
CORNER_FAN_N = 9

# --- bracket blocks (斗栱) ------------------------------------------------
BRACKET_SPACING = 0.44         # absolute, along the eave
BRACKET_W = 0.078              # half-size along the eave
BRACKET_R = 0.115              # half-size radial
BRACKET_H = 0.062
INNER_BRACKET_T = 0.52         # second, deeper row of red arms w/ white tips

# --- bodies ---------------------------------------------------------------
BODY_FRAC = 0.385              # body half-width / roof half-width
POST_W = 0.165                 # corner post half-thickness
POST_POS = (-1.0, -0.60, -0.20, 0.20, 0.60, 1.0)
RAIL_H = 0.14                  # nageshi horizontal band half-height

# --- railings (高欄) ------------------------------------------------------
RAILING_TIERS = (1, 2, 3)      # bodies that carry a balcony
BALUSTER_SPACING = 0.36

# --- base -----------------------------------------------------------------
BASE_TOP = -2.05
BASE_BOT = -3.35

# --- sorin (相輪) ---------------------------------------------------------
SORIN_H = 5.10
SORIN_RINGS = 9
MAST_R = 0.085

# ---------------------------------------------------------------------------
# 3. CAMERA + LIGHT
# ---------------------------------------------------------------------------
CAM_AZ = 5.0                  # degrees off dead-frontal; a hint of the corner
CAM_DIST = 15.6
CAM_Z = -1.10                   # below the first eave => we look UP
CAM_TARGET_Z = 5.95
CAM_LENS = 23.0

KEY_DIR   = (15.0, 5.0, 7.5)   # low warm key from frame-right, slightly behind
KEY_COLOR = (1.00, 0.57, 0.28)
KEY_POWER = 6.2
RIM_DIR   = (7.0, 13.0, 1.6)   # warm rim raking the eave edges
RIM_COLOR = (1.00, 0.63, 0.34)
RIM_POWER = 5.4
FILL_DIR  = (-12.0, -9.0, -3.0)
FILL_COLOR = (0.34, 0.46, 0.72)
FILL_POWER = 0.62
# up-facing bounce: the camera is below the eaves, so without this the
# soffits, rafters and bracket blocks are simply not in the picture.
BOUNCE_POS   = (16.0, -15.0, -4.0)
BOUNCE_SIZE  = 13.0
BOUNCE_COLOR = (1.00, 0.72, 0.50)
BOUNCE_POWER = 5600.0
WORLD_COLOR = (0.100, 0.078, 0.072)
WORLD_POWER = 1.45
EXPOSURE = -0.58

RES_X, RES_Y = (700, 950) if QUALITY == "preview" else (1400, 1900)
SAMPLES = 24 if QUALITY == "preview" else 160


# ===========================================================================
#  utilities
# ===========================================================================
def srgb(hexstr):
    def lin(c):
        c /= 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return tuple(lin(int(hexstr[i:i + 2], 16)) for i in (0, 2, 4))


def wipe():
    for coll in (bpy.data.objects, bpy.data.meshes, bpy.data.materials,
                 bpy.data.lights, bpy.data.cameras):
        for item in list(coll):
            coll.remove(item)


def mesh_from(name, verts, faces, mats):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.validate()
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    for m in mats:
        ob.data.materials.append(m)
    return ob


def shade_auto(ob, angle_deg=33.0):
    bpy.context.view_layer.objects.active = ob
    for o in bpy.context.selected_objects:
        o.select_set(False)
    ob.select_set(True)
    for opname, kw in (("shade_auto_smooth", {"angle": math.radians(angle_deg)}),
                       ("shade_smooth_by_angle", {"angle": math.radians(angle_deg)}),
                       ("shade_smooth", {})):
        op = getattr(bpy.ops.object, opname, None)
        if op is None:
            continue
        try:
            op(**kw)
            return
        except Exception:
            continue


# --- box builders ----------------------------------------------------------
def push_box(V, F, corners, mat=0):
    """corners: 8 points, bottom quad 0-3 then top quad 4-7 (matching winding)."""
    n = len(V)
    V.extend(corners)
    quads = ((0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1),
             (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0))
    for q in quads:
        F.append(([n + i for i in q], mat))


def box_aabb(V, F, cx, cy, cz, hx, hy, hz, mat=0):
    c = [(cx - hx, cy - hy, cz - hz), (cx + hx, cy - hy, cz - hz),
         (cx + hx, cy + hy, cz - hz), (cx - hx, cy + hy, cz - hz),
         (cx - hx, cy - hy, cz + hz), (cx + hx, cy - hy, cz + hz),
         (cx + hx, cy + hy, cz + hz), (cx - hx, cy + hy, cz + hz)]
    push_box(V, F, c, mat)


def box_between(V, F, p0, p1, hw, hh, mat=0, up=(0, 0, 1)):
    """Rectangular bar running p0 -> p1, hw across, hh vertical-ish."""
    p0, p1 = Vector(p0), Vector(p1)
    d = (p1 - p0)
    if d.length < 1e-6:
        return
    d.normalize()
    side = d.cross(Vector(up))
    if side.length < 1e-6:
        side = Vector((1, 0, 0))
    side.normalize()
    up2 = side.cross(d).normalized()
    c = [p0 - side * hw - up2 * hh, p0 + side * hw - up2 * hh,
         p1 + side * hw - up2 * hh, p1 - side * hw - up2 * hh,
         p0 - side * hw + up2 * hh, p0 + side * hw + up2 * hh,
         p1 + side * hw + up2 * hh, p1 - side * hw + up2 * hh]
    push_box(V, F, [tuple(v) for v in c], mat)


def bar_along(V, F, pts, hw, hh, mat=0, taper=1.0):
    """Chain of boxes through a polyline. Essential for anything that follows
    the roof: a straight chord under a concave soffit pokes through it."""
    n = len(pts) - 1
    for i in range(n):
        f = i / max(1, n - 1)
        s = 1.0 + (taper - 1.0) * f
        box_between(V, F, pts[i], pts[i + 1], hw * s, hh * s, mat)


def build(name, V, F, mats):
    faces = [f for f, _ in F]
    ob = mesh_from(name, V, faces, mats)
    for poly, (_, mi) in zip(ob.data.polygons, F):
        poly.material_index = mi
    return ob


# ===========================================================================
#  materials
# ===========================================================================
def make_mat(name, hexcol, rough=0.55, metal=0.0, zfade=True, spec=0.5):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    col = srgb(hexcol)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = spec
    if not zfade:
        bsdf.inputs["Base Color"].default_value = (*col, 1.0)
        return mat
    # albedo * maprange(worldZ) — the foot of the building sinks into the page
    geo = nt.nodes.new("ShaderNodeNewGeometry"); geo.location = (-900, 0)
    sep = nt.nodes.new("ShaderNodeSeparateXYZ"); sep.location = (-720, 0)
    mr = nt.nodes.new("ShaderNodeMapRange"); mr.location = (-540, 0)
    mr.inputs["From Min"].default_value = Z_FADE_LO
    mr.inputs["From Max"].default_value = Z_FADE_HI
    mr.inputs["To Min"].default_value = Z_FADE_MIN
    mr.inputs["To Max"].default_value = 1.0
    mr.clamp = True
    com = nt.nodes.new("ShaderNodeCombineXYZ"); com.location = (-360, 0)
    vm = nt.nodes.new("ShaderNodeVectorMath"); vm.location = (-190, 0)
    vm.operation = "MULTIPLY"
    vm.inputs[0].default_value = col
    nt.links.new(geo.outputs["Position"], sep.inputs["Vector"])
    nt.links.new(sep.outputs["Z"], mr.inputs["Value"])
    for ax in ("X", "Y", "Z"):
        nt.links.new(mr.outputs["Result"], com.inputs[ax])
    nt.links.new(com.outputs["Vector"], vm.inputs[1])
    nt.links.new(vm.outputs["Vector"], bsdf.inputs["Base Color"])
    return mat


# ===========================================================================
#  roof surface maths
# ===========================================================================
def rot90(p, k):
    x, y = p
    for _ in range(k % 4):
        x, y = -y, x
    return x, y


def eave_point(W, s, side):
    """Plan position + height offset of the eave at parameter s on `side`."""
    e = 1.0 + CORNER_EXT * abs(s) ** CORNER_EXT_POW
    x, y = rot90((W * e, W * s * e), side)
    dz = SWEEP * W * abs(s) ** SWEEP_POW
    return x, y, dz


def prof_g(t):
    """apex->eave height factor, 1 at the ridge, 0 at the eave tip.
    Cubic Bezier with a negative-going P2 so the last stretch flicks UP."""
    mt = 1.0 - t
    return (mt ** 3 * 1.0
            + 3 * mt * mt * t * (1.0 - PROF_C1)
            + 3 * mt * t * t * (-PROF_C2))


def surface_z(W, rise, ez, x, y):
    """World z of the roof top surface at an arbitrary plan point."""
    ax, ay = abs(x), abs(y)
    if ax < 1e-9 and ay < 1e-9:
        return ez + rise
    if ax >= ay:
        s = y / ax * (1 if x > 0 else -1)
        major = ax
    else:
        s = -x / ay * (1 if y > 0 else -1)
        major = ay
    s = max(-1.0, min(1.0, s))
    e = 1.0 + CORNER_EXT * abs(s) ** CORNER_EXT_POW
    t = min(1.0, major / (W * e))
    ze = ez + SWEEP * W * abs(s) ** SWEEP_POW
    drop = (ez + rise) - ze
    return ze + drop * prof_g(t)


def make_roof(idx, W, ez, mats):
    rise = ROOF_RISE * W
    apex_z = ez + rise
    N, NR = ROOF_SEG_SIDE, ROOF_SEG_RAD
    ring = []
    for side in range(4):
        for i in range(N):
            s = -1.0 + 2.0 * i / N
            ring.append(eave_point(W, s, side))
    M = len(ring)

    verts, faces = [], []
    for j in range(NR):                       # t = (j+1)/NR
        t = (j + 1) / NR
        g = prof_g(t)
        for (ex, ey, dz) in ring:
            ze = ez + dz
            drop = apex_z - ze
            verts.append((ex * t, ey * t, ze + drop * g))
    apex_i = len(verts)
    verts.append((0.0, 0.0, apex_z))

    def v(i, j):
        return j * M + (i % M)

    for j in range(NR - 1):
        for i in range(M):
            faces.append((v(i, j), v(i, j + 1), v(i + 1, j + 1), v(i + 1, j)))
    for i in range(M):
        faces.append((apex_i, v(i, 0), v(i + 1, 0)))

    ob = mesh_from(f"roof_{idx}", verts, faces, mats)
    shade_auto(ob, 33.0)
    sol = ob.modifiers.new("shell", "SOLIDIFY")
    sol.thickness = ROOF_THICK
    sol.offset = -1.0
    sol.use_even_offset = True
    sol.material_offset = 1        # soffit (cream)
    sol.material_offset_rim = 2    # copper band at the eave edge
    sol.use_rim = True
    return ob


# ===========================================================================
#  rafters + bracket blocks under the eaves
# ===========================================================================
def add_rafters(V, F, W, ez, mat_r):
    rise = ROOF_RISE * W
    drop_under = ROOF_THICK + RAFTER_H * 0.95

    def under(x, y):
        return surface_z(W, rise, ez, x, y) - drop_under

    def run(p_in, p_out, hw):
        pts = [(p_in[0] + (p_out[0] - p_in[0]) * f,
                p_in[1] + (p_out[1] - p_in[1]) * f, 0.0)
               for f in [i / RAFTER_SEGS for i in range(RAFTER_SEGS + 1)]]
        pts = [(x, y, under(x, y)) for x, y, _ in pts]
        bar_along(V, F, pts, hw, RAFTER_H, mat_r)

    for side in range(4):
        # --- parallel run across the flat of the side --------------------
        span = CORNER_S * W
        n = max(2, int(round(2 * span / RAFTER_SPACING)))
        for i in range(n + 1):
            yy = -span + 2 * span * i / n
            ex, ey, _ = eave_point(W, yy / W, side)
            xin = max(RAFTER_T_IN * W, abs(yy) + 0.02)
            lx, ly = rot90((xin, yy), side)
            run((lx, ly), (ex, ey), RAFTER_W)
        # --- corner fan: every rafter converges on ONE point near the wall
        #     corner, spaced by arc length along the eave. Fanning them from
        #     the roof centre instead gives the matted, crossing mess.
        cx, cy = rot90((RAFTER_T_IN * W, RAFTER_T_IN * W), side)
        arc = []
        prev = None
        for k in range(121):
            u = k / 120.0
            if u <= 0.5:                       # this side, s: CORNER_S -> 1
                s, sd = CORNER_S + (1 - CORNER_S) * (u / 0.5), side
            else:                              # next side, s: -1 -> -CORNER_S
                s, sd = -1.0 + (1 - CORNER_S) * ((u - 0.5) / 0.5), (side + 1) % 4
            p = eave_point(W, s, sd)
            if prev is not None:
                arc.append((arc[-1][0] + math.dist(p, prev) if arc else 0.0, p))
            else:
                arc.append((0.0, p))
            prev = p
        total = arc[-1][0]
        nfan = max(3, int(round(total / RAFTER_SPACING)))
        for k in range(nfan + 1):
            target = total * k / nfan
            p = min(arc, key=lambda ap: abs(ap[0] - target))[1]
            run((cx, cy), (p[0], p[1]), RAFTER_W * 1.02)


def add_fascia(V, F, W, ez, mat):
    """Kayaoi — the deep eave beam. In the reference photograph this solid red
    board is the strongest single line in the building; without it the eave
    curve has no edge and the corners read as a shapeless scoop."""
    rise = ROOF_RISE * W
    ring = []
    for side in range(4):
        for i in range(FASCIA_SEGS):
            s = -1.0 + 2.0 * i / FASCIA_SEGS
            ex, ey, _ = eave_point(W, s, side)
            d = Vector((ex, ey, 0.0)).normalized()
            c = Vector((ex, ey, surface_z(W, rise, ez, ex, ey))) - d * FASCIA_IN
            ring.append((c.x, c.y, c.z - ROOF_THICK * 0.5 - FASCIA_H * 0.55))
    ring.append(ring[0])
    bar_along(V, F, ring, FASCIA_T, FASCIA_H, mat)


def add_hips(V, F, W, ez, mat_ridge, mat_wood, mat_white):
    """Hip ridge on top + corner rafter (隅木) below + the big white corner
    block. Without these the corner is a shapeless flap; with them it reads
    as the pointed, lifted wing that says 'pagoda'."""
    rise = ROOF_RISE * W
    for side in range(4):
        ex, ey, _ = eave_point(W, 1.0, side)          # the corner itself
        # -- ridge tiles running apex -> corner tip ----------------------
        pts = []
        for i in range(HIP_SEGS + 1):
            t = 0.06 + 0.94 * i / HIP_SEGS
            x, y = ex * t, ey * t
            pts.append((x, y, surface_z(W, rise, ez, x, y) + HIP_LIFT))
        bar_along(V, F, pts, HIP_W, HIP_H, mat_ridge, taper=1.2)
        # -- corner rafter, heavier, protruding past the eave ------------
        pts = []
        for i in range(HIP_SEGS + 1):
            t = 0.30 + 0.72 * i / HIP_SEGS
            x, y = ex * t, ey * t
            zz = surface_z(W, rise, ez, min(x, ex), min(y, ey))
            if t > 1.0:                     # extrapolate the flick past the tip
                zz = surface_z(W, rise, ez, ex, ey) + (t - 1.0) * W * 0.22
            pts.append((x, y, zz - ROOF_THICK - RAFTER_H * 1.35))
        bar_along(V, F, pts, RAFTER_W * 2.0, RAFTER_H * 1.7, mat_wood, taper=0.85)
        # -- big white block at the tip ----------------------------------
        d = Vector((ex, ey, 0)).normalized()
        c = Vector((ex, ey, surface_z(W, rise, ez, ex, ey) - ROOF_THICK * 0.75)) \
            - d * 0.16
        box_between(V, F, c - d * 0.15, c + d * 0.15, 0.115, 0.095, mat_white)


def add_brackets(V, F, W, ez, mat_white, mat_red):
    rise = ROOF_RISE * W
    per_side = max(4, int(round(2 * W / BRACKET_SPACING)))
    for side in range(4):
        for i in range(per_side):
            s = -1.0 + 2.0 * (i + 0.5) / per_side
            ex, ey, _ = eave_point(W, s, side)
            zt = surface_z(W, rise, ez, ex, ey) - ROOF_THICK * 0.42
            # -- white block sitting on the top edge of the fascia beam ---
            d = Vector((ex, ey, 0.0)).normalized()
            c = Vector((ex, ey, zt)) - d * FASCIA_IN
            box_between(V, F, c - d * BRACKET_R, c + d * BRACKET_R * 0.55,
                        BRACKET_W, BRACKET_H, mat_white)
            # -- inner arm: red, white-tipped -----------------------------
            t = INNER_BRACKET_T
            ix, iy = ex * t, ey * t
            zi = surface_z(W, rise, ez, ix, iy) - ROOF_THICK - 0.19
            di = Vector((ix, iy, 0.0)).normalized()
            a0 = Vector((ix, iy, zi)) - di * 0.20
            a1 = Vector((ix, iy, zi)) + di * 0.30
            box_between(V, F, a0, a1, 0.085, 0.10, mat_red)
            tip = a1 + di * 0.055
            box_between(V, F, a1, tip + di * 0.06, 0.115, 0.115, mat_white)


# ===========================================================================
#  bodies, railings, base, sorin
# ===========================================================================
def add_body(V, F, bw, z0, z1, mats, ground=False):
    m_tim, m_pla, m_door = mats
    h = (z1 - z0) * 0.5
    cz = (z0 + z1) * 0.5
    # plaster core, slightly inset
    box_aabb(V, F, 0, 0, cz, bw - 0.055, bw - 0.055, h, m_pla)
    # corner posts + intermediates: the body must read RED with cream
    # panels punched into it, not as a pale lantern
    for p in POST_POS:
        for side in range(2):
            for sgn in (1, -1):
                cx, cy = ((bw * p, bw * sgn) if side == 0 else (bw * sgn, bw * p))
                box_aabb(V, F, cx, cy, cz, POST_W, POST_W, h, m_tim)
    # horizontal bands (nageshi): bottom, mid, head
    for f, hh in ((0.0, RAIL_H * 1.15), (0.46, 0.070), (1.0, RAIL_H * 1.45)):
        zz = z0 + (z1 - z0) * f
        zz = min(max(zz, z0 + hh), z1 - hh)
        box_aabb(V, F, 0, 0, zz, bw + 0.045, bw + 0.045, hh, m_tim)
    if ground:
        for sgn in (1, -1):
            box_aabb(V, F, 0, sgn * (bw + 0.045), z0 + (z1 - z0) * 0.30,
                     bw * 0.34, 0.045, (z1 - z0) * 0.26, m_door)
            box_aabb(V, F, sgn * (bw + 0.045), 0, z0 + (z1 - z0) * 0.30,
                     0.045, bw * 0.34, (z1 - z0) * 0.26, m_door)


def add_railing(V, F, rw, z, mat):
    top_z = z + 0.42
    for side in range(4):
        for a, b in ((-1, 1),):
            pass
        # rails
        for zz, hh in ((top_z, 0.055), (z + 0.10, 0.045)):
            x0, y0 = rot90((rw, -rw), side)
            x1, y1 = rot90((rw, rw), side)
            box_between(V, F, (x0, y0, zz), (x1, y1, zz), 0.055, hh, mat)
        # balusters
        n = max(3, int(round(2 * rw / BALUSTER_SPACING)))
        for i in range(n + 1):
            s = -1.0 + 2.0 * i / n
            bx, by = rot90((rw, rw * s), side)
            box_aabb(V, F, bx, by, (z + top_z) * 0.5, 0.032, 0.032,
                     (top_z - z) * 0.5, mat)
    # balcony deck
    box_aabb(V, F, 0, 0, z - 0.04, rw + 0.07, rw + 0.07, 0.055, mat)


def add_base(V, F, bw, mat):
    box_aabb(V, F, 0, 0, (BASE_TOP + BASE_BOT) * 0.5 + 0.25,
             bw * 1.16, bw * 1.16, (BASE_TOP - BASE_BOT) * 0.5 - 0.25, mat)
    box_aabb(V, F, 0, 0, BASE_BOT + 0.24, bw * 1.42, bw * 1.42, 0.24, mat)


def add_sorin(z0, mat):
    objs = []
    mast = bpy.data.objects.new("sorin_mast", bpy.data.meshes.new("m"))
    bpy.ops.mesh.primitive_cylinder_add(vertices=20, radius=MAST_R,
                                        depth=SORIN_H, location=(0, 0, z0 + SORIN_H * 0.5))
    objs.append(bpy.context.object)
    # roban (square plinth) + fukubachi (dome)
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, z0 + 0.14))
    o = bpy.context.object; o.scale = (0.46, 0.46, 0.14); objs.append(o)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=10, radius=0.34,
                                         location=(0, 0, z0 + 0.30))
    o = bpy.context.object; o.scale = (1, 1, 0.55); objs.append(o)
    # kurin: stack of rings
    r_lo, r_hi = z0 + 0.85, z0 + SORIN_H * 0.72
    for i in range(SORIN_RINGS):
        f = i / max(1, SORIN_RINGS - 1)
        z = r_lo + (r_hi - r_lo) * f
        rad = 0.40 - 0.10 * f
        bpy.ops.mesh.primitive_torus_add(major_segments=26, minor_segments=8,
                                         major_radius=rad, minor_radius=0.055,
                                         location=(0, 0, z))
        objs.append(bpy.context.object)
    # suien: four flame plates
    for k in range(4):
        a = math.radians(45 + 90 * k)
        bpy.ops.mesh.primitive_cube_add(size=1.0,
                                        location=(math.cos(a) * 0.20, math.sin(a) * 0.20,
                                                  z0 + SORIN_H * 0.845))
        o = bpy.context.object
        o.scale = (0.30, 0.022, 0.30)
        o.rotation_euler = (0, 0, a)
        objs.append(o)
    # ryusha + hoju
    bpy.ops.mesh.primitive_uv_sphere_add(segments=18, ring_count=9, radius=0.115,
                                         location=(0, 0, z0 + SORIN_H * 0.955))
    objs.append(bpy.context.object)
    bpy.ops.mesh.primitive_cone_add(vertices=18, radius1=0.10, radius2=0.0, depth=0.26,
                                    location=(0, 0, z0 + SORIN_H * 1.01))
    objs.append(bpy.context.object)
    for o in objs:
        o.data.materials.append(mat)
        shade_auto(o, 40.0)
    return objs


# ===========================================================================
#  scene
# ===========================================================================
def look_from(obj, pos):
    obj.rotation_euler = Vector(pos).normalized().to_track_quat("Z", "Y").to_euler()


def main():
    wipe()
    sc = bpy.context.scene

    M = {
        "timber": make_mat("timber", HEX_TIMBER, 0.56),
        "deep":   make_mat("timber_deep", HEX_TIMBER_DEEP, 0.62),
        "plaster": make_mat("plaster", HEX_PLASTER, 0.85, spec=0.25),
        "soffit": make_mat("soffit", HEX_SOFFIT, 0.88, spec=0.25),
        "bracket": make_mat("bracket", HEX_BRACKET, 0.72, spec=0.35),
        "tile":   make_mat("tile", HEX_TILE, 0.34, spec=0.7),
        "copper": make_mat("copper", HEX_COPPER, 0.50, metal=0.35),
        "stone":  make_mat("stone", HEX_STONE, 0.88, spec=0.2),
        "bronze": make_mat("bronze", HEX_BRONZE, 0.30, metal=0.85, zfade=False),
        "door":   make_mat("door", HEX_DOOR, 0.52),
    }

    roof_w = [ROOF_W0 * ROOF_TAPER ** i for i in range(TIERS)]
    body_w = [w * BODY_FRAC for w in roof_w]

    # --- roofs -----------------------------------------------------------
    for i in range(TIERS):
        make_roof(i, roof_w[i], EAVE_Z[i], [M["tile"], M["soffit"], M["copper"]])

    # --- rafters (one mesh, all tiers) ------------------------------------
    V, F = [], []
    for i in range(TIERS):
        add_rafters(V, F, roof_w[i], EAVE_Z[i], 0)
    build("rafters", V, F, [M["deep"]])

    # --- hip ridges, corner rafters, corner blocks ------------------------
    V, F = [], []
    for i in range(TIERS):
        add_hips(V, F, roof_w[i], EAVE_Z[i], 0, 1, 2)
        add_fascia(V, F, roof_w[i], EAVE_Z[i], 3)
    build("hips", V, F, [M["copper"], M["deep"], M["bracket"], M["timber"]])

    # --- bracket blocks ---------------------------------------------------
    V, F = [], []
    for i in range(TIERS):
        add_brackets(V, F, roof_w[i], EAVE_Z[i], 0, 1)
    build("brackets", V, F, [M["bracket"], M["timber"]])

    # --- bodies, railings, base ------------------------------------------
    V, F = [], []
    add_base(V, F, body_w[0], 3)
    for i in range(TIERS):
        z0 = BASE_TOP if i == 0 else EAVE_Z[i - 1] - 0.05
        # stop the wall just under its own roof — otherwise it punches
        # straight through the tiles
        z1 = (surface_z(roof_w[i], ROOF_RISE * roof_w[i], EAVE_Z[i], body_w[i], 0.0)
              - ROOF_THICK - 0.06)
        add_body(V, F, body_w[i], z0, z1, (0, 1, 2), ground=(i == 0))
        if i in RAILING_TIERS:
            rw = body_w[i] + 0.40
            deck = surface_z(roof_w[i - 1], ROOF_RISE * roof_w[i - 1],
                             EAVE_Z[i - 1], rw, 0.0) + 0.03
            add_railing(V, F, rw, deck, 0)
    build("body", V, F, [M["timber"], M["plaster"], M["door"], M["stone"]])

    # --- sorin ------------------------------------------------------------
    top_apex = EAVE_Z[TIERS - 1] + ROOF_RISE * roof_w[TIERS - 1]
    add_sorin(top_apex - 0.35, M["bronze"])

    # --- camera -----------------------------------------------------------
    az = math.radians(CAM_AZ)
    cam_d = bpy.data.cameras.new("cam")
    cam_d.lens = CAM_LENS
    cam = bpy.data.objects.new("cam", cam_d)
    bpy.context.collection.objects.link(cam)
    cam.location = (CAM_DIST * math.sin(az), -CAM_DIST * math.cos(az), CAM_Z)
    d = Vector((0, 0, CAM_TARGET_Z)) - Vector(cam.location)
    cam.rotation_euler = (-d).to_track_quat("Z", "Y").to_euler()
    sc.camera = cam
    if DIAG:   # dead-on orthographic elevation: judge the sori silhouette alone
        cam_d.type = "ORTHO"
        cam_d.ortho_scale = 22.0
        cam.location = (0, -60, 7.0)
        cam.rotation_euler = (math.radians(90), 0, 0)

    # --- lights -----------------------------------------------------------
    def sun(name, dirvec, color, power, angle=3.0):
        ld = bpy.data.lights.new(name, "SUN")
        ld.color = color
        ld.energy = power
        ld.angle = math.radians(angle)
        o = bpy.data.objects.new(name, ld)
        bpy.context.collection.objects.link(o)
        o.location = Vector(dirvec).normalized() * 30
        look_from(o, dirvec)
        return o

    sun("key", KEY_DIR, KEY_COLOR, KEY_POWER, 2.5)
    sun("rim", RIM_DIR, RIM_COLOR, RIM_POWER, 6.0)
    sun("fill", FILL_DIR, FILL_COLOR, FILL_POWER, 25.0)
    # ground/sky bounce from below — we are looking UP, so this is what
    # actually reveals the soffits, the rafter rhythm and the bracket blocks.
    bd = bpy.data.lights.new("bounce", "AREA")
    bd.shape = "DISK"
    bd.size = BOUNCE_SIZE
    bd.color = BOUNCE_COLOR
    bd.energy = BOUNCE_POWER
    bo = bpy.data.objects.new("bounce", bd)
    bpy.context.collection.objects.link(bo)
    bo.location = BOUNCE_POS
    look_from(bo, (BOUNCE_POS[0] * 0.15, BOUNCE_POS[1] * 0.15,
                   BOUNCE_POS[2] - 8.0))

    world = bpy.data.worlds.new("w")
    sc.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (*WORLD_COLOR, 1.0)
    bg.inputs[1].default_value = WORLD_POWER

    if DIAG:   # flat, even light: read the shape, not the mood
        for o in list(bpy.data.objects):
            if o.type == "LIGHT":
                bpy.data.objects.remove(o)
        for nm, dv in (("d0", (0, -1, 0.25)), ("d1", (0.6, -1, 0.6)),
                       ("d2", (-0.6, -1, -0.5))):
            sun(nm, dv, (1, 1, 1), 3.0, 10.0)
        bg.inputs[0].default_value = (0.25, 0.25, 0.28, 1.0)
        bg.inputs[1].default_value = 1.0

    # --- render settings --------------------------------------------------
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.film_transparent = True
    sc.render.resolution_x, sc.render.resolution_y = RES_X, RES_Y
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.render.filter_size = 1.4
    ee = sc.eevee
    for attr, val in (("taa_render_samples", SAMPLES), ("use_shadows", True),
                      ("use_raytracing", True), ("use_gtao", True),
                      ("shadow_ray_count", 2), ("shadow_step_count", 6),
                      ("use_bloom", False), ("use_volumetric_lights", False)):
        try:
            setattr(ee, attr, val)
        except Exception:
            pass
    try:
        rt = ee.ray_tracing_options
        rt.use_denoise = True
        rt.resolution_scale = "1"
    except Exception:
        pass
    try:
        sc.view_settings.view_transform = "AgX"
        sc.view_settings.look = "AgX - Medium Contrast"
    except Exception:
        try:
            sc.view_settings.look = "Medium Contrast"
        except Exception:
            pass
    sc.view_settings.exposure = EXPOSURE
    if DIAG:
        sc.view_settings.view_transform = "Standard"
        sc.view_settings.exposure = 0.0
        sc.render.film_transparent = True

    # --- compositor: whisper of bloom on the rim --------------------------
    try:
        ng = bpy.data.node_groups.new("comp", "CompositorNodeTree")
        sc.compositing_node_group = ng
        ng.interface.new_socket("Image", in_out="OUTPUT",
                                socket_type="NodeSocketColor")
        rl = ng.nodes.new("CompositorNodeRLayers"); rl.location = (-400, 0)
        gl = ng.nodes.new("CompositorNodeGlare"); gl.location = (-150, 0)
        for cand in ("BLOOM", "Bloom", "FOG_GLOW", "Fog Glow"):
            try:
                gl.inputs["Type"].default_value = cand
                break
            except Exception:
                continue
        for key, val in (("Threshold", 0.72), ("Strength", 0.22),
                         ("Size", 7.0), ("Quality", "HIGH")):
            try:
                gl.inputs[key].default_value = val
            except Exception:
                pass
        out = ng.nodes.new("NodeGroupOutput"); out.location = (120, 0)
        ng.links.new(rl.outputs["Image"], gl.inputs["Image"])
        ng.links.new(gl.outputs[0], out.inputs[0])
    except Exception as exc:
        print("compositor skipped:", exc)

    # --- stats ------------------------------------------------------------
    dg = bpy.context.evaluated_depsgraph_get()
    tris = 0
    for ob in sc.objects:
        if ob.type != "MESH":
            continue
        me = ob.evaluated_get(dg).to_mesh()
        me.calc_loop_triangles()
        tris += len(me.loop_triangles)
        ob.evaluated_get(dg).to_mesh_clear()
    print(f"### TRIANGLES: {tris}")
    print(f"### OBJECTS:   {len(sc.objects)}")

    bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)
    sc.render.filepath = OUT_PATH
    bpy.ops.render.render(write_still=True)
    print("### WROTE", OUT_PATH)


main()
