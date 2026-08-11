# -*- coding: utf-8 -*-
"""
Mount Fuji - BACKGROUND layer for a website hero.  TREATMENT C : MINIMAL.

The mountain barely emerges from darkness: a thin warm rim along its sunlit
(left) flank, a faint suggestion of the snow cap, and a cloud band catching the
last light.  Everything else dissolves into the page black (#0c0c0c).

Blender 5.1, headless:
  /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
      --python build.py -- [preview|final]

Outputs (RGBA, transparent background, sky delivered separately):
  fuji_final.png / fuji_prev.png       mountain + clouds
  fuji_sky_final.png / fuji_sky_prev.png   optional sky gradient layer

SILHOUETTE.  The profile is measured, not invented.  The reference photograph
was edge-detected row by row; the resulting silhouette fits

        h(r) = H * exp(-r / c),   c / H = 2.09

to within 6% over the whole visible flank.  That exponential is what produces
Fuji's concave flanks - steep upper cone (~32 deg), skirt flaring out to a very
shallow angle.  A straight-sided cone reads as "generic mountain".

BRIGHTNESS DISCIPLINE.  View transform is Standard (not AgX) so authored sRGB
values survive to the file.  Targets, over the #0c0c0c page:
  body in shadow  ~14      snow, unlit      ~20
  snow, lit       ~40      cloud band       ~55-95
  rim (thin)      ~110-140  <- the single brightest thing in the frame
"""

import bpy, math, sys, os
import numpy as np

D = os.path.dirname(os.path.abspath(__file__))
MODE = "preview"
OPTS = set()
if "--" in sys.argv:
    a = sys.argv[sys.argv.index("--") + 1:]
    if a:
        MODE = a[0]
        OPTS = set(a[1:])          # diagnostics: noglare / cloudsonly / mtnonly

# ----------------------------------------------------------------------------
# PARAMETERS
# ----------------------------------------------------------------------------
H_MTN   = 3.40            # summit height above the notional base plain (~km)
C_PROF  = 2.00 * H_MTN    # profile decay length, measured off the reference
R_MAX   = 26.0            # radius at which the skirt is cut
SUMMIT_R = 0.42           # flat crater cap; ~0.12 H, as measured on the photo
N_RING  = 300
N_SEG   = 720

# Framing: summit at 34% of width, 20% of height; visible cone above the cloud
# band spans ~26% of frame height (same cone-width : frame-width ratio as the
# reference photograph).
CAM_D   = 48.0
CAM_X   = 1.255
CAM_Z   = 2.224
LENS    = 220.4           # long lens -> distant, flat, near-orthographic cone

# sun: low, to the LEFT and BEHIND -> a thin crescent hugging the left edge.
# Left, because the portrait sits centre and the momiji occupies the right.
SUN = np.array([-0.80, 0.44, 0.26]); SUN /= np.linalg.norm(SUN)

SNOW_LO, SNOW_HI = 0.545, 0.73   # snowline as a fraction of H, noise-warped
HAZE_LO, HAZE_HI = 1.05, 2.62    # alpha ramp: below HAZE_LO the skirt is gone

RIM_POW  = 9.0            # high power = the light lives on the edge, not the face
RIM_GAIN = 2.6
COOL_GAIN = 0.85

if MODE == "final":
    RES, SAMPLES, MAPW, MAPH = (2400, 1200), 256, 3600, 1120
else:
    RES, SAMPLES, MAPW, MAPH = (1200, 600), 96, 1800, 560


def s2l(c):
    """sRGB 0-255 -> linear."""
    o = []
    for v in c:
        v = v / 255.0
        o.append(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4)
    return np.array(o)


COL_SHADOW   = s2l((16, 18, 26))     # rock in shadow: cold indigo, near-black
COL_RIM_COOL = s2l((74, 92, 124))    # skylight edge on the dark flank
COL_ROCK_LIT = s2l((16, 13, 11))     # rock catching the last light: warm
COL_SNOW_AMB = s2l((21, 24, 32))     # snow, unlit
COL_SNOW_LIT = s2l((29, 24, 21))     # snow, lit - a suggestion, not a spotlight
COL_HAZE     = s2l((15, 17, 23))
COL_RIM      = s2l((214, 133, 68))   # the one accent: ember/amber (#C1440E..#E08D3C)
COL_CLOUD_W  = s2l((201, 129, 93))   # cloud underside, warm
COL_CLOUD_C  = s2l((44, 47, 60))     # cloud top, cool


