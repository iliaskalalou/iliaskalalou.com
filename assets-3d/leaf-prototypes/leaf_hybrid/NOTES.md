# Momiji leaf system — notes

`demo.html` is self-contained (one file, vanilla JS, canvas 2D). Open it by
double-clicking; the three PNGs sit next to it and are the only external
requests. Verified loading over plain `file://` with default Chrome flags.

---

## 1. The physics model

Deliberately not a simulation. Four terms, chosen because each buys a visible
behaviour the brief asked for, and nothing else.

### Coordinates: normalised and anisotropic

The single most important decision. Positions `x,y` are **fractions of the
viewport**. Velocities are **anisotropic**: `vx` in viewport-widths/second,
`vy` in viewport-heights/second.

A leaf reaches the ground instead of crossing the frame iff

```
vy_px / vx_px  >  (groundY − y0) / x0
```

which in pixels depends on the aspect ratio. In *these* units the `W` and `H`
cancel and the condition becomes `vy/vx > 0.81` — **aspect-independent**. That
is why the fraction of leaves that land is 22–24% at every viewport from
390×800 to 2560×1440 (measured, §3) rather than drifting from "everything
lands" on mobile to "nothing lands" on ultrawide. Resize is also free: nothing
needs rescaling, because nothing is stored in pixels.

### Per-leaf motion (the whole of it)

```
lift  *= exp(−dt/ltau)                      // the updraft dies off
vx    += (wind·drag·zs − vx) · 2.4 · dt     // relax toward the wind
vy    += ((sink − lift)·zs − vy) · 1.8 · dt // relax toward terminal velocity
x     += (vx + fax·sin(ph)      ·zs) · dt
y     += (vy + fay·sin(2·ph)    ·zs) · dt   // bob at 2x the swing rate
```

- **Relaxation, not acceleration.** `v += (target − v)·k·dt` is a first-order
  approach to terminal velocity — the linearisation of gravity against
  quadratic drag. It is unconditionally stable, needs no clamping, and means a
  leaf entering a gust *eases* into it.
- **Flutter** swings horizontally at `ph` and bobs vertically at `2·ph`. The 2×
  is physically right: a leaf descends fastest at the middle of its swing and
  stalls at the extremes. Computed as `2·s·c` from the `sin`/`cos` already in
  hand.
- **Decaying lift** is what "some lose the updraft" means mechanically. A leaf
  starts with an upward `lift` that decays with its own `ltau ∈ [0.8, 3.6]s`;
  once it's gone, `sink` wins. This is why leaves visibly loft, hesitate, then
  give up — rather than being flagged "faller" at birth.
- **Whether a leaf lands is emergent**, never assigned. It falls out of the
  ratio of its own `sink` to the current wind. Consequence: in calm air 61% of
  leaves drop near the tree, in a strong gust 15% do. Intensity changes the
  *character* of the scene, not just the count. That was free and it's the part
  I'd keep if I had to throw everything else away.

### Depth

`z ∈ [0,1]` drives scale, speed, opacity, and **which of three pre-baked sprite
tiers** the leaf samples: full-res, half-res + blur + cool wash, quarter-res +
more blur + stronger wash. Aerial perspective is therefore paid once at load
and costs **zero per frame**. Note `zs` multiplies both `vx` and `vy`, so depth
does not bias the landing fraction.

### Tumble

Frame index advances at a rate proportional to the leaf's own speed, signed so
half tumble backwards. The edge-on frames (4–8% alpha coverage) make leaves
briefly vanish to a sliver, which is what sells three dimensions.

### Gust envelope

Four sines multiplying both wind and spawn rate. Frequencies were **searched,
not chosen by taste**: for a sum of sines the autocorrelation is exactly
`r(T) = Σ Aₖ²cos(ωₖT) / ΣAₖ²`, so "when does this visibly repeat" is a number
you can optimise. See §4 — this is where I got it wrong twice.

### Landing

On contact: skid and damp, rock with an exponentially-decaying oscillation,
foreshorten `scaleY → 0.62` (a leaf lying on the ground is seen at a glancing
angle), ease the tumble frame onto the nearest flat-faced frame (0/7/8/15), hold,
fade, recycle. Hold time is cut to 35% when more than 55 leaves are already
down, so a long gust can't carpet the floor.

### Free beauty, folded into the transform

Fast near leaves get a screen-space horizontal stretch. Because it composes as
`Stretch · Rotate · Scale` it rides in the `setTransform` call that was going to
happen anyway — **zero added cost** — and it reads as motion smear.

---

## 2. Performance

Pooled: 460 particles allocated once, `Int32Array` free-list, nine
`Int32Array` draw buckets (3 depth tiers × 3 sheets). No allocation, no
closures, no `sort` in the frame loop. Depth ordering comes from iterating
buckets far→near, which simultaneously batches by texture.

