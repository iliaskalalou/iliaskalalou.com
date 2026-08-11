/* Headless harness: extracts the exact <script id="leaf-source"> block from
   demo.html and drives createLeafSystem with a stub 2D context.
   Run: node --expose-gc harness.js                                        */
'use strict';
const fs = require('fs');
const path = require('path');

const HTML = fs.readFileSync(path.join(__dirname, 'demo.html'), 'utf8');
const m = HTML.match(/<script id="leaf-source">([\s\S]*?)<\/script>/);
if (!m) { console.error('could not find leaf-source script'); process.exit(1); }

const mod = { exports: {} };
new Function('module', 'exports', 'window', 'document', 'requestAnimationFrame', 'performance', m[1])
  (mod, mod.exports, undefined, undefined, undefined, undefined);

const { createLeafSystem, CONFIG } = mod.exports;
if (!createLeafSystem) { console.error('no export'); process.exit(1); }
const N = CONFIG.POOL;

function stubCtx() {
  const c = {
    calls: 0, nanTransforms: 0, globalAlpha: 1,
    setTransform(a, b, cc, d, e, f) {
      if (!(Number.isFinite(a) && Number.isFinite(b) && Number.isFinite(cc) &&
            Number.isFinite(d) && Number.isFinite(e) && Number.isFinite(f))) c.nanTransforms++;
    },
    drawImage() { c.calls++; }
  };
  return c;
}
const LV = n => ({ img: { __stub: true }, cell: n });
const SPR = (() => { const one = [LV(256), LV(128), LV(64), LV(32)]; return [one, one, one]; })();

const FAIL = [];
function ok(cond, label, detail) {
  console.log((cond ? '  PASS  ' : '  FAIL  ') + label + (detail === undefined ? '' : '   ' + detail));
  if (!cond) FAIL.push(label);
}
const f2 = n => (Math.round(n * 100) / 100);
const f3 = n => (Math.round(n * 1000) / 1000);

function makeSys(o) {
  o = o || {};
  const ctx = stubCtx();
  const sys = createLeafSystem({
    ctx, sprites: SPR,
    width: o.w || 1440, height: o.h || 860, dpr: o.dpr || 1.5,
    seed: o.seed === undefined ? 12345 : o.seed,
    intensity: o.i === undefined ? 1.0 : o.i
  });
  return { sys, ctx };
}

/* ======================================================================
   1. soak
   ====================================================================== */
