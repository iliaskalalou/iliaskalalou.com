const { run } = require("./harness");

let PASS = 0, FAIL = 0;
const ok = (c, msg, extra) => {
  if (c) { PASS++; console.log("  PASS  " + msg + (extra ? "   " + extra : "")); }
  else { FAIL++; console.log("  FAIL  " + msg + (extra ? "   " + extra : "")); }
};
const hdr = s => console.log("\n=== " + s + " " + "=".repeat(Math.max(0, 62 - s.length)));

const FIELDS = ["x","y","z","vx","vy","rot","fr","k","a","gy","ph","fade","flat"];
function scanNaN(P) {
  let bad = 0, offenders = [];
  for (const p of P) {
    if (p.st === 0) continue;
    for (const f of FIELDS) if (!Number.isFinite(p[f])) { bad++; offenders.push(f); break; }
  }
  return { bad, offenders: [...new Set(offenders)] };
}
function invariant(sys) {
  const s = sys.stats();
  return { poolOk: s.live + s.free === s.pool, ledgerOk: s.spawned - s.freed === s.live, s };
}

/* ───────────────────────────────────────────────────────────── 1. long soak */
hdr("1. LONG SOAK  1440x900, I=0.55, 12000 frames @60fps (200 s)");
{
  const H = run({ w: 1440, h: 900 });
  H.sys.setIntensity(0.55);
  let maxLive = 0, minFree = 1e9, maxDrawsPerFrame = 0, prevDraws = 0;
  for (let i = 0; i < 12000; i++) {
    H.tick(1 / 60);
    const s = H.sys.stats();
    if (s.live > maxLive) maxLive = s.live;
    if (s.free < minFree) minFree = s.free;
    const d = H.rec.draws - prevDraws; prevDraws = H.rec.draws;
    if (d > maxDrawsPerFrame) maxDrawsPerFrame = d;
  }
  const n = scanNaN(H.sys._P), inv = invariant(H.sys), s = inv.s;
  ok(n.bad === 0, "no NaN/Inf in any active particle", `(${s.live} live scanned)`);
  ok(inv.poolOk, "pool invariant live+free===pool", `${s.live}+${s.free}=${s.pool}`);
  ok(inv.ledgerOk, "ledger spawned-freed===live", `${s.spawned}-${s.freed}=${s.live}`);
  ok(minFree > 0, "pool never exhausted", `min free slots = ${minFree}`);
  ok(H.rec.badXf === 0, "no non-finite value ever reached setTransform", `${H.rec.xf} transforms`);
  ok(s.exitLeft > 0, "leaves exit on the LEFT", `${s.exitLeft}`);
  ok(s.landedTotal > 0, "leaves reach the GROUND", `${s.landedTotal}`);
  const frac = s.landedTotal / s.spawned;
  ok(frac > 0.05 && frac < 0.75, "ground fraction in a sane band", `${(frac * 100).toFixed(1)}%`);
  console.log(`        spawned=${s.spawned} exitLeft=${s.exitLeft} ` +
              `exitBottom/settled=${s.exitBottom} other=${s.exitOther}`);
  console.log(`        steady live≈${s.live}  peak live=${maxLive}  peak draws/frame=${maxDrawsPerFrame}`);
}

/* ─────────────────────────────────────────────────── 2. leak / stability */
hdr("2. LEAK CHECK  intensity thrashed 0<->1.2, 20000 frames");
{
  const H = run({ w: 1600, h: 900 });
  const samples = [];
  for (let i = 0; i < 20000; i++) {
    if (i % 137 === 0) H.sys.setIntensity(Math.random() * 1.2);
    H.tick(1 / 60);
    if (i % 2000 === 0) samples.push(H.sys.stats().free + H.sys.stats().live);
  }
  const s = H.sys.stats();
  ok(samples.every(v => v === s.pool), "pool size constant across the run",
     `[${[...new Set(samples)].join(",")}]`);
  ok(H.sys._P.length === s.pool, "particle array never reallocated", `len=${H.sys._P.length}`);
  ok(scanNaN(H.sys._P).bad === 0, "no NaN after 20000 thrashed frames");
  ok(invariant(H.sys).ledgerOk, "ledger balanced after thrash");
}

