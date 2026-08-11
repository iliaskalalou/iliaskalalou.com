"""
Chureito-style five-storey pagoda  --  TREATMENT C : HALF-LIT DUSK
Left-hand hero element, rendered RGBA over a #0c0c0c page.

Run:
  /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
      --python build.py -- [preview|final] [out.png]

Everything that governs shape or colour is a named constant in the CONFIG block.
"""

import bpy, bmesh, sys, math, os
from mathutils import Vector, Matrix

# ============================================================================
#  CONFIG
# ============================================================================

# ---- storeys ---------------------------------------------------------------
N_TIERS       = 5          # five roofs
ROOF_W0       = 1.00       # half-width of the bottom eave  (the master unit)
ROOF_WR       = 0.885      # each roof is this fraction of the one below
EAVE_Z0       = 1.16       # height of the bottom eave (low point, mid-side)
GAP0          = 0.66       # vertical distance eave0 -> eave1
GAPR          = 0.900      # that gap shrinks by this each storey

# ---- the sori : the single most important shape ----------------------------
ROOF_RISE     = 0.400      # apex height above the eave low point, x half-width
CORNER_LIFT   = 0.155      # how far the corner of the eave lifts above mid-side
LIFT_P1       = 0.34       # weight of u^2 in the lift curve (broad gentle part)
LIFT_P2       = 0.66       # weight of u^6 (the hard hook at the very corner)
CORNER_FLARE  = 0.130      # corners also push OUT in plan, diagonally
ROOF_Q        = 1.55       # roof section: high q = steep at ridge, flat at eave
ROOF_B        = 0.26       # linear blend so the eave keeps a shallow real slope
ROOF_THK      = 0.038      # roof shell thickness (x half-width)

# ---- eave underside rhythm -------------------------------------------------
N_RAFTER_BASE = 24         # rafters per side on the bottom roof
RAFTER_W      = 0.036      # rafter width  (x half-width)
RAFTER_H      = 0.016      # rafter depth
RAFTER_T_IN   = 0.44       # inner end, as a fraction of the eave radius
RAFTER_T_OUT  = 0.962
HIP_W         = 0.075      # the big diagonal corner beam (sumigi)
HIP_H         = 0.055
MENDO_W       = 0.042      # the little white blocks between the rafter ends
N_BRACKET     = 9          # bracket blocks per side at the top of each wall

# ---- bodies ----------------------------------------------------------------
BODY_WR       = 0.455      # wall half-width, as fraction of that storey's eave
BODY_W0       = 0.485      # ground floor is a touch wider
RAIL_OUT      = 0.175      # railing reach beyond the wall (x half-width)
PLINTH_H      = 0.42

# ---- sorin (the bronze finial) --------------------------------------------
SORIN_H       = 1.30
N_KURIN       = 9          # nine rings, as tradition demands

# ---- palette  (sRGB hex; converted to linear at build time) ----------------
#  Deliberately pulled DOWN from postcard vermilion: this building is the
#  momiji's cooler, quieter echo, not its rival.
C_VERMILION   = "#8E2A19"            # shu-iro, darkened ~25% from #D8442A
C_VERM_DARK   = "#571A10"            # beams in shadow / recessed timber
C_CREAM       = "#6E6659"            # wall plaster panels: recessed, muted
C_SOFFIT      = "#C6BAA1"            # eave underside: the pale field that reads
C_TILE        = "#2F3634"            # green-grey tile
C_COPPER      = "#46564A"            # patinated copper edge band
C_BRONZE      = "#5A452A"            # sorin
C_STONE       = "#1E1F1F"
C_WHITE_TIP   = "#BDB4A2"            # the white-tipped blocks
C_DARK_WOOD   = "#241612"

# ---- camera ----------------------------------------------------------------
CAM_AZIM      = 24.0       # degrees; +ve swings right so we see the +X flank
CAM_DIST      = 7.15
CAM_Z         = -0.20       # below mid-height -> we look UP at it
CAM_TARGET_Z  = 2.34
CAM_LENS      = 42.0
CAM_SHIFT_Y   = 0.0