console.log('\n=== 1. soak: 36 000 frames @ 1/60 (600 s), intensity stepped 0.6/0/1.2/0.15/1.0 ===');
{
  const { sys, ctx } = makeSys({ i: 0.6 });
  const A = sys._arrays, dt = 1 / 60;
  const prevX = new Float32Array(N).fill(NaN);
  const crossY = [];
  const ink = new Float64Array(10);
  let nanHits = 0, poolBad = 0, maxAlive = 0, maxGround = 0, minAlive = 1e9, outOfRange = 0;
  let originBad = 0, originN = 0, emptyFrames = 0;
  const seenOrigin = new Uint8Array(N);
  const ox = [], oy = [];
  /* "no popping": a leaf may only cease to exist off-frame or invisible */
  const wasAct = new Uint8Array(N);
  let popped = 0, poppedWorst = 0, vanishChecked = 0;

  for (let f = 0; f < 36000; f++) {
    if (f === 6000) sys.setIntensity(0.0);
    if (f === 13000) sys.setIntensity(1.2);
    if (f === 22000) sys.setIntensity(0.15);
    if (f === 29000) sys.setIntensity(1.0);
    for (let i = 0; i < N; i++) wasAct[i] = A.act[i];
    sys.step(dt); sys.render();
    for (let i = 0; i < N; i++) {
      if (wasAct[i] && !A.act[i]) {
        vanishChecked++;
        /* the whole sprite must be clear of the frame, not just its centre */
        const hx = A.sizeA[i] * 0.72 / 1440, hy = A.sizeA[i] * 0.72 / 860;
        const offFrame = A.nx[i] + hx < 0 || A.nx[i] - hx > 1 ||
                         A.ny[i] + hy < 0 || A.ny[i] - hy > 1;
        const invisible = A.curA[i] < 0.02;
        if (!offFrame && !invisible) { popped++; if (A.curA[i] > poppedWorst) poppedWorst = A.curA[i]; }
      }
    }

    if (sys.count() + sys._freeN() !== N) poolBad++;
    if (sys.count() > maxAlive) maxAlive = sys.count();
    if (f > 900 && sys.count() < minAlive) minAlive = sys.count();
    if (f > 900 && sys.count() === 0) emptyFrames++;
    if (sys.groundedCount() > maxGround) maxGround = sys.groundedCount();

    for (let i = 0; i < N; i++) {
      if (!A.act[i]) { prevX[i] = NaN; seenOrigin[i] = 0; continue; }
      const x = A.nx[i], y = A.ny[i];
      if (!(Number.isFinite(x) && Number.isFinite(y) && Number.isFinite(A.curA[i]) &&
            Number.isFinite(A.curRot[i]) && Number.isFinite(A.frP[i]) && Number.isFinite(A.u[i]) &&
            Number.isFinite(A.sizeA[i]))) nanHits++;
      if (x < -0.4 || x > 1.4 || y < -0.5 || y > 1.5) outOfRange++;
      if (!seenOrigin[i]) {
        seenOrigin[i] = 1; originN++;
        ox.push(A.nx0[i]); oy.push(A.ny0[i]);
        if (A.nx0[i] < 0.72 || A.nx0[i] > 1.0 || A.ny0[i] < 0.08 || A.ny0[i] > 0.65) originBad++;
      }
      if (Number.isFinite(prevX[i]) && prevX[i] > 0.5 && x <= 0.5) crossY.push(y);
      prevX[i] = x;
      if ((f & 3) === 0 && x > 0 && x < 1) ink[Math.max(0, Math.min(9, (y * 10) | 0))] += A.curA[i];
    }
  }

  const S = sys._stats;
  ok(nanHits === 0, 'no NaN / non-finite state anywhere', `checks over 36 000 frames, hits=${nanHits}`);
  ok(poolBad === 0, 'pool invariant alive+free===POOL held every frame', `violations=${poolBad}`);
  ok(S.spawned - S.despawned === sys.count(), 'spawn/despawn ledger balances',
     `spawned=${S.spawned} despawned=${S.despawned} alive=${sys.count()}`);
  ok(outOfRange === 0, 'no leaf escapes the sane coordinate box', `escapes=${outOfRange}`);
  ok(originBad === 0, 'every leaf originates inside the canopy box x[.72,1] y[.08,.65]',
     `${originN} spawns, ${originBad} outside`);
  ok(S.exitLeft > 0.55 * S.despawned, 'the majority of leaves exit on the LEFT',
     `exitLeft=${S.exitLeft} = ${f2(100 * S.exitLeft / S.despawned)}% of despawns`);
  ok(S.settled > 0.15 * S.despawned && S.settled < 0.45 * S.despawned,
     'a real minority reach the ground, settle and fade',
     `settled=${S.settled} = ${f2(100 * S.settled / S.despawned)}%`);
  ok(S.exitBottom + S.exitTop < 0.03 * S.despawned, 'almost nothing leaks out the top or bottom',
     `bottom=${S.exitBottom} top=${S.exitTop}`);
  ok(maxAlive < N, 'pool never saturates', `maxAlive=${maxAlive} pool=${N}`);
  ok(maxGround <= 60, 'grounded leaves never pile up', `maxGrounded=${maxGround}`);
  ok(emptyFrames / 35100 < 0.002, 'the field is essentially never empty, even at intensity 0',
     `min alive ${minAlive}, empty on ${f3(100 * emptyFrames / 35100)}% of frames`);
  ok(ctx.nanTransforms === 0, 'every draw transform is finite', `bad=${ctx.nanTransforms}`);
  ok(popped === 0, 'NO leaf ever pops out of existence while visible on screen',
     `${vanishChecked} despawns audited, ${popped} popped` + (popped ? ` (worst alpha ${f3(poppedWorst)})` : ''));
  console.log(`         mean leaf lifetime (EMA) ${f2(sys._meanLife())} s;  draw calls last frame ${ctx.calls > 0 ? 'yes' : 'no'}`);

  const oxm = ox.reduce((a, b) => a + b, 0) / ox.length;
  const oym = oy.reduce((a, b) => a + b, 0) / oy.length;
  console.log(`         emission centroid: x=${f3(oxm)} y=${f3(oym)}  (canopy mass, weighted toward lobe A)`);

  const bins = new Array(10).fill(0);
  let sum = 0, sum2 = 0;
  for (const y of crossY) { bins[Math.max(0, Math.min(9, Math.floor(y * 10)))]++; sum += y; sum2 += y * y; }
  const n = crossY.length, mean = sum / n, sd = Math.sqrt(sum2 / n - mean * mean);
  let Hh = 0; for (const b of bins) if (b) { const p = b / n; Hh -= p * Math.log2(p); }
  const usedBins = bins.filter(b => b > n * 0.005).length;
  console.log(`         mid-screen crossings n=${n}  meanY=${f2(mean)}  sdY=${f2(sd)}`);
  console.log(`         decile histogram of crossing height: [${bins.map(b => (100 * b / n).toFixed(1)).join('  ')}] %`);
  /* deciles 1..8 only: the 8->9 step is the ground line, a real floor, not a wall */
  let ratioMax = 0;
  for (let i = 1; i < 8; i++) {
    if (bins[i] < n * 0.004 || bins[i + 1] < n * 0.004) continue;
    ratioMax = Math.max(ratioMax, bins[i] / bins[i + 1], bins[i + 1] / bins[i]);
  }
  const inkTot = ink.reduce((a, b) => a + b, 0);
  const inkPct = Array.from(ink, v => 100 * v / inkTot);
  let inkH = 0; for (const v of inkPct) if (v) { const p = v / 100; inkH -= p * Math.log2(p); }
  /* deciles 1..8: decile 0 is the top edge of the frame and 9 is the floor,
     both real boundaries of the composition rather than artefacts */
  let inkSteep = 0;
  for (let i = 1; i < 8; i++)
    inkSteep = Math.max(inkSteep, inkPct[i] / inkPct[i + 1], inkPct[i + 1] / inkPct[i]);
  console.log(`         on-screen ink by decile of height:            [${inkPct.map(v => v.toFixed(1).padStart(5)).join('')}] %`);
  ok(inkH > 3.05, 'the visible field fills the frame evenly top to bottom',
     `entropy ${f2(inkH)} bits of max 3.32`);
  ok(inkSteep < 3.0, 'ink density has no cliff anywhere in the frame',
     `steepest neighbouring-decile ratio ${f2(inkSteep)}x`);
  ok(sd > 0.14, 'crossing heights are broadly spread (not one lane)', `sd=${f2(sd)}`);
  ok(usedBins >= 8, 'crossings cover most of the screen height', `deciles used=${usedBins}/10`);
  ok(Hh > 2.8, 'crossing-height entropy is high', `H=${f2(Hh)} bits of max 3.32`);
  ok(ratioMax < 3.0, 'density varies smoothly with height — no ridge, no invisible wall',
     `steepest neighbouring-decile ratio ${f2(ratioMax)}x`);
}

