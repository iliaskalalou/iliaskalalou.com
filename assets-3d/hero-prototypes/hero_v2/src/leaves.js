/* ============================================================================
   MOMIJI LEAF SYSTEM — physics lifted verbatim from
     scratchpad/leaf_forces/demo.html
   and re-rendered in 3D.

   NOTHING in the integrator, the wind field, the Poisson detachment, the
   canopy lobes or the parameter table has been touched. What changed is the
   last step only: instead of ctx.drawImage into a 2D canvas, each leaf's
   normalised (u, v) is projected onto a plane at a REAL depth in the same
   world the tree stands in, and drawn as a camera-facing instanced quad.

   How the projection preserves the tuned look exactly
   ---------------------------------------------------
   The 2D system fakes depth with one factor `par` in [0.58, 1.30] that scales
   accel, wind, velocity and drawn size together. Here `par` instead chooses a
   real z:

        z(par) = lerp(Z_FAR, Z_NEAR, (par - PAR_LO) / (PAR_HI - PAR_LO))

   and the leaf's WORLD size is then set to

        S = pSize * (2 * REF * tan(fov/2) / H_px) * |z|

   The perspective divide multiplies that back by 1/|z|, so the leaf lands on
   screen at exactly pSize * REF pixels — the size the 2D system asked for —
   at any depth. Position is projected the same way from the camera's REST
   pose, so with the pointer at centre the composition is pixel-identical to
   the 2D system's, and any camera motion moves the leaves with correct
   parallax and correct occlusion against the tree, the portrait and the
   pagoda. That is the whole point of doing this in 3D.
   ============================================================================ */

/* ------------------------------------------------------------------ config */
export var CFG = {
  MAX_LEAVES: 368,
  SOFT_CAP:   330,

  FIXED_DT:     1 / 120,
  MAX_FRAME_DT: 0.05,
  MAX_SUBSTEPS: 8,

  INTENSITY_TAU: 0.85,
  WIND_MIN:  0.055,
  WIND_MAX:  0.55,
  WIND_EXP:  1.2,
  TURB_MIN:  0.030,
  TURB_MAX:  0.185,
  SPAWN_MIN: 1.15,
  SPAWN_MAX: 42.0,
  SPAWN_EXP: 1.25,
  SPAWN_GUST_A: 0.55,
  SPAWN_GUST_B: 0.62,

  GRAV:        0.50,
  GRAV_JIT:    0.20,
  VTERM:       0.175,
  VTERM_SIGMA: 0.34,
  VTERM_LO:    0.095,
  VTERM_HI:    0.340,
  CD_MIN:      0.25,
  LIFT_LO:     1.20,
  LIFT_HI:     3.20,

  TUMBLE_BASE_LO: 0.50,
  TUMBLE_BASE_HI: 2.60,
  TUMBLE_K_LO:    4.0,
  TUMBLE_K_HI:   14.0,
  TUMBLE_CAP:    16.0,

  PAR_LO: 0.58,
  PAR_HI: 1.30,

  SIZE_FRAC:  0.046,
  SIZE_VAR_LO: 0.72,
  SIZE_VAR_HI: 1.28,

  GROUND_LO:  0.885,
  GROUND_HI:  0.995,
  BOUNCE:     0.18,
  GROUND_FRIC: 0.55,
  SETTLE_CALM: 0.60,
  FADE_DELAY: 0.28,
  FADE_DUR:   0.95,
  FADE_JITTER: 0.55,

  EXIT_MARGIN: 0.07,
  ALIGN_REF:   0.10,
  ALIGN_RATE:  6.0
};

var TWO_PI = Math.PI * 2, HALF_PI = Math.PI * 0.5, INV_TWO_PI = 1 / TWO_PI;

var CD_MEAN = (1 + CFG.CD_MIN) * 0.5;
var CD_A = CFG.CD_MIN / CD_MEAN;
var CD_B = (1 - CFG.CD_MIN) / CD_MEAN;

