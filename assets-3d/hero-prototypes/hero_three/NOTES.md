# Hero — approach 2: a real 3D scene in three.js

`demo.html` in this folder. Serve the scratchpad root over HTTP and open
`/hero_three/demo.html`. Everything it loads lives in `./assets/`.

One `PerspectiveCamera`, four meshes carrying the geometry that was modelled in
Blender, one instanced leaf system, six draw calls. Nothing is a flat layer.

---

## 1. What is actually in the scene

| element | source | in the browser |
|---|---|---|
| Mount Fuji | `fuji.blend`, 432,000 tri displaced heightfield | `fuji.glb`, 15,000 tri, two vertex-colour sets, custom view-dependent rim shader |
| Chureito pagoda | `pagoda.blend`, 59,972 tri, 9 flat materials | `pagoda.glb`, 10,987 tri, one vertex-coloured `MeshStandardMaterial`, flat-shaded from derivatives |
| momiji branches | `tree.blend` `branches` | `branches.glb`, 9,735 tri, `MeshStandardMaterial` |
| momiji foliage | `tree.blend`, 120 separate alpha-card objects | `foliage.glb`, **one** mesh, 240 tri, one alpha-tested draw call |
| portrait | — | **placeholder**, see §6 |
| leaves | the force-based system from `leaf_forces/demo.html` | one `InstancedBufferGeometry`, camera-facing quads at real depths |

Draw calls: **6**. Triangles: **38,200**. Shader programs: **6**. Textures: **4**
(two loaded, two generated).

---

## 2. Architecture

### 2.1 The leaf system is the existing one, re-rendered

`src/leaves.js` is the physics from `scratchpad/leaf_forces/demo.html`, lifted
verbatim: same integrator, same divergence-free wind field, same
frequency-modulated octaves, same non-homogeneous Poisson detachment, same
parameter table, same canopy lobes, same PRNG. I changed nothing in it. Only
the draw step is new.

The 2D system fakes depth with one factor `par ∈ [0.58, 1.30]` that scales
accel, wind, velocity and drawn size together. Here `par` picks a **real z**:

```
z(par)  = lerp(−46, −11.5, (par − 0.58) / 0.72)
S_world = pSize · (2·√(W·H)·tan(fov/2) / H_px) · |z|
```

The perspective divide multiplies `S_world` back by `1/|z|`, so every leaf lands
on screen at exactly `pSize · √(W·H)` pixels — the size the tuned 2D system
asked for — at any depth. Position is projected the same way, from the camera's
**rest** pose. So with the pointer at centre the leaf layer is the 2D layer,
pixel for pixel; move the pointer and the leaves parallax and occlude correctly
because they are genuinely at those depths.

Measured: leaves occupy z −43.9 → −13.4. The tree sits at −20 with its canopy
spanning −24 … −16, and the portrait plane at −22. Leaves therefore pass in
front of and behind both.

`setIntensity(0..1.2)` is preserved unchanged (it clamps at 1.6 and eases with
the original 0.85 s time constant).

### 2.2 What the 3D actually buys — measured, not asserted

I rendered the same frame twice, once with `depthTest` on the leaf material and
once off (off = what a flat overlay does), and diffed:

**6,009 pixels — 0.46 % of a 1440×900 frame — are leaves correctly hidden by
the canopy.** `shots/occl_on.png` vs `shots/occl_off.png`. Small in area,
but it is the difference between leaves *in* the tree and leaves *on* the page.

Three other things the flat approach cannot do, all visible in the demo:

- **Perspective on the pagoda.** Pointer left vs pointer right: the eave
  undersides open and close and the balcony rails re-order. Compare the two
  halves of `shots/d_tl.png` / `shots/d_br.png`.
- **Fuji's rim light is Fresnel, not baked.** The original build script baked
  `BODY` (body colour) and `MASK` (warm rim / snow / cool counter-rim) into two
  vertex-colour layers and computed the rim *per pixel* from
  `1 − dot(N, I)`. I reproduce that term in the shader, so the ember crescent
  on the left ridge slides as the camera moves. A PNG freezes it.
- **Depth-cued fog.** `Fog(#0c0c0c, 34, 190)` puts the pagoda 17 % into the
  page background at its actual distance. Fuji opts out (its haze is baked).

### 2.3 Camera and parallax