/* ======================================================================
   2. composition — does the portrait actually get protected?
   ====================================================================== */
console.log('\n=== 2. composition: portrait keep-clear, measured against a control ===');
{
  function measure(label) {
    const { sys } = makeSys({ i: 1.0, seed: 4242 });
    const A = sys._arrays;
    sys._prewarm(120);
    let inCore = 0, total = 0, inCoreCount = 0, totalCount = 0;
    const P = CONFIG.PORTRAIT, CR = 0.15, RX = 0.115;
    for (let f = 0; f < 24000; f++) {
      sys.step(1 / 60);
      if (f % 3) continue;
      for (let i = 0; i < N; i++) {
        if (!A.act[i]) continue;
        const a = A.curA[i];
        total += a; totalCount++;
        if (Math.abs(A.nx[i] - P.x) < RX && Math.abs(A.ny[i] - P.y) < CR) { inCore += a; inCoreCount++; }
      }
    }
    const r = { label, alphaShare: inCore / total, countShare: inCoreCount / totalCount };
    console.log(`   ${label.padEnd(18)} ink over the face = ${f2(100 * r.alphaShare)}% of all ink,  ` +
                `leaf count there = ${f2(100 * r.countShare)}%`);
    return r;
  }
  const on = measure('routing + veil');
  const dm = CONFIG.DEFLECT_MIN, ds = CONFIG.DEFLECT_SPAN, v = CONFIG.VEIL, rp = CONFIG.ROUTE_P;
  CONFIG.DEFLECT_MIN = 0; CONFIG.DEFLECT_SPAN = 0; CONFIG.VEIL = 0; CONFIG.ROUTE_P = 0;
  const off = measure('control (off)');
  CONFIG.DEFLECT_MIN = dm; CONFIG.DEFLECT_SPAN = ds; CONFIG.VEIL = v; CONFIG.ROUTE_P = rp;

  const inkDrop = 1 - on.alphaShare / off.alphaShare;
  const cntDrop = 1 - on.countShare / off.countShare;
  console.log(`   reduction vs control: ink ${f2(100 * inkDrop)}%,  leaf count ${f2(100 * cntDrop)}%`);
  ok(inkDrop > 0.35, 'the portrait area is substantially de-cluttered', `${f2(100 * inkDrop)}% less ink`);
  ok(cntDrop > 0.20, 'fewer leaves actually route through the face', `${f2(100 * cntDrop)}% fewer`);
  ok(on.countShare > 0.02, 'but it is thinned, not evacuated (no invisible wall)',
     `${f2(100 * on.countShare)}% of leaves still pass`);
}

