/* Real-browser verification over the Chrome DevTools Protocol.
   Runs the page in headless Chrome at real time, measures real frame rate with
   a rAF probe inside the page, and captures screenshots at several viewports
   and intensities. No dependencies: Node's global WebSocket + fetch. */
'use strict';
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const PORT = 9333;
const URL = 'http://127.0.0.1:8934/demo.html';
const OUT = path.join(__dirname, 'shots');
fs.mkdirSync(OUT, { recursive: true });

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

class CDP {
  constructor(ws) { this.ws = ws; this.id = 0; this.pending = new Map();
    ws.addEventListener('message', (e) => {
      const m = JSON.parse(e.data);
      if (m.id && this.pending.has(m.id)) {
        const { res, rej } = this.pending.get(m.id); this.pending.delete(m.id);
        m.error ? rej(new Error(JSON.stringify(m.error))) : res(m.result);
      }
    });
  }
  send(method, params) {
    const id = ++this.id;
    return new Promise((res, rej) => {
      this.pending.set(id, { res, rej });
      this.ws.send(JSON.stringify({ id, method, params: params || {} }));
    });
  }
  async evalJs(expr) {
    const r = await this.send('Runtime.evaluate', {
      expression: expr, returnByValue: true, awaitPromise: true
    });
    if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || 'eval failed');
    return r.result.value;
  }
}