/* ------------------------------------------------------------------ canopy */
var LOBES = [
  0.868, 0.300, 0.108, 0.190, 0.42,
  0.938, 0.442, 0.078, 0.170, 0.31,
  0.798, 0.198, 0.076, 0.112, 0.17,
  0.905, 0.585, 0.062, 0.075, 0.10
];
var LOBE_CDF = new Float64Array(LOBES.length / 5);
(function () {
  var acc = 0, i;
  for (i = 0; i < LOBE_CDF.length; i++) { acc += LOBES[i * 5 + 4]; LOBE_CDF[i] = acc; }
  for (i = 0; i < LOBE_CDF.length; i++) { LOBE_CDF[i] /= acc; }
})();

/* --------------------------------------------------------------- wind field */
var WAVES = new Float64Array([
   1.730,  2.310,  0.31700,  0.000,  0.34660,
   3.910,  2.870, -0.46910,  2.130,  0.09280,
   6.710,  5.330,  0.73310,  4.370,  0.02567,
  11.300,  9.130, -1.09370,  1.090,  0.00757
]);
var WMOD_DEPTH = new Float64Array([2.60, 2.10, 1.70, 1.30]);
var WMOD_RATE  = new Float64Array([0.05310, 0.07730, 0.11170, 0.14290]);
var WMOD_PHASE = new Float64Array([1.77, 4.03, 0.51, 2.99]);
var wavePhase  = new Float64Array(4);
var TURB_NORM = 0.72;

function updateWavePhases(t) {
  for (var i = 0, j = 0; i < 20; i += 5, j++) {
    wavePhase[j] = WAVES[i + 2] * t + WAVES[i + 3] +
                   WMOD_DEPTH[j] * Math.sin(WMOD_RATE[j] * t + WMOD_PHASE[j]);
  }
}

var windOutX = 0, windOutY = 0;

function groundProfile(v) {
  var d = (1 - v) * 6.6666667;
  var s = d <= 0 ? 0 : (d >= 1 ? 1 : d * d * (3 - 2 * d));
  return 0.07 + 0.93 * s * (0.82 + 0.30 * (1 - v));
}

function gustAt(t) {
  return 0.62 + 0.38 * (
    0.23 * Math.sin(0.13370 * t + 0.67) +
    0.21 * Math.sin(0.19910 * t + 1.31) +
    0.19 * Math.sin(0.31730 * t + 4.11) +
    0.15 * Math.sin(0.49870 * t + 2.23) +
    0.12 * Math.sin(0.80090 * t + 5.02) +
    0.10 * Math.sin(1.29310 * t + 3.44));
}

function sampleWind(u, v, t, meanU, turb) {
  var cx = 0, cy = 0, i, j, c;
  for (i = 0, j = 0; i < 20; i += 5, j++) {
    c = Math.cos(WAVES[i] * u + WAVES[i + 1] * v + wavePhase[j]) * WAVES[i + 4];
    cx += WAVES[i + 1] * c;
    cy -= WAVES[i] * c;
  }
  var prof = groundProfile(v);
  var tp = turb * TURB_NORM * prof;
  windOutX = -meanU * prof * gustNow + cx * tp;
  windOutY = cy * tp;
}

