# Momiji leaf field — choreography model

`demo.html` is self-contained. Open it directly; the three sheets sit next to it.
Everything below lives in one `CONFIG` object at the top of the inline script.

---

## 1. The core idea: paths, not forces

Nothing is integrated. A leaf's position at any instant is a **closed-form
function of a single progress scalar `u ∈ [0,1]`** plus three phase
accumulators. `u` advances at a per-leaf rate multiplied by the global wind:

```
u += uRate * dt * wind
```

`uRate = 1/duration`, and `duration` is derived from a desired speed in
*viewport widths per second*, so a leaf's journey takes the same number of
**seconds** on a phone and on a 5K display.

### Fate A — crosses the screen (≈ 79% of leaves)

```
x(u) = x0 + (xEnd - x0) · u·(0.86 + 0.14u)      // slight acceleration off the tree
y(u) = y0 + sink·u + arc·sin(π·u)               // net drift + one gentle bow
```

`sink` is the net height change over the whole traverse (−0.06 … +0.60 of the
viewport, clamped so the leaf stays in frame). `arc` is a single-hump bow that
is **zero at both ends** — which makes it the perfect lever for mid-screen
composition without touching where the leaf enters or leaves. More on that in §5.

### Fate B — descends and settles (≈ 21%)

```
x(u) = x0 + (xLand - x0) · (1 - (1-u)²)         // fast, then stalling: losing the wind
y(u) = y0 + (yLand - y0) · (0.45·smoothstep(u) + 0.55·u)
```

At `u = 1` the leaf is exactly on its landing point, because the flutter is
tapered to zero by a `smootherstep(0.70, 1, u)` window — it stops swinging as it
touches down rather than snapping. It then rests (2.2–6.8 s), does a short
damped bounce in the first 0.7 s, fades over 1.1–2.2 s, and recycles. If more
than 14 leaves are grounded at once, new arrivals get a 0.35× shorter rest, so
the ground thins itself out instead of accumulating.

`P(land)` is `0.42 - 0.20·intensity`, clamped to [0.12, 0.46] — a strong gust
carries more leaves across, which is both true and a nice readable effect.

### Flutter and tumble

On top of the path, two out-of-phase sinusoids with **incommensurate**
frequencies:

```
y += a1·sin(φ1) + a2·sin(φ2)
x += (a1·cos(φ1) + a2·cos(φ2)) · 0.70 · (H/W)   // aspect-corrected, so the swing is round
```

`ω2 = ω1 · 1.6180339887 · (0.85 … 1.15)`. The golden ratio guarantees the pair
never closes a cycle; the ±15% jitter guarantees **no two leaves in the field
share a ratio** (measured: 6000 spawns, closest pair differs by 1.3e-8).

The 16-frame sheet is what sells the 3D tumble. `framePhase` advances at
1.2–9.7 frames/s, signed for direction, itself slowly modulated by a third
phase accumulator so a leaf visibly speeds up and stalls as it turns. The 2D
`rotate` on top is only banking (±0.55 rad, driven by the same `sin(φ1)` as the
side-to-side swing, which is what a real leaf does). Sprites are also randomly
mirrored, doubling the apparent variety for free.

---

## 2. Wind: one global envelope

`wind ∈ [0.55, 2.40]` = 1 + slow breathing (two incommensurate sinusoids at
0.113 and 0.197 rad/s) + discrete gusts. A gust picks a duration (1.7–5.3 s)
and a peak, runs a `sin(πg)^2.5` envelope (slow attack, long tail), then waits a
random 1.2–6.7 s. Gust strength scales with intensity, so at 0 the field only
breathes.

Wind multiplies `u`, the flutter rate (at 45% strength), the tumble rate and the
spawn rate. The whole field surges and relaxes as one body while no two leaves
ever sync — that is the main defence against the "canned" failure mode of a
parametric system.

---

## 3. Intensity — the live parameter

```js
window.leafSystem.setIntensity(v)   // 0 … ~1.5, values above 1.2 are legal
window.leafSystem.getIntensity()
window.leafSystem.pause() / .resume() / .count()
```

Safe to call **every frame** from cursor distance, scroll or an idle timer. It
sets a target that is low-passed with a 0.9 s time constant; the population
controller reads only the smoothed value, so a hard 0 → 1.2 jump becomes an
8-second surge. Emission is a **Poisson process** (Exp(1) inter-arrival times,
time-rescaled so a changing rate stays correct), which is why the field has no
rhythm even under a constant intensity.

Population is closed-loop: `rate = target / meanLifetimeEMA`, with a weak
proportional correction and a hard cap of 5 spawns per frame. Speed, fate and
band are read from intensity **at spawn only** — existing leaves never change
their character mid-flight, so nothing pops when the parameter moves.

Measured steady states at 1440×860: I=0 → 8, 0.25 → 36, 0.5 → 79, 0.75 → 130,
1.0 → 185, 1.2 → 228, 1.5 → 299.