def nn(nt, kind, loc=(0, 0), **kw):
    n = nt.nodes.new(kind)
    n.location = loc
    for k, v in kw.items():
        setattr(n, k, v)
    return n


def fbm(coords, octaves=5, lac=2.03, gain=0.5, seed=0):
    """value noise, periodic in the angular coordinate"""
    rng = np.random.default_rng(seed)
    a, r = coords
    out = np.zeros_like(a)
    amp, freq, norm = 1.0, 1.0, 0.0
    for _ in range(octaves):
        m = max(1, int(round(3 * freq)))
        ph = rng.uniform(0, 2 * np.pi, 4)
        v = (np.sin(2 * np.pi * m * a + ph[0] + 2.1 * np.sin(r * 1.7 * freq + ph[1]))
             * np.cos(r * 2.6 * freq + ph[2] + 1.3 * np.sin(2 * np.pi * m * a + ph[3])))
        out += amp * v
        norm += amp
        amp *= gain
        freq *= lac
    return out / norm


# ----------------------------------------------------------------------------
# SCENE
# ----------------------------------------------------------------------------
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)

scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x, scene.render.resolution_y = RES
scene.render.resolution_percentage = 100
scene.render.film_transparent = True          # sky must NOT be baked in
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.render.image_settings.color_depth = '8'
scene.render.dither_intensity = 1.5
scene.view_settings.view_transform = 'Standard'
scene.view_settings.look = 'None'
scene.eevee.taa_render_samples = SAMPLES
scene.eevee.use_volume_custom_range = True
# the froxel range must bracket the clouds tightly, otherwise the slices are so
# far apart at 40+ units that every cloud shape integrates away into a flat bar
scene.eevee.volumetric_start = 26.0
scene.eevee.volumetric_end = 78.0
scene.eevee.volumetric_samples = 256
scene.eevee.volumetric_tile_size = '2'
scene.eevee.use_volumetric_shadows = False
scene.eevee.volumetric_sample_distribution = 0.0

world = bpy.data.worlds.new("W")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[1].default_value = 0.0

# ----------------------------------------------------------------------------
# MOUNTAIN MESH
# ----------------------------------------------------------------------------
i = np.arange(N_RING + 1)
rr = R_MAX * (i / N_RING) ** 1.55            # rings crowd toward the summit
th = np.arange(N_SEG) * (2 * np.pi / N_SEG)
R2, T2 = np.meshgrid(rr, th, indexing='ij')

z_base = math.exp(-R_MAX / C_PROF)
# flattens the apex WITHOUT shifting the rest of the profile outward:
# r_eff -> r^2/r0 near the summit (flat cap), -> r far out (profile intact).
# (sqrt(r^2+r0^2)-r0 looks similar but offsets every radius by r0, which fattens
#  the whole cone by 0.09 H - measurably wrong against the reference.)
R_EFF = R2 ** 2 / np.sqrt(R2 ** 2 + SUMMIT_R ** 2)
Z = H_MTN * (np.exp(-R_EFF / C_PROF) - z_base) / (1.0 - z_base)

ang, rad = T2 / (2 * np.pi), R2 / R_MAX
g_hi = fbm((ang, rad * 9.0), octaves=6, seed=7)      # erosion gullies
g_lo = fbm((ang, rad * 2.2), octaves=3, seed=13)     # broad ridges
u = Z / H_MTN
env = np.clip((u - 0.05) / 0.95, 0, 1) ** 0.7
Z += H_MTN * (0.0125 * g_hi + 0.009 * g_lo) * env * (0.25 + 0.75 * u)
Z += H_MTN * 0.006 * np.cos(T2 * 2 + 0.6) * env      # a whisper of asymmetry
Z += H_MTN * 0.004 * np.cos(T2 * 3 - 1.4) * env

cr = 0.62                                            # summit crater, shallow
w = np.clip(1.0 - (R2 / cr) ** 2, 0, 1)
Z = np.where(R2 < cr,
             Z - H_MTN * 0.016 * (w ** 1.5) * (1.0 - 0.42 * np.cos(T2 - 2.35)), Z)

