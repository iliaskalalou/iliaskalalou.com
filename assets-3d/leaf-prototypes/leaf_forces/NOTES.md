# Momiji leaf system — honest physics

`demo.html` is self-contained: open it directly, no server, no build. Verified
under `file://` in headless Chrome (screenshot: `shots/file_protocol.png`).

Nothing about a leaf's path is authored. Each leaf is a point mass released
from the canopy into a wind field, and the path is whatever the integrator
produces. Whether it crosses the frame or sinks to the ground is decided by
its own drag-to-mass ratio, where it happened to let go, and which gust or
eddy it fell into.

---

## 1. The physics

### Coordinates: normalised, deliberately anisotropic

Everything runs in `u,v ∈ [0,1]` — u across the width, v down the height.
Velocities are viewport-widths (or heights) per second. Pixels appear only at
draw time.

This is anisotropic on purpose. It is the single decision that buys resolution
independence: the time to cross the frame and the time to fall to the ground
are then *identical* on a 390 px phone and a 2560 px monitor, because both
distances are 1.0 by construction. Measured — median crossing time is
**3.125 s at 390×844, 1440×900 and 2560×1440 alike**, and the ground fraction
is 25.6% at all three.

The price is that a leaf's motion is affinely squashed on extreme aspect
ratios. It is invisible, and the alternative — isotropic units — makes a phone
either a leaf blizzard or an empty screen.

Sizes use an *isotropic* reference, `sqrt(w·h)`, so every leaf covers the same
share of screen **area** everywhere: 26 px on a phone, 52 px at 1440, 88 px at
2560. Because the count is also viewport-independent, areal coverage stays
constant (~18%) rather than the leaves getting denser on small screens.

### Forces

```
a = g  +  a_drag(v − W)  +  a_lift(v − W, φ)
```

Drag and lift both act on the velocity **relative to the air**, `v_rel = v − W`.
That is the whole reason wind works at all: a leaf at rest in moving air feels
a large `v_rel` and gets snatched; a leaf riding the wind feels only its own
fall speed and tumbles lazily. The same equation produces both.

Per leaf, drawn once at spawn:

- **Terminal fall speed** `v_t`, log-normal around 0.175 viewport-heights/s,
  clamped to `[0.095, 0.34]`.
- **Gravity** `g` ≈ 0.50 with ±10% jitter.
- **Drag** `k = g / v_t²`. This is the one parameter that decides a leaf's
  fate: `k = C_d·A/m`. A dense, small-area leaf has low `k`, so it *both* falls
  fast *and* couples weakly to the wind, and it lands. A broad light leaf rides
  across. The crosser/lander split is a consequence of one log-normal draw, not
  a scripted percentage.

### Quasi-steady flat plate — and why the sprite sheet sets the phase

The sheet is 16 frames of one full revolution. Reading it: frames 0 and 8 are
face-on, frames 3–4 and 11–12 are knife-edge slivers. So knife-edge sits at
`φ = π/2` and `3π/2`, face-on at `0` and `π`. Define angle of attack from
knife-edge, `ψ = φ − π/2`, and flat-plate aerodynamics falls straight out:

```
normal force ∝ sin ψ
  drag component ∝ sin²ψ      → max face-on, min edge-on
  lift component ∝ sin ψ cos ψ → zero at both, reverses 4× per revolution
```

```js
cd = CD_A + CD_B·sin²ψ          // normalised so its mean over a turn is 1
cl = liftGain · sin(2ψ)
ax = −k·|v_rel|·cd·rvx  +  k·|v_rel|·cl·(−rvy)
ay = −k·|v_rel|·cd·rvy  +  k·|v_rel|·cl·( rvx)  +  g
```

No normalisation of the perpendicular is needed — `k·|v_rel|·cl·(−rvy, rvx)`
already has magnitude `k·cl·|v_rel|²`.

The drag pulsing at `2ω` is not decoration: the leaf accelerates when it slips
knife-edge through the air and stalls when its face catches. It swims.

**Tumble rate** rises with airspeed, Strouhal-like:
`ω = ±(ω₀ + c_ω·|v_rel|/parallax)`, clamped at 16 rad/s. A leaf just torn off
the branch sees `|v_rel| ≈ 0.55` and spins hard; seconds later it is riding the
wind, `|v_rel|` has collapsed to its fall speed, and it settles into a lazy
tumble. That decay is free — it is the same formula.

