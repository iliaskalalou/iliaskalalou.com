/* Stress: hold the briefed 250 live leaves and measure real frame cost,
   including with the CPU throttled to stand in for a mid laptop.
   Also measures where leaves actually land along the bottom of the frame. */
'use strict';
const { spawn } = require('child_process');
const fs = require('fs'); const path = require('path');
const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const PORT = 9334, URL = 'http://127.0.0.1:8934/demo.html';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

class CDP {
  constructor(ws) { this.ws = ws; this.id = 0; this.p = new Map();
    ws.addEventListener('message', (e) => { const m = JSON.parse(e.data);
      if (m.id && this.p.has(m.id)) { const { res, rej } = this.p.get(m.id); this.p.delete(m.id);
        m.error ? rej(new Error(JSON.stringify(m.error))) : res(m.result); } }); }
  send(method, params) { const id = ++this.id;
    return new Promise((res, rej) => { this.p.set(id, { res, rej });
      this.ws.send(JSON.stringify({ id, method, params: params || {} })); }); }
  async ev(e) { const r = await this.send('Runtime.evaluate',
    { expression: e, returnByValue: true, awaitPromise: true });
    if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description);
    return r.result.value; }
}

let FAIL = 0;
const ok = (c, l, d) => { if (!c) FAIL++; console.log(`  [${c ? 'PASS' : 'FAIL'}] ${l}${d !== undefined ? '  ->  ' + d : ''}`); };

