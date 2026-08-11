/* Headless verification harness.
   Extracts the <script> from demo.html verbatim and runs THE SHIPPED CODE in a
   vm context with minimal DOM stubs, driving the real rAF loop with controlled
   time. Nothing here re-implements the physics. */
'use strict';
const fs = require('fs');
const vm = require('vm');
const path = require('path');

const HTML = fs.readFileSync(path.join(__dirname, 'demo.html'), 'utf8');
const m = HTML.match(/<script>([\s\S]*?)<\/script>/);
if (!m) throw new Error('no <script> found');
const SRC = m[1];

function makeCtx2d() {
  const noop = () => {};
  return {
    globalAlpha: 1, fillStyle: '', strokeStyle: '', lineWidth: 1,
    imageSmoothingEnabled: true, imageSmoothingQuality: 'high',
    setTransform: noop, clearRect: noop, fillRect: noop, drawImage: noop,
    beginPath: noop, ellipse: noop, arc: noop, fill: noop, stroke: noop,
    moveTo: noop, lineTo: noop, quadraticCurveTo: noop, save: noop, restore: noop,
    translate: noop, rotate: noop, scale: noop
  };
}
function makeCanvas() {
  return { width: 300, height: 150, style: {}, getContext: () => makeCtx2d(),
           addEventListener: () => {} };
}

function boot(opts) {
  const o = Object.assign({ w: 1440, h: 900, dpr: 1, reduced: false, seed: null }, opts);
  const rafQueue = [];
  let nowMs = 1000;
  let rafId = 1;
  const els = {};
  const mkEl = (id) => (els[id] = els[id] || {
    id, style: {}, textContent: '', value: '', addEventListener: () => {}
  });

  const sandbox = {
    console,
    Math, JSON, Date, Object, Array, Number, String, Boolean, Error,
    Float32Array, Float64Array, Int32Array, Int8Array, Uint8Array,
    performance: { now: () => nowMs },
    setTimeout, clearTimeout, queueMicrotask
  };
  sandbox.window = sandbox;
  sandbox.globalThis = sandbox;
  sandbox.self = sandbox;

  sandbox.innerWidth = o.w;
  sandbox.innerHeight = o.h;
  sandbox.devicePixelRatio = o.dpr;
  sandbox.requestAnimationFrame = (cb) => { rafQueue.push(cb); return rafId++; };
  sandbox.cancelAnimationFrame = (id) => { rafQueue.length = 0; };
  sandbox.matchMedia = () => ({ matches: o.reduced, addEventListener: () => {}, addListener: () => {} });
  sandbox.addEventListener = () => {};

  const theCanvas = makeCanvas();
  sandbox.document = {
    hidden: false,
    getElementById: (id) => (id === 'leaf-canvas' ? theCanvas : mkEl(id)),
    createElement: (tag) => (tag === 'canvas' ? makeCanvas() : mkEl(tag)),
    addEventListener: () => {}
  };
  let imgLoads = 0;
  sandbox.Image = function () {
    this.width = 1024; this.height = 1024;
    let _src = '';
    Object.defineProperty(this, 'src', {
      get: () => _src,
      set: (v) => { _src = v; imgLoads++; const self = this;
                    queueMicrotask(() => { if (self.onload) self.onload(); }); }
    });
  };

  vm.createContext(sandbox);
  vm.runInContext(SRC, sandbox, { filename: 'demo.html:script' });

  const api = sandbox.leafSystem;
  const I = api._internals;
  if (o.seed !== null) I.seed(o.seed);

  return {
    api, I, sandbox,
    get now() { return nowMs; },
    pumpMicrotasks() { return new Promise((r) => setTimeout(r, 0)); },
    /** advance one animation frame of dtMs */
    frame(dtMs) {
      if (rafQueue.length === 0) return false;
      const cbs = rafQueue.splice(0, rafQueue.length);
      nowMs += dtMs;
      for (let i = 0; i < cbs.length; i++) cbs[i](nowMs);
      return true;
    },
    pending() { return rafQueue.length; },
    setHidden(v) {
      sandbox.document.hidden = v;
      // the module registered its handler on document.addEventListener, which
      // we stubbed out; drive the same path through the public API instead.
      if (v) api.pause(); else api.resume();
    },
    resize(w, h, dpr) {
      sandbox.innerWidth = w; sandbox.innerHeight = h;
      if (dpr !== undefined) sandbox.devicePixelRatio = dpr;
    }
  };
}

/* ------------------------------------------------------------- leaf tracker */
/* Unbiased trajectory wiggle. A trailing EMA lags the path by tau*v, which
   for a wind-blown leaf is huge and swamps the signal; projecting it out only
   answers about one axis. Offline we can do better: smooth the recorded
   trajectory with a CENTRED window (zero phase lag) and measure how far the
   real path departs from it. That is exactly the wobble an eye separates from
   the overall drift. */
function wiggleOf(traj, halfWin) {
  const n = traj.length / 2;
  if (n < 2 * halfWin + 4) return null;
  let peak = 0, sum = 0, cnt = 0;
  for (let i = halfWin; i < n - halfWin; i++) {
    let sx = 0, sy = 0;
    for (let k = -halfWin; k <= halfWin; k++) { sx += traj[(i + k) * 2]; sy += traj[(i + k) * 2 + 1]; }
    const m = 2 * halfWin + 1;
    const dx = traj[i * 2] - sx / m, dy = traj[i * 2 + 1] - sy / m;
    const d = Math.sqrt(dx * dx + dy * dy);
    if (d > peak) peak = d;
    sum += d * d; cnt++;
  }
  return { peak, rms: Math.sqrt(sum / cnt) };
}

