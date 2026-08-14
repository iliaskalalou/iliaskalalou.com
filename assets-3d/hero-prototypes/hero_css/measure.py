#!/usr/bin/env python3
"""
Measurement harness. Everything reported in NOTES.md comes out of here.

  bytes  - summed from the CDP Network layer (encodedDataLength), i.e. what
           actually crossed the socket, headers included, not Content-Length.
  fps    - rAF callbacks per wall-clock second, sampled in-page.
  heap   - performance.memory.usedJSHeapSize after a forced GC where possible.
  4x cpu - Emulation.setCPUThrottlingRate(4).
"""
import json, sys, time
from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8777/hero_css/demo.html"
HEADED = "--headed" in sys.argv
SHOTS = "--shots" in sys.argv
VIEWPORTS = [("desktop", 1440, 900), ("mobile", 390, 844)]


def run():
    out = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not HEADED, args=[
            "--force-device-scale-factor=1",
            "--enable-gpu-rasterization",
        ])
        for name, w, h in VIEWPORTS:
            ctx = browser.new_context(viewport={"width": w, "height": h},
                                      device_scale_factor=2 if name == "mobile" else 1,
                                      is_mobile=(name == "mobile"),
                                      has_touch=(name == "mobile"))
            page = ctx.new_page()
            cdp = ctx.new_cdp_session(page)
            cdp.send("Network.enable")
            transferred = {}
            def on_finished(ev, store=transferred):
                store[ev["requestId"]] = ev.get("encodedDataLength", 0)
            def on_resp(ev, store=transferred):
                store.setdefault(ev["requestId"], 0)
            cdp.on("Network.loadingFinished", on_finished)

            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.on("console", lambda m: errors.append("console:" + m.text)
                    if m.type == "error" else None)

            page.goto(URL, wait_until="load")
            page.wait_for_timeout(1800)

            byte_rows = page.evaluate("""() => {
              const r = performance.getEntriesByType('resource').map(e => ({
                 n: e.name.split('/').slice(-1)[0], t: e.transferSize, d: e.decodedBodySize }));
              const nav = performance.getEntriesByType('navigation')[0];
              r.unshift({ n: 'demo.html', t: nav ? nav.transferSize : 0,
                          d: nav ? nav.decodedBodySize : 0 });
              return r;
            }""")
            cdp_total = sum(transferred.values())

            def fps_sample(seconds=4.0, label=""):
                page.evaluate("window.__f0 = window.heroDemo._dev.frames();")
                t0 = time.time()
                page.wait_for_timeout(int(seconds * 1000))
                dt = time.time() - t0
                df = page.evaluate("window.heroDemo._dev.frames() - window.__f0")
                return round(df / dt, 1)

            page.evaluate("window.heroDemo.setIntensity(0.55)")
            page.wait_for_timeout(1200)
            fps_055 = fps_sample()
            leaves_055 = page.evaluate("window.heroDemo._dev.count()")

            page.evaluate("window.heroDemo.setIntensity(1.2)")
            page.wait_for_timeout(2500)
            fps_12 = fps_sample()
            leaves_12 = page.evaluate("window.heroDemo._dev.count()")

            # pointer sweep while measuring, so the parallax cost is included
            page.evaluate("""() => {
              window.__sweep = setInterval(() => {
                const t = performance.now() / 700;
                window.heroDemo._dev.setPointer(Math.sin(t), Math.cos(t * 0.7));
              }, 16);
            }""")
            fps_par = fps_sample()
            page.evaluate("clearInterval(window.__sweep)")

            heap = page.evaluate("performance.memory ? performance.memory.usedJSHeapSize : -1")
            try:
                cdp.send("HeapProfiler.enable")
                cdp.send("HeapProfiler.collectGarbage")
                page.wait_for_timeout(400)
                heap_gc = page.evaluate("performance.memory ? performance.memory.usedJSHeapSize : -1")
            except Exception:
                heap_gc = -1

            # 4x CPU throttle
            cdp.send("Emulation.setCPUThrottlingRate", {"rate": 4})
            page.wait_for_timeout(1200)
            fps_thr = fps_sample()
            page.evaluate("window.heroDemo.setIntensity(0.55)")
            page.wait_for_timeout(1500)
            fps_thr_055 = fps_sample()
            cdp.send("Emulation.setCPUThrottlingRate", {"rate": 1})

            # parallax geometry check: measure real layer displacement
            page.evaluate("window.heroDemo.setIntensity(0.55)")
            disp = page.evaluate("""() => {
              const ids = ['fuji','pagoda','portrait','tree'];
              const pick = id => id === 'portrait'
                 ? document.getElementById('frame')
                 : document.querySelector('#' + id + ' picture');
              const at = (nx, ny) => {
                window.heroDemo._dev.setPointer(nx, ny);
                window.heroDemo._dev.settleParallax();
                const o = {};
                ids.forEach(i => { const r = pick(i).getBoundingClientRect();
                                   o[i] = [r.left, r.top, r.width]; });
                return o;
              };
              const L = at(-1, 0), R = at(1, 0);
              window.heroDemo._dev.setPointer(0, 0);
              window.heroDemo._dev.settleParallax();
              const d = {};
              ids.forEach(i => d[i] = { dx: +(R[i][0] - L[i][0]).toFixed(2),
                                        w: +L[i][2].toFixed(1) });
              return d;
            }""")

            overflow = page.evaluate(
                "({sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth,"
                " sh: document.documentElement.scrollHeight, ch: document.documentElement.clientHeight})")

            out[name] = {
                "viewport": [w, h],
                "dpr": page.evaluate("devicePixelRatio"),
                "bytes_cdp": cdp_total,
                "bytes_rows": byte_rows,
                "fps_055": fps_055, "leaves_055": leaves_055,
                "fps_12": fps_12, "leaves_12": leaves_12,
                "fps_parallax_sweep": fps_par,
                "fps_cpu4x_int12": fps_thr, "fps_cpu4x_int055": fps_thr_055,
                "heap": heap, "heap_after_gc": heap_gc,
                "parallax_travel": disp,
                "overflow": overflow,
                "errors": errors[:8],
            }
            if SHOTS:
                page.evaluate("document.getElementById('panel').style.display='none'")
                page.wait_for_timeout(300)
                page.screenshot(path="shots/%s_clean.png" % name)
                page.evaluate("document.getElementById('panel').style.display=''")
                page.screenshot(path="shots/%s_panel.png" % name)
            ctx.close()

        # reduced motion pass
        ctx = browser.new_context(viewport={"width": 1440, "height": 900},
                                  reduced_motion="reduce")
        page = ctx.new_page()
        page.goto(URL, wait_until="load")
        page.wait_for_timeout(1500)
        f0 = page.evaluate("window.heroDemo._dev.frames()")
        page.wait_for_timeout(2500)
        f1 = page.evaluate("window.heroDemo._dev.frames()")
        rm = {"frames_in_2.5s": f1 - f0,
              "leaves_drawn": page.evaluate("window.heroDemo._dev.count()"),
              "reduced_flag": page.evaluate("window.heroDemo._dev.reduced")}
        # does the pointer move anything?
        before = page.evaluate("getComputedStyle(document.getElementById('world')).transform")
        page.mouse.move(1300, 700)
        page.wait_for_timeout(500)
        after = page.evaluate("getComputedStyle(document.getElementById('world')).transform")
        rm["transform_before"] = before
        rm["transform_after"] = after
        rm["static"] = before == after
        if SHOTS:
            page.evaluate("document.getElementById('panel').style.display='none'")
            page.screenshot(path="shots/reduced_clean.png")
        out["reduced_motion"] = rm
        ctx.close()
        browser.close()
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    run()
