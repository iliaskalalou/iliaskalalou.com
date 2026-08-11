# 3D source assets

Blender sources for the Japanese hero scene. **Not shipped to the browser** —
these are the masters. The web only ever loads flattened, compressed exports
placed in `public/`.

Everything is scripted and reproducible. Blender is driven headless, no add-on
required:

```bash
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python build.py
```

## momiji/

A stylised *Acer palmatum* built from the owner's own photograph
(`reference/momiji_photo.png`). Branch skeleton is real geometry; the foliage is
120 alpha-mapped cards using the four leaf-cluster atlases in `atlas/`, each
baked from ~150 individually generated palmate leaves. Colour runs crimson at
the base to amber at the crown, driven by height and distance from the trunk.

~18k faces. Renders transparent, straight alpha.

```bash
Blender --background --factory-startup --python build.py -- final
```

## leaves/

One momiji leaf rendered at 16 orientations that loop seamlessly — the rotation
angles complete a whole number of turns across the set, so frame 16 returns to
frame 1 by construction. Three colourways: crimson, ember, amber. Feeds the 2D
canvas petal layer on the site.

Sheets are 4x4 grids, 1024x1024, transparent.

## reference/

The owner's photographs from Japan. These are the art direction.

## Blender 5.1 gotchas

Worth knowing before editing these scripts — each of these fails silently or
throws:

- The render engine enum only contains `BLENDER_EEVEE`. `BLENDER_EEVEE_NEXT`
  does not exist.
- `scene.node_tree` is gone; the compositor is a node group on
  `scene.compositing_node_group`.
- `CompositorNodeComposite` was removed. Go `CompositorNodeRLayers` →
  `NodeGroupOutput`. Feeding the group from `NodeGroupInput` renders a fully
  transparent frame with no error at all.
- `CompositorNodeGlare` parameters are input sockets now:
  `node.inputs['Type'].default_value = 'Bloom'`.
- EEVEE alpha is `material.surface_render_method`, `'DITHERED'` or `'BLENDED'`.
