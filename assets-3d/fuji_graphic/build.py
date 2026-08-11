"""
Mount Fuji - TREATMENT B : GRAPHIC / UKIYO-E
Background layer for a website hero (2:1), transparent PNG + optional sky layer.

Run:
  /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
      --python build.py -- <outdir> <res_x> <res_y> <samples> <tag>

Design notes
------------
* Everything is Emission + view_transform 'Standard', so every hex below lands in the
  PNG exactly as authored. No lights, no compositor.
* All shading is *stepped* with CONSTANT colour ramps -> flat woodblock bands.
* Shading term is azimuthal (cos of the angle around the cone axis), not a surface
  normal dot product: on a shallow cone the normal-based terminator collapses, while
  the azimuthal one gives a clean coherent "shadow wing" that reads as a deliberate
  graphic choice.
* Clouds are flat lozenges (pointed lens shapes) with their own 4-step ramp.
"""

import bpy, bmesh, math, sys, os
from math import sin, cos, pi, exp

# ----------------------------------------------------------------------------- args
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = argv[0] if len(argv) > 0 else '/tmp'
RX = int(argv[1]) if len(argv) > 1 else 1200
RY = int(argv[2]) if len(argv) > 2 else 600
SAMPLES = int(argv[3]) if len(argv) > 3 else 128
TAG = argv[4] if len(argv) > 4 else 'preview'