/* ─────────────────────────────────────────────── 3. intensity behaviour */
hdr("3. INTENSITY SWEEP  steady-state population + ground fraction");
{
  const rows = [];
  for (const I of [0, 0.15, 0.35, 0.55, 0.8, 1.0, 1.2]) {
    const H = run({ w: 1440, h: 900 });
    H.sys.setIntensity(I);
    for (let i = 0; i < 1800; i++) H.tick(1 / 60);   // 30 s settle
    const a = H.sys.stats();
    for (let i = 0; i < 3600; i++) H.tick(1 / 60);   // 60 s measure
    const b = H.sys.stats();
    const sp = b.spawned - a.spawned, ld = b.landedTotal - a.landedTotal;
    let live = 0;
    for (let i = 0; i < 600; i++) { H.tick(1 / 60); live += H.sys.stats().live; }
    rows.push({ I, live: Math.round(live / 600), rate: +(sp / 60).toFixed(1),
                ground: +(100 * ld / sp).toFixed(0) });
  }
  console.log("        I     live   spawn/s   %ground");
  rows.forEach(r => console.log(
    `        ${r.I.toFixed(2)}  ${String(r.live).padStart(5)}   ${String(r.rate).padStart(6)}   ${String(r.ground).padStart(6)}%`));
  ok(rows[0].live > 0 && rows[0].rate > 0.5, "I=0 is a trickle, NOT frozen",
     `${rows[0].live} live, ${rows[0].rate}/s`);
  ok(rows.every((r, i) => i === 0 || r.live >= rows[i - 1].live), "population monotonic in I");
  const at1 = rows.find(r => r.I === 1.0);
  ok(at1.live >= 180 && at1.live <= 320, "I=1.0 lands near the 250-leaf design target",
     `${at1.live} live`);
  ok(rows.every(r => r.ground > 8 && r.ground < 80), "ground fraction non-degenerate at every I");
  ok(rows[0].ground > rows[rows.length - 1].ground,
     "calm air drops more leaves than a gust (emergent, not scripted)",
     `${rows[0].ground}% vs ${rows[rows.length - 1].ground}%`);
}

/* ─────────────────────────────────────────── 4. smoothness of setIntensity */
hdr("4. NO POP  step 0 -> 1.2, measure per-frame spawn burst");
{
  const H = run({ w: 1440, h: 900 });
  H.sys.setIntensity(0);
  for (let i = 0; i < 1200; i++) H.tick(1 / 60);
  let prev = H.sys.stats().spawned, worst = 0, series = [];
  H.sys.setIntensity(1.2);
  for (let i = 0; i < 240; i++) {
    H.tick(1 / 60);
    const s = H.sys.stats(), d = s.spawned - prev; prev = s.spawned;
    if (d > worst) worst = d;
    if (i % 30 === 0) series.push(`${(i / 60).toFixed(1)}s:${H.sys.getIntensity().toFixed(2)}`);
  }
  ok(worst <= 2, "never more than 2 spawns in one frame during a hard step",
     `worst = ${worst}`);
  console.log("        smoothed intensity ramp  " + series.join("  "));
  const I05 = (() => {
    const G = run({ w: 1440, h: 900 }); G.sys.setIntensity(0);
    for (let i = 0; i < 600; i++) G.tick(1 / 60);
    G.sys.setIntensity(1.0);
    for (let i = 0; i < 33; i++) G.tick(1 / 60);      // 0.55 s == tau
    return G.sys.getIntensity();
  })();
  ok(I05 > 0.55 && I05 < 0.70, "one tau reaches ~63% of the step (exponential, as documented)",
     `I(tau)=${I05.toFixed(3)}`);
}

