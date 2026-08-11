/* Minimal CDP driver: launches an isolated headless Chrome, loads the demo
   over file:// (the real delivery path), measures and screenshots. */
const { spawn } = require("child_process");
const fs = require("fs"), path = require("path");

const SHELL = "/Users/iliaskalalou/Library/Caches/ms-playwright/" +
  "chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell";
const DIR = __dirname;

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function main() {
  const W = +process.argv[2] || 1440, H = +process.argv[3] || 900;
  const tag = process.argv[4] || `${W}x${H}`;
  const script = process.argv[5] || "";
  const port = 9400 + (process.pid % 400);

  const proc = spawn(SHELL, [
    `--remote-debugging-port=${port}`,
    `--window-size=${W},${H}`,
    "--hide-scrollbars",
    "--no-sandbox",
    "--force-device-scale-factor=1",
    "--user-data-dir=" + path.join(DIR, ".chrome-" + port),
    "about:blank"
  ], { stdio: ["ignore", "pipe", "pipe"] });

  let wsUrl = null;
  proc.stderr.on("data", d => {
    const m = String(d).match(/ws:\/\/[^\s]+/);
    if (m && !wsUrl) wsUrl = m[0];
  });
  for (let i = 0; i < 100 && !wsUrl; i++) await sleep(100);
  if (!wsUrl) { console.error("no ws url"); proc.kill(); process.exit(1); }

  const ws = new WebSocket(wsUrl);
  await new Promise(r => ws.onopen = r);
  let id = 0; const waiting = new Map();
  const logs = [];
  ws.onmessage = e => {
    const m = JSON.parse(e.data);
    if (m.id && waiting.has(m.id)) { waiting.get(m.id)(m); waiting.delete(m.id); }
    if (m.method === "Runtime.consoleAPICalled")
      logs.push(m.params.args.map(a => a.value).join(" "));
    if (m.method === "Runtime.exceptionThrown")
      logs.push("EXCEPTION " + JSON.stringify(m.params.exceptionDetails.text) + " " +
                (m.params.exceptionDetails.exception || {}).description);
    if (m.method === "Log.entryAdded" && m.params.entry.level === "error")
      logs.push("LOG_ERROR " + m.params.entry.text);
  };
  const send = (method, params) => new Promise(res => {
    const i = ++id; waiting.set(i, res);
    ws.send(JSON.stringify({ id: i, method, params: params || {} }));
  });

  // attach to the page target
  const { result: { targetInfos } } = await send("Target.getTargets");
  const pageT = targetInfos.find(t => t.type === "page");
  const { result: { sessionId } } = await send("Target.attachToTarget",
    { targetId: pageT.targetId, flatten: true });
  const sendS = (method, params) => new Promise(res => {
    const i = ++id; waiting.set(i, res);
    ws.send(JSON.stringify({ id: i, sessionId, method, params: params || {} }));
  });

  await sendS("Runtime.enable"); await sendS("Log.enable"); await sendS("Page.enable");
  await sendS("Emulation.setDeviceMetricsOverride",
    { width: W, height: H, deviceScaleFactor: +process.env.DSF || 1, mobile: false });
  if (process.env.REDUCE)
    await sendS("Emulation.setEmulatedMedia",
      { features: [{ name: "prefers-reduced-motion", value: "reduce" }] });

  const url = "file://" + path.join(DIR, "demo.html");
  await sendS("Page.navigate", { url });
  await sleep(2500);

  const evalJs = async expr => {
    const r = await sendS("Runtime.evaluate",
      { expression: expr, awaitPromise: true, returnByValue: true });
    if (r.result && r.result.exceptionDetails)
      return { __err: JSON.stringify(r.result.exceptionDetails) };
    return r.result.result.value;
  };

  const out = {};
  out.loaded = await evalJs("!!window.leafSystem");
  if (script) await evalJs(script);
  await sleep(7000);
  out.stats = await evalJs("JSON.stringify(window.leafSystem.stats())");
  out.fps = await evalJs(`(async()=>{let n=0;const t0=performance.now();
      await new Promise(r=>{function f(){n++;if(performance.now()-t0<3000)requestAnimationFrame(f);else r();}requestAnimationFrame(f);});
      return (n*1000/(performance.now()-t0)).toFixed(1);})()`);
  out.dpr = await evalJs("[window.devicePixelRatio, document.getElementById('stage').width, window.innerWidth].join('/')");
  if (process.env.PERF) out.perf = await evalJs(`(async()=>{
    const g=[]; let p=performance.now();
    await new Promise(r=>{function f(){const n=performance.now();g.push(n-p);p=n;
      if(g.length<600)requestAnimationFrame(f);else r();}requestAnimationFrame(f);});
    g.sort((a,b)=>a-b);
    const s=window.leafSystem.stats();
    return JSON.stringify({live:s.live,emaMs:+s.ms.toFixed(3),
      gapMedian:+g[300].toFixed(2),gapP95:+g[570].toFixed(2),gapMax:+g[599].toFixed(2),
      over16:g.filter(v=>v>16.9).length});})()`);

  const shot = await sendS("Page.captureScreenshot", { format: "png" });
  fs.writeFileSync(path.join(DIR, `shot_${tag}.png`),
    Buffer.from(shot.result.data, "base64"));

  console.log(JSON.stringify({ tag, ...out, logs: logs.slice(0, 12) }, null, 1));
  ws.close(); proc.kill();
  await sleep(300);
  fs.rmSync(path.join(DIR, ".chrome-" + port), { recursive: true, force: true });
  process.exit(0);
}
main().catch(e => { console.error(e); process.exit(1); });
