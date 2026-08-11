/* Headless harness: extracts the <script> from demo.html and runs the REAL code
   under a DOM stub, so what is tested is exactly what ships. */
const fs = require("fs"), vm = require("vm"), path = require("path");

const HTML = fs.readFileSync(path.join(__dirname, "demo.html"), "utf8");
const m = HTML.match(/<script>([\s\S]*?)<\/script>/);
if (!m) throw new Error("no <script> found");
const SRC = m[1];

function makeCtx(rec) {
  const c = {
    filter: "none", globalAlpha: 1, globalCompositeOperation: "source-over",
    fillStyle: "#000", strokeStyle: "#000", lineWidth: 1,
    setTransform(a, b, cc, d, e, f) {
      rec.xf++;
      if ([a, b, cc, d, e, f].some(v => !Number.isFinite(v))) rec.badXf++;
    },
    drawImage() { rec.draws++; },
    fillRect() {}, clearRect() {}, beginPath() {}, moveTo() {}, lineTo() {},
    closePath() {}, fill() {}, stroke() {}, ellipse() {}, arc() {}, save() {}, restore() {}
  };
  return c;
}

function run(opts) {
  opts = opts || {};
  const rec = { draws: 0, xf: 0, badXf: 0, rafCalls: 0 };
  let rafCb = null, rafId = 0;

  const mkEl = () => ({
    style: {}, textContent: "", value: "0", width: 0, height: 0,
    addEventListener(k, fn) { (this._l = this._l || {})[k] = fn; },
    getContext() { return makeCtx(rec); }
  });
  const els = {};
  const doc = {
    hidden: false,
    getElementById(id) { return els[id] || (els[id] = mkEl()); },
    createElement() {
      const cv = { width: 0, height: 0, style: {} };
      cv.getContext = () => makeCtx(rec);
      return cv;
    },
    addEventListener(k, fn) { (doc._l = doc._l || {})[k] = fn; }
  };

  const win = {
    innerWidth: opts.w || 1440,
    innerHeight: opts.h || 900,
    devicePixelRatio: opts.dpr || 2,
    matchMedia: () => ({ matches: !!opts.reduce }),
    addEventListener(k, fn) { (win._l = win._l || {})[k] = fn; },
    requestAnimationFrame(cb) { rec.rafCalls++; rafCb = cb; return ++rafId; },
    cancelAnimationFrame() { rafCb = null; }
  };

  let nowMs = 1000;
  const sandbox = {
    window: win, document: doc, console,
    performance: { now: () => nowMs },
    Image: class {
      constructor() { this.onload = null; this.onerror = null; }
      set src(v) { this._src = v; if (this.onload) this.onload(); }
      get src() { return this._src; }
    },
    Math, isFinite, Number, Array, Int32Array, Float32Array, Object, JSON, String
  };
  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(SRC, sandbox, { filename: "demo.html:script" });

  return {
    rec, win, doc, els,
    sys: win.leafSystem,
    // advance one rAF tick of `dt` seconds through the REAL frame() callback
    tick(dt) {
      if (!rafCb) return false;
      nowMs += dt * 1000;
      const cb = rafCb; rafCb = null;
      cb(nowMs);
      return true;
    },
    hasRaf: () => !!rafCb,
    setNow: v => { nowMs = v; },
    now: () => nowMs
  };
}

module.exports = { run, SRC };
