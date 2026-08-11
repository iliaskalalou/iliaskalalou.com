/* Dump real leaf trajectories to an SVG so the path shape can be judged by
   eye instead of by scalar. Left column: lift on. Right column: lift off. */
'use strict';
const fs = require('fs'), path = require('path'), vm = require('vm');
const HTML_SRC = fs.readFileSync(path.join(__dirname, 'demo.html'), 'utf8');
const SRC = HTML_SRC.match(/<script>([\s\S]*?)<\/script>/)[1];

function boot(opts) {
  const rafQ = []; let now = 1000, id = 1;
  const noop = () => {};
  const ctx2d = new Proxy({}, { get: (t, k) => (k in t ? t[k] : noop), set: (t, k, v) => (t[k] = v, true) });
  const canvas = { width: 0, height: 0, style: {}, getContext: () => ctx2d, addEventListener: noop };
  const el = () => ({ style: {}, textContent: '', value: '', addEventListener: noop });
  const s = { console, Math, JSON, Date, Object, Array, Number, String, Boolean, Error,
    Float32Array, Float64Array, Int32Array, Int8Array, Uint8Array,
    performance: { now: () => now }, setTimeout, queueMicrotask };
  s.window = s; s.globalThis = s;
  s.innerWidth = opts.w; s.innerHeight = opts.h; s.devicePixelRatio = 1;
  s.requestAnimationFrame = (cb) => (rafQ.push(cb), id++);
  s.cancelAnimationFrame = () => (rafQ.length = 0);
  s.matchMedia = () => ({ matches: false, addEventListener: noop, addListener: noop });
  s.addEventListener = noop;
  s.document = { hidden: false, getElementById: (i) => (i === 'leaf-canvas' ? canvas : el()),
    createElement: () => canvas, addEventListener: noop };
  s.Image = function () { Object.defineProperty(this, 'src', { set: () => { const me = this;
    queueMicrotask(() => me.onload && me.onload()); } }); };
  vm.createContext(s); vm.runInContext(SRC, s);
  const I = s.leafSystem._internals;
  I.seed(opts.seed);
  if (opts.noLift) { I.cfg.LIFT_LO = 0; I.cfg.LIFT_HI = 0; }
  return { api: s.leafSystem, I, frame: (dt) => { const c = rafQ.splice(0); now += dt; c.forEach((f) => f(now)); } };
}

function collect(opts, want) {
  const S = boot(opts);
  S.api.setIntensity(opts.I, true);
  const A = S.I.arrays, n = S.I.poolSize();
  const live = new Map(); const done = [];
  const lastAge = new Float64Array(n).fill(-1);
  for (let f = 0; f < 9000 && done.length < want * 6; f++) {
    S.frame(16.6667);
    for (let i = 0; i < n; i++) {
      const st = A.state[i], age = A.age[i];
      if (st === 0) { if (live.has(i)) { done.push(live.get(i)); live.delete(i); } lastAge[i] = -1; continue; }
      if (!live.has(i) || age < lastAge[i]) {
        if (live.has(i)) done.push(live.get(i));
        live.set(i, { pts: [], size: A.size[i] });
      }
      if (st === 1) live.get(i).pts.push(A.x[i], A.y[i]);
      lastAge[i] = age;
    }
  }
  const geom = S.I.geom();
  /* keep long-lived, well-spread examples */
  const good = done.filter((d) => d.pts.length > 150)
                   .sort((a, b) => b.pts.length - a.pts.length);
  const pick = [];
  for (let i = 0; i < good.length && pick.length < want; i += Math.max(1, (good.length / want) | 0)) pick.push(good[i]);
  return { pick, geom };
}

const W = 1440, H = 900;
function panel(res, title, ox, oy, scale) {
  let s = `<g transform="translate(${ox},${oy}) scale(${scale})">`;
  s += `<rect x="0" y="0" width="${W}" height="${H}" fill="#0c0c0c" stroke="#333"/>`;
  const cols = ['#e2703a', '#c8452b', '#d99a4e', '#b8563a', '#e0a35c', '#cc5533'];
  res.pick.forEach((d, k) => {
    let p = '';
    for (let i = 0; i < d.pts.length; i += 2) {
      p += (i ? 'L' : 'M') + (d.pts[i] * W).toFixed(1) + ' ' + (d.pts[i + 1] * H).toFixed(1) + ' ';
    }
    s += `<path d="${p}" fill="none" stroke="${cols[k % cols.length]}" stroke-width="2.2" opacity="0.95"/>`;
    /* leaf size marker at the start, so wobble can be read in leaf-widths */
    const lp = d.size * res.geom.REF;
    s += `<circle cx="${(d.pts[0] * W).toFixed(1)}" cy="${(d.pts[1] * H).toFixed(1)}" r="${(lp / 2).toFixed(1)}" fill="none" stroke="${cols[k % cols.length]}" stroke-width="1.5" opacity="0.5"/>`;
  });
  s += `<text x="18" y="42" fill="#ddd" font-family="monospace" font-size="30">${title}</text>`;
  s += `</g>`;
  return s;
}

const runs = [
  { I: 1.0, noLift: false, t: 'intensity 1.0 — lift ON' },
  { I: 1.0, noLift: true, t: 'intensity 1.0 — lift OFF' },
  { I: 0.3, noLift: false, t: 'intensity 0.3 — lift ON' },
  { I: 0.3, noLift: true, t: 'intensity 0.3 — lift OFF' }
];
let svg = `<svg xmlns="http://www.w3.org/2000/svg" width="1500" height="960" viewBox="0 0 1500 960">
<rect width="1500" height="960" fill="#111"/>`;
runs.forEach((r, k) => {
  const res = collect({ w: W, h: H, seed: 991, I: r.I, noLift: r.noLift }, 6);
  svg += panel(res, r.t, (k % 2) * 750 + 6, ((k / 2) | 0) * 474 + 6, 0.5);
  const circle = res.pick.length ? (res.pick[0].size * res.geom.REF).toFixed(0) : '?';
  console.log(`${r.t}: ${res.pick.length} paths, first leaf ${circle}px wide`);
});
svg += '</svg>';
fs.writeFileSync(path.join(__dirname, 'shots', 'paths.svg'), svg);
console.log('wrote shots/paths.svg');