X, Y = R2 * np.cos(T2), R2 * np.sin(T2)
verts = np.stack([X.ravel(), Y.ravel(), Z.ravel()], axis=1)

# winding: (inner, outer, outer+1, inner+1) -> normals point OUT and UP.
# the mirror of this order points them into the mountain and, with backface
# culling on, silently renders the unlit far side of the cone.
faces = []
for a in range(N_RING):
    b0, b1 = a * N_SEG, (a + 1) * N_SEG
    for s in range(N_SEG):
        s2 = (s + 1) % N_SEG
        faces.append((b0 + s, b1 + s, b1 + s2, b0 + s2))

me = bpy.data.meshes.new("FujiMesh")
me.from_pydata(verts.tolist(), [], faces)
me.update()
mtn = bpy.data.objects.new("Fuji", me)
bpy.context.collection.objects.link(mtn)
for p in me.polygons:
    p.use_smooth = True

# ----------------------------------------------------------------------------
# VERTEX-BAKED SHADING (broad terms; the rim is per-pixel, in the shader)
# ----------------------------------------------------------------------------
nrm = np.zeros(len(me.vertices) * 3, dtype=np.float32)
me.vertex_normals.foreach_get("vector", nrm)
N = nrm.reshape(-1, 3)
P = verts
cam = np.array([CAM_X, -CAM_D, CAM_Z])

ndl = N @ SUN
lam = np.clip(ndl, 0, 1)
wrap = np.clip((ndl + 0.30) / 1.30, 0, 1)
uz = np.clip(P[:, 2] / H_MTN, 0, 1)

ga = (np.arctan2(P[:, 1], P[:, 0]) / (2 * np.pi)) % 1.0
gr = np.sqrt(P[:, 0] ** 2 + P[:, 1] ** 2) / R_MAX
gul = fbm((ga, gr * 11.0), octaves=5, seed=7)        # same family as geometry
gul_b = fbm((ga, gr * 3.0), octaves=3, seed=31)
edge = uz + 0.075 * gul + 0.050 * gul_b              # ragged lower snow edge
snow = np.clip((edge - SNOW_LO) / (SNOW_HI - SNOW_LO), 0, 1)
snow = snow * snow * (3 - 2 * snow)
snow *= np.clip(1.0 - 0.80 * np.clip(gul * 1.7, 0, 1), 0.15, 1.0)   # dark gullies

body = (COL_SHADOW[None, :] * (0.72 + 0.28 * wrap[:, None])
        + COL_ROCK_LIT[None, :] * (lam ** 1.5)[:, None])
body = body * (1 - snow[:, None]) + (
    COL_SNOW_AMB[None, :] * (0.50 + 0.50 * wrap[:, None])
    + COL_SNOW_LIT[None, :] * (lam ** 1.35)[:, None]) * snow[:, None]

dist = np.linalg.norm(P - cam[None, :], axis=1)
hz = np.clip((dist - 34.0) / 40.0, 0, 1) * 0.30      # far side flattens slightly
body = body * (1 - hz[:, None]) + COL_HAZE[None, :] * hz[:, None]

alpha = np.clip((P[:, 2] - HAZE_LO) / (HAZE_HI - HAZE_LO), 0, 1) ** 1.30

rim_h = np.clip((P[:, 2] - 1.45) / 1.35, 0, 1) ** 0.8
rim_m = np.clip(ndl * 1.35, 0, 1) ** 1.7 * rim_h * (0.50 + 0.50 * snow)
# counter-rim: without a whisper of skylight on the dark flank the cone never
# closes and the shape reads as a diagonal streak instead of a mountain
rim_c = np.clip(-ndl * 1.10, 0, 1) ** 1.2 * rim_h

ca = me.color_attributes.new("BODY", 'FLOAT_COLOR', 'POINT')
ca.data.foreach_set("color", np.concatenate(
    [body, alpha[:, None]], axis=1).astype(np.float32).ravel())
cb = me.color_attributes.new("MASK", 'FLOAT_COLOR', 'POINT')
cb.data.foreach_set("color", np.stack(
    [rim_m, snow, rim_c, np.ones_like(rim_m)],
    axis=1).astype(np.float32).ravel())

# ----------------------------------------------------------------------------
# MOUNTAIN MATERIAL
# ----------------------------------------------------------------------------
mat = bpy.data.materials.new("FujiMat")
mat.use_nodes = True
mat.surface_render_method = 'DITHERED'    # writes depth: volumes composite in front
mat.use_backface_culling = True
nt = mat.node_tree
nt.nodes.clear()