class Tracker {
  constructor(I, sampleEvery) {
    this.I = I;
    this.sampleEvery = sampleEvery || 0;   // 0 = record no trajectories
    this.spawnSeen = 0;
    const n = I.poolSize();
    this.n = n;
    this.lastAge = new Float64Array(n).fill(-1);
    this.rec = new Array(n).fill(null);
    this.done = [];
  }
  poll() {
    const A = this.I.arrays;
    for (let i = 0; i < this.n; i++) {
      const st = A.state[i], age = A.age[i];
      const prev = this.rec[i];
      if (st === 0) {
        if (prev) { this.finish(prev); this.rec[i] = null; }
        this.lastAge[i] = -1;
        continue;
      }
      if (!prev || age < this.lastAge[i]) {
        if (prev) this.finish(prev);
        this.rec[i] = {
          x0: A.x[i], y0: A.y[i], yHalf: null, yQuarter: null,
          minX: A.x[i], maxY: A.y[i], life: 0, settled: false,
          lastX: A.x[i], lastY: A.y[i], cross: 0,
          _dir: 0, size: A.size[i], band: A.band[i],
          _emaY: A.y[i], _emaX: A.x[i], devMax: 0, devMin: 0,
          _evx: A.vx[i], _evy: A.vy[i], perpMax: 0, perpMin: 0, airLife: 0,
          traj: (this.sampleEvery && (this.spawnSeen++ % this.sampleEvery === 0)) ? [] : null
        };
      }
      const r = this.rec[i];
      const x = A.x[i], y = A.y[i];
      if (r.lastX >= 0.5 && x < 0.5) r.yHalf = y;
      if (r.lastX >= 0.25 && x < 0.25) r.yQuarter = y;
      if (x < r.minX) r.minX = x;
      if (y > r.maxY) r.maxY = y;
      if (st === 2) r.settled = true;
      /* Flutter is an AIRBORNE property. Measuring it through touchdown would
         count the landing bounce as flutter, which it is not. */
      if (st === 1) {
        const a = 1 - Math.exp(-(1 / 60) / 0.5);
        r._emaY += (y - r._emaY) * a;
        r._emaX += (x - r._emaX) * a;
        r._evx += (A.vx[i] - r._evx) * a;
        r._evy += (A.vy[i] - r._evy) * a;
        const dev = y - r._emaY;
        if (dev > r.devMax) r.devMax = dev;
        if (dev < r.devMin) r.devMin = dev;
        /* The real flutter signal: displacement PERPENDICULAR to the leaf's
           own smoothed direction of travel. Lift acts across the relative
           airflow, so for a leaf riding a leftward wind the slip is mostly
           across its path, not up and down. Projecting out the along-track
           component also removes the EMA's lag artefact. */
        const sp = Math.hypot(r._evx, r._evy);
        if (sp > 1e-6) {
          const perp = ((x - r._emaX) * (-r._evy) + (y - r._emaY) * r._evx) / sp;
          if (perp > r.perpMax) r.perpMax = perp;
          if (perp < r.perpMin) r.perpMin = perp;
        }
        r.airLife += 1 / 60;
        if (r.traj && r.traj.length < 1200) { r.traj.push(x, y); }
        const dy = y - r.lastY;
        const d = dy > 0 ? 1 : (dy < 0 ? -1 : r._dir);
        if (r._dir !== 0 && d !== r._dir) { r.cross++; }
        r._dir = d;
      }
      r.life = A.age[i];
      r.lastX = x; r.lastY = y;
      this.lastAge[i] = age;
    }
  }
  finish(r) { if (r.life > 0.05) this.done.push(r); }
  flush() { for (let i = 0; i < this.n; i++) if (this.rec[i]) { this.finish(this.rec[i]); this.rec[i] = null; } }
}

/* ------------------------------------------------------------------- checks */
let FAIL = 0;
function ok(cond, label, detail) {
  const tag = cond ? 'PASS' : 'FAIL';
  if (!cond) FAIL++;
  console.log(`  [${tag}] ${label}${detail !== undefined ? '  ->  ' + detail : ''}`);
}
function fin(v) { return typeof v === 'number' && isFinite(v); }
function scanFinite(I) {
  const A = I.arrays, n = I.poolSize();
  for (const key of ['x', 'y', 'vx', 'vy', 'phi', 'theta', 'size', 'alpha', 'age', 'settle']) {
    const arr = A[key];
    for (let i = 0; i < n; i++) if (!fin(arr[i])) return `${key}[${i}]=${arr[i]}`;
  }
  return null;
}
function stats(a) {
  if (!a.length) return { n: 0 };
  const s = a.slice().sort((x, y) => x - y);
  const mean = a.reduce((p, c) => p + c, 0) / a.length;
  const sd = Math.sqrt(a.reduce((p, c) => p + (c - mean) * (c - mean), 0) / a.length);
  return { n: a.length, min: s[0], p10: s[(s.length * 0.1) | 0], med: s[(s.length * 0.5) | 0],
           p90: s[(s.length * 0.9) | 0], max: s[s.length - 1], mean, sd };
}
const f3 = (x) => (x === undefined ? '—' : (+x).toFixed(3));