# ----------------------------------------------------------------------------- colour
def s2l(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

def H(hexstr, a=1.0):
    """hex sRGB -> linear RGBA tuple"""
    hexstr = hexstr.lstrip('#')
    r, g, b = (int(hexstr[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    return (s2l(r), s2l(g), s2l(b), a)

# ============================================================== ART DIRECTION =======
# frame: ortho, x in [-10,10], z in [-5,5]
SUMMIT_X = -3.20
SUMMIT_Z = 2.90
MH = 6.10          # height summit -> nominal base plane
# Silhouette is defined by the flank ANGLE, integrated into a radius. A power-law
# radius makes a spire; a slope that eases from steep at the summit to shallow at the
# base is what actually gives Fuji its concave flare.
S_TOP = 33.5       # degrees from horizontal, just under the summit
S_BOT = 8.5        # degrees at the nominal base plane
S_EXP = 1.22       # how fast the slope eases off
SUN_AZ = 2.95      # radians; sun low, behind-left

U_SNOW = 0.745     # snow line, normalised height (1 = summit)

# --- rock ladder, sunlit face (dusty rose-brown, not orange: the momiji owns orange)
ROCK_LIT = [
    (0.00, '#0f0e13'), (0.13, '#131017'), (0.26, '#17121a'), (0.39, '#1d161c'),
    (0.505, '#3a2a27'), (0.62, '#48332b'), (0.72, '#50392d'), (0.86, '#573e2f'),
]
# --- rock ladder, shadow face
ROCK_SHD = [
    (0.00, '#0d0e14'), (0.13, '#101118'), (0.26, '#12141c'), (0.39, '#171a23'),
    (0.505, '#202634'), (0.62, '#282d3c'), (0.72, '#2e3343'), (0.86, '#35394b'),
]
# --- snow ladder, sunlit face
SNOW_LIT = [
    (0.00, '#60564e'), (0.70, '#665b52'), (0.80, '#726459'), (0.88, '#7f7062'),
    (0.95, '#8a7867'),
]
# --- snow ladder, shadow face
SNOW_SHD = [
    (0.00, '#34363f'), (0.70, '#393b45'), (0.80, '#40414e'), (0.88, '#474857'),
    (0.95, '#4e4e60'),
]
# --- stepped light: (position on (d+1)/2, mix factor shadow->lit)
LIGHT_STEPS = [(0.00, 0.00), (0.44, 0.42), (0.60, 0.72), (0.72, 1.00)]

RIM_COLOR = '#a3652f'      # warm accent along the sunward silhouette
RIM_ANG = 0.20             # angular half width of the rim band

# --- alpha ladder: the base dissolves in discrete steps (screen-print fog)
ALPHA_STEPS = [(0.00, 0.00), (0.225, 0.16), (0.265, 0.44), (0.310, 0.74), (0.377, 1.00)]

# --- cloud ramps: (local z, hex).  local z of a lozenge runs -0.45 .. 1.00
# Most of the band is cool and dark. Only a few shapes catch the light, and only two
# small ones carry the ember accent - that is what keeps it from reading as sausages.
CLOUD_ROWS = {
    'cool':   [(-1.0, '#1a1823'), (0.22, '#23202b')],
    'cool2':  [(-1.0, '#1e1b26'), (0.22, '#2a2533')],
    'cool3':  [(-1.0, '#221f2a'), (0.22, '#322b3a')],
    'warm':   [(-1.0, '#2e2429'), (0.22, '#513830')],
    'warm2':  [(-1.0, '#372a2c'), (0.22, '#6f4632')],
    'accent': [(-1.0, '#513528'), (0.22, '#9c5630')],
    'haze':   [(-1.0, '#0e0e13'), (0.22, '#111017')],
    'wisp':   [(-1.0, '#121118'), (0.22, '#17161e')],
}

#            x       z     len    ht   row
CLOUDS = [
    # --- left group: the lit billows. Ragged top edge, warm tones riding highest.
    ( -9.8,  0.04,  6.8,  0.32, 'cool3'),
    ( -7.6, -0.04,  6.0,  0.30, 'warm'),
    ( -8.6,  0.14,  3.2,  0.26, 'warm2'),
    ( -6.9,  0.12,  1.8,  0.16, 'accent'),
    (-12.4, -0.18,  4.4,  0.24, 'cool2'),
    ( -9.4, -0.36,  7.4,  0.20, 'cool'),
    ( -5.4, -0.20,  3.6,  0.20, 'cool2'),
    # --- gap ---
    # --- middle group, crossing the summit axis
    ( -2.4, -0.04,  5.4,  0.28, 'cool3'),
    ( -3.6, -0.20,  3.2,  0.22, 'cool2'),
    ( -1.6,  0.04,  2.4,  0.16, 'warm2'),
    ( -2.0, -0.42,  6.0,  0.20, 'cool'),
    (  0.8, -0.18,  2.8,  0.16, 'cool'),
    # --- gap ---
    # --- right group: long, low, quiet. The momiji lives here.
    (  4.4, -0.10,  5.6,  0.22, 'cool2'),
    (  3.4, -0.38,  6.4,  0.17, 'cool'),
    (  8.6, -0.20,  5.0,  0.18, 'cool2'),
    (  7.2, -0.44,  6.0,  0.15, 'cool'),
    ( 10.6, -0.06,  3.0,  0.15, 'cool3'),
    # --- far shelf, almost black
    ( -3.0, -1.75, 17.0,  0.22, 'haze'),
    (  6.0, -1.60, 11.0,  0.18, 'haze'),
    # --- three thin bars in the sky, barely there
    ( -9.4,  2.18,  7.0, 0.070, 'wisp'),
    ( -7.4,  1.66,  4.6, 0.055, 'wisp'),
    (  6.8,  1.02,  7.0, 0.065, 'wisp'),
]

# --- sky: banded bokashi. Warm glow sits at the horizon, everything else falls to
# the site background so type stays readable on top.
SKY_STEPS = [
    (0.000, '#0c0c0d'), (0.230, '#0e0d10'), (0.300, '#131015'), (0.355, '#1b141a'),
    (0.405, '#24181b'), (0.455, '#2a1c18'), (0.505, '#22181b'), (0.560, '#191521'),
    (0.625, '#131223'), (0.700, '#101021'), (0.790, '#0e0e1a'), (0.880, '#0c0c11'),
]

# ============================================================== helpers =============
def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)

def link(nt, a, b):
    nt.links.new(a, b)

def setin(nt, socket, v):
    if hasattr(v, 'is_output'):
        link(nt, v, socket)
    else:
        socket.default_value = v

def mth(nt, op, a, b=None, c=None, clamp=False):
    n = nt.nodes.new('ShaderNodeMath')
    n.operation = op
    n.use_clamp = clamp
    setin(nt, n.inputs[0], a)
    if b is not None:
        setin(nt, n.inputs[1], b)
    if c is not None:
        setin(nt, n.inputs[2], c)
    return n.outputs[0]

def ramp(nt, fac, stops, constant=True):
    n = nt.nodes.new('ShaderNodeValToRGB')
    n.color_ramp.interpolation = 'CONSTANT' if constant else 'LINEAR'
    els = n.color_ramp.elements
    while len(els) > 1:
        els.remove(els[-1])
    els[0].position = 0.0
    for i, (p, col) in enumerate(stops):
        e = els[0] if i == 0 else els.new(max(0.0, min(1.0, p)))
        e.position = max(0.0, min(1.0, p))
        e.color = H(col) if isinstance(col, str) else col
    setin(nt, n.inputs['Fac'], fac)
    return n.outputs['Color']

def vramp(nt, fac, stops):
    """CONSTANT ramp returning a float (value stored in the red channel)"""
    n = nt.nodes.new('ShaderNodeValToRGB')
    n.color_ramp.interpolation = 'CONSTANT'
    els = n.color_ramp.elements
    while len(els) > 1:
        els.remove(els[-1])
    for i, (p, v) in enumerate(stops):
        e = els[0] if i == 0 else els.new(max(0.0, min(1.0, p)))
        e.position = max(0.0, min(1.0, p))
        e.color = (v, v, v, 1.0)
    setin(nt, n.inputs['Fac'], fac)
    sep = nt.nodes.new('ShaderNodeSeparateColor')
    link(nt, n.outputs['Color'], sep.inputs['Color'])
    return sep.outputs['Red']

def mix(nt, fac, a, b):
    n = nt.nodes.new('ShaderNodeMixRGB')
    setin(nt, n.inputs['Fac'], fac)
    setin(nt, n.inputs['Color1'], a)
    setin(nt, n.inputs['Color2'], b)
    return n.outputs['Color']

def finish(nt, color, alpha):
    """emission + stepped alpha -> output"""
    em = nt.nodes.new('ShaderNodeEmission')
    setin(nt, em.inputs['Color'], color)
    em.inputs['Strength'].default_value = 1.0
    tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    ms = nt.nodes.new('ShaderNodeMixShader')
    setin(nt, ms.inputs[0], alpha)
    link(nt, tr.outputs[0], ms.inputs[1])
    link(nt, em.outputs[0], ms.inputs[2])
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    link(nt, ms.outputs[0], out.inputs['Surface'])

def newmat(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.node_tree.nodes.clear()
    try:
        m.surface_render_method = 'DITHERED'
    except Exception:
        pass
    return m

# ============================================================== mountain ============
def _radius_table(h_max, n=4000):
    """r(h) from the flank angle, integrated. h = depth below the summit."""
    hs = [h_max * i / n for i in range(n + 1)]
    rs = [0.0]
    for i in range(1, n + 1):
        def cot(h):
            f = max(0.0, 1.0 - h / MH) ** S_EXP
            s = math.radians(S_BOT + (S_TOP - S_BOT) * f)
            return 1.0 / math.tan(s)
        dh = hs[i] - hs[i - 1]
        rs.append(rs[-1] + 0.5 * (cot(hs[i - 1]) + cot(hs[i])) * dh)
    return hs, rs

def radius_at(h, tab):
    hs, rs = tab
    if h <= 0:
        return 0.0
    if h >= hs[-1]:
        return rs[-1] + (h - hs[-1]) / math.tan(math.radians(S_BOT))
    k = h / hs[-1] * (len(hs) - 1)
    i = int(k)
    f = k - i
    return rs[i] * (1 - f) + rs[min(i + 1, len(rs) - 1)] * f

def mountain_mesh():
    h_top, h_bot = 0.20, 9.2
    nr, ns = 190, 512
    tab = _radius_table(h_bot + 0.5)
    verts, faces = [], []
    for i in range(nr):
        t = i / (nr - 1)
        h = h_top + (h_bot - h_top) * (t ** 1.75)
        for j in range(ns):
            th = 2 * pi * j / ns
            notch = (0.055 * sin(th + 0.6) + 0.026 * sin(3 * th + 2.1)) * exp(-h / 0.9)
            hh = max(0.02, h + notch)
            r = radius_at(hh, tab) * (1.0 + 0.028 * cos(th - 0.5) + 0.012 * cos(2 * th + 1.0))
            verts.append((r * cos(th), r * sin(th), MH - hh))
    for i in range(nr - 1):
        for j in range(ns):
            j2 = (j + 1) % ns
            faces.append((i * ns + j, i * ns + j2, (i + 1) * ns + j2, (i + 1) * ns + j))
    verts.append((0.0, 0.0, MH - h_top * 1.35))
    ci = len(verts) - 1
    for j in range(ns):
        faces.append((ci, (j + 1) % ns, j))

    me = bpy.data.meshes.new('fuji')
    me.from_pydata(verts, [], faces)
    me.update()
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new('Fuji', me)
    bpy.context.collection.objects.link(ob)
    ob.location = (SUMMIT_X, 0.0, SUMMIT_Z - MH)
    return ob

def mountain_mat():
    m = newmat('M_fuji')
    nt = m.node_tree
    tc = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    link(nt, tc.outputs['Object'], sep.inputs['Vector'])
    x, y, z = sep.outputs['X'], sep.outputs['Y'], sep.outputs['Z']

    u = mth(nt, 'DIVIDE', z, MH)                       # 0 at base plane, 1 at summit
    a = mth(nt, 'ARCTAN2', y, x)                       # -pi .. pi

    # --- irregular radial ribbing used both for the snow line and for the gullies
    am = mth(nt, 'ADD', a, mth(nt, 'MULTIPLY', mth(nt, 'SINE', mth(nt, 'MULTIPLY', a, 3.0)), 0.10))
    am = mth(nt, 'ADD', am, mth(nt, 'MULTIPLY',
             mth(nt, 'SINE', mth(nt, 'ADD', mth(nt, 'MULTIPLY', a, 7.0), 1.1)), 0.055))
    t = mth(nt, 'MULTIPLY', am, 21.0 / (2 * pi))
    tri = mth(nt, 'MULTIPLY', mth(nt, 'ABSOLUTE',
              mth(nt, 'SUBTRACT', mth(nt, 'FRACT', t), 0.5)), 2.0)   # 0 at gully axis

    # organic break-up
    nz = nt.nodes.new('ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = 5.0
    nz.inputs['Detail'].default_value = 3.0
    link(nt, tc.outputs['Object'], nz.inputs['Vector'])
    nzf = mth(nt, 'MULTIPLY', mth(nt, 'SUBTRACT', nz.outputs['Fac'], 0.5), 0.055)

    # snow boundary. Three scales at once, all periodic in the angle so nothing seams
    # on the silhouette: two big lobes, the fine scallop from the ribbing, then noise.
    lobe = mth(nt, 'MULTIPLY', mth(nt, 'SINE', mth(nt, 'ADD',
               mth(nt, 'MULTIPLY', a, 2.0), 0.9)), 0.038)
    lobe = mth(nt, 'ADD', lobe, mth(nt, 'MULTIPLY', mth(nt, 'SINE', mth(nt, 'ADD',
               mth(nt, 'MULTIPLY', a, 3.0), -2.0)), 0.024))
    bnd = mth(nt, 'ADD', U_SNOW, lobe)
    bnd = mth(nt, 'ADD', bnd, mth(nt, 'MULTIPLY', mth(nt, 'SUBTRACT', 0.5, tri), 0.052))
    bnd = mth(nt, 'ADD', bnd, nzf)
    snow = mth(nt, 'GREATER_THAN', u, bnd)

    # gullies: thin dark tongues of rock reaching UP out of the snow line, each with
    # its own reach. They must not become spokes running to the summit.
    rv = mth(nt, 'ADD', mth(nt, 'MULTIPLY', mth(nt, 'SINE', mth(nt, 'ADD',
             mth(nt, 'MULTIPLY', a, 5.0), 1.7)), 0.6),
             mth(nt, 'MULTIPLY', mth(nt, 'SINE', mth(nt, 'ADD',
             mth(nt, 'MULTIPLY', a, 8.0), -0.4)), 0.4))
    reach = mth(nt, 'ADD', 0.042, mth(nt, 'MULTIPLY',
                mth(nt, 'ADD', 0.5, mth(nt, 'MULTIPLY', rv, 0.5)), 0.125))
    w = mth(nt, 'MULTIPLY', mth(nt, 'SUBTRACT', mth(nt, 'ADD', bnd, reach), u), 1.1)
    w = mth(nt, 'MINIMUM', mth(nt, 'MAXIMUM', w, 0.0), 0.070)
    gul = mth(nt, 'MULTIPLY', mth(nt, 'LESS_THAN', tri, w),
                            mth(nt, 'LESS_THAN', u, 0.925))

    # --- stepped azimuthal light
    d = mth(nt, 'COSINE', mth(nt, 'SUBTRACT', a, SUN_AZ))
    d01 = mth(nt, 'MULTIPLY', mth(nt, 'ADD', d, 1.0), 0.5)
    f = vramp(nt, d01, LIGHT_STEPS)

    rock = mix(nt, f, ramp(nt, u, ROCK_SHD), ramp(nt, u, ROCK_LIT))
    snowc = mix(nt, f, ramp(nt, u, SNOW_SHD), ramp(nt, u, SNOW_LIT))
    capmask = mth(nt, 'MULTIPLY', snow, mth(nt, 'SUBTRACT', 1.0, gul))
    col = mix(nt, capmask, rock, snowc)

    # --- warm rim on the sunward silhouette, upper slopes only
    rim = mth(nt, 'LESS_THAN', mth(nt, 'ABSOLUTE', mth(nt, 'SUBTRACT',
              mth(nt, 'ABSOLUTE', a), pi)), RIM_ANG)
    rimfade = vramp(nt, u, [(0.0, 0.0), (0.30, 0.35), (0.46, 0.7), (0.62, 1.0)])
    col = mix(nt, mth(nt, 'MULTIPLY', rim, rimfade), col, H(RIM_COLOR)[:3] + (1.0,))

    alpha = vramp(nt, u, ALPHA_STEPS)
    finish(nt, col, alpha)
    return m

# ============================================================== clouds =============
def lozenge_mesh(name, phase, lobes=3):
    """Long flat cloud with a scalloped top and a quiet bottom: the ukiyo-e mist bar."""
    n = 180
    pts = []
    for i in range(n + 1):
        t = i / n
        env = sin(pi * t) ** 0.42                       # fat, flat-topped, pointed ends
        amp = 0.11 + 0.10 * (0.5 + 0.5 * sin(pi * t * 1.7 + phase))
        scal = (1.0 - amp) + amp * 2.0 * abs(sin(pi * (t * lobes + phase * 0.17))) ** 0.7
        pts.append((t - 0.5, env * scal))
    bot = []
    for i in range(n, -1, -1):
        t = i / n
        env = sin(pi * t) ** 0.95
        bot.append((t - 0.5, -0.42 * env * (0.82 + 0.18 * sin(t * 5.0 + phase * 1.7))))
    ring = pts + bot[1:-1]
    verts = [(p[0], 0.0, p[1]) for p in ring]
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], [tuple(range(len(verts)))])
    me.update()
    return me

def cloud_mat(row):
    m = newmat('M_cloud_' + row)
    nt = m.node_tree
    tc = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    link(nt, tc.outputs['Object'], sep.inputs['Vector'])
    z = sep.outputs['Z']
    # local z -0.45..1.0 -> 0..1
    zn = mth(nt, 'DIVIDE', mth(nt, 'ADD', z, 0.45), 1.45)
    stops = [((p + 0.45) / 1.45 if p > -0.9 else 0.0, c) for p, c in CLOUD_ROWS[row]]
    col = ramp(nt, zn, stops)
    # tiny per-object value jitter so the band is not mechanical
    oi = nt.nodes.new('ShaderNodeObjectInfo')
    j = mth(nt, 'ADD', 0.88, mth(nt, 'MULTIPLY', oi.outputs['Random'], 0.22))
    n = nt.nodes.new('ShaderNodeMixRGB')
    n.blend_type = 'MULTIPLY'
    n.inputs['Fac'].default_value = 1.0
    setin(nt, n.inputs['Color1'], col)
    jn = nt.nodes.new('ShaderNodeCombineColor')
    for s in ('Red', 'Green', 'Blue'):
        link(nt, j, jn.inputs[s])
    link(nt, jn.outputs['Color'], n.inputs['Color2'])
    finish(nt, n.outputs['Color'], 1.0)
    return m

# ============================================================== sky ================
def sky():
    me = bpy.data.meshes.new('sky')
    me.from_pydata([(-12, 0, -6.5), (12, 0, -6.5), (12, 0, 6.5), (-12, 0, 6.5)], [], [(0, 1, 2, 3)])
    me.update()
    ob = bpy.data.objects.new('Sky', me)
    bpy.context.collection.objects.link(ob)
    ob.location = (0, 34, 0)
    m = newmat('M_sky')
    nt = m.node_tree
    tc = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    link(nt, tc.outputs['Object'], sep.inputs['Vector'])
    v = mth(nt, 'ADD', mth(nt, 'DIVIDE', mth(nt, 'ADD', sep.outputs['Z'], 5.0), 10.0),
            mth(nt, 'MULTIPLY', sep.outputs['X'], 0.004))
    finish(nt, ramp(nt, v, SKY_STEPS), 1.0)
    ob.data.materials.append(m)
    return ob

# ============================================================== scene ==============
def main():
    clear()
    sc = bpy.context.scene

    fuji = mountain_mesh()
    fuji.data.materials.append(mountain_mat())

    mats = {k: cloud_mat(k) for k in CLOUD_ROWS}
    depth = {'haze': -16.0, 'cool': -18.0, 'cool2': -19.0, 'cool3': -19.5,
             'warm': -20.0, 'warm2': -20.5, 'accent': -21.0, 'wisp': -22.0}
    for i, (cx, cz, lx, lz, row) in enumerate(CLOUDS):
        me = lozenge_mesh('lz%d' % i, phase=(i * 2.39) % 6.28,
                          lobes=max(2, min(4, int(round(lx / 3.2)))))
        ob = bpy.data.objects.new('Cloud%02d' % i, me)
        bpy.context.collection.objects.link(ob)
        ob.location = (cx, depth[row], cz)
        ob.scale = (lx, 1.0, lz)
        ob.data.materials.append(mats[row])

    skyob = sky()

    cam_data = bpy.data.cameras.new('cam')
    cam_data.type = 'ORTHO'
    cam_data.ortho_scale = 20.0
    cam = bpy.data.objects.new('Camera', cam_data)
    bpy.context.collection.objects.link(cam)
    cam.location = (0.0, -60.0, 0.0)
    cam.rotation_euler = (pi / 2, 0.0, 0.0)
    sc.camera = cam

    sc.render.engine = 'BLENDER_EEVEE'
    try:
        sc.eevee.taa_render_samples = SAMPLES
    except Exception:
        pass
    sc.render.film_transparent = True
    sc.render.filter_size = 1.35
    sc.render.resolution_x = RX
    sc.render.resolution_y = RY
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA'
    sc.render.image_settings.color_depth = '8'
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'

    os.makedirs(OUT, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'fuji.blend'))

    # pass 1 : mountain + clouds, transparent
    skyob.hide_render = True
    sc.render.filepath = os.path.join(OUT, 'fuji_%s.png' % TAG)
    bpy.ops.render.render(write_still=True)

    # pass 2 : sky only
    skyob.hide_render = False
    fuji.hide_render = True
    for ob in bpy.data.objects:
        if ob.name.startswith('Cloud'):
            ob.hide_render = True
    sc.render.filepath = os.path.join(OUT, 'sky_%s.png' % TAG)
    bpy.ops.render.render(write_still=True)

main()