/* ======================================================================
   3. irregularity — no perceivable period
   ====================================================================== */
console.log('\n=== 3. irregularity ===');
{
  /* 3a. spawn inter-arrival statistics: Poisson => CV ~ 1, a metronome => CV ~ 0 */
  const { sys } = makeSys({ i: 1.0, seed: 900 });
  sys._prewarm(60);
  const dt = 1 / 60;
  let last = sys._stats.spawned, t = 0, prevT = 0;
  const gaps = [];
  for (let f = 0; f < 108000; f++) {           // 1800 s
    sys.step(dt); t += dt;
    const s = sys._stats.spawned;
    for (let k = last; k < s; k++) { gaps.push(t - prevT); prevT = t; }
    last = s;
  }
  const gm = gaps.reduce((a, b) => a + b, 0) / gaps.length;
  const gv = gaps.reduce((a, b) => a + (b - gm) * (b - gm), 0) / gaps.length;
  const cv = Math.sqrt(gv) / gm;
  console.log(`   ${gaps.length} spawns, mean gap ${f3(gm)} s, CV ${f2(cv)}  (Poisson = 1.0, metronome = 0)`);
  ok(cv > 0.75, 'emission timing is Poisson, not rhythmic', `CV=${f2(cv)}`);

  /* 3b. autocorrelation of the detrended mid-screen crossing rate at constant intensity */
  const { sys: s2 } = makeSys({ i: 1.0, seed: 77 });
  const A = s2._arrays;
  s2._prewarm(120);
  const B = 0.25, NB = 4000;                    // 1000 s of 0.25 s buckets
  const rate = new Float64Array(NB);
  const prevX = new Float32Array(N).fill(NaN);
  let tt = 0;
  for (let f = 0; f < NB * 15; f++) {
    s2.step(dt); tt += dt;
    const b = Math.min(NB - 1, (tt / B) | 0);
    for (let i = 0; i < N; i++) {
      if (!A.act[i]) { prevX[i] = NaN; continue; }
      if (Number.isFinite(prevX[i]) && prevX[i] > 0.5 && A.nx[i] <= 0.5) rate[b]++;
      prevX[i] = A.nx[i];
    }
  }
  /* detrend with a centred 10 s moving average so a slow drift in the mean
     cannot masquerade as periodicity */
  const Wm = 40, res = new Float64Array(NB);
  for (let i = 0; i < NB; i++) {
    let s = 0, c = 0;
    for (let k = Math.max(0, i - Wm); k <= Math.min(NB - 1, i + Wm); k++) { s += rate[k]; c++; }
    res[i] = rate[i] - s / c;
  }
  let r0 = 0; for (const v of res) r0 += v * v;
  let worst = 0, worstLag = 0;
  for (let lag = 1; lag < 400; lag++) {
    let s = 0;
    for (let k = 0; k + lag < NB; k++) s += res[k] * res[k + lag];
    const r = s / r0;
    if (Math.abs(r) > Math.abs(worst)) { worst = r; worstLag = lag; }
  }
  console.log(`   detrended crossing-rate autocorrelation over lags 0.25–100 s: ` +
              `worst |r| = ${f3(Math.abs(worst))} at ${f2(worstLag * B)} s`);
  ok(Math.abs(worst) < 0.15, 'no periodic pulse hides in the emission');

  /* 3c. path signatures and flutter frequency ratios must all be distinct */
  const { sys: s3 } = makeSys({ i: 1.0, seed: 31337 });
  const A3 = s3._arrays;
  const seen = new Set(); const ratios = []; const known = new Uint8Array(N);
  let dupes = 0, count = 0;
  for (let f = 0; f < 60000 && count < 6000; f++) {
    s3.step(dt);
    for (let i = 0; i < N; i++) {
      if (A3.act[i] && !known[i]) {
        known[i] = 1; count++;
        const sig = [A3.nx0[i], A3.ny0[i], A3.uRate[i], A3.sink[i], A3.arc[i], A3.w1[i]]
          .map(v => v.toFixed(5)).join('|');
        if (seen.has(sig)) dupes++; else seen.add(sig);
        ratios.push(A3.w2[i] / A3.w1[i]);
      } else if (!A3.act[i]) known[i] = 0;
    }
  }
  ratios.sort((a, b) => a - b);
  let minGap = Infinity;
  for (let i = 1; i < ratios.length; i++) minGap = Math.min(minGap, ratios[i] - ratios[i - 1]);
  ok(dupes === 0, 'no two leaves ever share a path signature', `${count} spawns, ${dupes} duplicates`);
  console.log(`   flutter frequency ratio w2/w1 spans ${f3(ratios[0])}–${f3(ratios[ratios.length - 1])}, ` +
              `closest pair differs by ${minGap.toExponential(1)}`);
  ok(ratios[0] > 1.30 && ratios[ratios.length - 1] < 1.95 && minGap > 0,
     'every leaf has its own irrational-ish flutter ratio (never in phase)');
}