/* ────────────────────────────────────────────────── 5. path non-degeneracy */
hdr("5. PATH DIVERSITY  exit-point spread + trajectory decorrelation");
{
  const H = run({ w: 1440, h: 900 });
  H.sys.setIntensity(0.7);
  for (let i = 0; i < 9000; i++) H.tick(1 / 60);
  const EX = H.sys._exits, n = H.sys._exitN();
  const ys = [], xs = [];
  for (let i = 0; i < n; i++) {
    const mode = EX[i * 3 + 2];
    if (mode === 0) ys.push(EX[i * 3 + 1]); else xs.push(EX[i * 3]);
  }
  const stats = a => {
    const mu = a.reduce((s, v) => s + v, 0) / a.length;
    const sd = Math.sqrt(a.reduce((s, v) => s + (v - mu) ** 2, 0) / a.length);
    return { mu, sd, min: Math.min(...a), max: Math.max(...a) };
  };
  const Y = stats(ys), X = stats(xs);
  console.log(`        left-exit  y: mean ${Y.mu.toFixed(3)} sd ${Y.sd.toFixed(3)} range [${Y.min.toFixed(2)}, ${Y.max.toFixed(2)}]  n=${ys.length}`);
  console.log(`        ground     x: mean ${X.mu.toFixed(3)} sd ${X.sd.toFixed(3)} range [${X.min.toFixed(2)}, ${X.max.toFixed(2)}]  n=${xs.length}`);
  ok(Y.sd > 0.10, "left-exit heights well spread (not a conveyor belt)", `sd=${Y.sd.toFixed(3)}`);
  ok(Y.max - Y.min > 0.45, "left exits span most of the frame height",
     `span=${(Y.max - Y.min).toFixed(2)}`);
  ok(X.sd > 0.08, "ground landings spread horizontally", `sd=${X.sd.toFixed(3)}`);
  // histogram entropy of left-exit heights (12 bins) — 1.0 == perfectly uniform
  const B = new Array(12).fill(0);
  ys.forEach(v => { let b = Math.floor(((v + 0.2) / 1.4) * 12); B[Math.max(0, Math.min(11, b))]++; });
  const H12 = -B.filter(c => c).reduce((s, c) => { const p = c / ys.length; return s + p * Math.log2(p); }, 0);
  ok(H12 / Math.log2(12) > 0.6, "exit-height entropy high (paths not clustered)",
     `${(100 * H12 / Math.log2(12)).toFixed(0)}% of uniform`);

  // no two live leaves share a trajectory: compare (vx,vy,phv,sink) tuples
  const live = H.sys._P.filter(p => p.st === 1);
  const keys = new Set(live.map(p => [p.vx, p.vy, p.phv, p.sink].map(v => v.toFixed(6)).join("|")));
  ok(keys.size === live.length, "every live leaf has a unique motion signature",
     `${keys.size}/${live.length}`);
}

/* ────────────────────────────────────────────────── 6. no visible period */
hdr("6. PERIODICITY  measured autocorrelation of the live gust signal");
{
  const H = run({ w: 1440, h: 900 });
  H.sys.setIntensity(0.7);
  const sig = [];                                    // 600 s sampled at 10 Hz
  for (let i = 0; i < 36000; i++) { H.tick(1 / 60); if (i % 6 === 0) sig.push(H.sys.stats().gust); }
  const mu = sig.reduce((a, b) => a + b) / sig.length;
  const d = sig.map(v => v - mu), v0 = d.reduce((s, x) => s + x * x, 0);
  const ac = lag => {
    let s = 0; for (let i = 0; i + lag < d.length; i++) s += d[i] * d[i + lag];
    return (s / v0) * (d.length / (d.length - lag));
  };
  // A smooth signal is ~1 at tiny lags by construction; that is smoothness, not
  // periodicity. What matters is when it comes BACK after first decorrelating.
  let decorr = 0;
  for (let L = 1; L < 3000; L++) if (ac(L) < 0.2) { decorr = L; break; }
  let recur = null;
  for (let L = decorr; L < 5000; L++) if (ac(L) > 0.6) { recur = L / 10; break; }
  const at30 = ac(300);
  ok(decorr > 0 && decorr / 10 < 25, "gust decorrelates within 25 s",
     `r<0.2 at ${(decorr / 10).toFixed(1)}s`);
  ok(at30 < 0.4, "no self-similarity at the brief's 30 s bar", `r(30s)=${at30.toFixed(2)}`);
  // The brief's bar is 30 s. Measured first recurrence is ~124 s (verified
  // stable over 300/600/1200/2400 s records), i.e. 4x margin.
  ok(recur === null || recur > 90, "first recurrence at least 3x the brief's 30 s bar",
     recur === null ? "none within 500s" : `first r>0.6 at ${recur.toFixed(0)}s`);
  console.log(`        gust range [${Math.min(...sig).toFixed(2)}, ${Math.max(...sig).toFixed(2)}]  mean ${mu.toFixed(2)}`);
}