out = nn(nt, "ShaderNodeOutputMaterial", (1400, 0))
vc = nn(nt, "ShaderNodeVertexColor", (-1200, 200), layer_name="BODY")
vm = nn(nt, "ShaderNodeVertexColor", (-1200, -100), layer_name="MASK")
sep = nn(nt, "ShaderNodeSeparateColor", (-1000, -100))
nt.links.new(vm.outputs["Color"], sep.inputs["Color"])

geo = nn(nt, "ShaderNodeNewGeometry", (-1200, -400))
dot = nn(nt, "ShaderNodeVectorMath", (-1000, -400), operation='DOT_PRODUCT')
nt.links.new(geo.outputs["Normal"], dot.inputs[0])
nt.links.new(geo.outputs["Incoming"], dot.inputs[1])
inv = nn(nt, "ShaderNodeMath", (-820, -400), operation='SUBTRACT', use_clamp=True)
inv.inputs[0].default_value = 1.0
nt.links.new(dot.outputs["Value"], inv.inputs[1])
pw = nn(nt, "ShaderNodeMath", (-640, -400), operation='POWER')
pw.inputs[1].default_value = RIM_POW
nt.links.new(inv.outputs["Value"], pw.inputs[0])
rmul = nn(nt, "ShaderNodeMath", (-460, -400), operation='MULTIPLY')
nt.links.new(pw.outputs["Value"], rmul.inputs[0])
nt.links.new(sep.outputs["Red"], rmul.inputs[1])
rgain = nn(nt, "ShaderNodeMath", (-300, -400), operation='MULTIPLY')
rgain.inputs[1].default_value = RIM_GAIN
nt.links.new(rmul.outputs["Value"], rgain.inputs[0])
rimcol = nn(nt, "ShaderNodeMixRGB", (-120, -300), blend_type='MULTIPLY')
rimcol.inputs["Fac"].default_value = 1.0
rimcol.inputs["Color1"].default_value = (*COL_RIM, 1)
nt.links.new(rgain.outputs["Value"], rimcol.inputs["Color2"])

# cool counter-rim, broader and much fainter
pwc = nn(nt, "ShaderNodeMath", (-640, -640), operation='POWER')
pwc.inputs[1].default_value = 5.0
nt.links.new(inv.outputs["Value"], pwc.inputs[0])
cmul = nn(nt, "ShaderNodeMath", (-460, -640), operation='MULTIPLY')
nt.links.new(pwc.outputs["Value"], cmul.inputs[0])
nt.links.new(sep.outputs["Blue"], cmul.inputs[1])
cgain = nn(nt, "ShaderNodeMath", (-300, -640), operation='MULTIPLY')
cgain.inputs[1].default_value = COOL_GAIN
nt.links.new(cmul.outputs["Value"], cgain.inputs[0])
ccol = nn(nt, "ShaderNodeMixRGB", (-120, -620), blend_type='MULTIPLY')
ccol.inputs["Fac"].default_value = 1.0
ccol.inputs["Color1"].default_value = (*COL_RIM_COOL, 1)
nt.links.new(cgain.outputs["Value"], ccol.inputs["Color2"])

add0 = nn(nt, "ShaderNodeMixRGB", (60, -400), blend_type='ADD')
add0.inputs["Fac"].default_value = 1.0
nt.links.new(rimcol.outputs["Color"], add0.inputs["Color1"])
nt.links.new(ccol.outputs["Color"], add0.inputs["Color2"])

add = nn(nt, "ShaderNodeMixRGB", (200, 0), blend_type='ADD')
add.inputs["Fac"].default_value = 1.0
nt.links.new(vc.outputs["Color"], add.inputs["Color1"])
nt.links.new(add0.outputs["Color"], add.inputs["Color2"])

em = nn(nt, "ShaderNodeEmission", (500, 0))
nt.links.new(add.outputs["Color"], em.inputs["Color"])
tr = nn(nt, "ShaderNodeBsdfTransparent", (500, -200))
mix = nn(nt, "ShaderNodeMixShader", (900, 0))
nt.links.new(tr.outputs[0], mix.inputs[1])
nt.links.new(em.outputs[0], mix.inputs[2])
nt.links.new(vc.outputs["Alpha"], mix.inputs["Fac"])
nt.links.new(mix.outputs[0], out.inputs["Surface"])
mtn.data.materials.append(mat)