/* ======================================================================
   4. intensity
   ====================================================================== */
console.log('\n=== 4. intensity response ===');
{
  for (const I of [0, 0.25, 0.5, 0.75, 1.0, 1.2, 1.5]) {
    const { sys } = makeSys({ i: I, seed: 77 });
    sys._prewarm(240);
    let sum = 0, k = 0, mx = 0, mn = 1e9, gmax = 0;
    for (let f = 0; f < 18000; f++) {
      sys.step(1 / 60);
      const c = sys.count(); sum += c; k++;
      if (c > mx) mx = c; if (c < mn) mn = c;
      if (sys.groundedCount() > gmax) gmax = sys.groundedCount();
    }
    console.log(`   I=${I.toFixed(2)}   mean alive ${(sum / k).toFixed(1).padStart(6)}   ` +
                `range ${String(mn).padStart(3)}–${String(mx).padStart(3)}   peak grounded ${gmax}`);
    if (I === 0) ok(sum / k > 1 && sum / k < 16, 'intensity 0 = a live trickle, not frozen', `mean=${f2(sum / k)}`);
    if (I === 1.0) ok(sum / k > 110 && sum / k < 240, 'intensity 1 = a strong field', `mean=${f2(sum / k)}`);
    if (I === 1.5) ok(mx < N, 'intensity 1.5 still fits the pool', `peak=${mx}`);
  }

  const { sys } = makeSys({ i: 0, seed: 5 });
  sys._prewarm(90);
  let prev = sys._stats.spawned, wAcc = 0, wT = 0, worstWin = 0;
  const curve = [], pop = [];
  let maxFrameJump = 0, maxRise1s = 0, lastC = sys.count();
  const hist = [];
  sys.setIntensity(1.2);
  for (let f = 0; f < 2400; f++) {
    sys.step(1 / 60);
    const c = sys.count();
    if (Math.abs(c - lastC) > maxFrameJump) maxFrameJump = Math.abs(c - lastC);
    lastC = c;
    hist.push(c);
    if (f >= 60 && hist[f] - hist[f - 60] > maxRise1s) maxRise1s = hist[f] - hist[f - 60];
    wAcc += sys._stats.spawned - prev; prev = sys._stats.spawned; wT += 1 / 60;
    if (wT >= 0.25) { if (wAcc > worstWin) worstWin = wAcc; curve.push(wAcc); pop.push(sys.count()); wAcc = 0; wT = 0; }
  }
  const avg = (a, s, e) => a.slice(s, e).reduce((x, y) => x + y, 0) / (e - s);
  console.log(`   spawns per 250 ms after a hard 0 -> 1.2 jump: ` +
              `t=0-1s ${f2(avg(curve, 0, 4))}, t=2-3s ${f2(avg(curve, 8, 12))}, t=8-10s ${f2(avg(curve, 32, 40))}, peak window ${worstWin}`);
  console.log(`   population: ${pop.filter((_, i) => i % 8 === 0).slice(0, 10).join(' -> ')}`);
  ok(avg(curve, 0, 4) < avg(curve, 32, 40) * 0.6, 'no spawn burst on an intensity jump — the rate ramps');
  ok(worstWin <= CONFIG.MAX_SPAWN_PER_FRAME * 15 + 2, 'per-window spawn count stays bounded', `peak=${worstWin}`);
  console.log(`   fastest single second of growth during the surge: ${maxRise1s} leaves ` +
              `(the wind visibly picking up, over ~8 s)`);
  ok(maxFrameJump <= CONFIG.MAX_SPAWN_PER_FRAME,
     'population never changes discontinuously in a single frame',
     `largest one-frame change = ${maxFrameJump} leaves (cap ${CONFIG.MAX_SPAWN_PER_FRAME})`);

  sys.setIntensity(0);
  const dn = [];
  for (let f = 0; f < 5400; f++) { sys.step(1 / 60); if (f % 60 === 0) dn.push(sys.count()); }
  let maxDrop = 0;
  for (let i = 1; i < dn.length; i++) maxDrop = Math.max(maxDrop, dn[i - 1] - dn[i]);
  console.log(`   decay 1.2 -> 0, population per second: ${dn.slice(0, 14).join(' ')} ... ${dn[dn.length - 1]}`);
  console.log(`   (fastest single second of decay: ${maxDrop} leaves = ` +
              `${f2(100 * maxDrop / dn[0])}% of the field; each of them left the frame normally)`);
  ok(maxDrop < 0.22 * dn[0], 'population decays gradually as leaves finish their paths',
     `max drop/s = ${maxDrop} of ${dn[0]}`);
  ok(dn[dn.length - 1] > 0, 'still alive at the bottom of the range', `final=${dn[dn.length - 1]}`);
}