Camera at the origin looking down −Z. Pointer drives 0.62 world units of
lateral dolly, 0.30 vertical, 0.92° of yaw and 0.46° of pitch, eased with a
0.28 s time constant. On a subject at 20 units that is about 12 px of relative
shift between the tree and the portrait — enough to feel solid, not enough to
read as an effect.

### 2.4 Two stagings, not one crop

A perspective camera loses *horizontal* field as the frame narrows. At 390×844
the pagoda and the momiji simply fall off the sides of the desktop staging. So
there are two hand-set layouts (`LANDSCAPE`, `PORTRAIT` in `src/main.js`),
switched at aspect 0.95, plus a mild FOV widening between them. Same geometry,
same camera, restaged. Verified at 1440×900, 1920×1080, 1024×768 and 390×844
(`shots/final_*.png`).

---

## 3. The asset pipeline (`tools/build_assets.sh`)

Blender 5.1.2 headless, then `gltfpack`, then `cwebp`. Reproducible.

**Draco vs meshopt — measured both, meshopt wins by 222 KB.**

| | geometry bytes | decoder bytes | total |
|---|---|---|---|
| `KHR_draco_mesh_compression` | 163,236 | 250,876 (`draco_decoder.wasm` + wrapper) | **414,112** |
| `EXT_meshopt_compression` | 164,568 | 26,463 (bundled) | **191,031** |

Draco compresses no better here and its decoder is 9.5× the size. Blender does
not emit meshopt, so the pipeline exports uncompressed GLB and packs with
`gltfpack -cc`.

Other reductions, each measured:

- **No normals are shipped.** `export_normals=False` on all three exports. Fuji
  and the branches get `computeVertexNormals()` at load; the pagoda uses
  `flatShading` (screen-space derivatives). This also let co-located pagoda
  vertices merge, taking the pagoda GLB from 317 KB (Draco, with normals) to
  44 KB.
- **Pagoda: 9 materials → 1 draw call.** Separate by material → planar dissolve
  at 3° → collapse to 0.30 → bake each material's base colour to a vertex
  colour → rejoin. 30,424 faces → 11,028.
- **Fuji: two reductions in order.** (1) Delete every face pointing away from
  the camera hemisphere — the blend renders this material backface-culled, so
  this is lossless: 39,384 faces gone. (2) Collapse 353,232 → 15,000 tri
  (95.8 % removed).
- **Fuji vertex colours are renormalised.** The body colour is a near-black
  linear ramp (0.003 … 0.019). At 8-bit quantisation that is about five
  distinct levels and the cone bands visibly. The exporter divides it by its
  own max (`BODY_SCALE = 0.019155`, printed at build time) and the shader
  multiplies it back — ~50× the effective precision for the same bits.
- **Foliage: 120 objects → 1 mesh.** The four 768² cluster atlases are packed
  2×2 into one 768² texture and every card's UVs remapped into its quadrant.
  Blender's per-object colour (tint in rgb, backlight strength 0…3 in alpha)
  does not survive glTF, so it is baked to a `COLOR_0` vertex attribute.
  Result: 6.5 KB of geometry, one alpha-tested draw call for the whole canopy.
- **Textures are WebP.** `leaf_atlas` 768² at q78/alpha_q70 = 156 KB (497 KB as
  PNG). `sprite_atlas` — the three tumbling-leaf sheets downscaled to 128 px
  cells and packed into one 8×6 grid — at q82/alpha_q100 = 121 KB (397 KB as
  PNG). Lossy alpha is a big win on the foliage (223 → 156 KB) and a *loss* on
  the sprites (alpha_q 100 compresses those cleaner shapes better than 85).

Two traps worth writing down, both of which shredded the mesh silently before I
caught them:

1. `BufferGeometry.applyMatrix4` on a `KHR_mesh_quantization` position
   attribute writes floats back into `Uint16` storage. Dequantise first.
2. meshopt pads a `uint16` VEC3 to an 8-byte stride. Reading `attribute.array`
   directly walks into the padding; use `getX/getY/getZ`.

And one colour trap: three only injects `<colorspace_fragment>` into *its own*
materials. A raw `ShaderMaterial` writes linear values straight to an sRGB
framebuffer and the whole scene comes out black. All four custom shaders
include it explicitly.

