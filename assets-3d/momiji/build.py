"""
Stylised Japanese maple (Acer palmatum / momiji) for a dark editorial web hero.

TECHNIQUE A -- alpha-card foliage.

Stage 1: build one palmate 7-lobed momiji leaf as flat geometry, scatter it into
         loose clusters, render each cluster orthographically on a transparent
         background -> leaf-cluster alpha atlases (PNG).
Stage 2: build a dark branch skeleton (short trunk -> 5 low limbs -> 3 levels of
         secondaries), then scatter alpha cards through the canopy volume in
         distinct horizontal TIERS, tinted crimson (low/outer) -> amber (high/inner).

Run:
  Blender --background --factory-startup --python build.py -- [preview|final] [--atlas]

Blender 5.1.2.  Engine identifier is BLENDER_EEVEE (EEVEE Next).
"""

import bpy, bmesh, math, random, os, sys
from mathutils import Vector, Matrix, Euler, Quaternion

# --------------------------------------------------------------------------- #
# config
# --------------------------------------------------------------------------- #
HERE = "/private/tmp/claude-501/-Users-iliaskalalou/1bd10a43-69c5-476d-82d4-b393f02194ee/scratchpad/cards"
ATLAS_DIR = os.path.join(HERE, "atlas")
os.makedirs(ATLAS_DIR, exist_ok=True)

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
MODE = "final" if "final" in argv else "preview"
FORCE_ATLAS = "--atlas" in argv
TAG = ""
for a in argv:
    if a.startswith("--tag="):
        TAG = a.split("=", 1)[1]

N_ATLAS = 4
ATLAS_RES = 768

MASTER_SEED = 20261111


def log(*a):
    print("[momiji]", *a)
    sys.stdout.flush()


# --------------------------------------------------------------------------- #
# colour helpers
# --------------------------------------------------------------------------- #
def s2l(c):
    """single sRGB channel 0..1 -> linear"""
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hexlin(h):
    h = h.lstrip("#")
    return tuple(s2l(int(h[i:i + 2], 16) / 255.0) for i in (0, 2, 4))