async function main() {
  const chrome = spawn(CHROME, [
    '--headless=new', `--remote-debugging-port=${PORT}`, '--remote-allow-origins=*',
    '--disable-gpu', '--hide-scrollbars', '--no-first-run', '--no-default-browser-check',
    '--user-data-dir=/tmp/leafchrome', '--window-size=1440,900'
  ], { stdio: 'ignore' });

  let wsUrl = null;
  for (let i = 0; i < 60 && !wsUrl; i++) {
    await sleep(250);
    try {
      const list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
      const page = list.find((t) => t.type === 'page');
      if (page) wsUrl = page.webSocketDebuggerUrl;
    } catch (e) { /* not up yet */ }
  }
  if (!wsUrl) throw new Error('chrome did not come up');

  const ws = new WebSocket(wsUrl);
  await new Promise((r) => ws.addEventListener('open', r));
  const cdp = new CDP(ws);
  await cdp.send('Page.enable');
  await cdp.send('Runtime.enable');

  let FAIL = 0;
  const ok = (c, label, detail) => {
    if (!c) FAIL++;
    console.log(`  [${c ? 'PASS' : 'FAIL'}] ${label}${detail !== undefined ? '  ->  ' + detail : ''}`);
  };

  async function loadAt(w, h, dpr) {
    await cdp.send('Emulation.setDeviceMetricsOverride', {
      width: w, height: h, deviceScaleFactor: dpr, mobile: false
    });
    await cdp.send('Page.navigate', { url: URL + '?t=' + Date.now() });
    await sleep(1400);                        // load + sheets decode
    await cdp.evalJs(`window.__p={n:0,t0:performance.now(),worst:0,last:performance.now()};
      (function f(){const now=performance.now();const d=now-window.__p.last;window.__p.last=now;
       if(window.__p.n>10&&d>window.__p.worst)window.__p.worst=d;window.__p.n++;
       requestAnimationFrame(f);})();`);
  }
  const probe = () => cdp.evalJs(`(()=>{const p=window.__p,el=performance.now()-p.t0;
    return {fps:+(p.n/(el/1000)).toFixed(1), worstFrameMs:+p.worst.toFixed(1),
            count:window.leafSystem.count(),
            stats:window.leafSystem._internals.stats(),
            geom:window.leafSystem._internals.geom()};})()`);
  async function shot(name) {
    const r = await cdp.send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(path.join(OUT, name), Buffer.from(r.data, 'base64'));
  }

  console.log('REAL BROWSER CHECK — headless Chrome over CDP, real time\n');

  /* -------- 1. does it actually animate, and at what rate ---------------- */
  console.log('1. 1440x900 @dpr1, intensity 1.0');
  await loadAt(1440, 900, 1);
  await cdp.evalJs('window.leafSystem.setIntensity(1.0)');
  await sleep(6000);
  let p = await probe();
  console.log(`      real fps=${p.fps}  worst frame=${p.worstFrameMs}ms  live=${p.count}`);
  console.log(`      simTime=${p.stats.simTime.toFixed(1)}s spawned=${p.stats.spawned}` +
              ` exitLeft=${p.stats.exitLeft} landed=${p.stats.landed}`);
  ok(p.stats.simTime > 4, 'the simulation is actually advancing', `${p.stats.simTime.toFixed(1)}s`);
  ok(p.count > 60, 'a full population builds up at intensity 1', `${p.count} leaves`);
  ok(p.stats.exitLeft > 0, 'leaves are reaching the left edge', p.stats.exitLeft);
  await shot('real_1440_i10.png');

  /* -------- 2. sustained load: 250+ leaves ------------------------------- */
  console.log('\n2. sustained load at intensity 1.2');
  await cdp.evalJs('window.leafSystem.setIntensity(1.2)');
  await sleep(3000);
  await cdp.evalJs('window.__p.n=0;window.__p.t0=performance.now();window.__p.worst=0;window.__p.last=performance.now();');
  let peak = 0;
  for (let i = 0; i < 14; i++) { await sleep(1000); const q = await probe(); peak = Math.max(peak, q.count); }
  p = await probe();
  console.log(`      real fps=${p.fps} over 14 s  worst frame=${p.worstFrameMs}ms` +
              `  live now=${p.count}  peak live=${peak}`);
  ok(p.fps > 55, 'holds ~60 fps under sustained maximum load', `${p.fps} fps`);
  ok(p.worstFrameMs < 40, 'no frame spikes', `worst ${p.worstFrameMs} ms`);
  await shot('real_1440_i12.png');

  /* -------- 3. mobile ---------------------------------------------------- */
  console.log('\n3. 390x844 @dpr3 (capped to 1.5), intensity 1.0');
  await loadAt(390, 844, 3);
  await cdp.evalJs('window.leafSystem.setIntensity(1.0)');
  await sleep(7000);
  p = await probe();
  const c = await cdp.evalJs(`(()=>{const c=document.getElementById('leaf-canvas');
     return {backing:c.width+'x'+c.height, css:c.style.width+'x'+c.style.height, dpr:devicePixelRatio};})()`);
  console.log(`      real fps=${p.fps}  live=${p.count}  dpr=${c.dpr} -> backing ${c.backing} css ${c.css}`);
  ok(c.backing === '585x1266', 'backing store uses the capped 1.5 dpr, not 3', c.backing);
  ok(p.count > 50, 'population builds on a phone viewport too', p.count);
  ok(p.fps > 55, 'holds 60 fps on the phone viewport', `${p.fps} fps`);
  await shot('real_390_i10.png');

  /* -------- 4. wide ------------------------------------------------------ */
  console.log('\n4. 2560x1440 @dpr1, intensity 1.0');
  await loadAt(2560, 1440, 1);
  await cdp.evalJs('window.leafSystem.setIntensity(1.0)');
  await sleep(7000);
  p = await probe();
  console.log(`      real fps=${p.fps}  worst frame=${p.worstFrameMs}ms  live=${p.count}` +
              `  exitLeft=${p.stats.exitLeft} landed=${p.stats.landed}`);
  ok(p.fps > 55, 'holds 60 fps at 2560 wide', `${p.fps} fps`);
  ok(p.stats.landed > 0, 'leaves still reach the ground at 2560 wide', p.stats.landed);
  await shot('real_2560_i10.png');

  /* -------- 5. intensity extremes ---------------------------------------- */
  console.log('\n5. intensity 0 and the tree-off view');
  await loadAt(1440, 900, 1);
  await cdp.evalJs('window.leafSystem.setIntensity(0, true)');
  await sleep(8000);
  p = await probe();
  console.log(`      intensity 0: live=${p.count} spawned=${p.stats.spawned}` +
              ` landed=${p.stats.landed} (a trickle that falls and settles)`);
  ok(p.count > 0, 'still alive at intensity 0', p.count);
  await shot('real_1440_i00.png');

  await cdp.evalJs('window.leafSystem.setIntensity(1.0)');
  await sleep(7000);
  await cdp.evalJs("document.getElementById('b-tree').click(); document.getElementById('panel').style.display='none';");
  await sleep(120);
  await shot('real_1440_clean.png');
  console.log('      captured a clean frame with the scaffolding hidden');

  /* -------- 6. reduced motion -------------------------------------------- */
  console.log('\n6. prefers-reduced-motion (real media emulation)');
  await cdp.send('Emulation.setEmulatedMedia', {
    features: [{ name: 'prefers-reduced-motion', value: 'reduce' }]
  });
  await loadAt(1440, 900, 1);
  await sleep(2500);
  const rm = await cdp.evalJs(`(()=>{const S=window.leafSystem;const a=S._internals.arrays;
     const x0=Array.from(a.x).join(',');return {count:S.count(),running:S._internals.isRunning(),
     sim:S._internals.stats().simTime, snap:x0};})()`);
  await sleep(2500);
  const rm2 = await cdp.evalJs(`(()=>{const S=window.leafSystem;const a=S._internals.arrays;
     return {sim:S._internals.stats().simTime, snap:Array.from(a.x).join(',')};})()`);
  console.log(`      live=${rm.count} running=${rm.running} simTime=${rm.sim.toFixed(3)}s` +
              ` -> after 2.5 more s simTime=${rm2.sim.toFixed(3)}s`);
  ok(rm.running === false, 'rAF loop never started under reduced motion');
  ok(rm.snap === rm2.snap, 'not a single leaf moved in 2.5 s');
  ok(rm.count > 0, 'a static frame of leaves is still drawn', rm.count);
  await shot('real_reduced_motion.png');
  await cdp.send('Emulation.setEmulatedMedia', { features: [] });

  console.log(`\n${FAIL === 0 ? 'ALL BROWSER CHECKS PASSED' : FAIL + ' BROWSER CHECK(S) FAILED'}`);
  ws.close(); chrome.kill();
  process.exit(FAIL === 0 ? 0 : 1);
}
main().catch((e) => { console.error(e); process.exit(2); });