**Measured in-browser** (headless Chromium, `file://`, DPR 1.5):

| viewport | backing | live leaves | main-thread ms/frame |
|---|---|---|---|
| 1440×900 | 2160×1440 | 239 | **0.141** |
| 2560×1440 | 3840×2160 | 351 | **0.224** |
| 2560×1440 | 2560×1440 | 388 | **0.249**, 0/600 frames > 16.9 ms |

That is the time to run `update()`, bucket, and issue every `drawImage` —
roughly **10× under the 2 ms budget at 250 leaves**.

Node harness, 20 000 timed frames at 278 live leaves: **0.264 ms/frame**, heap
delta **−1 KB** over 30 000 further frames (no per-frame allocation).

### One real bug this measurement caught

The first version painted the background fill *and* blitted the tree onto the
animation canvas every frame. At 3840×2160 that is 16.6 Mpx of fill and alpha
blending before a single leaf, and it pushed a 2560×1440 retina viewport to
**~45 fps (599/600 frames over 16.9 ms)**. Splitting the scaffolding onto its
own layer and making the leaf canvas transparent cut main-thread work
**25×, 5.66 ms → 0.224 ms**. It is also the correct structure for integration,
since the leaves must composite over Fuji, the portrait and the tree.

Isolating what remained: at 3840×2160, 32 leaves cost 16.4 ms/frame and 366
leaves cost 20.0 ms — i.e. **334 extra leaves cost 3.6 ms (~0.011 ms each)**
against a 16.4 ms floor with almost no leaves. Halving the pixel count at
constant leaf count moved the gap from 20.0 ms to 10.8 ms. The floor is
per-pixel software rasterisation in the headless shell, not the particle
system. **Caveat I can't close here: this environment has no GPU, so I could
not measure hardware-accelerated compositing.** On real hardware a full-screen
clear is GPU work in the microseconds; the number I stand behind is the
main-thread figure.

---

## 3. What was measured

`node --expose-gc test.js` → **57 assertions, 0 failures**. The harness pulls
the `<script>` out of `demo.html` and runs it under a DOM stub, so it tests the
shipped file rather than a copy.

- **No NaN**: 1.65 M `setTransform` calls over a 200 s soak, zero non-finite
  arguments. Survives `dt` = 0, negative, and 1e6.
- **No leak**: `live + free === pool` and `spawned − freed === live` hold after
  20 000 frames with intensity thrashed randomly; pool constant at 460.
- **Exits left**: 2 753 of 4 242 spawns (72–79% across viewports).
- **Reaches ground**: 1 393 of 4 242 (32.8% at I=0.55).
- **Not degenerate**: left-exit heights span y ∈ [−0.02, 0.98], sd 0.231, 84% of
  uniform entropy over 12 bins; ground landings sd 0.202. Every live leaf has a
  unique `(vx, vy, phv, sink)` signature.
- **Emission matches the brief**: 99.6% of spawns in x ∈ [0.72, 1.00], 100% in
  y ∈ [0.08, 0.65] (n = 6 000).
- **Intensity**: 13 live at I=0 (a trickle, not frozen) → 233 at I=1.2,
  monotonic. A hard 0 → 1.2 step never spawns more than 2 leaves in one frame.
  One time-constant reaches 63.2% of the step, as documented.
- **Aspect independence**: ground fraction 22–24% across 390×800 → 2560×1440.
- **dt clamp**: a 45 s tick displaces identity-matched leaves by at most 0.035
  viewports.
- **Reduced motion**: `requestAnimationFrame` called exactly 0 times.
- **DPR**: device DPR 3 → backing store exactly 1.5×.

Screenshots: `shot_final1440.png`, `shot_wide.png` (2560, 302 leaves),
`shot_mobile.png` (390), `shot_calm.png` (I=0), `shot_gust.png` (I=1.2),
`shot_reduced.png`.

---

## 4. Where I was wrong

**Twice on periodicity, both times by measuring a proxy instead of the thing.**

1. Hand-picked three sine frequencies that *looked* incommensurate. Measured:
   autocorrelation returns to **r = 0.96 after 73 s**. Nearly commensurate.
2. Optimised the analytic autocorrelation of a sum of sines. Predicted 460 s;
   measured **85 s**. The formula was right for a sum of sines, but the shipped
   signal has a `0.55·I·max(0,g)²` term that half-wave-rectifies and squares
   `g`, manufacturing harmonics and difference frequencies (0.0675 − 0.054 is a
   465 s beat) that a linear analysis cannot see.
3. Searched the **actual nonlinear signal** by FFT. That search reported 463 s;
   direct measurement said 124 s, stable across 300/600/1200/2400 s records.
   The FFT normalisation was wrong. **The shipped number is the directly
   measured one: decorrelates by ~16 s, first returns above r = 0.6 at ~124 s.**
   The brief's bar is 30 s (measured r(30 s) = −0.07), so this has 4× margin,
   but it is 124 s and not the 460 s I briefly believed.