def mixc(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


# canopy gradient: t=0 low/outer crimson-magenta  ->  t=1 high/inner amber
GRAD = [
    (0.00, hexlin("#AE2038")),   # deep crimson (photo: lower skirt)
    (0.26, hexlin("#C42B3E")),   # crimson
    (0.48, hexlin("#C1440E")),   # site ember
    (0.72, hexlin("#D2691E")),   # warm orange
    (1.00, hexlin("#E5983F")),   # site amber
]


def grad(t):
    t = max(0.0, min(1.0, t))
    for i in range(len(GRAD) - 1):
        a, ca = GRAD[i]
        b, cb = GRAD[i + 1]
        if t <= b:
            return mixc(ca, cb, (t - a) / (b - a))
    return GRAD[-1][1]


# Horizontal half-width of the foliage envelope as a function of height.
# Branches are steered back inside this: a limb that grows past the leaves
# reads as a dead branch sticking out of the crown.
CANOPY_PROFILE = [(1.20, 2.40), (1.92, 3.30), (2.55, 3.92), (3.30, 3.98),
                  (4.10, 3.50), (4.85, 3.35), (5.60, 2.85), (6.30, 2.10),
                  (6.95, 0.85)]
CANOPY_YSQUASH = 0.66


def canopy_radius(z):
    if z <= CANOPY_PROFILE[0][0]:
        return CANOPY_PROFILE[0][1]
    if z >= CANOPY_PROFILE[-1][0]:
        return CANOPY_PROFILE[-1][1]
    for i in range(len(CANOPY_PROFILE) - 1):
        z0, r0 = CANOPY_PROFILE[i]
        z1, r1 = CANOPY_PROFILE[i + 1]
        if z <= z1:
            return r0 + (r1 - r0) * (z - z0) / (z1 - z0)
    return CANOPY_PROFILE[-1][1]


# --------------------------------------------------------------------------- #
# scene plumbing
# --------------------------------------------------------------------------- #
def wipe():
    for c in (bpy.data.objects, bpy.data.meshes, bpy.data.materials,
              bpy.data.lights, bpy.data.cameras):
        for d in list(c):
            c.remove(d, do_unlink=True)


def new_obj(name, me):
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def mesh_from(name, verts, faces):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.validate()
    me.update()
    return me


# --------------------------------------------------------------------------- #
# STAGE 1 -- momiji leaf geometry
# --------------------------------------------------------------------------- #
def leaf_geo(rng, n_lobes=7):
    """
    One palmate Acer palmatum leaf in the XY plane, petiole at origin,
    central lobe along +Y.  Deeply divided, sharply pointed, serrated lobes.
    Returns (verts, faces).
    """
    verts, faces = [], []

    # lobes fan over ~300 deg; the two basal pairs point sideways / slightly back
    span = math.radians(148.0)                      # half-span
    lengths = {0: 1.00, 1: 0.94, 2: 0.76, 3: 0.50}  # by distance from centre
    half = n_lobes // 2

    NT = 11
    for li in range(n_lobes):
        k = li - half                                # -3..3
        ang = span * (k / half) if half else 0.0
        ang += rng.uniform(-0.05, 0.05)
        L = lengths[abs(k)] * rng.uniform(0.92, 1.06)
        W = 0.125 * (1.0 - 0.10 * abs(k)) * rng.uniform(0.9, 1.1)
        teeth = 7 + abs(k)
        phase = rng.uniform(0, 1)

        ca, sa = math.cos(ang), math.sin(ang)

        def place(t, off):
            # local: axis along +Y, offset along X
            x, y = off, 0.07 + t * L
            return (x * ca - y * sa, x * sa + y * ca, 0.0)

        ring_l, ring_c, ring_r = [], [], []
        for i in range(NT):
            t = i / (NT - 1)
            if t < 0.26:
                sh = (t / 0.26) ** 0.70
            else:
                sh = ((1.0 - t) / 0.74) ** 0.85
            frac = (t * teeth + phase) % 1.0
            ser = 1.0 + 0.16 * (frac - 0.5) * 2.0 * (1.0 - t) ** 0.4
            w = W * sh * ser
            if i == NT - 1:
                w = 0.0                              # sharp point
            ring_l.append(len(verts)); verts.append(place(t, -w))
            ring_c.append(len(verts)); verts.append(place(t, 0.0))
            ring_r.append(len(verts)); verts.append(place(t, w))

        for i in range(NT - 1):
            faces.append((ring_l[i], ring_l[i + 1], ring_c[i + 1], ring_c[i]))
            faces.append((ring_c[i], ring_c[i + 1], ring_r[i + 1], ring_r[i]))

    # small central disc so the lobes are joined, not a loose star
    c0 = len(verts)
    verts.append((0.0, 0.055, 0.0))
    ring = []
    for i in range(12):
        a = 2 * math.pi * i / 12
        ring.append(len(verts))
        verts.append((math.cos(a) * 0.085, 0.055 + math.sin(a) * 0.085, 0.0))
    for i in range(12):
        faces.append((c0, ring[i], ring[(i + 1) % 12]))

    # petiole
    pw = 0.014
    p0 = len(verts)
    verts += [(-pw, 0.05, 0.0), (pw, 0.05, 0.0), (pw * 0.6, -0.32, 0.0), (-pw * 0.6, -0.32, 0.0)]
    faces.append((p0, p0 + 1, p0 + 2, p0 + 3))

    return verts, faces


def flat_emit_mat(name, value):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = (value, value, value, 1.0)
    e.inputs["Strength"].default_value = 1.0
    o = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(e.outputs[0], o.inputs["Surface"])
    return m


def build_atlas(index, seed):
    """Render one loose leaf cluster orthographically on transparent bg."""
    wipe()
    sc = bpy.context.scene
    rng = random.Random(seed)

    # A cluster is MANY SMALL leaves, not a few big ones -- the whole point is
    # that one card reads as a fistful of foliage, so a leaf must end up ~20px
    # in the final frame.  Loose sub-clumps keep the silhouette ragged, and the
    # anisotropic spread stops every card being a circular blob.
    n_clumps = rng.randint(4, 6)
    clumps = [(rng.uniform(-0.52, 0.52), rng.uniform(-0.42, 0.42)) for _ in range(n_clumps)]
    ax, ay = rng.uniform(0.36, 0.48), rng.uniform(0.27, 0.38)
    n_leaves = rng.randint(120, 165)

    for i in range(n_leaves):
        v, f = leaf_geo(rng)
        me = mesh_from("leaf%d" % i, v, f)
        ob = new_obj("leaf%d" % i, me)

        cx, cy = clumps[i % len(clumps)]
        ob.location = (cx + rng.gauss(0, ax),
                       cy + rng.gauss(0, ay),
                       i * 0.002)
        ob.rotation_euler = Euler((math.radians(rng.uniform(-52, 52)),
                                   math.radians(rng.uniform(-40, 40)),
                                   rng.uniform(0, math.tau)), "XYZ")
        s = rng.uniform(0.085, 0.155)
        ob.scale = (s, s, s)
        # luminance variation reads as depth once the card is tinted
        ob.data.materials.append(flat_emit_mat("lm%d" % i, rng.uniform(0.42, 1.0)))

    cd = bpy.data.cameras.new("acam")
    cd.type = "ORTHO"
    cd.ortho_scale = 2.40
    cam = new_obj("acam", cd)
    cam.location = (0, 0, 6)
    sc.camera = cam

    sc.render.engine = "BLENDER_EEVEE"
    sc.render.film_transparent = True
    sc.render.resolution_x = ATLAS_RES
    sc.render.resolution_y = ATLAS_RES
    sc.render.resolution_percentage = 100
    sc.render.filter_size = 1.2
    sc.eevee.taa_render_samples = 24
    sc.eevee.use_shadows = False
    sc.eevee.use_raytracing = False
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.view_settings.view_transform = "Standard"

    path = os.path.join(ATLAS_DIR, "cluster_%d.png" % index)
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    log("atlas ->", path)
    return path


# --------------------------------------------------------------------------- #
# STAGE 2 -- branch skeleton
# --------------------------------------------------------------------------- #
TWIG_R = 0.0100      # ~3 px at final resolution


def add_tube(verts, faces, pts, radii, sides=6):
    base_ring = None
    for i, p in enumerate(pts):
        if i < len(pts) - 1:
            d = (pts[i + 1] - p)
        else:
            d = (p - pts[i - 1])
        if d.length < 1e-8:
            d = Vector((0, 0, 1))
        d.normalize()
        ref = Vector((0, 0, 1))
        if abs(d.dot(ref)) > 0.94:
            ref = Vector((1, 0, 0))
        ax = d.cross(ref).normalized()
        ay = d.cross(ax).normalized()
        ring = []
        for k in range(sides):
            a = math.tau * k / sides
            ring.append(len(verts))
            verts.append(tuple(p + (ax * math.cos(a) + ay * math.sin(a)) * radii[i]))
        if base_ring is not None:
            for k in range(sides):
                k2 = (k + 1) % sides
                faces.append((base_ring[k], base_ring[k2], ring[k2], ring[k]))
        base_ring = ring


def grow(rng, verts, faces, tips, p0, d0, length, radius, depth,
         gravity, spread, segs=6):
    """Recursive tapered limb.  Records endpoints of the finest level in `tips`."""
    pts = [p0.copy()]
    rads = [radius]
    d = d0.normalized()
    step = length / segs
    for i in range(segs):
        t = (i + 1) / segs
        # arch: gradually pull the direction toward horizontal / slightly down.
        # The wobble has to be substantial or the limbs come out as straight
        # rays and the tree reads as a firework instead of a maple.
        d = d + Vector((rng.gauss(0, 0.15), rng.gauss(0, 0.13), -gravity * step))
        # flatten -> tiers: horizontal component grows with distance
        hz = Vector((d.x, d.y, 0.0))
        if hz.length > 1e-6:
            d = hz.normalized() * (hz.length + spread * step * 0.5) + Vector((0, 0, d.z))
        d.normalize()
        p = pts[-1] + d * step
        # steer back inside the foliage envelope
        lim = canopy_radius(p.z) * 1.02
        hr = math.hypot(p.x, p.y / CANOPY_YSQUASH)
        if hr > lim:
            nrm = Vector((p.x, p.y / (CANOPY_YSQUASH ** 2), 0.0))
            if nrm.length > 1e-6:
                nrm.normalize()
                d = (d - nrm * d.dot(nrm) * 1.7)
                d.normalize()
                p = pts[-1] + d * step
        pts.append(p)
        # absolute floor: below ~0.010 units a twig is sub-pixel and the
        # branch tracery simply disappears behind the foliage.
        rads.append(max(TWIG_R, radius * (1.0 - 0.86 * t) + radius * 0.035))
    add_tube(verts, faces, pts, rads, sides=(8 if depth >= 3 else 6 if depth >= 1 else 5))

    if depth <= 0:
        tips.append((pts[-1].copy(), d.copy(), radius))
        return

    n_child = (rng.choice([2, 2, 3]) if depth >= 3
               else rng.choice([2, 3, 3]) if depth >= 2 else 2)
    for c in range(n_child):
        u = rng.uniform(0.30, 1.0)
        idx = min(len(pts) - 1, max(1, int(u * segs)))
        base = pts[idx]
        pd = (pts[idx] - pts[idx - 1]).normalized()
        # branch off sideways, biased outward from the trunk axis
        out = Vector((base.x, base.y, 0.0))
        out = out.normalized() if out.length > 0.2 else Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), 0)).normalized()
        side = pd.cross(Vector((0, 0, 1)))
        if side.length < 1e-5:
            side = Vector((1, 0, 0))
        side.normalize()
        # A strong, uniform outward bias combs every child into the same
        # plane and the limb comes out looking like a palm frond.  Weak radial
        # bias + big sideways/vertical scatter gives a real 3D fan.
        apical = (c == 0)
        k = 0.28 if apical else 1.0          # child 0 carries the limb on
        amt = rng.uniform(0.12, 0.40) * k
        nd = (pd
              + out * amt * rng.uniform(0.5, 1.15)
              + side * rng.gauss(0, 0.85 * k)
              + Vector((rng.gauss(0, 0.30 * k), rng.gauss(0, 0.30 * k),
                        rng.uniform(-0.38, 0.50) * k)))
        nd.normalize()
        nl = length * (rng.uniform(0.72, 0.88) if apical else rng.uniform(0.42, 0.62))
        nr = max(TWIG_R, rads[idx] * (rng.uniform(0.72, 0.86) if apical
                                     else rng.uniform(0.40, 0.56)))
        grow(rng, verts, faces, tips, base, nd, nl, nr, depth - 1,
             gravity * rng.uniform(0.85, 1.20), spread * rng.uniform(0.5, 1.0),
             segs=max(3, segs - 1))


