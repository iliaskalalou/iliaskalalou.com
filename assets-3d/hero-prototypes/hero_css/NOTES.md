# Hero — layered images in CSS 3D space

`demo.html` + `a/` (assets). No WebGL, no library, no framework, no build step.
Serve the scratchpad root over HTTP and open `/hero_css/demo.html`.

```
python3 -m http.server 8777 --bind 127.0.0.1   # from the scratchpad root
open http://127.0.0.1:8777/hero_css/demo.html
```

---

## 1. What it is

Four flat renders and one placeholder, hung at genuinely different depths inside
a single `perspective`, plus the leaf canvas on top.

| layer | z | scale | what |
|---|---|---|---|
| `#fuji` | −900 | 1.750 | Mount Fuji, pre-blurred and graded in the asset pipeline |
| `#air-far` | −800 | 1.667 | a sheet of atmosphere: dusk glow, base haze |
| `#pagoda` | −420 | 1.350 | Chureito, cooled and dimmed toward silhouette |
| `#portrait` | −60 | 1.050 | **placeholder** — see §4 |
| `#air-near` | −30 | 1.025 | ground haze + the momiji's warm spill |
| `#tree` | +170 | 0.858 | the momiji, the only sharp layer |
| `#leaf-canvas` | — | — | fixed above everything, `pointer-events: none` |
| `#grade` | — | — | vignette + film grain, fixed: this is the lens, not the world |

Every plane is a **full-stage sheet** (`inset: 0`), and the artwork is positioned
*inside* it. That is the trick that makes the depth free: because each plane's
centre coincides with the perspective origin, the compensating scale
`(P − z)/P` is a pure size correction with no positional side effect, so a layer
can be moved in depth without re-doing its layout. Change `--z-pagoda` and the
pagoda stays exactly where it is on screen; only its parallax response changes.

`--Pn: 1200` is the single number behind the perspective, every plane's scale,
and the JS shift formula. The mobile block overrides it to `900` and nothing
else has to follow.

## 2. The parallax is a real projection, not an offset per layer

`#world` sits **inside** the element that owns `perspective`, so its translate
is projected like everything else. A plane at `translateZ(z)` is at distance
`d = P − z` from the camera, and a world translate `T` moves it on screen by
`T·P/d`. Far planes therefore move *less* than near ones because of the
division, not because of a hand-tuned multiplier.

On top of that there is a small counter-rotation. `rotateY(θ)` about the world
origin displaces a plane by `z·sinθ·P/d` — negative for planes behind the
origin, positive for the one in front — so giving θ the same sign as T pulls
the far planes back and pushes the near one further. It widens the near/far
ratio without spending any extra travel. It is the move a camera operator makes
without thinking: dolly, and pan a little against it.

Measured travel across the full window (pointer at the left edge → right edge),
1440×900:

| layer | z | travel |
|---|---|---|
| fuji | −900 | **14.5 px** |
| pagoda | −420 | 25.7 px |
| portrait | −60 | 41.0 px |
| momiji | +170 | **53.2 px** |

3.7× separation between the furthest and the nearest, from `T = ±22 px` and
`θ = ∓0.30°`. Nothing about those four numbers is authored; they fall out of
the four `--z` values.

The emitter follows the tree: the leaf system's spawn lobes are expressed in
*tree-image* coordinates and mapped through the momiji's on-screen rectangle
each layout, then offset every frame by the tree plane's own computed screen
shift. Leaves keep leaving the branches they are drawn on while the branches
move.

## 3. The momiji crop — what I did

`assets-3d/momiji/tree_final.png` is cropped tight: measured, the alpha at
column 0 has a mean of 85/255 and touches the top and right edges too. There is
no placement that hides a cut that severe on the flank facing the centre of the
frame.