---

## 4. Depth, resolution independence, pooling

Three depth bands (far 42% / mid 38% / near 20%) drive size, speed, alpha and
flutter amplitude, and are drawn back-to-front in three passes over the pool —
cheaper and simpler than sorting, and zero allocation.

All coordinates are normalised to the viewport, so **resize is a no-op**: no
remapping, no popping. Leaf size is `clamp(√(W·H)·0.052, 22, 82)` px. Population
scales with `√(W·H)` too (clamped 0.42–1.30 of the reference), because a fixed
count on a 390px phone is a blizzard — this keeps the *fraction of frame covered
by leaves* roughly constant instead of the raw count.

Pool: 460 slots, ~30 typed arrays, structure-of-arrays, allocated once, free
list for reuse. Rendering is one `setTransform` + one `drawImage` per leaf, no
`save`/`restore`. Each sheet is sliced at load into 4 mip levels (cells
256/128/64/32) **per cell** by successive halving, and the smallest level that
covers the drawn size is used — this kills the shimmer you get downscaling 256px
cells to 40px and cuts GPU sampling cost.

DPR is capped at 1.5. `dt` is clamped to 50 ms. Hidden tabs cancel the rAF and
reset the clock on return. `prefers-reduced-motion` renders one static frame of
~20 scattered leaves and **never starts the loop**; it also honours a live change
of the media query.

---

## 5. Composition — the reason to choose choreography

Because the path is closed form, at spawn we can simply **ask where a leaf will
be when it reaches the portrait** and re-aim it before it ever moves:

```
uc      = (x0 - portraitX) / travelDistance
predY   = y0 + sink·uc + arc·sin(π·uc)
arc    += (target - predY) / sin(π·uc)          // bend the bow, keep both endpoints
```

A physics system cannot promise this. Two details matter more than the idea:

- The re-aim **probability ramps smoothly** with how dead-on the leaf is aimed
  (`smoothstep` of depth into the zone), and the per-leaf zone half-height is
  jittered ±45%. Without both, the zone empties and a visible ridge of leaves
  stacks along its edge — an invisible wall.
- Displaced leaves are scattered over a **wide** band (0.26 up / 0.15 down),
  not parked just outside the boundary.

A second, softer pass runs in flight: a smooth bow (`(1-dx²)²·(1-dy²)`) plus an
alpha veil over the portrait core.

Measured against a control run with routing and veil disabled: **65% less ink
and 57% fewer leaves over the face**, while 4.8% of leaves still cross it — a
thinning, not a force field. Steepest density change between adjacent deciles of
height: 2.6×.

This same machinery found and fixed a real defect: at 2560px the field formed a
single bright *ribbon* at the canopy's own height. Widening `SINK_SPAN`
(0.44 → 0.66) and `ARC_SPAN` (0.30 → 0.42) and loosening the emission lobes took
the two busiest deciles from 51% of traffic to 38%, and on-screen ink entropy
from 3.06 to 3.16 bits (max 3.32).

---

## 6. Measured, not intended

Headless: `node --expose-gc harness.js` — 44 assertions, all pass. It extracts
the exact `<script id="leaf-source">` block from `demo.html` and drives it with a
stub 2D context, so it tests the shipped code, not a copy.

| Check | Result |
|---|---|
| 36 000-frame soak (600 s), intensity stepped 0.6/0/1.2/0.15/1.0 | 6770 spawns, **0 NaN**, 0 out-of-range |
| Pool invariant `alive + free === 460` | held every frame, 0 violations |
| Exit accounting | **79.6% exit left**, **20.7% settle on the ground**, 0 top, 0 bottom |
| No popping (audit of every despawn) | 6597 audited, **0** vanished while on screen and visible |
| Peak grounded leaves | 32, never grows |
| Mid-screen crossing heights | sd 0.24, all 10 deciles used, entropy 2.96 / 3.32 bits |
| On-screen ink by height | entropy 3.16 / 3.32, steepest neighbour ratio 2.64× |
| Spawn inter-arrival CV | **0.98** (Poisson = 1, metronome = 0) |
| Detrended crossing-rate autocorrelation, lags 0.25–100 s | worst \|r\| = **0.10** — no periodicity |
| Path signature duplicates in 6000 spawns | **0** |
| 0 → 1.2 intensity jump | largest one-frame population change **4** leaves; ramp over ~8 s, no burst |
| 37.5 s frame (tab returning) | max displacement **0.025** of a viewport = one clamped tick |
| Traverse time at 390 / 768 / 1440 / 2560 px wide | 6.7 / 6.6 / 6.5 / 6.5 s — spread **1.03×** |
| Leaf size at those widths | 24 → 66 px; screen coverage 6.9 / 8.8 / 11.5 / 10.2% |
| `step()` at ~294 live leaves (Node) | **0.028 ms/frame** |
| Heap delta over 90 000 frames (1500 s) | **−0.6 KB** — nothing allocated in the loop |