Also wrong: my `rimBias` comment claimed `<1` biases spawns toward the canopy
rim. `pow(rand, 0.62)` *shrinks* radii — it was mildly centre-biased (28.8%
inner vs 25% uniform). Comment fixed, exponent moved to 0.45.

Two test failures in the first run were **my tests being wrong, not the code**:
comparing positionally-filtered particle arrays across a tick (recycling
misaligns them, faking a 1.02-viewport jump), and treating high autocorrelation
at a 0.6 s lag as periodicity when it is just smoothness.

---

## 5. Where this model looks cheap

Honest list.

- **No inter-leaf or leaf–object interaction.** Leaves pass through the trunk,
  and will pass through the portrait. For a hero in front of a face this may
  read as wrong; a cheap fix is a soft elliptical "avoid" region nudging `vx/vy`
  near the portrait.
- **The wind is uniform in space.** Real wind near a tree has a wake and shear.
  A single low-frequency spatial term (`wind · (1 + 0.2·sin(y·3 + t·0.2))`)
  would add curl for ~2 extra operations. I left it out under Philosophy C.
- **Landing is a hard `y ≥ gy` test**, so leaves stop dead at a horizontal line.
  The rock-and-foreshorten hides it, but there is no bounce, no skitter, and the
  "ground" is a line rather than a surface with perspective.
- **Settled leaves fade rather than accumulate.** Correct for a hero that runs
  forever, but it means the ground never builds a drift, which is a lovely
  effect I'm giving up.
- **Depth is quantised to three tiers** for texture batching, so there is a
  visible (if subtle) jump in blur between tiers if you look for it. Five tiers
  would smooth it at the cost of memory and batch count.
- **The tumble sheet is one leaf.** Every leaf is the same silhouette at a
  different hue, scale and phase. At high density and large near-field sizes a
  sharp eye can notice. A second leaf shape would fix it for ~450 KB.
- **No shadow or contact cue** where leaves land, so they read as floating just
  above the floor rather than resting on it.
- **`prefers-reduced-motion` renders a static arc** that is placed by a
  hand-tuned curve, not by the simulation. It looks plausible but it is not "a
  frozen frame of the real thing".

---

## 6. Tunables

`window.leafSystem.setIntensity(v)` — 0 to ~1.3, safe to call every frame
(exponentially smoothed, τ = 0.55 s). Also `getIntensity()`, `pause()`,
`resume()`, `count()`, and `stats()` for instrumentation.

Everything else is in the `C` object at the top of the script.

| knob | now | what it does |
|---|---|---|
| `rateMin` / `rateMax` | 1.3 / 46 | leaves/s at I=0 and I=1, before viewport scaling. **The first knob to turn** — raise `rateMax` for a denser hero. |
| `windMin` / `windMax` | 0.070 / 0.300 | widths/s. Raising `windMin` makes calm air drift more and reduces the 61% calm-air landing rate. |
| `sinkSpan` / `sinkPow` | 0.420 / 2.60 | descent-rate distribution. **`sinkPow` is the landing-fraction dial**: lower ⇒ more leaves fall. |
| `liftMax` | 0.150 | initial updraft. Raise for more loft-then-give-up drama. |
| `ax` / `ay` | 2.4 / 1.8 | how hard leaves are yanked by gusts. Lower = floatier, more lag. |
| `zk0..zk1`, `zs0..zs1`, `za0..za1` | — | depth ramps for scale / speed / opacity. Widening `zs1` gives near leaves the "crosses in a second" streak. |
| `size` | 0.055 | base leaf size as a fraction of `sqrt(W·H)`. Near leaves currently peak ~110 px at 1440×900 — **drop to ~0.045 if they compete with the portrait**. |
| `stretch` | 0.00040 | motion smear. Free; 0 disables. |
| `ecx/ecy/erx/ery`, `rimBias` | — | emission ellipse. **Re-fit these to the real tree art**; the placeholder ellipse is not the real canopy, and on a tall phone it becomes an implausibly narrow sliver. |
| `POOL` | 460 | hard ceiling. Spawns are skipped when exhausted (never grows). |

### What I would do next, in order

1. **Re-fit the emission region to the real tree art**, ideally by sampling an
   alpha mask of the canopy instead of an ellipse. Biggest visual win.
2. **Add the portrait avoid-region** — leaves ploughing through a face is the
   most likely thing to look wrong in situ.
3. Wire intensity to cursor proximity / scroll / idle with a gentle ease; the
   smoothing is already there, so this is a few lines.
4. Consider capping DPR to ~1.25 above 2000 px wide. The brief specifies 1.5 and
   I honoured it, but the 4K fill-rate cost above is real on weak GPUs.
5. A second leaf silhouette, if the budget allows the extra sheet.