**I re-rendered it.** `rerender_tree.py` opens `tree.blend` headless
(Blender 5.1.2, ~90 s), divides the camera's focal length by 1.34 and multiplies
the resolution by the same factor. Camera position, lighting, materials and the
compositor glare are untouched, so the tree comes out at **exactly the same
pixel scale** — it simply gains margin. Result `tree_margin.png`, 1716×2144:

| | original 1280×1600 | re-render 1716×2144 |
|---|---|---|
| left margin | 0 px (alpha mean 85) | **23 px**, canopy feathers out over ~180 px |
| top margin | 0 px | 234 px |
| right margin | 0 px | 0 px — still clipped |

The left flank — the one that faces the portrait — is now a natural thinning
canopy, and that is the flank that matters. The **right** flank still runs off
its frame, and I dealt with that the cheap way: the far-right 12 % of the image
is cropped away in the asset build, and the layer is positioned with its right
edge at 111.5 % of the stage. Verified at ten viewport sizes from 360×640 to
2560×1440, at all four parallax extremes: the tree's right edge is always past
the viewport edge, and Fuji's left cut is always negative. Nothing reveals.

## 4. The portrait is a placeholder

**The owner has not sent his photograph.** `#frame` is a vertical rounded
rectangle, aspect-ratio 4:5, filled with a dark gradient, a warm rim from the
momiji side and a cool one from the mountain side, the letters `IK` in large
muted type, and the words `PORTRAIT · PLACEHOLDER` in small letterspaced type
inside the frame so nobody can mistake it for finished work. Replacing it is one
element: drop an `<img>` into `#frame` and delete the two text divs. Everything
else — its depth, its shadow, its rim light, the leaves that cross in front of
it — keeps working.

## 5. Asset pipeline (`build_assets.py`)

Everything the browser pays for is produced offline:

- **Atmospheric blur is baked**, not a CSS `filter`. A `filter: blur()` on a
  layer that is being transform-animated can be re-rasterised; a pre-blurred
  texture costs zero at runtime. Fuji gets 2.5 px of blur, γ 1.24, saturation
  0.66 and a cool tint; the pagoda 0.65 px and saturation 0.70.
- **Premultiplied resize and blur.** Filtering straight-alpha RGBA pulls the
  colour of fully transparent pixels into the edges and haloes the foliage.
- **Alpha floor**: the render leaves a dust of alpha 1–14 that is invisible and
  expensive. Snapping it to zero cost 10 % of the tree's file size.
- **RGB bleed**: colour is dilated outward into transparent pixels so the codec
  never has to encode a colour cliff at every leaf edge. Floor + bleed together
  took the tree from 360 KB to 310 KB at equal quality, and Fuji from 80 KB to
  14 KB.
- **Grain** is added to Fuji and the pagoda before encoding: 8-bit WebP bands a
  smooth dark gradient badly, and noise below the quantisation step removes it.
- **Four cuts of the momiji**, chosen by `srcset` x-descriptors, so the cost of
  a retina-sharp tree falls only on screens that can show it: 800 px (216 KB),
  1000 px @2x (320 KB), 430 px and 620 px for the vertical layout.
- Fuji and the pagoda ship AVIF with a WebP fallback. AVIF is worth 4.5 KB vs
  14 KB on Fuji's smooth gradients. On the tree it was *worse* at equal
  perceived quality — its alpha crushed the leaf holes — so the tree is WebP.
- The **film grain tile is generated into a 96 px canvas at boot** and pushed in
  as the first background layer of `#grade`. Zero bytes over the wire, one
  rasterisation, and one full-viewport blend instead of two.

## 6. Mobile is a different cut, not a scale-down

The vertical layout triggers on `(max-width: 760px), (max-aspect-ratio: 1/1)` —
aspect, not just width, because the decision is really "is this frame taller
than it is wide". At 390×844 four elements cannot all carry meaning, so:

- the **momiji** owns the top of the frame and **loses its trunk**: an extra
  mask fades the image out at 54–76 % of its height, so it reads as foliage
  overhanging the frame rather than a potted tree;
