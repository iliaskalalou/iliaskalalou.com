"""Chureito pagoda -> one mesh, one material, vertex-coloured.

The blend carries 9 flat-colour materials and no textures at all, so the whole
building can collapse to a single vertex-coloured draw call. Colours are baked
per material AFTER separating by material, which is what stops a vermilion
timber vertex from bleeding into the cream panel next to it.

Decimation is PLANAR (dissolve limited) first -- this is architecture, most of
those 60k triangles are coplanar tessellation of flat panels -- then collapse
only if a hard budget is given.

Run: Blender --background pagoda.blend --python export_pagoda.py -- out.glb [angle_deg] [collapse]
"""
import bpy, sys, os, math
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else "/tmp/pagoda.glb"
ANGLE = math.radians(float(argv[1])) if len(argv) > 1 else math.radians(2.0)
COLLAPSE = float(argv[2]) if len(argv) > 2 else 1.0

D, C = bpy.data, bpy.context


def deselect():
    for o in D.objects:
        o.select_set(False)
    C.view_layer.objects.active = None


for ob in list(D.objects):
    if ob.type != 'MESH':
        D.objects.remove(ob, do_unlink=True)

src = [o for o in D.objects if o.type == 'MESH'][0]
print("source faces", len(src.data.polygons), "mats", len(src.material_slots))

deselect()
src.select_set(True)
C.view_layer.objects.active = src
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# ------------------------------------------------------- separate by material
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.separate(type='MATERIAL')
bpy.ops.object.mode_set(mode='OBJECT')

pieces = [o for o in D.objects if o.type == 'MESH']
print("pieces", len(pieces))

total_before = total_after = 0
for ob in pieces:
    me = ob.data
    mat = ob.material_slots[0].material if ob.material_slots else None
    col = (0.5, 0.5, 0.5)
    if mat and mat.use_nodes:
        for n in mat.node_tree.nodes:
            if n.type == 'BSDF_PRINCIPLED':
                c = n.inputs['Base Color'].default_value
                col = (c[0], c[1], c[2])
                break

    total_before += len(me.polygons)
    deselect()
    ob.select_set(True)
    C.view_layer.objects.active = ob
    d1 = ob.modifiers.new("planar", 'DECIMATE')
    d1.decimate_type = 'DISSOLVE'
    d1.angle_limit = ANGLE
    bpy.ops.object.modifier_apply(modifier=d1.name)
    if COLLAPSE < 1.0:
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.quads_convert_to_tris()
        bpy.ops.object.mode_set(mode='OBJECT')
        d2 = ob.modifiers.new("col", 'DECIMATE')
        d2.decimate_type = 'COLLAPSE'
        d2.ratio = COLLAPSE
        bpy.ops.object.modifier_apply(modifier=d2.name)
    total_after += len(me.polygons)

    # normals are NOT exported (the browser uses derivative flat shading), so
    # co-located vertices that only differed by normal can now collapse
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=0.0005)
    bpy.ops.object.mode_set(mode='OBJECT')

    ca = me.color_attributes.new("Col", 'FLOAT_COLOR', 'POINT')
    for dpt in ca.data:
        dpt.color = (col[0], col[1], col[2], 1.0)
    me.materials.clear()

print("faces %d -> %d" % (total_before, total_after))

deselect()
for o in pieces:
    o.select_set(True)
C.view_layer.objects.active = pieces[0]
bpy.ops.object.join()
pag = C.view_layer.objects.active
pag.name = "pagoda"
pag.data.name = "pagoda"
m = D.materials.new("pagoda")
pag.data.materials.append(m)

pag.data.calc_loop_triangles()
print("final verts=%d tris=%d" % (len(pag.data.vertices), len(pag.data.loop_triangles)))
bb = [pag.matrix_world @ Vector(c) for c in pag.bound_box]
print("BBOX min=(%.2f %.2f %.2f) max=(%.2f %.2f %.2f)" % (
    min(v.x for v in bb), min(v.y for v in bb), min(v.z for v in bb),
    max(v.x for v in bb), max(v.y for v in bb), max(v.z for v in bb)))

deselect()
pag.select_set(True)
C.view_layer.objects.active = pag
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
    export_draco_color_quantization=8,
)
print("WROTE", OUT, os.path.getsize(OUT))