Measured tumble: **median 0.51 rev/s** (8.2 sheet-frames/s), p10 0.28, p90 1.24,
max 2.39 rev/s = 38 sheet-frames/s, safely under the aliasing limit for a
16-frame sheet.

### Parallax as one coherent factor

Depth `d` gives `f ∈ [0.58, 1.30]`, and *everything* scales by it: `g·f`,
`k/f`, sampled wind `·f`, size `·f`. That is exactly what "further away" means
in screen space — terminal velocity, drift and size all scale together, and the
far leaves are genuinely slower rather than fake-slowed. Leaves are drawn in
three depth bands, far first.

### Wind field

```
W = −U(I)·profile(v)·gust(t)  +  curl ψ(u,v,t)
```

- The eddies are the **curl of a stream function**, so they are exactly
  divergence-free: real swirls, no invisible drains herding leaves together.
  Four octaves, amplitudes pre-divided by `|k|` so the velocity spectrum falls
  off instead of being dominated by the finest octave. Cost: one `cos` per
  octave per sample.
- `profile(v)` is a no-slip boundary layer — the bottom 15% of the frame is
  nearly still. This is *why* a leaf that sinks that low stops crossing and
  settles. Landing is not scripted; it is a leaf running out of wind.
- Turbulence amplitude is comparable to the mean flow at intensity 1, so there
  are genuine low-wind pockets where leaves lose horizontal momentum and fall,
  and gust streaks where they are flung across.

### Detachment

A **non-homogeneous Poisson process**: integrate the rate, fire when the
integral crosses an `Exp(1)` draw. No cadence exists to be perceived, and a
smooth rate change cannot produce a burst. Measured spawn dispersion
`sd/√mean = 1.006` — Poisson to within 1%.

Emission samples two candidate points on the canopy and takes the windier one,
so detachment follows the gust across the tree instead of being uniform.

---

## 2. Making sure it never repeats

The per-leaf randomness handles individual paths — **0 near-duplicate pairs in
244,650 compared**. The risk is the *field*, which is deterministic.

I measured this rather than assuming it, and found a real defect. Four pure
tones, however irrational their ratios, drift back into alignment: the eddy
field measured **only 21% different from itself at a 40-second lag** — inside
the window where a viewer would notice.

Two fixes, both measured:

1. **Phase modulation.** Each octave's phase gets a slow sine of its own, so
   the octaves drift instead of marching. This is free — the phase depends only
   on `t`, not position, so it is computed once per step, not once per leaf.
   The 45-second recurrence went from 21% to 50% different, with the worst
   match now at the edge of the band rather than an interior dip.
2. **Gust envelope** rebuilt from 6 components (periods 47 / 31.6 / 19.8 /
   12.6 / 7.8 / 4.9 s), chosen by sweeping candidates for the one with no
   near-recurrence under 300 s. Its first genuine near-loop is at **377 s**.

End state: over a 200 s soak, the closest the whole system comes to repeating
at any lag from 5 to 60 s is **91% different**, against a band mean of 99% —
no dip anywhere, i.e. no period.

---

## 3. What I measured

`node --expose-gc harness.js` — **58 checks, 0 failures**. It extracts the
`<script>` from `demo.html` verbatim and runs the shipped code in a `vm` with
DOM stubs, driving the real rAF loop with controlled time.