/* -------------------------------------------------------------------- prng */
var rngState = 0x8f1bbcdc;
function rnd() {
  rngState = (rngState + 0x6D2B79F5) | 0;
  var t = rngState;
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
function gauss() { return (rnd() + rnd() + rnd() - 1.5) * 2; }
function rrange(a, b) { return a + (b - a) * rnd(); }

/* ---------------------------------------------------------------- the pool */
var N = CFG.MAX_LEAVES;
var ST_FREE = 0, ST_FLY = 1, ST_SETTLE = 2;

export var pX      = new Float32Array(N);
export var pY      = new Float32Array(N);
var pVX     = new Float32Array(N);
var pVY     = new Float32Array(N);
export var pPhi    = new Float32Array(N);
export var pTheta  = new Float32Array(N);
var pK      = new Float32Array(N);
var pG      = new Float32Array(N);
var pLift   = new Float32Array(N);
var pTumbB  = new Float32Array(N);
var pTumbK  = new Float32Array(N);
var pTumbS  = new Float32Array(N);
var pSpin   = new Float32Array(N);
var pAlignO = new Float32Array(N);
export var pPar    = new Float32Array(N);
export var pSize   = new Float32Array(N);
export var pAlpha  = new Float32Array(N);
var pGround = new Float32Array(N);
var pSettle = new Float32Array(N);
var pFadeMul = new Float32Array(N);
var pAge    = new Float32Array(N);
export var pFlip   = new Int8Array(N);
export var pSheet  = new Uint8Array(N);
export var pBand   = new Uint8Array(N);
export var pState  = new Uint8Array(N);

var freeList = new Int32Array(N), freeCount = N;
export var activeIdx = new Int32Array(N);
export var activeCount = 0;
var slotAt = new Int32Array(N);
(function () { for (var i = 0; i < N; i++) { freeList[i] = i; pState[i] = ST_FREE; } })();
updateWavePhases(0);

var statSpawned = 0, statExitLeft = 0, statExitOther = 0, statLanded = 0, statLandFaded = 0;
var statAttempt = 0;

/* ------------------------------------------------------------------- state */
var simTime = 0;
var gustNow = 1;
var intensityTarget = 0.55, intensityEff = 0.55;
var meanU = 0, turbAmp = 0;
var spawnAccum = 0, spawnThreshold = 1;

/* ---------------------------------------------------------------- lifecycle */
function activate(i) { slotAt[i] = activeCount; activeIdx[activeCount++] = i; }
function deactivate(slot) {
  var i = activeIdx[slot];
  var last = activeIdx[--activeCount];
  activeIdx[slot] = last; slotAt[last] = slot;
  pState[i] = ST_FREE;
  freeList[freeCount++] = i;
}

function spawnLeaf() {
  if (freeCount === 0 || activeCount >= CFG.SOFT_CAP) return -1;
  var i = freeList[--freeCount];

  var bu = 0, bv = 0, bw = 1e9, c, r, a, li, u, v;
  for (c = 0; c < 2; c++) {
    r = rnd();
    for (li = 0; li < LOBE_CDF.length - 1; li++) { if (r < LOBE_CDF[li]) break; }
    a = rnd() * TWO_PI;
    r = Math.pow(rnd(), 0.62);
    u = LOBES[li * 5] + LOBES[li * 5 + 2] * r * Math.cos(a);
    v = LOBES[li * 5 + 1] + LOBES[li * 5 + 3] * r * Math.sin(a);
    if (u < 0.720) u = 0.720; else if (u > 1.020) u = 1.020;
    if (v < 0.060) v = 0.060; else if (v > 0.660) v = 0.660;
    sampleWind(u, v, simTime, meanU, turbAmp);
    if (windOutX < bw) { bw = windOutX; bu = u; bv = v; }
  }

  var d = 0.5 * (rnd() + rnd());
  var par = CFG.PAR_LO + (CFG.PAR_HI - CFG.PAR_LO) * d;

  var vt = CFG.VTERM * Math.exp(CFG.VTERM_SIGMA * gauss());
  if (vt < CFG.VTERM_LO) vt = CFG.VTERM_LO; else if (vt > CFG.VTERM_HI) vt = CFG.VTERM_HI;
  var g0 = CFG.GRAV * (1 - CFG.GRAV_JIT * 0.5 + CFG.GRAV_JIT * rnd());
  var k0 = g0 / (vt * vt);

  pX[i] = bu; pY[i] = bv;
  pVX[i] = (-0.05 * rnd() * meanU + 0.012 * gauss()) * par;
  pVY[i] = (0.010 + 0.020 * gauss()) * par;

  pK[i] = k0 / par;
  pG[i] = g0 * par;
  pPar[i] = par;
  pLift[i] = rrange(CFG.LIFT_LO, CFG.LIFT_HI);
  pTumbB[i] = rrange(CFG.TUMBLE_BASE_LO, CFG.TUMBLE_BASE_HI);
  pTumbK[i] = rrange(CFG.TUMBLE_K_LO, CFG.TUMBLE_K_HI);
  pTumbS[i] = rnd() < 0.5 ? -1 : 1;
  pSpin[i] = rrange(-1.6, 1.6);
  pAlignO[i] = gauss() * 0.5;
  pPhi[i] = rnd() * TWO_PI;
  pTheta[i] = rnd() * TWO_PI;
  pSize[i] = CFG.SIZE_FRAC * rrange(CFG.SIZE_VAR_LO, CFG.SIZE_VAR_HI) * par;
  pAlpha[i] = (0.42 + 0.58 * d) * rrange(0.80, 1.0);
  pGround[i] = CFG.GROUND_LO + (CFG.GROUND_HI - CFG.GROUND_LO) * d + 0.012 * (rnd() - 0.5);
  pFlip[i] = rnd() < 0.5 ? -1 : 1;
  pSheet[i] = (rnd() * 3) | 0;
  pBand[i] = d < 0.34 ? 0 : (d < 0.67 ? 1 : 2);
  pFadeMul[i] = 1 + CFG.FADE_JITTER * (rnd() - 0.5);
  pSettle[i] = 0; pAge[i] = 0;
  pState[i] = ST_FLY;

  activate(i);
  statSpawned++;
  return i;
}

/* --------------------------------------------------------------- integrator */
export function step(dt) {
  simTime += dt;
  gustNow = gustAt(simTime);
  updateWavePhases(simTime);

  intensityEff += (intensityTarget - intensityEff) * (1 - Math.exp(-dt / CFG.INTENSITY_TAU));
  var ip = Math.pow(intensityEff, CFG.WIND_EXP);
  meanU = CFG.WIND_MIN + (CFG.WIND_MAX - CFG.WIND_MIN) * ip;
  turbAmp = CFG.TURB_MIN + (CFG.TURB_MAX - CFG.TURB_MIN) * intensityEff;

  var rate = (CFG.SPAWN_MIN + CFG.SPAWN_MAX * Math.pow(intensityEff, CFG.SPAWN_EXP))
             * (CFG.SPAWN_GUST_A + CFG.SPAWN_GUST_B * gustNow);
  spawnAccum += rate * dt;
  while (spawnAccum >= spawnThreshold) {
    spawnAccum -= spawnThreshold;
    spawnThreshold = -Math.log(1 - rnd() * 0.999999);
    statAttempt++;
    spawnLeaf();
  }

  var margin = CFG.EXIT_MARGIN;
  for (var s = 0; s < activeCount; s++) {
    var i = activeIdx[s];
    var par = pPar[i], k = pK[i];
    var x = pX[i], y = pY[i], vx = pVX[i], vy = pVY[i];

    pAge[i] += dt;

    sampleWind(x, y, simTime, meanU, turbAmp);
    var wx = windOutX * par, wy = windOutY * par;

    var rvx = vx - wx, rvy = vy - wy;
    var spd = Math.sqrt(rvx * rvx + rvy * rvy);

    var settleMul = 1;
    if (pState[i] === ST_SETTLE) {
      settleMul = 1 - pSettle[i] / CFG.SETTLE_CALM;
      if (settleMul < 0) settleMul = 0;
    }
    var om = pTumbS[i] * (pTumbB[i] + pTumbK[i] * spd / par) * settleMul;
    if (om > CFG.TUMBLE_CAP) om = CFG.TUMBLE_CAP;
    else if (om < -CFG.TUMBLE_CAP) om = -CFG.TUMBLE_CAP;
    var phi = pPhi[i] + om * dt;
    if (phi > 1e6 || phi < -1e6) phi = phi % TWO_PI;
    pPhi[i] = phi;

    var psi = phi - HALF_PI;
    var sa = Math.sin(psi), ca = Math.cos(psi);
    var cd = CD_A + CD_B * sa * sa;
    var cl = pLift[i] * 2 * sa * ca * settleMul;

    var kd = k * spd;
    var ax = -kd * cd * rvx + kd * cl * (-rvy);
    var ay = -kd * cd * rvy + kd * cl * (rvx) + pG[i];

    vx += ax * dt; vy += ay * dt;
    x += vx * dt;  y += vy * dt;

    var align = spd / (spd + CFG.ALIGN_REF);
    var want = Math.atan2(rvy, rvx) + pAlignO[i];
    var dA = want - pTheta[i];
    dA -= TWO_PI * Math.floor((dA + Math.PI) * INV_TWO_PI);
    var f = CFG.ALIGN_RATE * align * dt;
    if (f > 1) f = 1;
    pTheta[i] += dA * f + pSpin[i] * (1 - 0.85 * align) * dt;

    var gy = pGround[i];
    if (y >= gy) {
      y = gy;
      if (vy > 0) vy = -vy * CFG.BOUNCE;
      vx *= Math.exp(-CFG.GROUND_FRIC * 12 * dt);
      if (pState[i] === ST_FLY) { pState[i] = ST_SETTLE; statLanded++; }
    }
    if (pState[i] === ST_SETTLE) pSettle[i] += dt;

    pX[i] = x; pY[i] = y; pVX[i] = vx; pVY[i] = vy;

    var dead = 0;
    if (x < -margin) { statExitLeft++; dead = 1; }
    else if (x > 1 + margin || y < -margin || y > 1 + margin) { statExitOther++; dead = 1; }
    else if (pState[i] === ST_SETTLE &&
             pSettle[i] > (CFG.FADE_DELAY + CFG.FADE_DUR) * pFadeMul[i]) {
      statLandFaded++; dead = 1;
    } else if (!(x === x) || !(y === y)) { dead = 1; }
    if (dead) { deactivate(s); s--; }
  }
}

/* -------------------------------------------------- alpha, incl. settle fade */
export function drawAlpha(i) {
  var a = pAlpha[i];
  if (pState[i] === 2) {
    var fm = pFadeMul[i];
    var ft = pSettle[i] - CFG.FADE_DELAY * fm;
    if (ft > 0) {
      var u = 1 - ft / (CFG.FADE_DUR * fm);
      if (u <= 0) return 0;
      a *= u * u * (3 - 2 * u);
    }
  }
  return a;
}

export function frameOf(i) {
  var f = pPhi[i] * INV_TWO_PI;
  f -= Math.floor(f);
  var fi = (f * 16) | 0;
  return fi > 15 ? 15 : fi;
}

export function getActiveCount() { return activeCount; }

export function setIntensity(v, immediate) {
  v = +v;
  if (!(v >= 0)) v = 0;
  if (v > 1.6) v = 1.6;
  intensityTarget = v;
  if (immediate) intensityEff = v;
}
export function getIntensity() { return intensityTarget; }

/* Static arrangement for prefers-reduced-motion: a handful of leaves parked
   along plausible drift lines, integrated zero times. */
export function staticFrame() {
  while (activeCount > 0) deactivate(0);
  simTime = 0; gustNow = 1; meanU = 0.30; turbAmp = 0.08;
  var NSTATIC = 15;
  for (var n = 0; n < NSTATIC; n++) {
    var i = spawnLeaf();
    if (i < 0) break;
    var t = (n + 0.5) / NSTATIC;
    pX[i] = 0.90 - 0.90 * Math.pow(t, 0.80) + 0.04 * gauss();
    pY[i] = pY[i] + (0.74 - pY[i]) * t * (0.30 + 0.6 * rnd());
    pPhi[i] = rnd() * TWO_PI;
    pTheta[i] = rnd() * TWO_PI;
  }
}

export function stats() {
  return { spawned: statSpawned, attempts: statAttempt, exitLeft: statExitLeft,
           exitOther: statExitOther, landed: statLanded, landFaded: statLandFaded,
           active: activeCount, free: freeCount, pool: N, simTime: simTime,
           meanU: meanU, turb: turbAmp, gust: gustNow };
}