- the **portrait** drops to the lower middle, out of the thumb zone;
- **Fuji** is blown up to 300 % width so only the summit and one shoulder are in
  frame, and moved down so the peak sits in the clear band between the canopy
  and the portrait;
- the **pagoda** is demoted to a small silhouette at the bottom-left that the
  portrait partly occludes — a depth cue, not a subject;
- `--Pn` drops to 900 and the parallax amplitude to 14 px, because the frame is
  narrower and the same travel would read as a lurch.

It also holds at 768×1024 and 820×1180 (tablet portrait picks up the vertical
layout via the aspect clause) and at 1024×768 / 1920×1080 / 2560×1440.

## 7. The leaf system

Lifted from `leaf_forces/demo.html` with the **physics untouched**: gravity +
quadratic drag + a lift that reverses with the tumble phase, all acting on
velocity relative to a divergence-free wind field, and the same tumble phase
picks the sprite frame. `setIntensity(0..1.2)` behaves exactly as before.

Four changes, all of them integration, one of them a judgement call:

1. Emission lobes are expressed in tree-image space and mapped onto the
   momiji's actual rectangle (§2), instead of being hard-coded to the viewport.
2. The atlas builder respects the source cell size. The sheets now ship at
   512 px (128 px cells) instead of 1024 — the largest leaf ever drawn is
   130 device px at 1440×900 / DPR 1.5, so 1024 was 4× wasted bytes. The old
   code would have keyed off a 256 px cell and sampled the wrong sub-rectangle.
3. The scaffolding tree drawing is gone; there is a real tree behind it now.
4. **`SIZE_FRAC` 0.046 → 0.030.** This is a deliberate deviation from the
   prototype. At 0.046 the flying leaves were four to five times the size of the
   leaves painted on the tree they had just left, and the scale mismatch was the
   single thing that made the composite read as pasted-together. At 0.030 they
   are still 1.5–3× the tree's own leaves, which is right for foliage that is
   nearer the camera.

At a gust peak the stream does cross the portrait — six or seven leaves can sit
over the frame at once. That is the physics doing what it was asked to do
(*across everything, right to left*), not a bug, and `setIntensity` is the lever
if the owner wants the face clearer once his photograph is in.

`prefers-reduced-motion` also got a better still frame: 14 leaves along the
drift line the simulation would have produced, each given a near face-on tumble
phase so none of them is an edge-on sliver.

## 8. Measurements

Environment: Apple M4 Max, macOS 26.2, Chromium 140.0.7339.16 driven by
Playwright, **headed** (real GPU), 120 Hz display — so 120 fps is the ceiling,
not 60. Frame times are rAF deltas sampled in-page; `js work` is the
main-thread time inside the frame callback (parallax + physics + canvas), and
`performance.now()` is clamped to 100 µs, which is the resolution floor on
those columns.

### Bytes over the wire (CDP `encodedDataLength`, headers included)

| | desktop @1 dpr | desktop @2 dpr | mobile 390×844 @3 dpr |
|---|---|---|---|
| `demo.html` | 47.7 KB | 47.7 KB | 47.7 KB |
| momiji | 215.7 KB (`tree`) | 319.9 KB (`tree_2x`) | 145.3 KB (`tree_md`) |
| leaf sheets ×3 | 117.2 KB | 117.2 KB | 117.2 KB |
| pagoda (AVIF) | 16.7 KB | 16.7 KB | 16.7 KB |
| fuji (AVIF) | 4.8 KB | 4.8 KB | 4.8 KB |
| **total** | **402.0 KB** | **506.2 KB** | **331.7 KB** |

`demo.html` is served uncompressed by `python -m http.server`; it is 15.6 KB
gzip −9 and 13.5 KB brotli −11, so on a real server the totals are ≈ 370 /
474 / 300 KB. There are zero other requests — no favicon, no fonts, no
scripts, no CSS files. The grain texture is generated in-page.