Colour management: `fuji.blend` and `tree.blend` both render with Blender's
`Standard` view transform — a straight linear→sRGB encode, no filmic curve — so
the renderer uses `NoToneMapping` and the baked vertex colours land at the
values `fuji_final.png` has. (`pagoda.blend` used AgX; the pagoda is relit by
three.js lights here anyway and was matched by eye instead. See §7.)

---

## 4. Measurements

Chrome 3-something headless (`--headless=new`), real GPU:
`ANGLE (Apple, ANGLE Metal Renderer: Apple M4 Max)` — confirmed via
`WEBGL_debug_renderer_info`, not SwiftShader. Server is `python3 -m
http.server`, **no compression**. Harness: `tools/cdp.mjs`, `tools/measure.mjs`,
raw output in `build/measure.json`.

### 4.1 Bytes over the wire — 1,106,832 B (1.06 MB)

Every request on a cold first load at 1440×900, off the network stack:

| resource | bytes |
|---|---:|
| `hero.js` | 652,484 |
| `leaf_atlas.webp` | 159,946 |
| `sprite_atlas.webp` | 123,960 |
| `fuji.glb` | 67,767 |
| `branches.glb` | 46,563 |
| `pagoda.glb` | 44,327 |
| `foliage.glb` | 6,722 |
| `demo.html` | 5,063 |
| **total** | **1,106,832** |

`hero.js` breaks down (esbuild metafile, post-minification):

| | bytes |
|---|---:|
| `three.module.js` + `three.core.js` | 559,213 |
| `GLTFLoader` | 42,579 |
| `MeshoptDecoder` | 26,463 |
| `BufferGeometryUtils` + `SkeletonUtils` (pulled in by GLTFLoader) | 1,429 |
| **my code** (`main.js` + `leaves.js`) | **22,511** |

**That is the headline: 630 KB of library for 22 KB of scene.** Gzipped,
`hero.js` is 169,107 B and the whole page would be ~623 KB on any server with
compression on — but the stated brief is a plain `http.server`, so 1.06 MB is
the honest number. I did not use a client-side `DecompressionStream` trick to
make the figure look better.

`assets/fallback.webp` (126,228 B) is **not** in that list: it is a CSS
background on a `[hidden]` element and is only fetched if the fallback shows.
Confirmed — the no-WebGL run transfers 783,775 B and never requests a GLB.

### 4.2 Frame rate and frame cost, 1440×900

| run | mean frame | p95 | fps |
|---|---:|---:|---:|
| vsync on (headless panel is 120 Hz) | 8.333 ms | 9.0 ms | **120.0** |
| vsync on, **4× CPU throttle** | 8.333 ms | 9.1 ms | **120.0** |
| rAF unthrottled (frame-rate limiter off) | 1.113 ms | 2.5 ms | 898 |
| rAF unthrottled, 4× CPU throttle | 1.145 ms | 2.6 ms | 873 |
| rAF unthrottled, intensity 1.2 (150 leaves) | 1.262 ms | 2.5 ms | 793 |
| rAF unthrottled, intensity 1.2, 4× throttle | 1.228 ms | 2.7 ms | 814 |
| 390×844, rAF unthrottled | 1.027 ms | 2.5 ms | 973 |
| 390×844, 4× throttle, vsync | 8.334 ms | 9.1 ms | **120.0** |

**60 fps and 120 fps are both hit with a large margin, and a 4× CPU throttle
does not move the number.** At 1.11 ms per delivered frame the scene uses 6.7 %
of a 60 Hz budget.

Where the time goes (`_internals.bench(500)`, which times the work directly and
ends with `gl.finish()`):

| | sim (physics + instance rebuild) | draw (submit + finish) | total |
|---|---:|---:|---:|
| 1440×900, 87 leaves | 0.010 ms | 0.381 ms | 0.392 ms |
| 1440×900, 146 leaves | 0.017 ms | 0.375 ms | 0.392 ms |
| 1440×900, 146 leaves, CPU 4× | 0.063 ms | — | 0.390 ms |
| 1440×900, 146 leaves, CPU 8× | 0.117 ms | — | 0.388 ms |
| 2560×1440 (3.7 Mpx ≈ 1440×900 @ DPR 1.6) | 0.026 ms | 0.502 ms | 0.528 ms |