| | measured |
|---|---|
| NaN/Inf over 12,000 frames | none, in any integrated field |
| Pool | 368 slots, `active+free==368` every frame, never reallocated |
| Heap over 30,000 further frames | **+10 KB** (gc forced) |
| Fate | 78.9% exit left, 21.1% settle and fade, 0.0% other edges |
| Reached the ground | **24.9%** at intensity 1.0, **75%** at 0.35, **90%** at 0 |
| Crossing height at mid-screen | p10 0.24 → p90 0.75, sd 0.19 |
| Lifetime | median 3.2 s, cv 0.34 |
| Duplicate paths | 0 / 244,650 pairs |
| Emission | x ∈ [0.723, 1.014], y ∈ [0.089, 0.658]; canopy-weighted 7.2:1 |
| Intensity 0 | 67 detachments/min, 7.7 leaves alive — a trickle, not frozen |
| Intensity ramp 0→1.2 | 330 events vs 324 predicted, **z = 0.32**; across 8 seeds mean z = −0.09 |
| 5 s frame stall | largest jump 0.029 of the frame |
| Resume | 0.009 displacement on the first frame (one frame's travel ≈ 0.01) |
| Reduced motion | rAF never scheduled, 0 leaves moved in 2.5 s |
| Physics cost | 0.33 ms/frame, 2 substeps |

**Real browser** (`browser_check.js`, `stress.js` — headless Chrome over CDP):

| | measured |
|---|---|
| Frame rate, 1440×900 / 390×844 / 2560×1440 | 119–120 fps, worst frame 10.2 ms |
| Population driven to | **302 live leaves** |
| **JS per frame at 302 leaves** | **0.30 ms** — 1.8% of a 16.7 ms budget |
| Marginal cost | **0.70 µs per leaf per frame** |
| Frame interval at 302 leaves | median 16.6 ms, p99 18.4 ms, **zero frames over 33 ms** |
| At 4× CPU throttle | JS 2.08 ms/frame — still fits 60 fps |
| DPR cap | dpr 3 device → backing store 585×1266, i.e. 1.5 |
| Settled leaves in the bottom-left corner | 2 |

The "whole main-thread task" figure is ~17 ms at 300 leaves, but that is Chrome
software-rasterising a full-screen canvas with `--disable-gpu`; the baseline at
**0 leaves is already 2.5 ms**, and the leaves themselves add 0.30 ms of JS.

**Flutter** was the hardest thing to measure honestly, and I got it wrong twice:

- First metric (vertical deviation from a trailing EMA) reported 1.73
  leaf-heights. Wrong — it was counting the landing bounce and the EMA's own
  lag.
- Second metric (deviation perpendicular to the path) reported 0.077
  leaf-widths and I nearly concluded the flutter was invisible. Also wrong:
  with wind dominating, the leaf's screen path is horizontal *and* lift is
  horizontal (it acts across `v_rel`, which is mostly the downward fall), so
  the perpendicular axis is the one axis that sees least of it.
- Third and correct: record real trajectories and smooth them with a **centred**
  (zero-lag) window *longer than the flutter period*. Measured **0.48
  leaf-widths** peak departure at intensity 1.0, **0.46** at 0.35, and — the
  control that matters — rerunning with lift forced to zero and nothing else
  changed drops it to 0.27 and 0.19. **Lift accounts for 1.8× to 2.4× the
  wobble**, and moves the ground fraction by 15–20 points.

`shots/paths.svg` / `paths.png` plots real trajectories with lift on and off.
At intensity 0.3 the difference is unmistakable: serpentine weaving with lift,
near-straight lines without.

---

## 4. Honest weaknesses

**The lift gain is the one number tuned to the eye, not derived.** Peak lift is
1.2–3.2× that leaf's mean drag. A rigid flat plate tops out near 1. At strict
plate values the flutter measured 0.08 leaf-widths — real but invisible,
because amplitude goes as `a/Ω²` and the lift reverses 4× per revolution. A
momiji leaf is lobed and cambered rather than a plate, so >1 is defensible, but
I chose the value because it looked right and I am not going to pretend
otherwise.

**Flutter washes out at high intensity.** At intensity 1 the wind carries a
leaf 0.55 widths/s while the flutter oscillates at ~1 s, so the weave is
stretched into a long shallow ripple. This is physically correct — a leaf in a
gale streaks, a leaf in still air flutters — and it means the *character*
changes across the intensity range rather than just the quantity. Whether that
is a feature depends on taste; I think it is.

**Fall lines converge on the bottom-left.** 33% of touchdowns land in the
leftmost tenth. This is geometry, not a bug: every leaf that has not landed or
exited keeps descending as it travels left, so trajectories pile toward that
corner. I tried the obvious lever — raising the boundary-layer floor from 0.07
to 0.13 — and it made things *worse* (38% in the leftmost tenth), because low
leaves then skate further left before sinking. Reverted. The lever that
actually works is the settle fade, now 0.28 s rest + 0.95 s dissolve with ±27%
per-leaf jitter, which holds the corner to ~2 settled leaves at any instant.

**In-plane orientation is a cheap approximation.** The drawn angle chases the
airflow heading with a saturating weight plus a free spin, rather than being a
real rigid-body rotation. It reads fine; it is not rigid-body dynamics.

**Determinism.** The PRNG is seeded with a constant, so every page load shows
the same sequence. Reproducible and testable, but if two visitors compare
screens at the same moment they would match. One line to seed from
`Date.now()`.

**No wake interaction.** Leaves do not see each other. At 300 leaves in a
hero this is unnoticeable and the alternative costs O(n²) or a spatial hash.

---

## 5. Tunables

Everything is in `CFG` at the top of the script. The ones worth turning:

| parameter | now | range | effect |
|---|---|---|---|
| `WIND_MAX` | 0.55 | 0.35–0.8 | crossing speed at intensity 1. Raise and the ground fraction drops. |
| `WIND_MIN` | 0.055 | 0.02–0.12 | the idle trickle. 0 is allowed and still not frozen — leaves fall. |
| `VTERM` | 0.175 | 0.12–0.25 | fall speed. **The main crosser/lander dial.** |
| `VTERM_SIGMA` | 0.34 | 0.2–0.5 | spread of leaf types. Lower = more uniform, less interesting. |
| `LIFT_LO/HI` | 1.2 / 3.2 | 0.8–4 | flutter amplitude. Above ~4 leaves start to look nervous. |
| `TUMBLE_K_LO/HI` | 4 / 14 | 3–20 | spin rate. **Raise and the flutter shrinks as 1/Ω²** — these two fight. |
| `TURB_MAX` | 0.185 | 0.1–0.28 | pocket and eddy strength; how much paths diverge. |
| `SPAWN_MAX` | 42 | 20–130 | population. 42 gives mean 140 / peak 263 at intensity 1.2. |
| `FADE_DELAY/DUR` | 0.28 / 0.95 | — | how much litter gathers at the bottom. |
| `SIZE_FRAC` | 0.046 | 0.03–0.06 | leaf size as a fraction of `sqrt(w·h)`. |
| `INTENSITY_TAU` | 0.85 s | 0.4–2 | how fast the knob responds. Below ~0.4 s the ramp becomes visible as a surge. |

### What I would tune next, in order

1. **Sit with the intensity slider on the real page.** Every number above was
   chosen against a black rectangle. With Fuji and the portrait behind, the
   right population and the right leaf size will both change, and `SIZE_FRAC`
   and `SPAWN_MAX` are the two I expect to move.
2. **A tuned curve for cursor proximity.** `setIntensity` is smoothed at 0.85 s,
   which suits scroll and idle. Cursor proximity to the tree will want a
   faster attack and a slower release than one symmetric time constant gives —
   that belongs in the caller, not in here.
3. **Reduce the count on narrow viewports.** Areal coverage is already
   constant, but a phone hero with a portrait in it may still want ~30% fewer
   leaves. One multiplier on the spawn rate keyed to `w`.
4. **Consider a slight upward bias in the eddy field near the canopy.** Real
   leaves lift off a branch before they fall. Right now they release and drop
   immediately; a small localised updraft on the tree's windward side would
   buy a beat of hesitation at the moment of detachment.

---

## 6. Integration

```js
window.leafSystem.setIntensity(v)   // 0..~1.2 (clamped 1.6); eased, cannot pop
window.leafSystem.getIntensity()    // the target last set
window.leafSystem.pause()           // stops rAF
window.leafSystem.resume()          // restarts with no time jump
window.leafSystem.count()           // leaves alive
```

`_internals` is test-only and not part of the contract.

To strip the scaffolding: delete `drawTree()` and its call, and the `#panel`
markup, CSS and its listeners. The canvas is already cleared rather than
filled, so it composites transparently over whatever sits behind it.

Files: `demo.html` (the deliverable, sheets alongside it), `harness.js`
(headless), `browser_check.js` + `stress.js` (CDP), `plot_paths.js`
(trajectory plots), `tune_gust.js` (the frequency sweep), `shots/`.