### Frame rate and main-thread cost

| scenario | fps | dt p50 | dt p99 | js work mean | js work p95 | leaves |
|---|---|---|---|---|---|---|
| **1440×900 @2 dpr** | | | | | | |
| leaves only, i=0.55 | 120.2 | 8.30 ms | 9.40 | 0.13 ms | 0.2 | 124 |
| leaves + parallax | 120.1 | 8.30 | 9.30 | 0.14 | 0.3 | 94 |
| i=1.2 + parallax | 120.2 | 8.30 | 9.30 | 0.26 | 0.4 | 134 |
| **4× CPU**, i=1.2 + parallax | 120.1 | 8.30 | 9.30 | 0.17 | 0.5 | 108 |
| **4× CPU**, i=0.55 + parallax | 119.9 | 8.30 | 16.00 | 0.39 | 1.0 | 111 |
| **390×844 @3 dpr** | | | | | | |
| leaves + parallax | 120.1 | 8.30 | 9.40 | 0.17 | 0.3 | 96 |
| i=1.2 + parallax | 120.0 | 8.30 | 9.30 | 0.16 | 0.3 | 114 |
| **4× CPU**, i=1.2 + parallax | 120.2 | 8.30 | 9.30 | 0.37 | 0.9 | 58 |

The 4× throttle is real and verified in the same session: a fixed 4M-iteration
busy loop goes from 6.0 ms to 12.7 ms (desktop @2dpr) and 3.7 ms to 13.2 ms
(mobile) with `Emulation.setCPUThrottlingRate`. It does not move the frame rate
because there is almost no main-thread work to slow down: 0.2 ms of a 8.3 ms
budget. One dropped frame appears in one 5-second sample (p99 16 ms).

### JS heap

`Runtime.getHeapUsage` after a forced GC: **1.37 MB** used / 2.36 MB total
(desktop), 1.45 MB / 2.36 MB (mobile). The leaf pool is 368 slots of 22
`Float32Array`/`Uint8Array` columns, allocated once at load; nothing in the
frame loop allocates. The panel shows `performance.memory` instead, which
Chrome quantises to 10 MB buckets without cross-origin isolation — that is why
it reads `~9.5 MB`; the 1.37 MB figure is the real one.

### The floor: no GPU at all

Same machine, Chromium launched `--disable-gpu` (software compositing), real
window, 1440×900, leaves + parallax: **5.1 fps**. This is the one number that
is bad, and it is worth understanding: the cost is *fill rate*, not compute.
Ablation in that mode:

| | fps |
|---|---|
| as shipped | 5.1 |
| minus the atmosphere planes | 6.3 |
| minus atmosphere, vignette and grain | 7.7 |

That measurement is why the composition ships with **two** sheets of atmosphere
instead of five. Collapsing them was worth 38 % of the software-composited
frame rate and costs nothing visually — a gradient that smooth parallaxes
invisibly, so the only thing that matters is which side of an image layer each
sheet of air sits on. Merging the grain tile into `#grade` removed one more
full-viewport blend.

Headless Chromium (SwiftShader) sits between the two: 31 fps at 1440×900,
60 fps at 390×844. **Do not trust headless numbers for this demo** — the
headed figures above are the real ones.

### What I could not measure

- A weak *GPU*. The 4× CPU throttle slows the main thread; there is no
  equivalent knob for fill rate, and I have no low-end Android or old integrated
  GPU here. Given that this design's cost is overdraw, that is exactly the
  hardware where it would be least comfortable, and I have no number for it.
- Real iOS Safari. `-webkit-mask-image` on a `preserve-3d` descendant and the
  dynamic-toolbar viewport are both places where iOS diverges, and this was only
  driven through Chromium.
- First paint / LCP on a cold cache over a real network.

## 9. What this approach does badly