/* ======================================================================
   5. dt robustness
   ====================================================================== */
console.log('\n=== 5. delta-time robustness ===');
{
  const { sys } = makeSys({ i: 0.8, seed: 31 });
  sys._prewarm(90);
  const A = sys._arrays;
  const before = [];
  for (let i = 0; i < N; i++) if (A.act[i]) before.push([i, A.nx[i], A.ny[i]]);
  const spawnedBefore = sys._stats.spawned;
  sys.step(37.5);                                  // a tab returning after 37 s
  let maxJump = 0, bad = 0;
  for (const [i, x, y] of before) {
    if (!A.act[i]) continue;
    const d = Math.hypot(A.nx[i] - x, A.ny[i] - y);
    if (!Number.isFinite(d)) bad++;
    if (d > maxJump) maxJump = d;
  }
  ok(bad === 0 && maxJump < 0.06, 'a 37.5 s frame moves nothing further than one clamped tick',
     `max displacement = ${f3(maxJump)} of a viewport`);
  ok(sys._stats.spawned - spawnedBefore <= CONFIG.MAX_SPAWN_PER_FRAME,
     'and it cannot dump a spawn burst', `spawned=${sys._stats.spawned - spawnedBefore}`);
  const c0 = sys.count();
  sys.step(0); sys.step(-1); sys.step(NaN); sys.step(undefined);
  ok(sys.count() === c0 && Number.isFinite(sys.count()),
     'zero / negative / NaN / undefined dt are ignored, not propagated');
}

