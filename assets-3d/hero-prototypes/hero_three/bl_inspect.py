import bpy, sys, os

print("=== BLENDER", bpy.app.version_string)
print("=== FILE", bpy.data.filepath)

tris_total = 0
for ob in bpy.data.objects:
    line = "OBJ %-28s type=%-10s" % (ob.name[:28], ob.type)
    if ob.type == 'MESH':
        me = ob.data
        me.calc_loop_triangles()
        nt = len(me.loop_triangles)
        tris_total += nt
        mods = ",".join(m.type for m in ob.modifiers)
        mats = ",".join((s.material.name if s.material else "None") for s in ob.material_slots)
        line += " verts=%-7d tris=%-7d mods=[%s] mats=[%s] hide_render=%s" % (
            len(me.vertices), nt, mods, mats, ob.hide_render)
    print(line)
    print("     loc=%s rot=%s scale=%s" % (tuple(round(v,3) for v in ob.location),
          tuple(round(v,3) for v in ob.rotation_euler), tuple(round(v,3) for v in ob.scale)))

print("=== TOTAL TRIS (pre-modifier):", tris_total)

print("=== MATERIALS")
for m in bpy.data.materials:
    print(" MAT", m.name, "blend=", getattr(m, 'surface_render_method', '?'),
          "backface_culling=", getattr(m, 'use_backface_culling', '?'))
    if m.use_nodes:
        for n in m.node_tree.nodes:
            if n.type == 'TEX_IMAGE':
                img = n.image
                print("    TEX", n.name, "->", img.name if img else None,
                      (img.size[0], img.size[1]) if img else None,
                      "file=", (img.filepath if img else None),
                      "packed=", bool(img.packed_file) if img else None)
            elif n.type == 'BSDF_PRINCIPLED':
                try:
                    print("    PRINCIPLED base=", tuple(round(v,3) for v in n.inputs['Base Color'].default_value),
                          "rough=", round(n.inputs['Roughness'].default_value,3),
                          "alpha_linked=", n.inputs['Alpha'].is_linked)
                except Exception as e:
                    print("    PRINCIPLED (read err)", e)
            elif n.type in ('EMISSION',):
                print("    EMISSION", tuple(round(v,3) for v in n.inputs[0].default_value), n.inputs[1].default_value)

print("=== IMAGES")
for img in bpy.data.images:
    print(" IMG", img.name, img.size[0], img.size[1], "packed=", bool(img.packed_file), "path=", img.filepath)

print("=== SCENES/COLLECTIONS")
for sc in bpy.data.scenes:
    print(" SCENE", sc.name, "engine=", sc.render.engine, "res=", sc.render.resolution_x, sc.render.resolution_y)
for c in bpy.data.collections:
    print(" COLL", c.name, "objs=", len(c.objects))

print("=== CAMERAS/LIGHTS")
for ob in bpy.data.objects:
    if ob.type == 'CAMERA':
        print(" CAM", ob.name, "lens=", ob.data.lens, "loc=", tuple(round(v,3) for v in ob.location),
              "rot=", tuple(round(v,3) for v in ob.rotation_euler), "type=", ob.data.type,
              "sensor=", ob.data.sensor_width, "shiftx=", ob.data.shift_x, "shifty=", ob.data.shift_y)
    if ob.type == 'LIGHT':
        print(" LIGHT", ob.name, ob.data.type, "energy=", ob.data.energy, "color=", tuple(round(v,3) for v in ob.data.color),
              "loc=", tuple(round(v,3) for v in ob.location), "rot=", tuple(round(v,3) for v in ob.rotation_euler))