/* ───────────────────────────────────────────────────── 7. viewport sweep */
hdr("7. RESOLUTION INDEPENDENCE  390 -> 2560");
{
  console.log("        viewport      live  spawn/s  %ground  %exitLeft");
  const rows = [];
  for (const [w, h] of [[390, 800], [768, 1024], [1280, 720], [1440, 900], [1920, 1080], [2560, 1440]]) {
    const H = run({ w, h, dpr: 2 });
    H.sys.setIntensity(0.8);
    for (let i = 0; i < 1800; i++) H.tick(1 / 60);
    const a = H.sys.stats();
    for (let i = 0; i < 3600; i++) H.tick(1 / 60);
    const b = H.sys.stats();
    const sp = b.spawned - a.spawned, ld = b.landedTotal - a.landedTotal,
          lf = b.exitLeft - a.exitLeft;
    const r = { w, h, live: b.live, rate: +(sp / 60).toFixed(1),
                g: Math.round(100 * ld / sp), l: Math.round(100 * lf / sp),
                nan: scanNaN(H.sys._P).bad };
    rows.push(r);
    console.log(`        ${String(w + "x" + h).padEnd(12)} ${String(r.live).padStart(4)}  ` +
                `${String(r.rate).padStart(6)}   ${String(r.g).padStart(5)}%   ${String(r.l).padStart(7)}%`);
  }
  ok(rows.every(r => r.nan === 0), "no NaN at any viewport");
  ok(rows.every(r => r.live > 20), "every viewport sustains a population");
  const gs = rows.map(r => r.g);
  ok(Math.max(...gs) - Math.min(...gs) < 16,
     "ground fraction ~constant across a 6.5x aspect/size range (design goal)",
     `spread ${Math.min(...gs)}%..${Math.max(...gs)}%`);
  ok(rows[0].rate < rows[rows.length - 1].rate, "density scales with viewport",
     `${rows[0].rate}/s @390  ->  ${rows[rows.length - 1].rate}/s @2560`);
}

/* ─────────────────────────────────────────────── 8. dt clamp / tab return */
hdr("8. TIME ROBUSTNESS  giant dt, zero dt, negative dt");
{
  const H = run({ w: 1440, h: 900 });
  H.sys.setIntensity(0.8);
  for (let i = 0; i < 1200; i++) H.tick(1 / 60);
  // Track leaves by IDENTITY (pool slot + birth stamp). Comparing filtered
  // arrays positionally is wrong: recycling shifts them and fakes huge jumps.
  const before = H.sys._P.map(p => ({ st: p.st, x: p.x, y: p.y, tb: p.tb }));
  H.tick(45);                       // 45 s "tab was in the background"
  let maxJump = 0, matched = 0;
  H.sys._P.forEach((p, i) => {
    const b = before[i];
    if (p.st === 1 && b.st === 1 && p.tb === b.tb) {
      matched++;
      maxJump = Math.max(maxJump, Math.abs(p.x - b.x), Math.abs(p.y - b.y));
    }
  });
  ok(matched > 50, "enough surviving leaves to judge", `${matched} identity-matched`);
  ok(maxJump < 0.09, "45 s dt moves nothing more than a clamped 50 ms step",
     `max displacement = ${maxJump.toFixed(4)} viewports`);
  H.tick(0); H.tick(-1); H.tick(1e6);
  ok(scanNaN(H.sys._P).bad === 0, "survives dt = 0, negative and 1e6 s");
  ok(invariant(H.sys).poolOk, "pool intact afterwards");
}

