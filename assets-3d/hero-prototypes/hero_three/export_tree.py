"""Export the momiji as ONE-draw-call-per-part geometry.

Two output meshes:
  foliage  -- all 120 alpha cards joined into a single mesh. The four cluster
              atlases are packed 2x2 by tools/make_atlases.py, so every card's
              UVs are remapped into its quadrant and the whole canopy becomes a
              single alpha-tested draw call.
  branches -- the bark, decimated.

The per-card look in Blender lives in OBJECT COLOR (ob.color = tint.rgb,
emission strength in .a, up to 3.0). Object colour does not survive glTF, so it
is baked into a COLOR_0 vertex attribute: rgb = tint, a = emission/3.

Run:  Blender --background tree.blend --python export_tree.py -- <out.glb>
"""
import bpy, sys, os, math
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else "/tmp/tree.glb"
BRANCH_RATIO = float(argv[1]) if len(argv) > 1 else 0.34

D = bpy.data
C = bpy.context


def deselect():
    for o in D.objects:
        o.select_set(False)
    C.view_layer.objects.active = None


# purge everything that is not geometry we want
for ob in list(D.objects):
    if ob.type in ('LIGHT', 'CAMERA', 'EMPTY'):
        D.objects.remove(ob, do_unlink=True)

cards = [o for o in D.objects if o.type == 'MESH' and o.name.startswith(('card_', 'litter'))]
branches = [o for o in D.objects if o.type == 'MESH' and o not in cards]
print("cards=%d  other=%d" % (len(cards), len(branches)))

# --------------------------------------------------------------- atlas layout
# tools/make_atlases.py pastes cluster i at PIL cell (col=i%2, row=i//2), row 0
# at the TOP of the image. Blender's v axis runs bottom-up, so cluster i lives
# at u in [col/2, col/2+1/2] and v in [1-(row+1)/2, 1-row/2].
def quad_offset(i):
    col, row = i % 2, i // 2
    return (col * 0.5, 1.0 - (row + 1) * 0.5)


MAT_INDEX = {"leafcard_%d" % i: i for i in range(4)}

# --------------------------------------------------------------------- cards
made = []
for ob in cards:
    slot = ob.material_slots[0] if ob.material_slots else None
    mat = slot.material if slot else None
    ci = MAT_INDEX.get(mat.name if mat else "", 0)
    ou, ov = quad_offset(ci)

    # every card shares one mesh datablock -> give this one its own copy
    me = ob.data.copy()
    ob.data = me

    uv = me.uv_layers[0]
    for lp in uv.data:
        u, v = lp.uv
        lp.uv = (u * 0.5 + ou, v * 0.5 + ov)

    col = ob.color  # (r, g, b, emission 0..3)
    ca = me.color_attributes.new("Col", 'FLOAT_COLOR', 'CORNER')
    r, g, b = min(col[0], 4.0), min(col[1], 4.0), min(col[2], 4.0)
    e = min(col[3], 3.0) / 3.0
    for d in ca.data:
        d.color = (r, g, b, e)

    ob.data.materials.clear()
    made.append(ob)

# the emission strength runs to 3.0 and the tint is a saturated leaf colour;
# both are stored 0..1 and scaled back in the shader (see FOLIAGE_SCALE)
# join
deselect()
for o in made:
    o.select_set(True)
C.view_layer.objects.active = made[0]
bpy.ops.object.join()
foliage = C.view_layer.objects.active
foliage.name = "foliage"
foliage.data.name = "foliage"
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

mat = D.materials.new("foliage")
mat.use_nodes = False
foliage.data.materials.append(mat)
print("foliage verts=%d tris=%d" % (len(foliage.data.vertices),
                                    len(foliage.data.loop_triangles) or
                                    len(foliage.data.polygons) * 2))

# ------------------------------------------------------------------ branches
deselect()
for o in branches:
    o.select_set(True)
C.view_layer.objects.active = branches[0]
if len(branches) > 1:
    bpy.ops.object.join()
bark = C.view_layer.objects.active
bark.name = "branches"
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

before = len(bark.data.polygons)
dec = bark.modifiers.new("dec", 'DECIMATE')
dec.decimate_type = 'COLLAPSE'
dec.ratio = BRANCH_RATIO
bpy.ops.object.modifier_apply(modifier=dec.name)
print("branches faces %d -> %d" % (before, len(bark.data.polygons)))
bark.data.materials.clear()
bmat = D.materials.new("bark")
bmat.use_nodes = False
bark.data.materials.append(bmat)

# ------------------------------------------------------------------- extents
for o in (foliage, bark):
    bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
    lo = Vector((min(v.x for v in bb), min(v.y for v in bb), min(v.z for v in bb)))
    hi = Vector((max(v.x for v in bb), max(v.y for v in bb), max(v.z for v in bb)))
    print("BBOX %-9s min=(%.2f %.2f %.2f) max=(%.2f %.2f %.2f)" %
          (o.name, lo.x, lo.y, lo.z, hi.x, hi.y, hi.z))

# --------------------------------------------------------------------- export
def write(ob, path):
    deselect()
    ob.select_set(True)
    C.view_layer.objects.active = ob
    _export(path)
    print("WROTE", path, os.path.getsize(path))


def _export(OUT):
    bpy.ops.export_scene.gltf(
    filepath=OUT,
    export_format='GLB',
    use_selection=True,
    export_yup=True,
    export_apply=False,
    export_materials='EXPORT',
    export_image_format='NONE',
    export_normals=False,
    export_tangents=False,
    export_all_vertex_colors=True,
    export_attributes=False,
    export_cameras=False,
    export_lights=False,
    export_animations=False,
    export_skins=False,
    export_morph=False,
    export_extras=False,
    export_draco_mesh_compression_enable=True,
    export_draco_mesh_compression_level=10,
    export_draco_position_quantization=13,
    export_draco_normal_quantization=8,
    export_draco_texcoord_quantization=12,
    export_draco_color_quantization=10,
    )


write(foliage, OUT.replace(".glb", "_foliage.glb"))
write(bark, OUT.replace(".glb", "_branches.glb"))
