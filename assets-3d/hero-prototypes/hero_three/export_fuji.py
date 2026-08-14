"""Mount Fuji: a 432,000-triangle displaced heightfield -> something shippable.

Two reductions, in this order:
  1. Delete every face whose normal points away from the render camera. The
     blend renders this material with backface culling ON, so those faces were
     never visible; this is lossless and roughly halves the mesh before the
     lossy step gets to spend its budget.
  2. Collapse-decimate to the requested triangle budget.

The shading is already baked into two vertex-colour layers by the original
build script and both are carried through:
     BODY  rgb = body colour, a = haze/alpha ramp that dissolves the skirt
     MASK  r = warm rim mask, g = snow, b = cool counter-rim mask
The rim terms are per-pixel and view-dependent, so they are reproduced in the
browser shader rather than baked -- which means the rim actually moves when the
camera moves.

Run: Blender --background fuji.blend --python export_fuji.py -- out.glb [tris]
"""
import bpy, sys, os, math, bmesh
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else "/tmp/fuji.glb"
TARGET = int(argv[1]) if len(argv) > 1 else 14000

D, C = bpy.data, bpy.context
CAM = Vector((1.255, -48.0, 2.224))


def deselect():
    for o in D.objects:
        o.select_set(False)
    C.view_layer.objects.active = None


keep = D.objects.get("Fuji")
for ob in list(D.objects):
    if ob is not keep:
        D.objects.remove(ob, do_unlink=True)

me = keep.data
print("start verts=%d faces=%d  colattrs=%s" % (
    len(me.vertices), len(me.polygons), [c.name for c in me.color_attributes]))

# ------------------------------------------------- 1. drop the invisible half
bm = bmesh.new()
bm.from_mesh(me)
bm.faces.ensure_lookup_table()
# A DIRECTIONAL test, not a per-face one. The hero camera sits at a different
# relative position from the render camera, so culling by the exact per-face
# view vector removes flank triangles that the hero view can still see (it
# left a hard straight cut across the right flank). Keeping the whole -Y
# hemisphere plus a 0.12 margin costs a few thousand triangles and no longer
# depends on where the camera ends up.
doomed = [f for f in bm.faces if f.normal.y > 0.12]
print("culling %d of %d faces (back side)" % (len(doomed), len(bm.faces)))
bmesh.ops.delete(bm, geom=doomed, context='FACES')
bm.to_mesh(me)
bm.free()
me.update()

deselect()
keep.select_set(True)
C.view_layer.objects.active = keep
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.delete_loose()
bpy.ops.object.mode_set(mode='OBJECT')
print("after cull verts=%d faces=%d" % (len(me.vertices), len(me.polygons)))

# --------------------------------------------------------- 2. collapse to budget
me.calc_loop_triangles()
tris = len(me.loop_triangles)
ratio = min(1.0, TARGET / float(tris))
dec = keep.modifiers.new("dec", 'DECIMATE')
dec.decimate_type = 'COLLAPSE'
dec.ratio = ratio
bpy.ops.object.modifier_apply(modifier=dec.name)
me = keep.data
me.calc_loop_triangles()
print("decimate ratio=%.4f  tris %d -> %d" % (ratio, tris, len(me.loop_triangles)))
print("colattrs after decimate:", [(c.name, c.domain, c.data_type) for c in me.color_attributes])

for p in me.polygons:
    p.use_smooth = True

# --------------------------------------------- 3. renormalise BODY.rgb
# The body colour is a near-black linear ramp (0.003 .. 0.02). Quantised to
# 8 bits straight it would survive as about five distinct levels and the cone
# would band. Scale it to fill 0..1 here and divide it back out in the shader:
# the same bits then buy ~50x the precision where the picture actually lives.
body = me.color_attributes["BODY"]
n = len(body.data)
buf = np.empty(n * 4, dtype=np.float32)
body.data.foreach_get("color", buf)
buf = buf.reshape(-1, 4)
BODY_SCALE = float(buf[:, :3].max())
buf[:, :3] /= BODY_SCALE
body.data.foreach_set("color", buf.ravel())
print("BODY_SCALE %.6f" % BODY_SCALE)

bb = [keep.matrix_world @ Vector(c) for c in keep.bound_box]
print("BBOX min=(%.2f %.2f %.2f) max=(%.2f %.2f %.2f)" % (
    min(v.x for v in bb), min(v.y for v in bb), min(v.z for v in bb),
    max(v.x for v in bb), max(v.y for v in bb), max(v.z for v in bb)))

me.materials.clear()
me.materials.append(D.materials.new("fuji"))

deselect()
keep.select_set(True)
C.view_layer.objects.active = keep
bpy.ops.export_scene.gltf(
    filepath=OUT, export_format='GLB', use_selection=True, export_yup=True,
    export_materials='EXPORT', export_image_format='NONE',
    export_normals=False, export_tangents=False,
    export_all_vertex_colors=True, export_attributes=False,
    export_cameras=False, export_lights=False, export_animations=False,
    export_skins=False, export_morph=False, export_extras=False,
    export_draco_mesh_compression_enable=True,
    export_draco_mesh_compression_level=10,
    export_draco_position_quantization=14,
    export_draco_normal_quantization=9,
    export_draco_color_quantization=10,
)
print("WROTE", OUT, os.path.getsize(OUT))