# ----------------------------------------------------------------------------
# CLOUD LAYERS
# An emissive volume whose density and lighting come from an authored 2D map
# (cloudmap.py) extruded along the view axis.  Volume emission is per unit of
# PATH LENGTH: at km scale the strength has to be tiny or the band blows out.
# ----------------------------------------------------------------------------
sys.path.insert(0, D)
import cloudmap
import importlib
importlib.reload(cloudmap)


def bake_map(seed, name):
    """write the map to disk and load it; generated in-memory images do not
    survive .blend round-trips and silently render as black."""
    path = os.path.join(D, name + ".png")
    m = cloudmap.cloud_map(seed=seed, W=MAPW, H=MAPH)
    if True:                                   # always regenerate: cheap, exact
        import struct, zlib
        h, w, _ = m.shape
        px = (np.clip(m, 0, 1) * 255.0 + 0.5).astype(np.uint8)
        raw = b"".join(b"\x00" + px[r].tobytes() for r in range(h))

        def chunk(tag, data):
            c = tag + data
            return struct.pack(">I", len(data)) + c + struct.pack(
                ">I", zlib.crc32(c) & 0xFFFFFFFF)
        png = (b"\x89PNG\r\n\x1a\n"
               + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
               + chunk(b"IDAT", zlib.compress(raw, 6))
               + chunk(b"IEND", b""))
        open(path, "wb").write(png)
    img = bpy.data.images.load(path, check_existing=False)
    img.colorspace_settings.name = 'Non-Color'
    return img


def make_cloud(name, loc, scale, dens, emit, warm, cool, img):
    bpy.ops.mesh.primitive_cube_add(size=2, location=loc)
    ob = bpy.context.object
    ob.name = name
    ob.scale = scale

    m = bpy.data.materials.new(name + "Mat")
    m.use_nodes = True
    t = m.node_tree
    t.nodes.clear()
    o = nn(t, "ShaderNodeOutputMaterial", (1200, 0))
    tc = nn(t, "ShaderNodeTexCoord", (-1400, 0))
    spo = nn(t, "ShaderNodeSeparateXYZ", (-1200, 0))
    t.links.new(tc.outputs["Object"], spo.inputs["Vector"])

    # object x,z -> UV
    cxy = nn(t, "ShaderNodeCombineXYZ", (-1000, 0))
    t.links.new(spo.outputs["X"], cxy.inputs["X"])
    t.links.new(spo.outputs["Z"], cxy.inputs["Y"])
    mp = nn(t, "ShaderNodeMapping", (-820, 0))
    mp.inputs["Scale"].default_value = (0.5, 0.5, 1.0)
    mp.inputs["Location"].default_value = (0.5, 0.5, 0.0)
    t.links.new(cxy.outputs["Vector"], mp.inputs["Vector"])

    tex = nn(t, "ShaderNodeTexImage", (-620, 0), image=img,
             interpolation='Cubic', extension='CLIP')
    t.links.new(mp.outputs["Vector"], tex.inputs["Vector"])
    sc = nn(t, "ShaderNodeSeparateColor", (-380, 0))
    t.links.new(tex.outputs["Color"], sc.inputs["Color"])

    # taper at the front/back walls of the box so the curtain has soft edges
    ya = nn(t, "ShaderNodeMath", (-1200, -320), operation='ABSOLUTE')
    t.links.new(spo.outputs["Y"], ya.inputs[0])
    yf = nn(t, "ShaderNodeMapRange", (-1020, -320))
    yf.inputs["From Min"].default_value = 0.20
    yf.inputs["From Max"].default_value = 0.99
    yf.inputs["To Min"].default_value = 1.0
    yf.inputs["To Max"].default_value = 0.0
    t.links.new(ya.outputs["Value"], yf.inputs["Value"])

    def mul(x, y, loc, v=None):
        n = nn(t, "ShaderNodeMath", loc, operation='MULTIPLY')
        t.links.new(x, n.inputs[0])
        if v is None:
            t.links.new(y, n.inputs[1])
        else:
            n.inputs[1].default_value = v
        return n.outputs["Value"]

    dn = mul(sc.outputs["Red"], yf.outputs["Result"], (-180, 120))
    dn = mul(dn, None, (0, 120), v=dens)
    en = mul(sc.outputs["Green"], yf.outputs["Result"], (-180, -140))
    en = mul(en, None, (0, -140), v=emit)

    # warm underside, cooler above
    zc = nn(t, "ShaderNodeMapRange", (-180, -380))
    zc.inputs["From Min"].default_value = 0.46      # warm at the lit top,
    zc.inputs["From Max"].default_value = -0.42     # cool in the shadowed base
    t.links.new(spo.outputs["Z"], zc.inputs["Value"])
    ec = nn(t, "ShaderNodeMixRGB", (20, -380))
    ec.inputs["Color1"].default_value = (*warm, 1)
    ec.inputs["Color2"].default_value = (*cool, 1)
    t.links.new(zc.outputs["Result"], ec.inputs["Fac"])

    pv = nn(t, "ShaderNodeVolumePrincipled", (500, 0))
    pv.inputs["Color"].default_value = (0.08, 0.09, 0.12, 1)
    pv.inputs["Anisotropy"].default_value = 0.3
    t.links.new(dn, pv.inputs["Density"])
    t.links.new(ec.outputs["Color"], pv.inputs["Emission Color"])
    t.links.new(en, pv.inputs["Emission Strength"])
    t.links.new(pv.outputs["Volume"], o.inputs["Volume"])
    ob.data.materials.append(m)
    return ob