/* ======================================================================
   6. resolution independence
   ====================================================================== */
console.log('\n=== 6. resolution independence ===');
{
  const rows = [];
  for (const [w, h] of [[390, 844], [768, 1024], [1440, 860], [2560, 1440]]) {
    const { sys } = makeSys({ w, h, i: 1.0, seed: 606 });
    const A = sys._arrays;
    sys._prewarm(150);
    const prevX = new Float32Array(N), born = new Float64Array(N), tracking = new Uint8Array(N);
    let t = 0; const times = [], sizes = [];
    for (let f = 0; f < 27000; f++) {
      sys.step(1 / 60); t += 1 / 60;
      for (let i = 0; i < N; i++) {
        if (!A.act[i]) { tracking[i] = 0; continue; }
        if (!tracking[i]) { tracking[i] = 1; born[i] = t; prevX[i] = A.nx[i]; sizes.push(A.sizeA[i]); continue; }
        if (A.fate[i] === 0 && prevX[i] > 0.15 && A.nx[i] <= 0.15) times.push(t - born[i]);
        prevX[i] = A.nx[i];
      }
    }
    times.sort((a, b) => a - b); sizes.sort((a, b) => a - b);
    const med = a => a[a.length >> 1];
    rows.push({ w, h, tMed: med(times), n: times.length, szMed: med(sizes), alive: sys.count() });
  }
  for (const r of rows) {
    const cover = r.alive * Math.pow(r.szMed * 0.62, 2) / (r.w * r.h);   // rough ink coverage
    r.cover = cover;
    console.log(`   ${String(r.w).padStart(4)}x${String(r.h).padEnd(4)}  canopy->x15% median ${f2(r.tMed)} s (n=${r.n})   ` +
                `median leaf ${f2(r.szMed)} px = ${f2(100 * r.szMed / r.h)}% of height   ` +
                `alive ${String(r.alive).padStart(3)}   screen coverage ~${f2(100 * cover)}%`);
  }
  const ts = rows.map(r => r.tMed);
  ok(Math.max(...ts) / Math.min(...ts) < 1.25, 'traverse time in SECONDS is ~constant across viewports',
     `spread ${f2(Math.max(...ts) / Math.min(...ts))}x`);
  const al = rows.map(r => r.alive);
  ok(al[0] < al[1] && al[1] < al[2] && al[2] <= al[3],
     'population scales up with viewport area, monotonically', `alive ${al.join(' / ')}`);
  const cv2 = rows.map(r => r.cover);
  ok(Math.max(...cv2) / Math.min(...cv2) < 1.9,
     'apparent leaf density (screen coverage) stays comparable at every size',
     `${cv2.map(v => f2(100 * v) + '%').join(' / ')}`);
  ok(rows[0].szMed > 20 && rows[3].szMed < 90, 'leaf pixel size stays sane at both extremes',
     `${f2(rows[0].szMed)} px at 390 wide, ${f2(rows[3].szMed)} px at 2560 wide`);
}