/* ───────────────────────────────────────────── 9. pause / resume / hidden */
hdr("9. LIFECYCLE  pause, resume, visibilitychange");
{
  const H = run({ w: 1440, h: 900 });
  for (let i = 0; i < 300; i++) H.tick(1 / 60);
  const n0 = H.sys.stats().spawned;
  H.sys.pause();
  ok(!H.hasRaf(), "pause() cancels the rAF loop");
  ok(H.sys.stats().spawned === n0, "nothing advances while paused");
  H.sys.resume();
  ok(H.hasRaf(), "resume() restarts the loop");
  H.setNow(H.now() + 600000);       // 10 real minutes elapse before the next tick
  H.tick(1 / 60);
  ok(scanNaN(H.sys._P).bad === 0, "resume after 10 min wall-clock gap: no teleport, no NaN");
  H.doc.hidden = true;  H.doc._l.visibilitychange();
  ok(!H.hasRaf(), "document hidden stops the loop");
  H.doc.hidden = false; H.doc._l.visibilitychange();
  ok(H.hasRaf(), "document visible resumes the loop");
  for (let i = 0; i < 120; i++) H.tick(1 / 60);
  ok(H.sys.stats().spawned > n0, "still emitting after the cycle");
}

/* ─────────────────────────────────────────────────── 10. reduced motion */
hdr("10. prefers-reduced-motion");
{
  const H = run({ w: 1440, h: 900, reduce: true });
  ok(H.sys._reduced(), "media query detected");
  ok(!H.hasRaf() && H.rec.rafCalls === 0, "requestAnimationFrame NEVER called",
     `calls = ${H.rec.rafCalls}`);
  ok(H.sys.count() > 0 && H.sys.count() <= 20, "a handful of static leaves rendered",
     `${H.sys.count()} leaves`);
  ok(H.rec.draws > H.sys.count(), "one static draw pass happened", `${H.rec.draws} drawImage`);
  H.sys.resume();
  ok(H.rec.rafCalls === 0, "resume() is a no-op under reduced motion");
}

/* ──────────────────────────────────────────────────── 11. API surface */
hdr("11. PUBLIC API");
{
  const H = run({ w: 1440, h: 900 });
  const s = H.sys;
  ok(["setIntensity", "getIntensity", "pause", "resume", "count"].every(k => typeof s[k] === "function"),
     "window.leafSystem exposes the documented five");
  s.setIntensity(0.42);
  ok(Math.abs(s.targetIntensity() - 0.42) < 1e-9, "setIntensity stores the target");
  s.setIntensity(-5);  ok(s.targetIntensity() === 0, "clamps below 0");
  s.setIntensity(99);  ok(s.targetIntensity() === 1.6, "clamps above 1.6");
  s.setIntensity(NaN); ok(s.targetIntensity() === 1.6, "rejects NaN (keeps last good)");
  s.setIntensity("0.9"); ok(Math.abs(s.targetIntensity() - 0.9) < 1e-9, "coerces numeric strings");
  ok(typeof s.count() === "number", "count() returns a number");
  ok(H.els.ival.textContent === "0.90", "panel readout tracks the API");
}

/* ─────────────────────────────────────────────────────── 12. cpu cost */
hdr("12. MAIN-THREAD COST  (JS only; canvas is stubbed)");
{
  const H = run({ w: 1920, h: 1080 });
  H.sys.setIntensity(1.2);
  for (let i = 0; i < 3000; i++) H.tick(1 / 60);
  const live = H.sys.stats().live;
  for (let i = 0; i < 2000; i++) H.tick(1 / 60);        // warm JIT
  const N = 20000, t0 = process.hrtime.bigint();
  for (let i = 0; i < N; i++) H.tick(1 / 60);
  const per = Number(process.hrtime.bigint() - t0) / 1e6 / N;
  console.log(`        ${live} live leaves — ${per.toFixed(4)} ms/frame of update+bucket+transform JS`);
  console.log(`        (${(per * 1000).toFixed(1)} us; the real cost adds GPU-backed drawImage)`);
  ok(per < 0.35, "JS half of the frame is well under budget", `${per.toFixed(4)} ms`);

  // allocation check: heap must not grow across a long steady run
  global.gc && global.gc();
  const h0 = process.memoryUsage().heapUsed;
  for (let i = 0; i < 30000; i++) H.tick(1 / 60);
  global.gc && global.gc();
  const h1 = process.memoryUsage().heapUsed;
  const grow = (h1 - h0) / 1024;
  console.log(`        heap delta over 30000 further frames: ${grow.toFixed(0)} KB`);
  ok(Math.abs(grow) < 800, "no measurable per-frame allocation", `${grow.toFixed(0)} KB`);
}

console.log(`\n${"=".repeat(66)}\n  ${PASS} passed, ${FAIL} failed\n`);
process.exit(FAIL ? 1 : 0);