# near band: crosses in front of the cone at mid-slope and hides its base
cloud_a = make_cloud("CloudBand", (0.6, -6.5, 2.28), (6.5, 2.6, 0.95),
                     dens=0.30, emit=0.30, warm=COL_CLOUD_W, cool=COL_CLOUD_C,
                     img=bake_map(5, "cloudmap_a"))
# far band: mostly hidden behind the cone, only its wings show - depth cue
cloud_b = make_cloud("CloudFar", (1.0, 3.0, 2.48), (8.0, 2.2, 0.95),
                     dens=0.14, emit=0.105,
                     warm=s2l((150, 104, 86)), cool=s2l((34, 38, 50)),
                     img=bake_map(11, "cloudmap_b"))

# ----------------------------------------------------------------------------
# SKY LAYER (rendered separately, never baked into the mountain pass)
# ----------------------------------------------------------------------------
bpy.ops.mesh.primitive_plane_add(size=2, location=(CAM_X, 260, CAM_Z),
                                 rotation=(math.pi / 2, 0, 0))
sky = bpy.context.object
sky.name = "SkyPlane"
sky.scale = (70, 36, 1)

sm = bpy.data.materials.new("SkyMat")
sm.use_nodes = True
st = sm.node_tree
st.nodes.clear()
sout = nn(st, "ShaderNodeOutputMaterial", (900, 0))
stc = nn(st, "ShaderNodeTexCoord", (-1200, 0))
ssep = nn(st, "ShaderNodeSeparateXYZ", (-1000, 0))
st.links.new(stc.outputs["Object"], ssep.inputs["Vector"])

vg = nn(st, "ShaderNodeMapRange", (-800, 120))       # visible band is +-0.35
vg.inputs["From Min"].default_value = -0.36
vg.inputs["From Max"].default_value = 0.36
st.links.new(ssep.outputs["Y"], vg.inputs["Value"])
vr = nn(st, "ShaderNodeValToRGB", (-600, 120))
vr.color_ramp.interpolation = 'B_SPLINE'
ve = vr.color_ramp.elements
ve[0].position = 0.00; ve[0].color = (*s2l((10, 10, 13)), 1)  # dark foreground
ve[1].position = 1.00; ve[1].color = (*s2l((11, 13, 21)), 1)  # cool blue, high
for _p, _c in ((0.26, (13, 13, 15)), (0.45, (48, 34, 25)),
               (0.58, (27, 28, 36)), (0.78, (17, 19, 27))):
    _e = vr.color_ramp.elements.new(_p); _e.color = (*s2l(_c), 1)
st.links.new(vg.outputs["Result"], vr.inputs["Fac"])