1. **It is a photograph of a 3D scene, not a 3D scene.** Four flat cutouts. The
   parallax is a shear of cardboard, and it breaks if you push it — which is
   why the amplitude is capped at ~53 px on the nearest layer. You can never see
   round the pagoda, the tree cannot turn, and no layer can occlude itself.
   A WebGL build could move the camera ten times as far.
2. **Leaves can only ever fly in front.** The canvas is above the whole stack,
   so no leaf ever passes *behind* the momiji or the portrait. The physics has
   three depth bands; the compositing has none. This is the most visible
   correctness gap versus a 3D renderer, and there is no cheap fix — the canvas
   would have to be split in two, at the cost of a second full-viewport surface.
3. **Fill rate is the whole budget.** Eight composited planes plus the canvas
   plus the vignette is ~10 full-viewport blends at device resolution. Free on
   a GPU (0.2 ms of main thread, 120 fps), 5 fps without one.
4. **The nearest layer is a bitmap, so sharpness costs bytes.** The momiji is
   54 % of the desktop payload, and even the 2× cut (1000 px into ~763 CSS px
   at DPR 2) is still a 1.5× upscale — the leaf serration is visibly soft if
   you look closely. Geometry would be resolution-independent; this is not.
   Foliage with 50 % alpha coverage is intrinsically high-entropy: I measured
   360 KB before the encoder work and got it to 216 KB, and there is not much
   left to win.
5. **Two hand-authored layouts, not a responsive system.** Every position is an
   absolute percentage per breakpoint. 1440×900 and 390×844 are composed;
   1024×768 and 2560×1440 are merely *verified not to break*. Nobody designed
   them.
6. **`mask-image` inside `preserve-3d` is exotic.** It is correct in Chromium
   today and the spec supports it, but it is the kind of combination that finds
   browser bugs. Likewise the plane ordering relies on `preserve-3d` z-sorting;
   two planes at equal z would silently fall back to DOM order.
7. **Touch gets no parallax** unless the visitor drags, and the scene springs
   back on `touchend`. I did not use the gyroscope: on iOS it needs a permission
   prompt, and a hero should not ask for anything.
8. **No loading story.** The tree pops in when it decodes. No LQIP, no blur-up,
   no fade. First paint is the background gradients alone.
9. **The scene is baked.** One time of day, one light direction, forever. No
   day/night, no relight, no reaction to anything. That is also exactly why it
   is cheap — but if the owner ever wants the hero to respond to something, this
   architecture has nothing to offer and the whole thing has to be re-rendered
   in Blender.
10. **Rejected optimisation, recorded honestly:** the three leaf sheets are
    pixel-identical in alpha and differ only in RGB. Packing them as one RGB
    strip plus a single shared alpha map measured 88.7 KB against 113.5 KB —
    a 25 KB saving for a runtime compositing step and a non-obvious atlas
    layout. I judged that a bad trade and left it.

## 10. Files

```
demo.html            the whole thing: markup, CSS, leaf system, panel
a/                   built assets (tree ×4 cuts, pagoda, fuji, 3 leaf sheets)
build_assets.py      the asset pipeline described in §5
rerender_tree.py     the Blender re-render described in §3
final_measure.py     the harness behind every number in §8
perf.py              subsystem ablation (idle / parallax / leaves / masks)
measure.py           byte + reduced-motion + overflow checks
tree_margin.png      the Blender re-render, before the asset pipeline
m_final.json         raw results
shots/               screenshots at every viewport tested
```

The panel (`#panel`) and the `_dev` surface on `window.heroDemo` are dev
scaffolding. Deleting the `<aside id="panel">`, its CSS block, the `_dev`
object and the two `performance.now()` calls around the frame body is the whole
integration cleanup. The public API is `window.heroDemo.setIntensity(0..1.2)`,
`.pause()` and `.resume()`; `pause()` cancels the rAF loop entirely, so a
paused hero costs nothing at all.