# ---- lighting : half-lit dusk ---------------------------------------------
#  Azimuth is measured from the camera axis: 0 = frontal, +90 = right of
#  frame, 180 = straight behind the building. Elevation may be NEGATIVE --
#  a sun under the eave line is what makes a pagoda's soffits glow at dusk.
#  "bounce" is the crucial one, and it is a soft SPOT that casts NO shadows.
#  A pagoda's eave soffits are lit by light coming off the ground -- but any
#  shadow-casting source below the horizon is blocked by the roof of the storey
#  underneath, so every soffit but the lowest goes black. Faking the bounce as
#  a shadowless warm wash is what a gaffer would do. Making it a positioned
#  spot rather than a sun is what buys the half-lit look: inverse-square gives
#  the left-right gradient (right eaves glow, left ones fall away) and the very
#  soft cone edge gives the vertical one, sinking the base into the dark.
LIGHTS = [
    dict(kind='SPOT', name='bounce', azim=76,   elev=-17, dist=5.6, aim=2.95,
         color=(1.00, 0.645, 0.450), energy=820.0, size=1.60,
         spot=52.0, blend=0.95, shadow=False),
    dict(kind='SUN',  name='graze',  azim=86,   elev=-11,
         color=(1.00, 0.545, 0.270), energy=0.55, size=0.08, shadow=True),
    dict(kind='SUN',  name='key',    azim=48,   elev=19,
         color=(1.00, 0.590, 0.320), energy=0.85, size=0.05, shadow=True),
    dict(kind='SUN',  name='rim',    azim=165,  elev=9,
         color=(1.00, 0.605, 0.345), energy=3.00, size=0.07, shadow=True),
    dict(kind='SUN',  name='fill',   azim=-100, elev=22,
         color=(0.40, 0.470, 0.600), energy=0.42, size=0.30, shadow=False),
]
LIGHT_AIM_Z   = 2.00       # default aim height
WORLD_COLOR   = (0.020, 0.026, 0.038)
WORLD_STR     = 0.30

RES_FINAL     = (1400, 1900)
RES_PREVIEW   = (700, 950)
SAMPLES_FINAL = 220
SAMPLES_PREV  = 24

HERE = os.path.dirname(os.path.abspath(__file__))
NO_SHADOW = False
SOLO = None

# ============================================================================
#  small helpers
# ============================================================================

def s2l(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

def hexl(h):
    h = h.lstrip("#")
    return tuple(s2l(int(h[i:i + 2], 16) / 255.0) for i in (0, 2, 4))


class MB:
    """Accumulates verts/faces/material-indices for one object."""
    def __init__(self):
        self.v, self.f, self.m = [], [], []

    def add(self, verts, faces, mat):
        o = len(self.v)
        self.v.extend([tuple(p) for p in verts])
        for fc in faces:
            self.f.append(tuple(i + o for i in fc))
            self.m.append(mat)

    def object(self, name, mats, coll=None):
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.v, [], self.f)
        me.validate(verbose=False)
        for m in mats:
            me.materials.append(m)
        for i, p in enumerate(me.polygons):
            p.material_index = self.m[i]
        me.update()
        ob = bpy.data.objects.new(name, me)
        (coll or bpy.context.scene.collection).objects.link(ob)
        return ob