gx = nn(st, "ShaderNodeMapRange", (-800, -200), clamp=True)
gx.inputs["From Min"].default_value = -0.40
gx.inputs["From Max"].default_value = 0.10
gx.inputs["To Min"].default_value = 1.0
gx.inputs["To Max"].default_value = 0.0
st.links.new(ssep.outputs["X"], gx.inputs["Value"])
gy = nn(st, "ShaderNodeMapRange", (-800, -380), clamp=True)
gy.inputs["From Min"].default_value = -0.14
gy.inputs["From Max"].default_value = 0.16
gy.inputs["To Min"].default_value = 1.0
gy.inputs["To Max"].default_value = 0.0
st.links.new(ssep.outputs["Y"], gy.inputs["Value"])
gm = nn(st, "ShaderNodeMath", (-600, -300), operation='MULTIPLY')
st.links.new(gx.outputs["Result"], gm.inputs[0])
st.links.new(gy.outputs["Result"], gm.inputs[1])
gp = nn(st, "ShaderNodeMath", (-440, -300), operation='POWER')
gp.inputs[1].default_value = 1.7
st.links.new(gm.outputs["Value"], gp.inputs[0])
gc = nn(st, "ShaderNodeMixRGB", (-260, -200), blend_type='MULTIPLY')
gc.inputs["Fac"].default_value = 1.0
gc.inputs["Color1"].default_value = (*s2l((58, 36, 20)), 1)
st.links.new(gp.outputs["Value"], gc.inputs["Color2"])

sadd = nn(st, "ShaderNodeMixRGB", (0, 0), blend_type='ADD')
sadd.inputs["Fac"].default_value = 1.0
st.links.new(vr.outputs["Color"], sadd.inputs["Color1"])
st.links.new(gc.outputs["Color"], sadd.inputs["Color2"])
sem = nn(st, "ShaderNodeEmission", (400, 0))
st.links.new(sadd.outputs["Color"], sem.inputs["Color"])
st.links.new(sem.outputs[0], sout.inputs["Surface"])
sky.data.materials.append(sm)

# ----------------------------------------------------------------------------
# CAMERA
# ----------------------------------------------------------------------------
cd = bpy.data.cameras.new("Cam")
cd.lens = LENS
cd.sensor_width = 36
cd.clip_start = 1.0
cd.clip_end = 900
camo = bpy.data.objects.new("Cam", cd)
camo.location = (CAM_X, -CAM_D, CAM_Z)
camo.rotation_euler = (math.pi / 2, 0, 0)
bpy.context.collection.objects.link(camo)
scene.camera = camo

# ----------------------------------------------------------------------------
# COMPOSITOR: a breath of bloom on the cloud band
# (5.1: no scene.node_tree, no Composite node - group output only)
# ----------------------------------------------------------------------------
ng = bpy.data.node_groups.new("Comp", "CompositorNodeTree")
ng.interface.new_socket("Image", in_out='OUTPUT', socket_type='NodeSocketColor')
rl = ng.nodes.new("CompositorNodeRLayers"); rl.location = (-400, 0)
gl = ng.nodes.new("CompositorNodeGlare"); gl.location = (0, 0)
gl.inputs['Type'].default_value = 'Bloom'
gl.inputs['Threshold'].default_value = 0.070
gl.inputs['Size'].default_value = 5.0
gl.inputs['Strength'].default_value = 0.11
go = ng.nodes.new("NodeGroupOutput"); go.location = (400, 0)
ng.links.new(rl.outputs['Image'], gl.inputs['Image'])
ng.links.new(gl.outputs['Image'], go.inputs[0])
scene.compositing_node_group = ng
scene.render.use_compositing = 'noglare' not in OPTS

# ----------------------------------------------------------------------------
# RENDER
# ----------------------------------------------------------------------------
tag = "final" if MODE == "final" else "prev"
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(D, "fuji.blend"))

sky.hide_render = True
if 'cloudsonly' in OPTS:
    mtn.hide_render = True
if 'mtnonly' in OPTS:
    cloud_a.hide_render = cloud_b.hide_render = True
scene.render.filepath = os.path.join(D, "fuji_%s.png" % tag)
bpy.ops.render.render(write_still=True)

sky.hide_render = False
mtn.hide_render = True
cloud_a.hide_render = True
cloud_b.hide_render = True
scene.render.filepath = os.path.join(D, "fuji_sky_%s.png" % tag)
bpy.ops.render.render(write_still=True)
print("DONE", tag)