/* ======================================================================
   7. performance at 250 live leaves
   ====================================================================== */
console.log('\n=== 7. performance at 250 live leaves ===');
{
  const { sys, ctx } = makeSys({ i: 1.45, seed: 8 });
  sys._prewarm(300);
  let guard = 0;
  while (sys.count() < 250 && guard++ < 120000) sys.step(1 / 60);
  const live = sys.count();
  for (let f = 0; f < 4000; f++) { sys.step(1 / 60); sys.render(); }   // warm the JIT
  const nF = 8000;
  let t0 = process.hrtime.bigint();
  for (let f = 0; f < nF; f++) sys.step(1 / 60);
  let t1 = process.hrtime.bigint();
  const stepMs = Number(t1 - t0) / 1e6 / nF;
  ctx.calls = 0;
  t0 = process.hrtime.bigint();
  for (let f = 0; f < nF; f++) sys.render();
  t1 = process.hrtime.bigint();
  const renderMs = Number(t1 - t0) / 1e6 / nF;
  console.log(`   live leaves at intensity 1.45: ${live} (peak reached ${Math.max(live, sys.count())})`);
  console.log(`   step()   ${stepMs.toFixed(4)} ms/frame`);
  console.log(`   render() ${renderMs.toFixed(4)} ms/frame  (CPU side only, drawImage stubbed)`);
  console.log(`   draw calls issued: ${(ctx.calls / nF).toFixed(0)} per frame`);
  ok(live >= 250, 'the system can hold 250 live leaves', `${live}`);
  ok(stepMs + renderMs < 1.5, 'CPU cost is a rounding error against the 16.7 ms budget',
     `${(stepMs + renderMs).toFixed(3)} ms/frame`);
}

/* ======================================================================
   8. allocation stability
   ====================================================================== */
console.log('\n=== 8. allocation stability ===');
{
  const { sys } = makeSys({ i: 1.1, seed: 21 });
  sys._prewarm(150);
  if (global.gc) { global.gc(); global.gc(); }
  const h0 = process.memoryUsage().heapUsed;
  for (let f = 0; f < 90000; f++) { sys.step(1 / 60); sys.render(); }
  if (global.gc) { global.gc(); global.gc(); }
  const h1 = process.memoryUsage().heapUsed;
  const dk = (h1 - h0) / 1024;
  console.log(`   heapUsed delta over 90 000 frames (1500 s of animation): ${dk.toFixed(1)} KB` +
              (global.gc ? '' : '   (run with --expose-gc for an exact figure)'));
  ok(Math.abs(dk) < 512, 'zero heap growth: nothing is allocated in the frame loop', `${dk.toFixed(1)} KB`);
}

console.log('\n' + (FAIL.length ? 'FAILED (' + FAIL.length + '): ' + FAIL.join(' | ') : 'ALL CHECKS PASSED'));
process.exit(FAIL.length ? 1 : 0);
