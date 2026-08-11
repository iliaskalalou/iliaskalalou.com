# Chureito Pagoda

Modelled from Ilias's own photograph (`reference/pagode_photo.png`) of the
Chureito Pagoda (忠霊塔) at Arakurayama Sengen Park, Fujiyoshida — the same
viewpoint his Mount Fuji photograph was taken from.

A five-storey *gojūnotō*. What makes it read as this building rather than a
generic tower: five tiers with dramatically upswept eave corners (*sori*),
vermilion timber against cream panels, the dense rhythm of white-tipped bracket
blocks under every eave, and the bronze *sōrin* finial.

All three are deliberately graded **below** the momiji. Two saturated warm
masses flanking a portrait would fight the face. Measured over `#0c0c0c`, the
architectural version sits at half the tree's mean luminance and a third of its
p90.

Rebuild any of them:

```bash
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
  --python build.py -- --final --out pagoda_final.png
```

## pagoda_dusk — best overall

Architecture stays readable — you can count the tiers, read the balconies and
the bracket rows — but the vermilion only ignites where the low warm key grazes
it. Present without shouting. **Recommended.**

## pagoda_silhouette — most elegant

Near-black cut-out revealed by a thin amber rim along each eave curve and the
gold finial. Beautiful on a dark page and the safest behind a portrait; the
trade is that the body carries no information. 24.5k faces.

## pagoda_arch — most detailed, but flawed

Genuine lofted eaves, ~1,100 rafter bars, 600 bracket blocks, railings, stone
podium. 78.6k triangles. But the corner wings read as sagging fabric rather than
lifting to a point — the *sori* is missed, which is the one thing a pagoda
cannot get wrong. Kept for its geometry, which is reusable.

Its author's finding is worth keeping: this composition needs a **close wide
angle from below**, not a long lens. At 40mm the receding side faces stay
visible and every corner reads as a downward fishhook; at 23mm from podium
height the near eave magnifies and occludes them. Camera azimuth must also stay
near-frontal — at 15° off, the symmetric eave curve collapses.

## Directory contents

Each folder holds `build.py`, the analysis helpers, `pagoda.blend`, the final
transparent render, and `iterations/` — the render-and-judge trail, compressed
to WebP since it is documentation rather than a master.