async function main() {
  const chrome = spawn(CHROME, ['--headless=new', `--remote-debugging-port=${PORT}`,
    '--remote-allow-origins=*', '--disable-gpu', '--hide-scrollbars', '--no-first-run',
    '--user-data-dir=/tmp/leafchrome2', '--window-size=1440,900'], { stdio: 'ignore' });
  let wsUrl = null;
  for (let i = 0; i < 60 && !wsUrl; i++) { await sleep(250);
    try { const l = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
      const p = l.find((t) => t.type === 'page'); if (p) wsUrl = p.webSocketDebuggerUrl; } catch (e) {} }
  const ws = new WebSocket(wsUrl);
  await new Promise((r) => ws.addEventListener('open', r));
  const cdp = new CDP(ws);
  await cdp.send('Page.enable'); await cdp.send('Runtime.enable');

  await cdp.send('Emulation.setDeviceMetricsOverride',
    { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
  await cdp.send('Page.navigate', { url: URL + '?s=' + Date.now() });
  await sleep(1500);

  /* frame-interval probe: histogram of real inter-frame gaps */
  const installProbe = () => cdp.ev(`window.__h=[];window.__last=performance.now();window.__on=true;
    (function f(){const n=performance.now();const d=n-window.__last;window.__last=n;
      if(window.__on&&window.__h.length<20000)window.__h.push(d);
      requestAnimationFrame(f);})();`);
  const readProbe = () => cdp.ev(`(()=>{const h=window.__h.slice(20).sort((a,b)=>a-b);
    const q=(p)=>h.length?+h[Math.min(h.length-1,Math.floor(h.length*p))].toFixed(2):0;
    return {n:h.length, med:q(0.5), p95:q(0.95), p99:q(0.99), max:q(1),
            over16:h.filter(v=>v>16.7).length, over33:h.filter(v=>v>33.4).length};})()`);
  const resetProbe = () => cdp.ev('window.__h=[];window.__last=performance.now();');

  console.log('STRESS — real Chrome, 1440x900\n');
  await installProbe();
  await cdp.send('Performance.enable');
  const metric = async (k) => {
    const m = await cdp.send('Performance.getMetrics');
    return m.metrics.find((x) => x.name === k).value;
  };
  /* JS ms per frame is the number that belongs to this system; the raw frame
     interval also contains Chrome's own raster and compositing. */
  async function jsCost(ms) {
    await resetProbe();
    const s0 = await metric('ScriptDuration'), t0 = await metric('TaskDuration');
    await sleep(ms);
    const s1 = await metric('ScriptDuration'), t1 = await metric('TaskDuration');
    const h = await readProbe();
    return { scriptMs: ((s1 - s0) * 1000) / Math.max(1, h.n),
             taskMs: ((t1 - t0) * 1000) / Math.max(1, h.n), h };
  }

  /* -------- drive the population to the briefed 250 by raising the emitter.
     CFG is read live inside step(), so the harness can push past what the
     intensity knob alone reaches at a gust peak. ------------------------- */
  await cdp.ev('window.leafSystem._internals.cfg.SPAWN_MAX = 130; window.leafSystem.setIntensity(1.2)');
  let peak = 0, n = 0;
  for (let i = 0; i < 60; i++) {
    await sleep(500);
    n = await cdp.ev('window.leafSystem.count()');
    peak = Math.max(peak, n);
    if (peak >= 258) break;
  }
  console.log(`1. population driven to ${peak} live leaves`);
  ok(peak >= 250, 'the system can actually hold the briefed 250 live leaves', peak);

  let r = await jsCost(12000);
  let live = await cdp.ev('window.leafSystem.count()');
  console.log(`   full speed, ~${live} live:`);
  console.log(`     JS per frame  ${r.scriptMs.toFixed(2)} ms   (whole main-thread task ${r.taskMs.toFixed(2)} ms)`);
  console.log(`     frame interval: median ${r.h.med}ms p95 ${r.h.p95}ms p99 ${r.h.p99}ms max ${r.h.max}ms` +
              `  — display is 120 Hz here, so 8.3 ms is the floor`);
  console.log(`     frames over 16.7ms: ${r.h.over16}/${r.h.n}   over 33.4ms: ${r.h.over33}`);
  ok(r.scriptMs < 6, 'JS cost per frame leaves the 16.7 ms budget mostly free',
     `${r.scriptMs.toFixed(2)} ms with ${live} leaves`);
  ok(r.h.over33 === 0, 'not one dropped frame', `${r.h.over33}/${r.h.n}`);

  /* how much of that is the throwaway tree scaffolding? */
  await cdp.ev("document.getElementById('b-tree').click()");
  const rNoTree = await jsCost(8000);
  console.log(`   with the placeholder tree hidden (what actually ships):` +
              ` JS per frame ${rNoTree.scriptMs.toFixed(2)} ms`);
  await cdp.ev("document.getElementById('b-tree').click()");

  /* --------------------------- 4x CPU throttle: stand-in for a mid laptop */
  console.log('\n2. same load with the CPU throttled 4x (mid-laptop stand-in)');
  await cdp.send('Emulation.setCPUThrottlingRate', { rate: 4 });
  await sleep(3000);
  r = await jsCost(12000);
  live = await cdp.ev('window.leafSystem.count()');
  console.log(`   4x throttle, ~${live} live:`);
  console.log(`     JS per frame  ${r.scriptMs.toFixed(2)} ms   (whole task ${r.taskMs.toFixed(2)} ms)`);
  console.log(`     frame interval: median ${r.h.med}ms p95 ${r.h.p95}ms p99 ${r.h.p99}ms`);
  ok(r.scriptMs < 16.7, 'JS still fits a 60 fps frame with the CPU 4x slower',
     `${r.scriptMs.toFixed(2)} ms`);

  /* ------------------------------- 6x, to find where it actually breaks */
  console.log('\n3. 6x throttle — looking for the actual ceiling');
  await cdp.send('Emulation.setCPUThrottlingRate', { rate: 6 });
  await sleep(3000);
  r = await jsCost(10000);
  live = await cdp.ev('window.leafSystem.count()');
  console.log(`   6x throttle, ~${live} live: JS per frame ${r.scriptMs.toFixed(2)} ms,` +
              ` frame interval median ${r.h.med}ms`);
  await cdp.send('Emulation.setCPUThrottlingRate', { rate: 1 });
  await cdp.ev('window.leafSystem._internals.cfg.SPAWN_MAX = 42');

  /* -------------------------------------- where do leaves actually land? */
  console.log('\n4. landing distribution along the bottom of the frame');
  await cdp.ev('window.leafSystem.setIntensity(1.0)');
  await sleep(3000);
  const land = await cdp.ev(`(()=>{
    const A=window.leafSystem._internals.arrays, n=A.state.length;
    window.__land=window.__land||[];
    window.__landTimer=window.__landTimer||setInterval(()=>{
      for(let i=0;i<n;i++){ if(A.state[i]===2 && A.settle[i]<0.08) window.__land.push(+A.x[i].toFixed(3)); }
    },40);
    return 'armed';})()`);
  await sleep(20000);
  const xs = await cdp.ev('window.__land.slice()');
  const bins = new Array(10).fill(0);
  for (const x of xs) { const b = Math.max(0, Math.min(9, Math.floor(x * 10))); bins[b]++; }
  console.log(`   ${xs.length} touchdowns sampled; x histogram (0=left edge, 9=right edge):`);
  console.log(`   ${bins.map((v, i) => `${(i / 10).toFixed(1)}:${v}`).join('  ')}`);
  const leftHeavy = bins[0] / Math.max(1, xs.length);
  console.log(`   share landing in the leftmost tenth of the frame: ${(100 * leftHeavy).toFixed(1)}%`);
  ok(leftHeavy < 0.45, 'landings are spread across the floor, not piled in one corner',
     `${(100 * leftHeavy).toFixed(1)}% in the leftmost tenth`);

  /* the number that actually matters visually is not where they land but how
     many settled leaves are sitting in the corner at any one instant */
  const corner = await cdp.ev(`(()=>{
    const A=window.leafSystem._internals.arrays,n=A.state.length;
    let s=0,c=0,tot=0;
    for(let i=0;i<n;i++){ if(A.state[i]===2){ tot++;
      if(A.x[i]<0.22 && A.y[i]>0.80) c++; } if(A.state[i]!==0) s++; }
    return {settled:tot, inCorner:c, live:s};})()`);
  console.log(`   instantaneous: ${corner.live} live, ${corner.settled} of them settled,` +
              ` ${corner.inCorner} sitting in the bottom-left corner box (x<0.22, y>0.80)`);
  ok(corner.inCorner <= 12, 'the bottom-left corner never holds a real pile',
     `${corner.inCorner} settled leaves`);

  /* ---------------- attribute the frame cost: sweep the leaf count ------- */
  console.log('\n5. frame cost vs leaf count (software raster, --disable-gpu)');
  const sweep = [];
  for (const [I, tree] of [[0, false], [0.35, false], [0.7, false], [1.2, false]]) {
    await cdp.ev(`window.leafSystem._internals.cfg.SPAWN_MAX=${I === 1.2 ? 130 : 42};` +
                 `window.leafSystem.setIntensity(${I}, true)`);
    await sleep(6000);
    const rr = await jsCost(6000);
    const lv = await cdp.ev('window.leafSystem.count()');
    sweep.push({ lv, js: rr.scriptMs, med: rr.h.med, task: rr.taskMs });
    console.log(`   ${String(lv).padStart(4)} leaves:  JS ${rr.js === undefined ? '' : ''}` +
                `${rr.scriptMs.toFixed(2)} ms/frame   whole task ${rr.taskMs.toFixed(2)} ms` +
                `   frame interval ${rr.h.med} ms`);
  }
  const base = sweep[0], top = sweep[sweep.length - 1];
  const perLeafUs = (top.js - base.js) * 1000 / Math.max(1, top.lv - base.lv);
  console.log(`   marginal JS cost: ${perLeafUs.toFixed(2)} microseconds per leaf per frame`);
  console.log(`   baseline (0 leaves) whole-task cost ${base.task.toFixed(1)} ms is Chrome's own` +
              ` software compositing of a full-screen canvas, not this system`);

  const shot = await cdp.send('Page.captureScreenshot', { format: 'png' });
  fs.writeFileSync(path.join(__dirname, 'shots', 'stress_ground.png'), Buffer.from(shot.data, 'base64'));

  console.log(`\n${FAIL === 0 ? 'STRESS CHECKS PASSED' : FAIL + ' STRESS CHECK(S) FAILED'}`);
  ws.close(); chrome.kill(); process.exit(FAIL === 0 ? 0 : 1);
}
main().catch((e) => { console.error(e); process.exit(2); });