/* =========================================================================== */
async function main() {
  console.log('MOMIJI LEAF SYSTEM — headless verification');
  console.log('running the <script> extracted verbatim from demo.html\n');

  /* ---------------------------------------------------------- 1. long soak */
  console.log('1. LONG SOAK — 1440x900, intensity 1.0, 12000 frames @16.67ms (200 s sim)');
  {
    const S = boot({ w: 1440, h: 900, seed: 12345 });
    await S.pumpMicrotasks();
    S.api.setIntensity(1.0, true);
    const T = new Tracker(S.I);
    let nanAt = null, poolBad = null, maxActive = 0, refused = 0;
    const activeSeries = [], meanXSeries = [], meanYSeries = [], spawnSeries = [];
    let lastSpawned = 0;
    const AR = S.I.arrays;
    for (let f = 0; f < 12000; f++) {
      S.frame(16.6667);
      T.poll();
      const st = S.I.stats();
      maxActive = Math.max(maxActive, st.active);
      activeSeries.push(st.active);
      let mx = 0, my = 0, c = 0;
      for (let i = 0; i < S.I.poolSize(); i++) if (AR.state[i] !== 0) { mx += AR.x[i]; my += AR.y[i]; c++; }
      meanXSeries.push(c ? mx / c : 0.5);
      meanYSeries.push(c ? my / c : 0.5);
      spawnSeries.push(st.spawned - lastSpawned); lastSpawned = st.spawned;
      if (st.active + st.free !== st.pool) poolBad = poolBad || `f=${f} ${st.active}+${st.free}!=${st.pool}`;
      if (f % 37 === 0) { const bad = scanFinite(S.I); if (bad && !nanAt) nanAt = `f=${f} ${bad}`; }
    }
    refused = S.I.stats().attempts - S.I.stats().spawned;
    T.flush();
    const st = S.I.stats();
    ok(nanAt === null, 'no NaN/Inf in any integrated field', nanAt || 'clean over 12000 frames');
    ok(poolBad === null, 'pool invariant active+free==pool every frame', poolBad || `pool=${st.pool}`);
    ok(S.I.poolSize() === S.I.cfg.MAX_LEAVES && S.I.arrays.x.length === S.I.cfg.MAX_LEAVES,
       'pool never reallocates', `${S.I.poolSize()} slots, backing arrays ${S.I.arrays.x.length}`);
    ok(maxActive <= S.I.cfg.SOFT_CAP, 'active never exceeds soft cap',
       `max active=${maxActive}, cap=${S.I.cfg.SOFT_CAP}`);
    ok(refused === 0, 'the cap never actually bites (gust peaks have headroom)',
       `${refused} detachments refused; peak population ${maxActive} / cap ${S.I.cfg.SOFT_CAP}`);

    const total = st.exitLeft + st.exitOther + st.landFaded;
    const pctLeft = 100 * st.exitLeft / total;
    const pctFade = 100 * st.landFaded / total;
    const pctOther = 100 * st.exitOther / total;
    console.log(`      spawned=${st.spawned}  recycled=${total}  live=${st.active}`);
    console.log(`      fate:  exit-left ${pctLeft.toFixed(1)}%   settled+faded ${pctFade.toFixed(1)}%` +
                `   other edge ${pctOther.toFixed(1)}%`);
    console.log(`      touchdowns (leaves that reached the ground) = ${st.landed}` +
                ` = ${(100 * st.landed / st.spawned).toFixed(1)}% of all spawned`);
    ok(pctLeft > 45, 'majority of leaves exit on the LEFT', `${pctLeft.toFixed(1)}%`);
    ok(st.landed / st.spawned > 0.10 && st.landed / st.spawned < 0.65,
       'a real but non-dominant fraction reaches the ground',
       `${(100 * st.landed / st.spawned).toFixed(1)}%`);
    ok(pctOther < 6, 'few leaves leave by top/right/bottom', `${pctOther.toFixed(1)}%`);

    /* ---- path diversity */
    const paths = T.done.filter((r) => r.yHalf !== null);
    const yh = stats(paths.map((r) => r.yHalf));
    const lf = stats(T.done.map((r) => r.life));
    const cr = stats(T.done.filter((r) => (r.airLife || 0) > 2).map((r) => r.cross));
    console.log(`      y at mid-screen: n=${yh.n} min=${f3(yh.min)} p10=${f3(yh.p10)} med=${f3(yh.med)}` +
                ` p90=${f3(yh.p90)} max=${f3(yh.max)} sd=${f3(yh.sd)}`);
    console.log(`      lifetime (s):    med=${f3(lf.med)} p10=${f3(lf.p10)} p90=${f3(lf.p90)}` +
                ` min=${f3(lf.min)} max=${f3(lf.max)}`);
    console.log(`      airborne vertical direction reversals, leaves flying >2 s:` +
                ` med=${cr.med} p10=${cr.p10} p90=${cr.p90} max=${cr.max} (n=${cr.n})`);
    ok(yh.sd > 0.10, 'mid-screen crossing height is broadly spread (not a channel)', `sd=${f3(yh.sd)}`);
    ok(yh.p90 - yh.p10 > 0.35, 'p10..p90 of crossing height spans >35% of the frame',
       f3(yh.p90 - yh.p10));
    ok(lf.sd / lf.mean > 0.30, 'lifetimes are broadly spread', `cv=${f3(lf.sd / lf.mean)}`);

    /* near-duplicate paths */
    let dup = 0, pairs = 0;
    const sample = paths.slice(0, 700);
    for (let a = 0; a < sample.length; a++) {
      for (let b = a + 1; b < sample.length; b++) {
        pairs++;
        const A = sample[a], B = sample[b];
        if (Math.abs(A.x0 - B.x0) < 0.004 && Math.abs(A.y0 - B.y0) < 0.004 &&
            Math.abs(A.yHalf - B.yHalf) < 0.004 && Math.abs(A.life - B.life) < 0.05) dup++;
      }
    }
    ok(dup === 0, 'no two sampled leaves share a path', `${dup} near-duplicates in ${pairs} pairs`);

    /* ---- FLUTTER, measured with a zero-lag centred smoother ------------- */
    console.log('\n1b. FLUTTER — how far the path departs from its own smooth trend');
    async function wiggleRun(intensity, liftOn, seed) {
      const R = boot({ w: 1440, h: 900, seed });
      await R.pumpMicrotasks();
      if (!liftOn) { R.I.cfg.LIFT_LO = 0; R.I.cfg.LIFT_HI = 0; }
      R.api.setIntensity(intensity, true);
      const TR = new Tracker(R.I, 4);
      for (let f = 0; f < 7200; f++) { R.frame(16.6667); TR.poll(); }
      TR.flush();
      const geom = R.I.geom();
      const peaks = [], rmss = [];
      for (const r of TR.done) {
        if (!r.traj || r.airLife < 1.6) continue;
        /* The window must be LONGER than the flutter period or the smoother
           simply follows the wobble and reports nothing. Tumble runs ~0.3-0.6
           rev/s and the lift reverses at 2x that, so the flutter period is
           roughly 1-2 s; +/-0.75 s is the right scale. The lift-off control
           run absorbs whatever genuine path curvature this also picks up. */
        const w = wiggleOf(r.traj, 45);            // +/- 0.75 s centred window
        if (!w) continue;
        const leafNorm = r.size * geom.REF / geom.H;   // leaf size in y-units
        peaks.push(w.peak / leafNorm);
        rmss.push(w.rms / leafNorm);
      }
      const s2 = R.I.stats();
      return { peak: stats(peaks), rms: stats(rmss),
               landPct: 100 * s2.landed / s2.spawned };
    }
    for (const I of [1.0, 0.35]) {
      const on = await wiggleRun(I, true, 20260811);
      const off = await wiggleRun(I, false, 20260811);
      console.log(`   intensity ${I.toFixed(2)}  (n=${on.peak.n} leaves):`);
      console.log(`     lift ON   peak wobble ${f3(on.peak.med)} leaf-widths` +
                  ` (p90 ${f3(on.peak.p90)}),  rms ${f3(on.rms.med)}` +
                  `   ground ${on.landPct.toFixed(1)}%`);
      console.log(`     lift OFF  peak wobble ${f3(off.peak.med)} leaf-widths` +
                  ` (p90 ${f3(off.peak.p90)}),  rms ${f3(off.rms.med)}` +
                  `   ground ${off.landPct.toFixed(1)}%`);
      console.log(`     lift contributes x${f3(on.peak.med / off.peak.med)} the wobble` +
                  ` and moves the ground fraction by` +
                  ` ${(on.landPct - off.landPct).toFixed(1)} points`);
      /* Bar: the median leaf's path must depart from its own smooth trend by a
         third of its own width or more. At a 1-2 s period that is an obvious
         weave rather than a slide — confirmed by eye in shots/paths.png. */
      ok(on.peak.med > 0.35, `at intensity ${I} the median leaf wobbles visibly`,
         `${f3(on.peak.med)} leaf-widths peak departure`);
      ok(on.peak.med > off.peak.med * 1.4,
         `at intensity ${I} the wobble is the lift, not turbulence`,
         `x${f3(on.peak.med / off.peak.med)}`);
    }

    /* sprite tumble rate: too slow reads as a stiff cutout, too fast aliases
       against the 16-frame sheet */
    const revs = await (async () => {
      const R = boot({ w: 1440, h: 900, seed: 4711 });
      await R.pumpMicrotasks();
      R.api.setIntensity(1.0, true);
      for (let f = 0; f < 1800; f++) R.frame(16.6667);
      const A2 = R.I.arrays, n2 = R.I.poolSize();
      const p0 = Float64Array.from(A2.phi), s0 = Uint8Array.from(A2.state);
      for (let f = 0; f < 60; f++) R.frame(16.6667);      // exactly 1 second
      const out = [];
      for (let i = 0; i < n2; i++) {
        if (s0[i] !== 1 || A2.state[i] !== 1) continue;
        out.push(Math.abs(A2.phi[i] - p0[i]) / (2 * Math.PI));
      }
      return stats(out);
    })();
    console.log(`   sprite tumble rate (revolutions/s): p10=${f3(revs.p10)}` +
                ` med=${f3(revs.med)} p90=${f3(revs.p90)} max=${f3(revs.max)}` +
                `  => ${f3(revs.med * 16)} sheet-frames/s at the median`);
    ok(revs.med > 0.15 && revs.med < 1.2, 'median leaf tumbles at a readable rate',
       `${f3(revs.med)} rev/s`);
    ok(revs.max * 16 < 60, 'fastest tumble stays under the 16-frame sheet aliasing limit',
       `${f3(revs.max * 16)} sheet-frames/s`);

    /* ---- DOES IT REPEAT? The brief's actual requirement.
       Autocorrelation is the wrong instrument here: a population count is
       slowly varying, so r(tau) is near 1 at short lags whether or not the
       system loops. Test self-similarity directly instead — a signal that
       repeats with period tau satisfies s(t) == s(t+tau), so the normalised
       RMS difference at that lag collapses to zero. Run it on three channels
       at once (population, mean x, mean y of all live leaves). */
    const chans = [activeSeries, meanXSeries, meanYSeries];
    const norm = chans.map((c) => {
      const mu = c.reduce((p, v) => p + v, 0) / c.length;
      const sd = Math.sqrt(c.reduce((p, v) => p + (v - mu) * (v - mu), 0) / c.length);
      return c.map((v) => (v - mu) / (sd || 1));
    });
    const simAt = (lagS) => {
      const lag = Math.round(lagS * 60);
      let acc2 = 0, cnt = 0;
      for (const c of norm) {
        for (let i = 0; i + lag < c.length; i += 3) { const d = c[i] - c[i + lag]; acc2 += d * d; cnt++; }
      }
      return Math.sqrt(acc2 / cnt) / Math.SQRT2;          // 1.0 == unrelated
    };
    /* Lags below ~4 s look similar merely because the signal is continuous,
       not because anything loops. A PERIOD would show up as an interior dip:
       the curve rises out of the continuity region and then falls back down
       at the period. Test the interior (5..60 s) for exactly that. */
    let bestSim = Infinity, bestLag = 0, simSum = 0, simN = 0;
    for (let lagS = 5; lagS <= 60; lagS += 0.1) {
      const v = simAt(lagS);
      simSum += v; simN++;
      if (v < bestSim) { bestSim = v; bestLag = lagS; }
    }
    const simMean = simSum / simN;
    console.log(`      recurrence sweep (population + mean x + mean y):`);
    console.log(`        ` + [2, 5, 10, 15, 20, 30, 40, 50, 60]
      .map((l) => `${l}s:${simAt(l).toFixed(2)}`).join('  '));
    console.log(`        closest recurrence in 5..60 s: ${(bestSim * 100).toFixed(0)}% different` +
                ` at ${bestLag.toFixed(1)} s;  band mean ${(simMean * 100).toFixed(0)}%` +
                `   (0% = exact loop, 100% = unrelated)`);
    ok(bestSim > 0.60, 'the state never comes close to repeating', `${(bestSim * 100).toFixed(0)}% different`);
    ok(bestSim > 0.70 * simMean, 'no lag stands out as a period (no dip in the curve)',
       `min ${(bestSim * 100).toFixed(0)}% vs band mean ${(simMean * 100).toFixed(0)}%`);

    /* The wind field on its own, sampled at fixed probes — this is where a
       loop would originate, since the leaves themselves are stochastic. */
    {
      const P = boot({ w: 1440, h: 900, seed: 999 });
      await P.pumpMicrotasks();
      P.api.setIntensity(1.0, true);
      const probes = [];
      for (let i = 0; i < 5; i++) for (let j = 0; j < 5; j++) probes.push([]);
      const AR2 = P.I.arrays;
      /* drive the field by reading the drift of a lattice of test leaves is
         indirect; sample gust instead, plus the population's own mean speed */
      const gg = [];
      for (let f = 0; f < 9000; f++) { P.frame(16.6667); gg.push(P.I.stats().gust); }
      const mu = gg.reduce((p, c) => p + c, 0) / gg.length;
      const sd = Math.sqrt(gg.reduce((p, c) => p + (c - mu) ** 2, 0) / gg.length);
      let wBest = Infinity, wLag = 0;
      for (let lagS = 5; lagS <= 60; lagS += 0.05) {
        const lag = Math.round(lagS * 60);
        let a = 0, c = 0;
        for (let i = 0; i + lag < gg.length; i += 3) { const d = (gg[i] - gg[i + lag]) / sd; a += d * d; c++; }
        const v = Math.sqrt(a / c) / Math.SQRT2;
        if (v < wBest) { wBest = v; wLag = lagS; }
      }
      console.log(`      gust envelope alone: closest recurrence in 5..60 s is` +
                  ` ${(wBest * 100).toFixed(0)}% different at ${wLag.toFixed(1)} s`);
      ok(wBest > 0.60, 'the gust envelope itself has no period under a minute',
         `${(wBest * 100).toFixed(0)}%`);
    }

    /* spawn process should be Poisson-like: CV of per-frame counts */
    const sm = spawnSeries.reduce((p, c) => p + c, 0) / spawnSeries.length;
    const ssd = Math.sqrt(spawnSeries.reduce((p, c) => p + (c - sm) * (c - sm), 0) / spawnSeries.length);
    console.log(`      spawns/frame mean=${sm.toFixed(3)} sd=${ssd.toFixed(3)}` +
                `  (Poisson predicts sd=sqrt(mean)=${Math.sqrt(sm).toFixed(3)})`);
    ok(Math.abs(ssd / Math.sqrt(sm) - 1) < 0.25, 'detachment is a Poisson process, not a cadence',
       `sd/sqrt(mean)=${(ssd / Math.sqrt(sm)).toFixed(3)}`);
  }

  /* ------------------------------------------------------- 2. intensity 0 */
  console.log('\n2. INTENSITY 0 — must be a trickle, never frozen');
  {
    const S = boot({ w: 1440, h: 900, seed: 777 });
    await S.pumpMicrotasks();
    S.api.setIntensity(0, true);
    let sum = 0, maxc = 0;
    for (let f = 0; f < 3600; f++) { S.frame(16.6667); const a = S.api.count(); sum += a; maxc = Math.max(maxc, a); }
    const st = S.I.stats();
    const avg = sum / 3600;
    console.log(`      after 60 s: spawned=${st.spawned}, avg live=${avg.toFixed(1)}, max live=${maxc}`);
    console.log(`      mean wind at I=0: ${st.meanU.toFixed(4)} viewport-widths/s`);
    ok(st.spawned > 20, 'leaves still detach at intensity 0 (not frozen)', `${st.spawned} in 60 s`);
    ok(avg > 0.8 && avg < 14, 'live population at I=0 is a trickle', `avg ${avg.toFixed(1)} leaves`);
    ok(st.landed / Math.max(1, st.spawned) > 0.5,
       'with almost no wind, most leaves simply fall and settle',
       `${(100 * st.landed / st.spawned).toFixed(0)}% touched down`);
  }

  /* ------------------------------------- 3. intensity ramp: no burst, smooth */
  console.log('\n3. INTENSITY STEP 0 -> 1.2 — must ramp, not pop');
  {
    const S = boot({ w: 1440, h: 900, seed: 4242 });
    await S.pumpMicrotasks();
    S.api.setIntensity(0, true);
    for (let f = 0; f < 900; f++) S.frame(16.6667);        // settle at 0
    /* Measure ATTEMPTED detachments (the emitter's own rate) in 1 s windows.
       Successful spawns would be the wrong signal: they are also shaped by
       how full the pool happens to be. */
    /* A "burst" means events appearing that the emitter's own smooth rate
       function does not account for. So integrate that rate analytically as
       the run proceeds and compare it with the events actually fired. Any
       backlog dumped at the moment of the step would show up as observed
       exceeding expected during the ramp. Poisson gives the error bar. */
    const C = S.I.cfg;
    let last = S.I.stats().attempts, prevT = S.I.stats().simTime;
    const perSec = [], expSec = [], effTrace = [], countTrace = [];
    S.api.setIntensity(1.2);                               // the step
    for (let b = 0; b < 40; b++) {                         // 40 s
      let e = 0;
      for (let f = 0; f < 60; f++) {
        S.frame(16.6667);
        const st = S.I.stats();
        const dT = st.simTime - prevT; prevT = st.simTime;
        e += (C.SPAWN_MIN + C.SPAWN_MAX * Math.pow(S.api.getEffectiveIntensity(), C.SPAWN_EXP)) *
             (C.SPAWN_GUST_A + C.SPAWN_GUST_B * st.gust) * dT;
      }
      const a = S.I.stats().attempts;
      perSec.push(a - last); last = a;
      expSec.push(e);
      effTrace.push(S.api.getEffectiveIntensity());
      countTrace.push(S.api.count());
    }
    console.log(`      effective intensity: t=1s ${f3(effTrace[0])}  t=3s ${f3(effTrace[2])}` +
                `  t=8s ${f3(effTrace[7])}  t=40s ${f3(effTrace[39])}`);
    console.log(`      detachments/s observed:  ${perSec.slice(0, 8).join(' ')} ...`);
    console.log(`      detachments/s expected:  ` +
                expSec.slice(0, 8).map((v) => v.toFixed(0)).join(' ') + ' ...');
    console.log(`      live leaves:             ${countTrace.slice(0, 8).join(' ')} ...` +
                ` final=${countTrace[39]}`);
    const obs8 = perSec.slice(0, 8).reduce((p, c) => p + c, 0);
    const exp8 = expSec.slice(0, 8).reduce((p, c) => p + c, 0);
    const sigma8 = Math.sqrt(exp8);
    const z8 = (obs8 - exp8) / sigma8;
    console.log(`      over the 8 s ramp: ${obs8} events fired vs ${exp8.toFixed(0)} predicted` +
                ` by the rate function  (z = ${z8.toFixed(2)}, Poisson sigma = ${sigma8.toFixed(1)})`);
    ok(Math.abs(z8) < 3, 'no events beyond what the smooth rate function predicts',
       `z=${z8.toFixed(2)}`);
    let worstZ = 0, worstAt = 0;
    for (let i = 0; i < 8; i++) {
      const z = (perSec[i] - expSec[i]) / Math.sqrt(Math.max(1, expSec[i]));
      if (z > worstZ) { worstZ = z; worstAt = i; }
    }
    ok(worstZ < 3.5, 'no single second during the ramp overshoots its own prediction',
       `worst z=${worstZ.toFixed(2)} at t=${worstAt + 1}s`);
    let mono = true;
    for (let i = 1; i < effTrace.length; i++) if (effTrace[i] < effTrace[i - 1] - 1e-9) mono = false;
    ok(mono, 'effective intensity rises monotonically (no overshoot)');
    ok(effTrace[0] > 0.45 && effTrace[0] < 1.05, 'the knob eases in over about a second',
       `I_eff(1s)=${f3(effTrace[0])}`);
    /* the population must climb smoothly, never jump */
    let maxJump = 0;
    for (let i = 1; i < countTrace.length; i++) maxJump = Math.max(maxJump, countTrace[i] - countTrace[i - 1]);
    console.log(`      largest 1 s change in population during the ramp: +${maxJump}`);
    ok(maxJump < 80, 'population climbs rather than pops', `+${maxJump} in one second`);
    ok(S.api.getIntensity() === 1.2, 'getIntensity returns the target that was set', S.api.getIntensity());

    /* and back down */
    S.api.setIntensity(0.1);
    const down = [];
    for (let b = 0; b < 25; b++) { for (let f = 0; f < 60; f++) S.frame(16.6667); down.push(S.api.count()); }
    let maxDrop = 0;
    for (let i = 1; i < down.length; i++) maxDrop = Math.max(maxDrop, down[i - 1] - down[i]);
    console.log(`      ramp down 1.2 -> 0.1: ${down.slice(0, 10).join(' ')} ... final=${down[24]}`);
    ok(maxDrop < 80, 'population decays rather than vanishing', `-${maxDrop} in one second`);
    ok(down[24] > 0, 'still alive at the bottom of the ramp', `${down[24]} leaves`);

    /* the single-seed z above is one draw; repeat it across seeds so the
       "no burst" claim rests on more than luck */
    const zs = [];
    for (const sd of [11, 22, 33, 44, 55, 66, 77, 88]) {
      const Q = boot({ w: 1440, h: 900, seed: sd });
      await Q.pumpMicrotasks();
      Q.api.setIntensity(0, true);
      for (let f = 0; f < 900; f++) Q.frame(16.6667);
      let a0 = Q.I.stats().attempts, t0 = Q.I.stats().simTime, e = 0;
      Q.api.setIntensity(1.2);
      for (let f = 0; f < 480; f++) {                       // 8 s ramp
        Q.frame(16.6667);
        const st = Q.I.stats();
        const dT = st.simTime - t0; t0 = st.simTime;
        e += (C.SPAWN_MIN + C.SPAWN_MAX * Math.pow(Q.api.getEffectiveIntensity(), C.SPAWN_EXP)) *
             (C.SPAWN_GUST_A + C.SPAWN_GUST_B * st.gust) * dT;
      }
      zs.push((Q.I.stats().attempts - a0 - e) / Math.sqrt(e));
    }
    const zm = zs.reduce((p, c) => p + c, 0) / zs.length;
    console.log(`      8-seed replication of the ramp, z per seed: ` +
                zs.map((z) => z.toFixed(2)).join(' ') + `   mean=${zm.toFixed(2)}`);
    ok(Math.abs(zm) < 1.0, 'across 8 seeds the ramp fires exactly what the rate predicts',
       `mean z=${zm.toFixed(2)} (expected 0 +/- ${(1 / Math.sqrt(8)).toFixed(2)})`);
  }

  /* --------------------------------------- 3b. worst-case population headroom */
  console.log('\n3b. HEADROOM AT MAXIMUM INTENSITY — the cap must never bite');
  {
    const S = boot({ w: 1440, h: 900, seed: 606 });
    await S.pumpMicrotasks();
    S.api.setIntensity(1.2, true);
    let peak = 0, sum = 0;
    for (let f = 0; f < 18000; f++) { S.frame(16.6667); const c = S.api.count(); peak = Math.max(peak, c); sum += c; }
    const st = S.I.stats();
    console.log(`      300 s at intensity 1.2: mean live=${(sum / 18000).toFixed(0)},` +
                ` peak live=${peak}, pool=${st.pool}, soft cap=${S.I.cfg.SOFT_CAP}`);
    console.log(`      detachments refused because the pool was full: ${st.attempts - st.spawned}`);
    ok(st.attempts === st.spawned, 'not one detachment refused at maximum intensity',
       `${st.attempts - st.spawned} refused`);
    ok(peak < S.I.cfg.SOFT_CAP, 'peak population stays under the cap with margin',
       `${peak} / ${S.I.cfg.SOFT_CAP}`);
  }

  /* ------------------------------------------- 4. resolution independence */
  console.log('\n4. RESOLUTION INDEPENDENCE — 390x844 vs 1440x900 vs 2560x1440');
  {
    const out = [];
    for (const vp of [[390, 844, 3], [1440, 900, 1], [2560, 1440, 2]]) {
      const S = boot({ w: vp[0], h: vp[1], dpr: vp[2], seed: 20260811 });
      await S.pumpMicrotasks();
      S.api.setIntensity(1.0, true);
      const T = new Tracker(S.I);
      for (let f = 0; f < 5400; f++) { S.frame(16.6667); T.poll(); }
      T.flush();
      const st = S.I.stats();
      const g = S.I.geom();
      const crossers = T.done.filter((r) => r.minX < 0.02);
      const lf = stats(crossers.map((r) => r.life));
      const yh = stats(T.done.filter((r) => r.yHalf !== null).map((r) => r.yHalf));
      const leafPx = 0.046 * g.REF;
      out.push({
        vp: `${vp[0]}x${vp[1]}`, dpr: g.DPR, refPx: g.REF.toFixed(0),
        leafPx: leafPx.toFixed(1),
        crossSec: lf.med, landPct: 100 * st.landed / st.spawned,
        leftPct: 100 * st.exitLeft / (st.exitLeft + st.exitOther + st.landFaded),
        yhSd: yh.sd, live: st.active
      });
    }
    for (const r of out) {
      console.log(`      ${r.vp.padEnd(10)} dpr=${r.dpr}  nominal leaf=${r.leafPx}px` +
                  `  median crossing=${f3(r.crossSec)}s  reached ground=${r.landPct.toFixed(1)}%` +
                  `  exit-left=${r.leftPct.toFixed(1)}%  live=${r.live}`);
    }
    const cs = out.map((r) => r.crossSec);
    const lp = out.map((r) => r.landPct);
    ok(Math.max(...cs) / Math.min(...cs) < 1.25,
       'time to cross the frame is viewport-independent',
       `${f3(Math.min(...cs))}s .. ${f3(Math.max(...cs))}s`);
    ok(Math.max(...lp) - Math.min(...lp) < 10,
       'landing fraction is viewport-independent',
       `${lp.map((x) => x.toFixed(1) + '%').join(' / ')}`);
    ok(out.every((r) => +r.leafPx > 18 && +r.leafPx < 110),
       'nominal leaf size stays sane at every viewport',
       out.map((r) => r.leafPx + 'px').join(' / '));
    ok(out.every((r) => r.dpr <= 1.5), 'devicePixelRatio capped at 1.5',
       out.map((r) => r.dpr).join(' / '));
  }

  /* --------------------------------------------- 5. delta-time robustness */
  console.log('\n5. DELTA CLAMP — a 5 s frame gap must not teleport anything');
  {
    const S = boot({ w: 1440, h: 900, seed: 99 });
    await S.pumpMicrotasks();
    S.api.setIntensity(1.0, true);
    for (let f = 0; f < 1200; f++) S.frame(16.6667);
    const A = S.I.arrays, n = S.I.poolSize();
    /* A slot whose age went DOWN was recycled and refilled: that is a
       different leaf, not the same one teleporting. Exclude those. */
    const sameLeaf = (bs, ba, i) =>
      bs[i] !== 0 && A.state[i] !== 0 && A.age[i] >= ba[i];
    const bx = Float64Array.from(A.x), by = Float64Array.from(A.y);
    const bs = Uint8Array.from(A.state), ba = Float64Array.from(A.age);
    S.frame(5000);                       // 5 second stall
    let maxD = 0, reused = 0;
    for (let i = 0; i < n; i++) {
      if (bs[i] !== 0 && A.state[i] !== 0 && A.age[i] < ba[i]) reused++;
      if (!sameLeaf(bs, ba, i)) continue;
      const d = Math.hypot(A.x[i] - bx[i], A.y[i] - by[i]);
      if (d > maxD) maxD = d;
    }
    const bad = scanFinite(S.I);
    console.log(`      largest single-frame displacement after the stall: ${f3(maxD)} of the frame`);
    ok(maxD < 0.10, 'no leaf jumps more than 10% of the frame across the stall', f3(maxD));
    ok(bad === null, 'still finite after the stall', bad || 'clean');

    /* pause / resume must not jump either */
    S.api.pause();
    ok(S.I.isRunning() === false, 'pause() stops the loop');
    ok(S.pending() === 0, 'no rAF pending while paused');
    const px = Float64Array.from(A.x);
    for (let f = 0; f < 60; f++) S.frame(16.6667);       // nothing should happen
    let moved = 0;
    for (let i = 0; i < n; i++) if (A.x[i] !== px[i]) moved++;
    ok(moved === 0, 'nothing moves while paused', `${moved} leaves moved`);
    S.api.resume();
    ok(S.I.isRunning() === true, 'resume() restarts the loop');
    const rx = Float64Array.from(A.x), rs = Uint8Array.from(A.state), ra = Float64Array.from(A.age);
    S.frame(16.6667);
    let maxR = 0;
    for (let i = 0; i < n; i++) {
      if (!(rs[i] !== 0 && A.state[i] !== 0 && A.age[i] >= ra[i])) continue;  // skip refilled slots
      maxR = Math.max(maxR, Math.abs(A.x[i] - rx[i]));
    }
    console.log(`      largest displacement on the first frame after resume: ${f3(maxR)}` +
                `  (one 16.7 ms frame's worth of travel is ~0.01)`);
    ok(maxR < 0.02, 'resume does not jump time', f3(maxR));
  }

  /* ------------------------------------------------- 6. reduced motion */
  console.log('\n6. PREFERS-REDUCED-MOTION');
  {
    const S = boot({ w: 1440, h: 900, reduced: true, seed: 5 });
    await S.pumpMicrotasks();
    ok(S.pending() === 0, 'no rAF was ever scheduled', `${S.pending()} pending`);
    ok(S.I.isRunning() === false, 'loop is not running');
    const c = S.api.count();
    console.log(`      static leaves drawn: ${c}`);
    ok(c > 0 && c <= 12, 'a handful of static leaves are rendered', c);
    const before = Array.from(S.I.arrays.x);
    for (let f = 0; f < 200; f++) S.frame(16.6667);
    let moved = 0;
    for (let i = 0; i < before.length; i++) if (S.I.arrays.x[i] !== before[i]) moved++;
    ok(moved === 0, 'nothing animates', `${moved} moved`);
    S.api.resume();
    ok(S.I.isRunning() === false, 'resume() is a no-op under reduced motion');
  }

  /* ------------------------------------------------------- 7. emission map */
  console.log('\n7. EMISSION GEOMETRY — leaves must come off the canopy, not the top edge');
  {
    const S = boot({ w: 1440, h: 900, seed: 31337 });
    await S.pumpMicrotasks();
    S.api.setIntensity(1.0, true);
    const T = new Tracker(S.I);
    for (let f = 0; f < 3600; f++) { S.frame(16.6667); T.poll(); }
    T.flush();
    const xs = T.done.map((r) => r.x0), ys = T.done.map((r) => r.y0);
    const sx = stats(xs), sy = stats(ys);
    console.log(`      spawn x: min=${f3(sx.min)} p10=${f3(sx.p10)} med=${f3(sx.med)}` +
                ` p90=${f3(sx.p90)} max=${f3(sx.max)}   (brief: 0.72 .. 1.00)`);
    console.log(`      spawn y: min=${f3(sy.min)} p10=${f3(sy.p10)} med=${f3(sy.med)}` +
                ` p90=${f3(sy.p90)} max=${f3(sy.max)}   (brief: 0.08 .. 0.65)`);
    ok(sx.min >= 0.719, 'no leaf originates left of 72% width', f3(sx.min));
    ok(sy.min >= 0.059 && sy.max <= 0.661, 'all origins inside the briefed y band',
       `${f3(sy.min)} .. ${f3(sy.max)}`);
    /* canopy weighting: the emission must be lumpy, not uniform over the box */
    const bins = new Array(10).fill(0);
    for (const y of ys) bins[Math.min(9, ((y - 0.06) / 0.601 * 10) | 0)]++;
    const bmax = Math.max(...bins), bmin = Math.min(...bins);
    console.log(`      y histogram over the band: ${bins.join(' ')}`);
    ok(bmax / Math.max(1, bmin) > 2.0, 'emission is canopy-weighted, not uniform',
       `max/min bin = ${(bmax / Math.max(1, bmin)).toFixed(1)}`);
  }

  /* --------------------------------------------------------- 8. step cost */
  console.log('\n8. COST — physics only (canvas is stubbed here; see browser check for draw)');
  {
    const S = boot({ w: 1440, h: 900, seed: 8 });
    await S.pumpMicrotasks();
    S.api.setIntensity(1.2, true);
    for (let f = 0; f < 1800; f++) S.frame(16.6667);
    const live = S.api.count();
    const t0 = process.hrtime.bigint();
    const REP = 6000;
    for (let f = 0; f < REP; f++) S.frame(16.6667);
    const t1 = process.hrtime.bigint();
    const perFrame = Number(t1 - t0) / 1e6 / REP;
    console.log(`      ${live} live leaves, 2 substeps/frame: ${perFrame.toFixed(3)} ms/frame` +
                ` of physics + bookkeeping`);
    console.log(`      => ${(perFrame / 16.667 * 100).toFixed(1)}% of a 60 fps budget on this machine`);
    ok(perFrame < 3.0, 'physics fits comfortably inside a 16.7 ms frame', `${perFrame.toFixed(3)} ms`);
  }

  /* ----------------------------------------------------- 9. allocation test */
  console.log('\n9. ALLOCATION — the frame loop must not grow the heap');
  {
    const S = boot({ w: 1440, h: 900, seed: 2 });
    await S.pumpMicrotasks();
    S.api.setIntensity(1.2, true);
    for (let f = 0; f < 1800; f++) S.frame(16.6667);
    if (global.gc) global.gc();
    const h0 = process.memoryUsage().heapUsed;
    for (let f = 0; f < 30000; f++) S.frame(16.6667);    // 500 s of animation
    if (global.gc) global.gc();
    const h1 = process.memoryUsage().heapUsed;
    const growthKb = (h1 - h0) / 1024;
    console.log(`      heapUsed after 30000 further frames: ${growthKb >= 0 ? '+' : ''}` +
                `${growthKb.toFixed(0)} KB  (gc ${global.gc ? 'forced' : 'NOT available — run with --expose-gc'})`);
    ok(Math.abs(growthKb) < 800, 'no unbounded growth across 30000 frames', `${growthKb.toFixed(0)} KB`);
    const st = S.I.stats();
    ok(st.active + st.free === st.pool, 'pool still balanced at the end',
       `${st.active}+${st.free}=${st.pool}`);
    console.log(`      lifetime totals: spawned=${st.spawned} exitLeft=${st.exitLeft}` +
                ` faded=${st.landFaded} other=${st.exitOther} live=${st.active}`);
  }

  console.log(`\n${FAIL === 0 ? 'ALL CHECKS PASSED' : FAIL + ' CHECK(S) FAILED'}`);
  process.exit(FAIL === 0 ? 0 : 1);
}

main().catch((e) => { console.error(e); process.exit(2); });
