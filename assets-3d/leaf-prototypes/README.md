# Leaf-wind prototypes

Three self-contained canvas demos of momiji leaves blowing off the tree, which
sits on the right of the hero. Each is a single HTML file — open it directly, no
build step. Each exposes `window.leafSystem.setIntensity(0..1.2)` plus
`getIntensity() / pause() / resume() / count()`.

## leaf_forces — **CHOSEN**

Ilias's pick, watched live. Honest physics: gravity, quadratic drag and lift all
act on velocity *relative to the air*, so a leaf at rest gets snatched by a gust
while a leaf already riding the wind tumbles lazily — same equation, both
behaviours.

The detail that earns it: lift reverses with the leaf's tumble phase, and that
same phase drives the sprite frame. So the leaf visibly *swims* — stalling
face-on, accelerating edge-on — instead of falling like a card. Whether a leaf
crosses the screen or lands emerges from one number per leaf (its terminal fall
speed), not from a scripted percentage.

Measured: ~79% exit left, ~21% settle and fade, 0.30 ms/frame at 302 leaves,
identical behaviour at 390 / 1440 / 2560 px wide.

This is the one to integrate.

## leaf_hybrid

Depth-first: every leaf gets a z, so distant ones are small, slow and dim while
near ones streak past. Prettiest in a still frame and the cheapest
(0.21 ms/frame), but the motion itself is simpler.

## leaf_paths

Analytic trajectories rather than simulation — total compositional control,
including a keep-clear zone around the portrait. Worth stealing that idea. Reads
too uniform overall: leaves everywhere rather than streaming off the tree.

## Note on judging

A screenshot cannot show motion. My own ranking put `leaf_hybrid` first on the
strength of stills; Ilias watched all three running and picked `leaf_forces`,
whose advantage is precisely the thing a still cannot capture. Judge animation
in motion.