def box(mb, cx, cy, z0, z1, hx, hy, mat):
    """Axis-aligned box, given centre xy, z range and half extents."""
    v = [(cx - hx, cy - hy, z0), (cx + hx, cy - hy, z0),
         (cx + hx, cy + hy, z0), (cx - hx, cy + hy, z0),
         (cx - hx, cy - hy, z1), (cx + hx, cy - hy, z1),
         (cx + hx, cy + hy, z1), (cx - hx, cy + hy, z1)]
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
         (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    mb.add(v, f, mat)


def sweep(mb, pts, w, h, mat, updir=(0, 0, 1)):
    """Sweep a rectangular section along a polyline."""
    P = [Vector(p) for p in pts]
    n = len(P)
    if n < 2:
        return
    U = Vector(updir)
    verts = []
    for i, p in enumerate(P):
        if i == 0:
            t = P[1] - P[0]
        elif i == n - 1:
            t = P[-1] - P[-2]
        else:
            t = P[i + 1] - P[i - 1]
        t.normalize()
        s = t.cross(U)
        if s.length < 1e-7:
            s = Vector((1, 0, 0))
        s.normalize()
        up = s.cross(t).normalized()
        verts += [p + s * (w / 2) + up * (h / 2),
                  p - s * (w / 2) + up * (h / 2),
                  p - s * (w / 2) - up * (h / 2),
                  p + s * (w / 2) - up * (h / 2)]
    faces = []
    for i in range(n - 1):
        a, b = i * 4, (i + 1) * 4
        for k in range(4):
            k2 = (k + 1) % 4
            faces.append((a + k, a + k2, b + k2, b + k))
    faces.append((3, 2, 1, 0))
    L = (n - 1) * 4
    faces.append((L + 0, L + 1, L + 2, L + 3))
    mb.add(verts, faces, mat)


def cyl(mb, cx, cy, z0, z1, r0, r1, mat, seg=20):
    v, f = [], []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        v.append((cx + r0 * math.cos(a), cy + r0 * math.sin(a), z0))
    for i in range(seg):
        a = 2 * math.pi * i / seg
        v.append((cx + r1 * math.cos(a), cy + r1 * math.sin(a), z1))
    for i in range(seg):
        j = (i + 1) % seg
        f.append((i, j, seg + j, seg + i))
    f.append(tuple(range(seg - 1, -1, -1)))
    f.append(tuple(range(seg, 2 * seg)))
    mb.add(v, f, mat)


def torus(mb, cx, cy, cz, R, r, mat, seg=22, ring=8):
    v, f = [], []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        ca, sa = math.cos(a), math.sin(a)
        for j in range(ring):
            b = 2 * math.pi * j / ring
            rr = R + r * math.cos(b)
            v.append((cx + rr * ca, cy + rr * sa, cz + r * math.sin(b) * 0.72))
    for i in range(seg):
        i2 = (i + 1) % seg
        for j in range(ring):
            j2 = (j + 1) % ring
            f.append((i * ring + j, i2 * ring + j, i2 * ring + j2, i * ring + j2))
    mb.add(v, f, mat)


def sphere(mb, cx, cy, cz, r, mat, seg=16, ring=10, squash=1.0):
    v, f = [], []
    for j in range(ring + 1):
        phi = math.pi * j / ring
        for i in range(seg):
            th = 2 * math.pi * i / seg
            v.append((cx + r * math.sin(phi) * math.cos(th),
                      cy + r * math.sin(phi) * math.sin(th),
                      cz + r * math.cos(phi) * squash))
    for j in range(ring):
        for i in range(seg):
            i2 = (i + 1) % seg
            f.append((j * seg + i, j * seg + i2, (j + 1) * seg + i2, (j + 1) * seg + i))
    mb.add(v, f, mat)


# ============================================================================
#  the roof surface  --  this is where the pagoda lives or dies
# ============================================================================

def prof(t):
    """Vertical profile from apex (t=0, ->1) to eave (t=1, ->0). Concave."""
    s = max(0.0, 1.0 - t)
    return ROOF_B * s + (1 - ROOF_B) * s ** ROOF_Q


def eave_lift(u):
    """How much the eave rises at plan-parameter u along one side.
       u=0 mid-side (lowest), u=+-1 the corner (highest)."""
    return LIFT_P1 * u * u + LIFT_P2 * u ** 6


def roof_pt(W, rise, u, t, side):
    """Point on the roof surface. side 0..3 rotates by -90 deg each time."""
    ex = W * (u + CORNER_FLARE * u ** 5)
    ey = W * (1.0 + CORNER_FLARE * u ** 4)
    x, y = t * ex, t * ey
    for _ in range(side):                       # rotate -90: (x,y)->(y,-x)
        x, y = y, -x
    z = rise * prof(t) + CORNER_LIFT * W * eave_lift(u) * (t ** 2.5)
    return Vector((x, y, z))


# ring parameters : denser toward the eave so the edge band is crisp
T_RINGS = [0.05, 0.13, 0.22, 0.31, 0.41, 0.51, 0.60, 0.68,
           0.755, 0.822, 0.878, 0.925, 0.958, 0.980, 1.0]
COPPER_FROM = 0.958     # rings beyond this get the patinated edge material
NU = 25                 # samples per side (u = -1 .. +1 inclusive)


def ring_verts(W, rise, t):
    out = []
    for side in range(4):
        for i in range(NU - 1):                 # skip u=+1: it is next side's u=-1
            u = -1.0 + 2.0 * i / (NU - 1)
            out.append(roof_pt(W, rise, u, t, side))
    return out


M_TILE, M_CREAM, M_COPPER, M_VERM, M_WHITE, M_VDARK = 0, 1, 2, 3, 4, 5
M_BRONZE, M_STONE, M_SOFFIT = 6, 7, 8


def build_roof_shell(mb, W, rise, eave_z, thk):
    """Closed roof shell: tiled top, cream soffit, copper rim."""
    per = 4 * (NU - 1)
    top_rings, bot_rings = [], []
    for t in T_RINGS:
        rv = ring_verts(W, rise, t)
        top_rings.append([v + Vector((0, 0, eave_z)) for v in rv])
        bot_rings.append([v + Vector((0, 0, eave_z - thk)) for v in rv])

    verts, faces, mats = [], [], []

    def push(ring):
        base = len(verts)
        verts.extend([tuple(p) for p in ring])
        return base

    top_base = [push(r) for r in top_rings]
    bot_base = [push(r) for r in bot_rings]

    # apex caps
    apex_t = tuple(Vector((0, 0, eave_z + rise * prof(0.0))))
    apex_b = tuple(Vector((0, 0, eave_z + rise * prof(0.0) - thk)))
    ai_t, ai_b = len(verts), len(verts) + 1
    verts.append(apex_t)
    verts.append(apex_b)
    for i in range(per):
        j = (i + 1) % per
        faces.append((ai_t, top_base[0] + j, top_base[0] + i)); mats.append(M_TILE)
        faces.append((ai_b, bot_base[0] + i, bot_base[0] + j)); mats.append(M_SOFFIT)

    # bands
    for k in range(len(T_RINGS) - 1):
        cop = T_RINGS[k] >= COPPER_FROM - 1e-6
        mt = M_COPPER if cop else M_TILE
        mb_ = M_COPPER if cop else M_SOFFIT
        a, b = top_base[k], top_base[k + 1]
        c, d = bot_base[k], bot_base[k + 1]
        for i in range(per):
            j = (i + 1) % per
            faces.append((a + i, a + j, b + j, b + i)); mats.append(mt)
            faces.append((c + j, c + i, d + i, d + j)); mats.append(mb_)

    # rim at the eave edge
    a, c = top_base[-1], bot_base[-1]
    for i in range(per):
        j = (i + 1) % per
        faces.append((a + j, a + i, c + i, c + j)); mats.append(M_COPPER)

    o = len(mb.v)
    mb.v.extend(verts)
    for f, m in zip(faces, mats):
        mb.f.append(tuple(i + o for i in f))
        mb.m.append(m)


def build_eave_detail(mb, W, rise, eave_z, thk, n_raf):
    """Radiating rafters, the four hip beams, and the white mendo blocks."""
    soff = eave_z - thk

    def P(u, t, side, dz):
        p = roof_pt(W, rise, u, t, side)
        return (p.x, p.y, p.z + soff + dz)

    # --- fan rafters -------------------------------------------------------
    ts = [RAFTER_T_IN + (RAFTER_T_OUT - RAFTER_T_IN) * k / 4.0 for k in range(5)]
    for side in range(4):
        for r in range(n_raf):
            u = -0.955 + 1.910 * r / (n_raf - 1)
            if abs(u) > 0.90:                   # near the corner the hip beam rules
                continue
            pts = [P(u, t, side, -RAFTER_H * 0.5) for t in ts]
            sweep(mb, pts, RAFTER_W * W, RAFTER_H * W, M_VERM)

    # --- hip beams : the strong diagonals under each corner ----------------
    hts = [0.30 + 0.70 * k / 5.0 for k in range(6)]
    for side in range(4):
        pts = [P(1.0, t, side, -HIP_H * 0.42) for t in hts]
        sweep(mb, pts, HIP_W * W, HIP_H * W, M_VERM)

    # --- white blocks between the rafter ends ------------------------------
    for side in range(4):
        for r in range(n_raf - 1):
            u = -0.955 + 1.910 * (r + 0.5) / (n_raf - 1)
            if abs(u) > 0.88:
                continue
            p0 = P(u, 0.945, side, -RAFTER_H * 0.28)
            p1 = P(u, 1.004, side, -RAFTER_H * 0.28)
            sweep(mb, [p0, p1], MENDO_W * W, RAFTER_H * 0.62 * W, M_WHITE)

    # --- a thin dark shadow-line fascia just inside the copper band --------
    for side in range(4):
        pts = [P(-1.0 + 2.0 * i / 16.0, 0.930, side, -RAFTER_H * 0.95) for i in range(17)]
        sweep(mb, pts, W * 0.013, W * 0.026, M_VDARK)


# ============================================================================
#  bodies, railings, base, finial
# ============================================================================

def build_body(mb, bw, z0, z1, W, ground=False):
    """Cream wall panels framed by vermilion posts and beams."""
    box(mb, 0, 0, z0, z1, bw, bw, M_CREAM)

    post = bw * 0.085
    # corner + intermediate posts on each face. Three bays everywhere: at hero
    # scale a fourth bay just reads as picket-fence noise once the front and
    # the flank overlap in perspective.
    ncol = 3
    for side in range(4):
        for c in range(ncol + 1):
            u = -1.0 + 2.0 * c / ncol
            x, y = u * bw, bw + post * 0.35
            for _ in range(side):
                x, y = y, -x
            hx = post if abs(u) < 0.99 else post
            box(mb, x, y, z0, z1, hx if side % 2 == 0 else post * 0.9,
                post * 0.9 if side % 2 == 0 else hx, M_VERM)
    # corner posts, fat
    for sx in (-1, 1):
        for sy in (-1, 1):
            box(mb, sx * bw, sy * bw, z0, z1, post * 1.5, post * 1.5, M_VERM)

    # beams: sill, mid rail, head
    bh = (z1 - z0)
    levels = [(z0, z0 + bh * 0.055), (z1 - bh * 0.075, z1)]
    if ground:
        levels.insert(1, (z0 + bh * 0.60, z0 + bh * 0.665))
    for (a, b) in levels:
        e = bw + post * 0.5
        box(mb, 0, 0, a, b, e, e, M_VERM)

    if ground:
        # One recessed door per face and nothing else. The grille windows that
        # used to flank it disappeared into visual noise at this scale.
        for side in range(4):
            dz0, dz1 = z0 + bh * 0.12, z0 + bh * 0.66
            x, y = 0.0, -(bw + post * 0.55)
            for _ in range(side):
                x, y = y, -x
            hx, hy = bw * 0.30, post * 0.55
            if side % 2 == 1:
                hx, hy = hy, hx
            box(mb, x, y, dz0, dz1, hx, hy, M_VERM)
            box(mb, x, y, dz0 + bh * 0.025, dz1 - bh * 0.025,
                hx * 0.84, hy * 1.2, M_VDARK)


def build_brackets(mb, bw, z_top, W):
    """The dense row of white-tipped bracket blocks under every eave."""
    proj = W * 0.085
    h = W * 0.048
    for side in range(4):
        for i in range(N_BRACKET):
            u = -0.88 + 1.76 * i / (N_BRACKET - 1)
            x, y = u * bw, bw
            dx, dy = 0.0, 1.0
            for _ in range(side):
                x, y = y, -x
                dx, dy = dy, -dx
            p0 = (x, y, z_top - h * 0.5)
            p1 = (x + dx * proj, y + dy * proj, z_top - h * 0.5)
            sweep(mb, [p0, p1], W * 0.040, h, M_VERM)
            p2 = (x + dx * proj * 0.98, y + dy * proj * 0.98, z_top - h * 0.5)
            p3 = (x + dx * proj * 1.20, y + dy * proj * 1.20, z_top - h * 0.5)
            sweep(mb, [p2, p3], W * 0.046, h * 1.05, M_WHITE)
        # continuous head beam behind them
    e = bw + W * 0.012
    box(mb, 0, 0, z_top - h * 1.9, z_top - h * 0.95, e, e, M_VERM)


def build_railing(mb, r, z_deck, W):
    """Balcony rail on the middle storeys."""
    post = W * 0.016
    rail_z = z_deck + W * 0.115
    # deck lip
    box(mb, 0, 0, z_deck - W * 0.02, z_deck + W * 0.012, r, r, M_VDARK)
    # top rail
    box(mb, 0, 0, rail_z, rail_z + W * 0.024, r + post, r + post, M_VERM)
    # mid rail
    box(mb, 0, 0, rail_z - W * 0.055, rail_z - W * 0.037, r + post * 0.6,
        r + post * 0.6, M_VERM)
    # balusters
    n = max(6, int(r / (W * 0.085)))
    for side in range(4):
        for i in range(n):
            u = -0.94 + 1.88 * i / (n - 1)
            x, y = u * r, r
            for _ in range(side):
                x, y = y, -x
            box(mb, x, y, z_deck, rail_z, post, post, M_VERM)
    # corner newels
    for sx in (-1, 1):
        for sy in (-1, 1):
            box(mb, sx * r, sy * r, z_deck - W * 0.03, rail_z + W * 0.05,
                post * 2.0, post * 2.0, M_VERM)


def build_sorin(mb, z0, W):
    """Bronze finial: roban, fukubachi, nine rings, suien, hoju."""
    M = M_BRONZE
    h = SORIN_H
    box(mb, 0, 0, z0 - 0.02, z0 + h * 0.055, W * 0.115, W * 0.115, M)
    sphere(mb, 0, 0, z0 + h * 0.055, W * 0.095, M, squash=0.62)
    cyl(mb, 0, 0, z0 + h * 0.09, z0 + h * 0.145, W * 0.030, W * 0.075, M)
    # mast
    cyl(mb, 0, 0, z0 + h * 0.10, z0 + h * 1.00, W * 0.026, W * 0.017, M, seg=14)
    # nine rings
    for i in range(N_KURIN):
        f = i / (N_KURIN - 1)
        z = z0 + h * (0.185 + 0.520 * f)
        R = W * (0.108 - 0.030 * f)
        torus(mb, 0, 0, z, R, W * 0.021, M)
    # suien : four pierced flame plates
    zs = z0 + h * 0.755
    for side in range(4):
        for k in range(3):
            u = (k - 1) * W * 0.052
            x, y = u, W * 0.030
            for _ in range(side):
                x, y = y, -x
            hh = h * (0.115 if k == 1 else 0.088)
            box(mb, x, y, zs, zs + hh, W * 0.010, W * 0.010, M)
        x, y = 0.0, W * 0.030
        for _ in range(side):
            x, y = y, -x
        box(mb, x, y, zs + h * 0.088, zs + h * 0.102, W * 0.060, W * 0.010, M)
    # ryusha + hoju
    cyl(mb, 0, 0, z0 + h * 0.905, z0 + h * 0.935, W * 0.048, W * 0.038, M)
    sphere(mb, 0, 0, z0 + h * 0.985, W * 0.052, M, squash=1.25)


def build_base(mb, W):
    """A quiet stacked-stone plinth. It is meant to sink into the dark."""
    M = M_STONE
    box(mb, 0, 0, -PLINTH_H, -PLINTH_H * 0.55, W * 0.82, W * 0.82, M)
    box(mb, 0, 0, -PLINTH_H * 0.56, -PLINTH_H * 0.22, W * 0.72, W * 0.72, M)
    box(mb, 0, 0, -PLINTH_H * 0.23, 0.012, W * 0.615, W * 0.615, M)


# ============================================================================
#  materials
# ============================================================================

def mat(name, hexcol, rough=0.62, metal=0.0, spec=0.4):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    b.inputs["Base Color"].default_value = (*hexl(hexcol), 1.0)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    for key in ("Specular IOR Level", "Specular"):
        if key in b.inputs:
            b.inputs[key].default_value = spec
            break
    try:
        m.surface_render_method = 'DITHERED'
    except Exception:
        pass
    return m


# ============================================================================
#  scene
# ============================================================================

def clear():
    for c in (bpy.data.objects, bpy.data.meshes, bpy.data.materials,
              bpy.data.lights, bpy.data.cameras):
        for d in list(c):
            c.remove(d, do_unlink=True)


def light(spec):
    """Place one light. azim 0 = from the camera, +90 = frame-right,
       180 = from behind. Elevation may be negative (a source below the eaves)."""
    kind = spec["kind"]
    d = bpy.data.lights.new(spec["name"], kind)
    d.color = spec["color"]
    d.energy = spec["energy"]
    if kind == 'SUN':
        d.angle = spec.get("size", 0.03)
    else:
        if kind == 'AREA':
            d.shape = 'DISK'
        d.shadow_soft_size = spec.get("size", 0.5)
        if kind == 'SPOT':
            d.spot_size = math.radians(spec.get("spot", 45.0))
            d.spot_blend = spec.get("blend", 0.9)
    try:
        d.use_shadow = spec.get("shadow", True) and not NO_SHADOW
    except Exception:
        pass
    ob = bpy.data.objects.new(spec["name"], d)
    bpy.context.scene.collection.objects.link(ob)
    ang = math.radians(CAM_AZIM - 90.0 + spec["azim"])
    e = math.radians(spec["elev"])
    direction = Vector((math.cos(ang) * math.cos(e),
                        math.sin(ang) * math.cos(e),
                        math.sin(e)))
    aim = Vector((0, 0, spec.get("aim", LIGHT_AIM_Z)))
    ob.location = aim + direction * spec.get("dist", 20.0)
    ob.rotation_euler = (-direction).to_track_quat('-Z', 'Y').to_euler()
    return ob


def build_scene():
    clear()
    sc = bpy.context.scene

    mats = [
        mat("tile",    C_TILE,     0.78),
        mat("cream",   C_CREAM,    0.86, spec=0.28),
        mat("copper",  C_COPPER,   0.44, metal=0.68),
        mat("verm",    C_VERMILION, 0.60),
        mat("white",   C_WHITE_TIP, 0.80, spec=0.3),
        mat("vdark",   C_VERM_DARK, 0.70),
        mat("bronze",  C_BRONZE,   0.42, metal=0.85),
        mat("stone",   C_STONE,    0.90, spec=0.2),
        mat("soffit",  C_SOFFIT,   0.88, spec=0.24),
    ]

    # ---- storey table -----------------------------------------------------
    Ws, Zs, rises = [], [], []
    z = EAVE_Z0
    gap = GAP0
    for i in range(N_TIERS):
        W = ROOF_W0 * (ROOF_WR ** i)
        Ws.append(W)
        Zs.append(z)
        rises.append(ROOF_RISE * W)
        z += gap
        gap *= GAPR

    mb = MB()
    build_base(mb, ROOF_W0)

    for i in range(N_TIERS):
        W, ez, rise = Ws[i], Zs[i], rises[i]
        bw = (BODY_W0 if i == 0 else BODY_WR) * W
        thk = ROOF_THK * W

        # wall: from the roof surface below (or the plinth) up into the roof
        if i == 0:
            z0 = 0.0
        else:
            t_wall = min(0.98, bw / Ws[i - 1])
            z0 = Zs[i - 1] + rises[i - 1] * prof(t_wall) - 0.02
        z1 = ez + rise * 0.20
        build_body(mb, bw, z0, z1, W, ground=(i == 0))
        build_brackets(mb, bw, ez + rise * 0.06, W)

        # railing sits on the roof below
        if 1 <= i <= 3:
            r = bw + RAIL_OUT * W
            t_r = min(0.985, r / Ws[i - 1])
            z_deck = Zs[i - 1] + rises[i - 1] * prof(t_r)
            build_railing(mb, r, z_deck, W)

        n_raf = max(11, int(round(N_RAFTER_BASE * W / ROOF_W0)))
        build_roof_shell(mb, W, rise, ez, thk)
        build_eave_detail(mb, W, rise, ez, thk, n_raf)

    build_sorin(mb, Zs[-1] + rises[-1] * prof(0.0) - 0.04, ROOF_W0)

    ob = mb.object("Pagoda", mats)
    ob.rotation_euler = (0, 0, 0)

    # ---- camera -----------------------------------------------------------
    cd = bpy.data.cameras.new("Cam")
    cd.lens = CAM_LENS
    cd.sensor_fit = 'AUTO'
    cd.shift_y = CAM_SHIFT_Y
    cam = bpy.data.objects.new("Cam", cd)
    sc.collection.objects.link(cam)
    a = math.radians(CAM_AZIM)
    cam.location = Vector((math.sin(a) * CAM_DIST, -math.cos(a) * CAM_DIST, CAM_Z))
    tgt = Vector((0, 0, CAM_TARGET_Z))
    cam.rotation_euler = (cam.location - tgt).to_track_quat('Z', 'Y').to_euler()
    sc.camera = cam
    bpy.context.view_layer.update()

    # ---- light ------------------------------------------------------------
    for spec in LIGHTS:
        light(spec)

    world = bpy.data.worlds.new("W")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (*WORLD_COLOR, 1.0)
    bg.inputs[1].default_value = WORLD_STR
    sc.world = world
    return ob


def setup_render(preview):
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE'          # 5.1: only this enum exists
    sc.render.film_transparent = True
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA'
    sc.render.image_settings.color_depth = '8'
    res = RES_PREVIEW if preview else RES_FINAL
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.filter_size = 1.40

    ev = sc.eevee
    ev.taa_render_samples = SAMPLES_PREV if preview else SAMPLES_FINAL
    for attr, val in (("use_raytracing", True), ("use_shadows", True),
                      ("shadow_ray_count", 2 if preview else 4),
                      ("shadow_step_count", 4 if preview else 8),
                      ("use_shadow_jitter_viewport", True)):
        try:
            setattr(ev, attr, val)
        except Exception:
            pass
    try:
        ev.ray_tracing_options.resolution_scale = '1'
        ev.ray_tracing_options.use_denoise = True
    except Exception:
        pass

    vs = sc.view_settings
    try:
        vs.view_transform = 'AgX'
    except Exception:
        pass
    for look in ("AgX - Base Contrast", "Base Contrast", "None"):
        try:
            vs.look = look
            break
        except Exception:
            continue
    vs.exposure = 0.0
    vs.gamma = 1.0


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    mode = argv[0] if argv else "preview"
    out = argv[1] if len(argv) > 1 else "out.png"
    if not os.path.isabs(out):
        out = os.path.join(HERE, out)
    preview = (mode != "final")

    global LIGHTS, WORLD_COLOR, WORLD_STR
    if "flat" in argv:                       # diagnostic: pure ambient
        LIGHTS, WORLD_COLOR, WORLD_STR = [], (1.0, 1.0, 1.0), 1.6
    global NO_SHADOW, SOLO
    NO_SHADOW = "noshadow" in argv
    for tok in argv:                          # diagnostic: solo one light
        if tok.startswith("solo="):
            SOLO = tok.split("=", 1)[1]
            LIGHTS = [L for L in LIGHTS if L["name"] == SOLO]
    build_scene()
    setup_render(preview)

    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "pagoda.blend"))
    bpy.context.scene.render.filepath = out
    bpy.ops.render.render(write_still=True)
    print("WROTE", out)

    tri = sum(len(p.vertices) - 2 for p in bpy.data.objects["Pagoda"].data.polygons)
    print("TRIS", tri, "VERTS", len(bpy.data.objects["Pagoda"].data.vertices))


main()