The JS half is 1–2 % of the frame; it grows 4× and 8× exactly as the throttle
says it should, and the total does not move, which is the proof that this scene
is GPU/compositor bound and not CPU bound. **Caveat: `bench` runs the two loops
separately, which lets the driver pipeline the draws. The interleaved variant
measured 0.675 ms. Take 0.4–1.1 ms as the bracket; the 1.11 ms rAF interval is
the one to quote because it includes Chrome's own per-frame work.**

### 4.3 JS heap

**4.8 – 7.0 MB** used across all runs (`performance.memory.usedJSHeapSize`),
5.7 MB typical at rest. It does not trend upward with leaf count or time: the
leaf pool is 368 slots of typed arrays allocated once, and `syncLeaves()`
writes into pre-allocated `Float32Array`s. Nothing in the frame loop allocates.

GPU memory is *not* included in that figure and I did not measure it. Rough
static estimate, unverified: 768²+1024×768 RGBA textures ≈ 5.4 MB decoded, plus
~1.5 MB of vertex buffers.

### 4.4 Correctness checks, all verified by script

- `devicePixelRatio: 3` → renderer pixel ratio **1.5**, buffer 2160×1350. Cap works.
- Tab hidden → `isRunning() === false`; visible again → `true`.
- `prefers-reduced-motion` → rAF **never starts**; 15 leaves parked on plausible
  drift lines; leaf x is bit-identical 4 s apart (0.8107702136039734 twice).
- WebGL2 disabled → fallback image shown, canvas hidden, on-screen message says
  so, and none of the 3D assets are requested.
- `webglcontextlost` is handled: loop stops, same fallback path.
- `window.heroDemo` exposes `setIntensity`, `getIntensity`, `pause`, `resume`,
  `count`, `bytes`, `_internals`.

### 4.5 What I could not measure

- **No low-end hardware.** Everything above is an M4 Max. A 4× CPU throttle is
  not a weak GPU, and this scene is GPU-bound — so the throttle result says
  much less than it looks like it does. On an older integrated GPU the 0.4 ms
  draw could plausibly be 5–10×; I have no measurement to back a number.
- **Shader compilation.** Six programs compile on first frame. I did not
  isolate that cost, and on a cold shader cache it is the largest single stall
  in the load.
- **GPU time proper.** Inferred from `gl.finish()` and rAF intervals, not from
  `EXT_disjoint_timer_query_webgl2`.
- **A real phone.** 390×844 here is a resized desktop Chrome viewport.

---

## 5. The cropped-momiji defect

`assets-3d/momiji/tree_final.png` is cropped tight and shows a hard vertical cut
where the foliage meets the left edge of its own frame.

**This demo never loads that file.** The defect belongs to the flat render; this
approach loads the geometry it was rendered from — `branches.glb` and
`foliage.glb`, exported from `tree.blend` — and the canopy edge on screen is
whatever the 120 cards actually form in space. There is no frame for it to be
cropped by. Verified in `shots/final_1440x900.png`: the left edge of the canopy
is ragged and card-shaped, not a straight cut.

Two related things I did check rather than assume:

- The four cluster atlases the cards sample have their own margin (19 % opaque
  coverage, leaf shapes nowhere near the edge), so repacking them 2×2 at 384 px
  each clips nothing.
- The no-WebGL fallback image is a capture of *this* 3D scene
  (`tools/make_fallback.mjs`), not the supplied PNG — so the cut cannot sneak
  back in through the fallback either.

---

## 6. The portrait is a placeholder

The owner has not sent his photograph. The centre element is a
**vertical rounded rectangle, 4:5, filled with a dark gradient, the letters
"IK" in large muted type, and the words "PORTRAIT · PLACEHOLDER" beneath them.**

It is drawn to a `<canvas>` at runtime and used as a `CanvasTexture`, so it
costs **0 bytes over the wire**. It is a real textured plane at z = −22 with
`depthWrite` on, which is why leaves sort against it. When the photograph
arrives, replace `makePortrait()` with a texture load; nothing else changes.

---

## 7. What this approach does badly

An honest list. Several of these are structural, not bugs.

1. **652 KB of JavaScript before a single pixel.** 630 KB of it is three.js and
   its loader. Nothing in this scene — six meshes and a camera — justifies a
   general-purpose renderer, a full PBR shader library, a glTF parser and a
   mesh decompressor. The flat-layer approach ships kilobytes. This is the
   single biggest cost and no amount of asset tuning offsets it. (Deliberately
   plain three.js, no R3F: R3F would have added another 108 KB gzip for a
   reconciler this scene has no use for.)