Real Chromium, 1440×860, DPR 1, real PNGs, real `drawImage`:

| Check | Result |
|---|---|
| Live leaves at intensity 1.45 | 265–277 |
| Full frame body (step + fullscreen fill + ~265 real `drawImage`) | **0.48 ms** |
| rAF interval, 259 sampled frames | median **8.3 ms**, p95 10.0 ms — 120 fps sustained |
| Same at 2560×1300, 231 leaves | median 8.3 ms, p95 9.7 ms |
| `prefers-reduced-motion: reduce` | rAF **never starts**, frame byte-identical over 3 s, 20 static leaves drawn |
| All three sheets 404 | still boots and animates at 121 fps on the procedural fallback |
| External requests | the three PNGs, nothing else; no WebGL, no `getImageData` |

Caveat I will not paper over: 120 fps is the headless compositor's cadence, not
a mid-2019 laptop's. What is solid is the 0.48 ms CPU frame body and the 248
draw calls; the GPU-side fill of ~250 alpha-blended 40–80 px sprites is the part
I have not measured on real hardware.

Also `tune.js` — a fast probe printing the vertical distribution; that is what I
used to diagnose the ribbon. `_test_reduced.html` / `_test_nosheets.html` are the
two failure-path pages.

---

## 7. Where this model looks wrong or cheap

- **Landing points are pre-decided.** A leaf commits at spawn to where it will
  touch down. It cannot be blown further by a gust that arrives late in its
  descent — the gust speeds it *along* its path but cannot change the
  destination. Nobody will notice, but it is a lie.
- **The bow is a single hump.** `arc·sin(πu)` means every crossing leaf makes at
  most one large vertical excursion. Real leaves in real wind wander more. The
  flutter hides this at normal amplitudes; at low intensity, where flutter is
  relatively smaller, long paths read slightly too clean.
- **No collision, no wake, no interaction.** Leaves pass through each other and
  through the tree. At intensity 1.5 you occasionally see two overlap almost
  exactly for a moment.
- **The ground is a line, not a surface.** Settled leaves lie at a y determined
  by their depth band; there is no perspective floor and no stacking. They also
  fade out in place, which is graceful but not what happens outdoors.
- **The keep-clear zone is an ellipse in normalised coordinates**, so on a very
  wide short viewport it is a wide flat ellipse and on a phone a tall one. It
  should be tied to the actual portrait bounding box at integration time.
- **Sprite mips are chosen per leaf per frame** by size. A leaf sitting exactly
  on a threshold does not visibly switch (levels are half-steps apart), but
  strictly there is a discontinuity.
- **`meanLifetime` is an EMA over completed lives**, so the population overshoots
  its target by 5–15% for a few seconds after a large intensity change before
  settling. Visible only as instrumentation, not as motion.

---

## 8. What I would turn next, in order

| Parameter | Now | Range | Effect |
|---|---|---|---|
| `DENSITY_GAIN` | 168 | 90–220 | **First knob.** Leaves alive at intensity 1. 168 is deliberately generous so the slider proves 250+; a dark editorial hero probably wants 110–130. |
| `SPEED_MIN` / `SPEED_SPAN` | 0.055 / 0.115 | ±40% | Viewport widths per second. Lower both for a more contemplative hero. |
| `VEIL` | 0.36 | 0.2–0.6 | Alpha attenuation over the face. The cheapest way to protect the portrait once you have the real artwork. |
| `PORTRAIT` / `PORTRAIT_CORE` | 0.145 × 0.32 / 0.15 | — | Must be re-fitted to the real portrait box. Everything else follows. |
| `BAND_P` / `BAND_SIZE` | 42/38/20 | — | Raise the near-band share for a more aggressive foreground; drop it if leaves crowd the copy. |
| `LAND_P_BASE` | 0.42 | 0.25–0.5 | How many leaves reach the ground. The owner asked for "some" — 21% at intensity 1 is my reading of "some". |
| `GUST_PEAK_SPAN` | 0.60 | 0.3–0.9 | Drama of the surges. |
| `SINK_SPAN` | 0.66 | 0.4–0.8 | Vertical spread. Lower it and the ribbon comes back. |
| `INTENSITY_TAU` | 0.9 s | 0.5–2.0 | Lower feels responsive to the cursor, higher feels like weather. |

**Not yet done, worth doing at integration:**

1. Drive intensity from cursor proximity to the tree, scroll and idle time —
   sum them, clamp, call `setIntensity` every frame. The smoothing is already there.
2. A `setWindOrigin(x, y)` so a mouse gesture can nudge the emission point.
3. Split the field into two canvases (behind / in front of the portrait) if the
   art director wants leaves passing *behind* the subject — currently everything
   is in front, per the brief.
4. Cut the pool to ~300 once the final density is chosen; 460 is headroom.
