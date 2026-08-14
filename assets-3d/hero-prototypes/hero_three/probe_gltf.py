import bpy
op = bpy.ops.export_scene.gltf
rna = op.get_rna_type()
names = sorted(p.identifier for p in rna.properties if p.identifier != 'rna_type')
print("NPROPS", len(names))
want = ['draco','export_format','materials','image','texture','jpeg','webp','yup','apply','compress','quantiz','use_selection','use_visible','colors','attributes','normals','tangents','extras','cameras','lights','skins','morph','animation','optimize']
for n in names:
    if any(w in n.lower() for w in want):
        p = rna.properties[n]
        d = getattr(p, 'default', None)
        en = ''
        if p.type == 'ENUM':
            en = ' items=' + ','.join(i.identifier for i in p.enum_items)
        print("  %-42s type=%-8s default=%s%s" % (n, p.type, d, en))