def build_branches(rng):
    verts, faces, tips = [], [], []

    # --- short trunk, leaning slightly, splitting LOW -----------------------
    tpts, trads = [], []
    TH = 1.55
    for i in range(7):
        t = i / 6
        z = t * TH
        tpts.append(Vector((-0.30 * t ** 1.5 + 0.06 * math.sin(t * 3.1),
                            -0.05 * t,
                            z)))
        trads.append(0.205 * (1.0 - 0.44 * t) * (1.0 + 0.06 * math.sin(t * 7.0)))
    add_tube(verts, faces, tpts, trads, sides=10)
    # slight root flare
    add_tube(verts, faces,
             [Vector((0, 0, -0.10)), Vector((0, 0, 0.16))],
             [0.295, 0.205], sides=10)

    top = tpts[-1]

    # --- 6 main limbs off the low fork --------------------------------------
    N_LIMB = 6
    a0 = rng.uniform(0, math.tau)
    for i in range(N_LIMB):
        a = a0 + math.tau * i / N_LIMB + rng.gauss(0, 0.24)
        lean = rng.uniform(0.52, 0.92)          # horizontal push
        d = Vector((math.cos(a) * lean, math.sin(a) * lean * 0.62, rng.uniform(1.50, 2.40)))
        d.normalize()
        start = top + Vector((rng.gauss(0, 0.05), rng.gauss(0, 0.05),
                              rng.uniform(-0.70, 0.30)))
        grow(rng, verts, faces, tips, start, d,
             length=rng.uniform(2.00, 2.50),
             radius=rng.uniform(0.082, 0.112),
             depth=5, gravity=0.17, spread=0.11, segs=7)

    # --- taller central leader: gives the bare twigs above the canopy --------
    d = Vector((rng.gauss(0, 0.20), rng.gauss(0, 0.14), 1.0)).normalized()
    grow(rng, verts, faces, tips, top + Vector((0, 0, 0.05)), d,
         length=3.2, radius=0.098, depth=5, gravity=0.09, spread=0.07, segs=8)

    me = mesh_from("branches", verts, faces)
    for p in me.polygons:
        p.use_smooth = True
    ob = new_obj("branches", me)
    log("branches: %d verts, %d faces, %d tips" % (len(verts), len(faces), len(tips)))
    return ob, tips


