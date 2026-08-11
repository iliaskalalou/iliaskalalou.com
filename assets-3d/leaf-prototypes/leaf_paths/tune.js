/* Fast tuning probe: vertical distribution of leaves across the frame.
   node tune.js [overrideJSON]                                            */
'use strict';
const fs = require('fs'), path = require('path');
const SRC = fs.readFileSync(path.join(__dirname, 'demo.html'), 'utf8')
  .match(/<script id="leaf-source">([\s\S]*?)<\/script>/)[1];
const mod = { exports: {} };
new Function('module', 'exports', 'window', 'document', 'requestAnimationFrame', 'performance', SRC)
  (mod, mod.exports, undefined, undefined, undefined, undefined);
const { createLeafSystem, CONFIG } = mod.exports;
if (process.argv[2]) Object.assign(CONFIG, JSON.parse(process.argv[2]));

const N = CONFIG.POOL;
const LV = n => ({ img: {}, cell: n });
const SPR = [[LV(256), LV(128), LV(64), LV(32)], [LV(256), LV(128), LV(64), LV(32)], [LV(256), LV(128), LV(64), LV(32)]];

function run(w, h, seed) {
  const sys = createLeafSystem({ ctx: { setTransform() {}, drawImage() {} }, sprites: SPR,
    width: w, height: h, dpr: 1, seed, intensity: 1.0 });
  const A = sys._arrays;
  sys._prewarm(150);
  const prevX = new Float32Array(N).fill(NaN);
  const cross = [];                 // y at x = 0.5
  const occ = new Float64Array(10); // time-weighted vertical occupancy of the whole frame
  let frames = 0;
  for (let f = 0; f < 30000; f++) {
    sys.step(1 / 60);
    for (let i = 0; i < N; i++) {
      if (!A.act[i]) { prevX[i] = NaN; continue; }
      if (Number.isFinite(prevX[i]) && prevX[i] > 0.5 && A.nx[i] <= 0.5) cross.push(A.ny[i]);
      prevX[i] = A.nx[i];
      if (f % 5 === 0 && A.nx[i] > 0 && A.nx[i] < 1)
        occ[Math.max(0, Math.min(9, (A.ny[i] * 10) | 0))] += A.curA[i];
    }
    if (f % 5 === 0) frames++;
  }
  const hist = k => {
    const b = new Array(10).fill(0);
    for (const y of k) b[Math.max(0, Math.min(9, (y * 10) | 0))]++;
    const n = k.length; let H = 0;
    for (const v of b) if (v) { const p = v / n; H -= p * Math.log2(p); }
    const pct = b.map(v => 100 * v / n);
    const top2 = [...pct].sort((a, b2) => b2 - a).slice(0, 2).reduce((a, b2) => a + b2, 0);
    let steep = 0;
    for (let i = 1; i < 9; i++) if (pct[i] > 0.4 && pct[i + 1] > 0.4)
      steep = Math.max(steep, pct[i] / pct[i + 1], pct[i + 1] / pct[i]);
    return { pct, H, top2, steep, n };
  };
  const c = hist(cross);
  const tot = occ.reduce((a, b) => a + b, 0);
  const opct = Array.from(occ, v => 100 * v / tot);
  let osteep = 0;
  for (let i = 1; i < 9; i++) if (opct[i] > 0.4 && opct[i + 1] > 0.4)
    osteep = Math.max(osteep, opct[i] / opct[i + 1], opct[i + 1] / opct[i]);
  let oH = 0; for (const v of opct) if (v) { const p = v / 100; oH -= p * Math.log2(p); }
  return { c, opct, oH, osteep, alive: sys.count() };
}

for (const [w, h] of [[1440, 860], [2560, 1300]]) {
  const r = run(w, h, 4242);
  console.log(`\n${w}x${h}  alive=${r.alive}`);
  console.log(`  crossings @x=0.5 : [${r.c.pct.map(v => v.toFixed(1).padStart(5)).join('')}]  H=${r.c.H.toFixed(2)}  top2=${r.c.top2.toFixed(0)}%  steepest=${r.c.steep.toFixed(2)}x`);
  console.log(`  on-screen ink    : [${r.opct.map(v => v.toFixed(1).padStart(5)).join('')}]  H=${r.oH.toFixed(2)}  steepest=${r.osteep.toFixed(2)}x`);
}