2. **Nothing renders until everything is ready.** Four GLBs, two WebP textures,
   the meshopt decoder init and six shader compiles all sit between navigation
   and first paint. The CSS approach can show a background colour and a first
   layer almost immediately. I mitigate it with a 0.9 s fade-in, which is a
   cosmetic answer to a structural problem.
3. **The composition is a matte painting, not a survey.** Fuji is stretched
   2.6× vertically (`FUJI_STRETCH`) and staged at 380 units, the pagoda at 60,
   the tree at 20. Those are picture-making numbers, not relative scales. The
   blend's Fuji is a stylised flat cone shot on a 220 mm lens; at a 33° hero
   lens its peak sits barely above the horizon, so I stretched it. I would
   rather say that plainly than imply the scene is geometrically true.
4. **The foliage is billboards baked toward the original Blender camera.** They
   survive the ±0.9° pointer move. They would not survive a real orbit — past
   maybe 8–10° the cards start reading as cards. So "it's real 3D" is true of
   the pagoda and Fuji and only conditionally true of the tree.
5. **Leaf sorting is approximate.** Leaves are filled into the instance buffer
   in three depth bands, not sorted back-to-front, and the material has
   `depthWrite` off. Two overlapping leaves in the same band can composite in
   the wrong order. On a near-black ground it is invisible, but it is wrong,
   and a true sort would cost a per-frame sort of ~150 items.
6. **Two hand-tuned stagings.** Landscape and portrait are separate constant
   blocks that must be maintained together. Aspect ratios between 0.95 and 1.35
   get whichever staging is closer plus a FOV nudge — a compromise, visibly so
   at 1024×768 where the momiji crowds the right edge.
7. **Fuji lost 95.8 % of its triangles.** At this distance the ridge holds. Push
   the camera in and the silhouette will facet.
8. **The pagoda's colour is not the reference's colour.** `pagoda.blend` was
   graded through AgX with four lights; I bake its nine flat base colours to
   vertex colours and relight with three directional lights matched by eye.
   Fuji and the momiji reproduce their references' pixel values by construction;
   the pagoda only approximates it.
9. **8-bit vertex colours needed a trick.** The Fuji `BODY_SCALE` renormalisation
   is invisible but it is a hard-coded constant coupled to the export. If the
   body colour range ever changes and the constant is not re-copied from the
   exporter's printout, the mountain silently changes brightness.
10. **No depth of field, no shadows.** Both were on the table. DOF needs a
    full-screen post pass (`EffectComposer` + `BokehPass`, ~15 KB and a second
    render target) and on a scene this dark it would be nearly invisible.
    Shadow maps need another pass and the dusk key is too soft to read. So the
    "real DOF" that this approach could in principle offer is not in the demo —
    only fog and real occlusion are.
11. **The fallback is a 126 KB download at the worst moment.** If the context is
    lost mid-session the user pays for an image right when things are already
    going wrong.
12. **The dev panel's byte counter is `PerformanceResourceTiming`.** It reports
    what this document reports, but it is measured in-page and will read 0 for
    cross-origin resources without `Timing-Allow-Origin`. Fine here; a trap if
    the assets ever move to a CDN.

---

## 8. Files

```
demo.html                the demo
hero.js                  esbuild bundle of src/  (652 KB, generated)
src/main.js              scene, camera, materials, leaf renderer, panel, API
src/leaves.js            the leaf physics, lifted unchanged from leaf_forces/
assets/*.glb             meshopt-compressed geometry
assets/*.webp            foliage atlas, leaf sprite atlas, no-WebGL fallback
tools/build_assets.sh    .blend -> .glb + .png -> .webp, reproducible
tools/export_*.py        the three Blender export scripts
tools/make_atlases.py    texture packing
tools/bundle.sh          esbuild
tools/cdp.mjs            DevTools-protocol harness (no dependencies)
tools/measure.mjs        the measurement run in §4
tools/tune.mjs           live layout tuning; the LAYOUT numbers came from it
tools/make_fallback.mjs  renders the static fallback from the live scene
build/measure.json       raw measurement output
build/meta.json          esbuild metafile
shots/                   screenshots, including the occlusion A/B
```

Rebuild everything:

```bash
bash tools/build_assets.sh     # needs Blender 5.1.2 and cwebp
bash tools/bundle.sh
```