def branch_material():
    m = bpy.data.materials.new("bark")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    p = nt.nodes.new("ShaderNodeBsdfPrincipled")
    p.inputs["Base Color"].default_value = (0.0090, 0.0068, 0.0056, 1.0)
    p.inputs["Roughness"].default_value = 0.52
    p.inputs["Specular IOR Level"].default_value = 0.22
    # Warm rim so the backlight just catches the limbs.  Keep this WEAK: on a
    # thin cylinder almost the whole visible surface is near-grazing, so a broad
    # fresnel turns every twig into a glowing whisker.  Narrow blend + a 0.30
    # ceiling on the mix keeps the branches reading as near-black.
    lw = nt.nodes.new("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.45
    rim = nt.nodes.new("ShaderNodeMath")
    rim.operation = "MULTIPLY"
    rim.inputs[1].default_value = 0.10
    nt.links.new(lw.outputs["Fresnel"], rim.inputs[0])
    em = nt.nodes.new("ShaderNodeEmission")
    ec = hexlin("#8C6A3F")
    em.inputs["Color"].default_value = (*ec, 1.0)
    em.inputs["Strength"].default_value = 0.11
    mx = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(rim.outputs[0], mx.inputs["Factor"])
    nt.links.new(p.outputs["BSDF"], mx.inputs[1])
    nt.links.new(em.outputs["Emission"], mx.inputs[2])
    o = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(mx.outputs[0], o.inputs["Surface"])
    return m


# --------------------------------------------------------------------------- #
# STAGE 2 -- alpha cards
# --------------------------------------------------------------------------- #
def card_material(name, img_path, emit_k=0.62):
    img = bpy.data.images.load(img_path, check_existing=True)
    img.colorspace_settings.name = "sRGB"

    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.surface_render_method = "DITHERED"     # alpha hashed: correct depth + shadows
    m.use_backface_culling = False
    m.use_transparent_shadow = True
    nt = m.node_tree
    nt.nodes.clear()

    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    tex.interpolation = "Cubic"
    tex.extension = "CLIP"

    oi = nt.nodes.new("ShaderNodeObjectInfo")     # .Color = tint, .Alpha = emission

    tint = nt.nodes.new("ShaderNodeMix")
    tint.data_type = "RGBA"
    tint.blend_type = "MULTIPLY"
    tint.inputs["Factor"].default_value = 1.0
    nt.links.new(tex.outputs["Color"], tint.inputs[6])   # A (colour)
    nt.links.new(oi.outputs["Color"], tint.inputs[7])    # B (colour)

    # front-lit body
    pr = nt.nodes.new("ShaderNodeBsdfPrincipled")
    pr.inputs["Roughness"].default_value = 0.58
    pr.inputs["Specular IOR Level"].default_value = 0.30
    nt.links.new(tint.outputs[2], pr.inputs["Base Color"])

    # light coming THROUGH the leaf -- this is what sells the backlit look
    tr = nt.nodes.new("ShaderNodeBsdfTranslucent")
    nt.links.new(tint.outputs[2], tr.inputs["Color"])

    mix = nt.nodes.new("ShaderNodeMixShader")
    mix.inputs["Factor"].default_value = 0.55
    nt.links.new(pr.outputs["BSDF"], mix.inputs[1])
    nt.links.new(tr.outputs["BSDF"], mix.inputs[2])

    # per-card emission, strength carried in object-colour alpha
    em = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(tint.outputs[2], em.inputs["Color"])
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    mul.inputs[1].default_value = emit_k
    nt.links.new(oi.outputs["Alpha"], mul.inputs[0])
    nt.links.new(mul.outputs[0], em.inputs["Strength"])

    add = nt.nodes.new("ShaderNodeAddShader")
    nt.links.new(mix.outputs[0], add.inputs[0])
    nt.links.new(em.outputs["Emission"], add.inputs[1])

    tp = nt.nodes.new("ShaderNodeBsdfTransparent")
    cut = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(tex.outputs["Alpha"], cut.inputs["Factor"])
    nt.links.new(tp.outputs["BSDF"], cut.inputs[1])
    nt.links.new(add.outputs[0], cut.inputs[2])

    o = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(cut.outputs[0], o.inputs["Surface"])
    return m


def card_mesh(name):
    me = bpy.data.meshes.new(name)
    me.from_pydata([(-0.5, -0.5, 0), (0.5, -0.5, 0), (0.5, 0.5, 0), (-0.5, 0.5, 0)],
                   [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new(name="UVMap")
    for i, c in enumerate([(0, 0), (1, 0), (1, 1), (0, 1)]):
        uv.data[i].uv = c
    me.update()
    return me


# Distinct horizontal PLATEAUS, thin and well separated, so dark branch
# tracery shows in the gaps -- this is the photo's defining silhouette.
# `t` is the position on the colour ramp (0 crimson .. 1 amber).
# Tier 4 is deliberately sparse: it is the dark waist the photo has between the
# amber upper mass and the big crimson lower plateau.
TIERS = [
    dict(z=6.30, rx=2.10, ry=1.40, th=0.17, droop=0.45, n=14, size=1.55, t=0.97),
    dict(z=5.60, rx=2.85, ry=1.85, th=0.18, droop=0.62, n=19, size=1.65, t=0.86),
    dict(z=4.85, rx=3.35, ry=2.15, th=0.18, droop=0.55, n=22, size=1.72, t=0.70),
    dict(z=4.10, rx=3.50, ry=2.25, th=0.22, droop=0.80, n=14, size=1.66, t=0.55),
    dict(z=3.30, rx=3.98, ry=2.55, th=0.19, droop=0.98, n=22, size=1.80, t=0.34),
    dict(z=2.55, rx=3.92, ry=2.52, th=0.19, droop=1.02, n=19, size=1.78, t=0.18),
    dict(z=1.92, rx=3.30, ry=2.15, th=0.15, droop=1.00, n=10, size=1.60, t=0.06),
]

CANOPY_Z0, CANOPY_Z1 = 1.55, 6.55
RMAX = 3.98


def scatter_cards(rng, mats, cam_loc, tips):
    cards = []
    cm = card_mesh("cardmesh")

    # tip positions help the cards clump where the branches actually end
    tip_pts = [t[0] for t in tips]

    idx = 0
    for ti, T in enumerate(TIERS):
        # scallop the plan-view outline; a plain ellipse projects to a dome,
        # the photo's tiers have lumpy, overlapping edges
        p1, p2 = rng.uniform(0, math.tau), rng.uniform(0, math.tau)
        tilt_x, tilt_y = rng.uniform(-0.10, 0.10), rng.uniform(-0.07, 0.07)
        for k in range(T["n"]):
            # outward-biased sampling: foliage is a shell, densest near the rim
            u = rng.random() ** 0.42
            a = rng.uniform(0, math.tau)
            lobe = 1.0 + 0.20 * math.sin(3 * a + p1) + 0.12 * math.sin(5 * a + p2)
            rx, ry = T["rx"] * u * lobe, T["ry"] * u * lobe
            x = math.cos(a) * rx
            y = math.sin(a) * ry
            z = (T["z"] + rng.gauss(0, T["th"]) - T["droop"] * (u ** 2.2)
                 + tilt_x * x + tilt_y * y)

            # snap a portion of the cards onto nearby branch tips
            if tip_pts and rng.random() < 0.45:
                p = Vector((x, y, z))
                best = min(tip_pts, key=lambda q: (q - p).length_squared)
                if (best - p).length < 2.0:
                    p = p.lerp(best, rng.uniform(0.35, 0.75))
                    x, y, z = p.x, p.y, p.z

            pos = Vector((x, y, z))

            ob = bpy.data.objects.new("card_%03d" % idx, cm)
            bpy.context.scene.collection.objects.link(ob)
            ob.location = pos

            # billboard toward camera, then break it up
            d = (Vector(cam_loc) - pos).normalized()
            q = d.to_track_quat("Z", "Y")
            jit = Euler((math.radians(rng.uniform(-26, 26)),
                         math.radians(rng.uniform(-30, 30)),
                         rng.uniform(0, math.tau)), "XYZ").to_quaternion()
            ob.rotation_mode = "QUATERNION"
            ob.rotation_quaternion = q @ jit

            s = T["size"] * rng.uniform(0.78, 1.28)
            ob.scale = (s * rng.choice([1.0, -1.0]), s, s)   # random UV mirror

            # ---- colour: crimson low/outer -> amber high/inner --------------
            zn = (z - CANOPY_Z0) / (CANOPY_Z1 - CANOPY_Z0)
            rn = min(1.0, math.hypot(x, y / 0.63) / RMAX)
            t = T["t"] + 0.30 * (0.55 - rn) + rng.gauss(0, 0.15)
            col = grad(t)
            col = tuple(c * rng.uniform(0.78, 1.20) for c in col)

            # ---- emission: backlit, strongest high up and at the thin edges --
            e = 0.18 + 1.65 * max(0.0, zn) ** 1.30 + 0.85 * rn ** 2.2
            e *= rng.uniform(0.72, 1.30) * (1.0 + 2.0 * max(0.0, zn - 0.75))
            ob.color = (col[0], col[1], col[2], min(3.0, e))

            cards.append((ob, rng.randrange(len(mats))))
            idx += 1

    # all cards share one mesh -> the material must be linked to the OBJECT,
    # not to the mesh, otherwise every card gets the same atlas variant.
    cm.materials.append(mats[0])
    for ob, mi in cards:
        ob.material_slots[0].link = "OBJECT"
        ob.material_slots[0].material = mats[mi]

    log("cards:", len(cards))
    return [c[0] for c in cards]


def scatter_litter(rng, mats, n=10):
    """A few fallen leaves at the foot of the trunk to ground the composition."""
    cm = card_mesh("littermesh")
    cm.materials.append(mats[0])
    obs = []
    for i in range(n):
        a = rng.uniform(0, math.tau)
        r = rng.uniform(0.6, 3.4) ** 1.0
        x, y = math.cos(a) * r, math.sin(a) * r * 0.55 - 0.3
        ob = bpy.data.objects.new("litter_%02d" % i, cm)
        bpy.context.scene.collection.objects.link(ob)
        ob.location = (x, y, 0.02 + rng.uniform(0, 0.05))
        ob.rotation_euler = Euler((math.radians(rng.uniform(72, 92)),
                                   0.0,
                                   rng.uniform(0, math.tau)), "XYZ")
        s = rng.uniform(0.45, 0.85)
        ob.scale = (s, s, s)
        col = grad(rng.uniform(0.0, 0.35))
        ob.color = (col[0] * 0.55, col[1] * 0.55, col[2] * 0.55, 0.10)
        for si in range(len(ob.material_slots)):
            ob.material_slots[si].link = "OBJECT"
        ob.material_slots[0].material = mats[rng.randrange(len(mats))]
        obs.append(ob)
    log("litter:", len(obs))
    return obs


# --------------------------------------------------------------------------- #
# lighting / camera / render
# --------------------------------------------------------------------------- #
def add_light(name, ltype, loc, aim, energy, color, size=4.0, angle=None):
    ld = bpy.data.lights.new(name, ltype)
    ld.energy = energy
    ld.color = color
    if ltype == "AREA":
        ld.shape = "DISK"
        ld.size = size
    if ltype == "SUN" and angle is not None:
        ld.angle = angle
    ob = new_obj(name, ld)
    ob.location = loc
    d = (Vector(aim) - Vector(loc)).normalized()
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return ob


def setup_world():
    w = bpy.data.worlds.new("w")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Color"].default_value = (0.020, 0.023, 0.034, 1.0)   # cool ambient
    bg.inputs["Strength"].default_value = 1.0
    o = nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(bg.outputs[0], o.inputs["Surface"])


def setup_camera(sc):
    cd = bpy.data.cameras.new("cam")
    cd.sensor_fit = "VERTICAL"
    cd.sensor_height = 24.0
    dist = 26.0
    view_h = 7.62
    cd.lens = 24.0 * dist / view_h
    cd.clip_end = 200.0
    cam = new_obj("cam", cd)
    loc = Vector((0.45, -dist, 2.05))            # slight low angle
    aim = Vector((0.0, 0.0, 3.45))
    cam.location = loc
    cam.rotation_euler = (aim - loc).to_track_quat("-Z", "Y").to_euler()
    sc.camera = cam
    log("cam lens %.1fmm  view_h %.2f  view_w %.2f" % (cd.lens, view_h, view_h * 0.8))
    return cam, loc


def setup_glare(sc):
    """
    Blender 5.x: the scene compositor is a node GROUP.  CompositorNodeComposite
    no longer exists -- the render is fetched with a Render Layers node and the
    result goes to the group output.  (Feeding it from NodeGroupInput yields a
    fully transparent frame; verified the hard way.)
    """
    try:
        ng = bpy.data.node_groups.new("CompGlare", "CompositorNodeTree")
        ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
        gi = ng.nodes.new("CompositorNodeRLayers")
        gi.scene = sc
        go = ng.nodes.new("NodeGroupOutput")
        gl = ng.nodes.new("CompositorNodeGlare")
        ok = False
        for want in ("Bloom", "Fog Glow", "FOG_GLOW", "BLOOM"):
            try:
                gl.inputs["Type"].default_value = want
                ok = True
                log("glare type =", want)
                break
            except Exception:
                continue
        if not ok:
            log("glare: could not set type, using default", gl.inputs["Type"].default_value)
        for k, v in (("Threshold", 0.35), ("Strength", 0.70), ("Size", 0.62),
                     ("Smoothness", 0.35), ("Saturation", 1.15)):
            if k in gl.inputs:
                try:
                    gl.inputs[k].default_value = v
                except Exception as e:
                    log("glare input", k, "failed", e)
        ng.links.new(gi.outputs["Image"], gl.inputs["Image"])
        ng.links.new(gl.outputs["Image"], go.inputs[0])
        sc.use_nodes = True
        sc.compositing_node_group = ng
        log("compositor glare attached")
    except Exception as e:
        import traceback
        traceback.print_exc()
        log("GLARE FAILED (continuing without):", e)


def setup_render(sc, mode):
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.film_transparent = True
    sc.render.filter_size = 1.5
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.render.image_settings.compression = 15
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.view_settings.exposure = 0.0

    ee = sc.eevee
    ee.use_shadows = True
    ee.shadow_ray_count = 2
    ee.shadow_step_count = 4
    ee.use_raytracing = False
    ee.use_fast_gi = True
    ee.fast_gi_ray_count = 2

    if mode == "final":
        sc.render.resolution_x = 1280
        sc.render.resolution_y = 1600
        ee.taa_render_samples = 320
    else:
        sc.render.resolution_x = 800
        sc.render.resolution_y = 1000
        ee.taa_render_samples = 64


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main():
    log("blender", bpy.app.version_string, "mode", MODE)

    atlases = [os.path.join(ATLAS_DIR, "cluster_%d.png" % i) for i in range(N_ATLAS)]
    if FORCE_ATLAS or not all(os.path.exists(p) for p in atlases):
        for i in range(N_ATLAS):
            build_atlas(i, MASTER_SEED + 777 * i)
    else:
        log("atlases already present, reusing")

    wipe()
    sc = bpy.context.scene
    rng = random.Random(MASTER_SEED)

    setup_render(sc, MODE)
    setup_world()
    cam, cam_loc = setup_camera(sc)

    br_ob, tips = build_branches(rng)
    br_ob.data.materials.append(branch_material())
    # Single fixed hero view, so this is a legitimate cheat: nudging the whole
    # skeleton 0.45 toward camera puts the dark tracery in front of part of the
    # canopy shell, which is how it reads in the photo.  Invisible in silhouette.
    br_ob.location.y = -0.20

    mats = [card_material("leafcard_%d" % i, atlases[i]) for i in range(N_ATLAS)]
    scatter_cards(rng, mats, cam_loc, tips)

    # --- lighting: warm backlight/rim + soft cool fill ----------------------
    add_light("backsun", "SUN", (2.0, 14.0, 9.5), (0.0, 0.0, 4.0),
              energy=5.2, color=hexlin("#FFB066"), angle=math.radians(6.0))
    add_light("rim_area", "AREA", (-4.5, 11.0, 7.0), (0.0, 0.0, 4.2),
              energy=2600.0, color=hexlin("#FF8A3C"), size=9.0)
    add_light("fill_cool", "AREA", (-8.0, -10.0, 5.0), (0.0, 0.0, 3.4),
              energy=620.0, color=hexlin("#6E8CB8"), size=12.0)
    add_light("bounce", "AREA", (1.5, -6.0, -1.2), (0.0, 0.0, 2.2),
              energy=210.0, color=hexlin("#C1440E"), size=10.0)

    setup_glare(sc)

    blend = os.path.join(HERE, "tree.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend)
    log("saved", blend)

    name = ("tree_final" if MODE == "final" else "preview") + (("_" + TAG) if TAG else "")
    out = os.path.join(HERE, name + ".png")
    sc.render.filepath = out
    import time
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    log("rendered %s in %.1fs" % (out, time.time() - t0))


main()
