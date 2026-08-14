#!/usr/bin/env python3
"""Isolate what each subsystem costs. Run headed (real GPU) unless --headless."""
import json, sys, time
from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8777/hero_css/demo.html"
HEADLESS = "--headless" in sys.argv
W, H = 1440, 900
for a in sys.argv:
    if a.startswith("--vp="):
        W, H = [int(x) for x in a.split("=")[1].split("x")]

DRIVE = """() => {
  // drive the pointer from rAF, not a timer, so the measurement is not
  // polluted by an extra 60Hz task
  window.__stop = false;
  const tick = () => {
    if (window.__stop) return;
    const t = performance.now() / 700;
    window.heroDemo._dev.setPointer(Math.sin(t), Math.cos(t * 0.7));
    requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}"""


def sample(page, seconds=4.0):
    page.evaluate("window.__f0 = window.heroDemo._dev.frames()")
    t0 = time.time()
    page.wait_for_timeout(int(seconds * 1000))
    dt = time.time() - t0
    return round(page.evaluate("window.heroDemo._dev.frames() - window.__f0") / dt, 1)


with sync_playwright() as p:
    b = p.chromium.launch(headless=HEADLESS)
    ctx = b.new_context(viewport={"width": W, "height": H})
    page = ctx.new_page()
    cdp = ctx.new_cdp_session(page)
    page.goto(URL, wait_until="load")
    page.wait_for_timeout(2500)

    res = {"headless": HEADLESS, "vp": [W, H]}
    # 1. nothing: leaves paused, pointer parked
    page.evaluate("window.heroDemo.pause(); window.heroDemo._dev.setPointer(0,0)")
    page.wait_for_timeout(600)
    res["idle"] = sample(page, 3)
    # 2. parallax only
    page.evaluate(DRIVE)
    res["parallax_only"] = sample(page, 4)
    page.evaluate("window.__stop = true")
    page.wait_for_timeout(300)
    # 3. leaves only
    page.evaluate("window.heroDemo.resume(); window.heroDemo.setIntensity(0.55)")
    page.wait_for_timeout(2500)
    res["leaves_055"] = sample(page, 4)
    res["n_055"] = page.evaluate("window.heroDemo._dev.count()")
    page.evaluate("window.heroDemo.setIntensity(1.2)")
    page.wait_for_timeout(3000)
    res["leaves_12"] = sample(page, 4)
    res["n_12"] = page.evaluate("window.heroDemo._dev.count()")
    # 4. both
    page.evaluate(DRIVE)
    res["both_12"] = sample(page, 4)
    page.evaluate("window.heroDemo.setIntensity(0.55)")
    page.wait_for_timeout(2500)
    res["both_055"] = sample(page, 4)
    page.evaluate("window.__stop = true")
    # 5. 4x cpu
    cdp.send("Emulation.setCPUThrottlingRate", {"rate": 4})
    page.wait_for_timeout(1500)
    res["cpu4x_055"] = sample(page, 4)
    page.evaluate(DRIVE)
    res["cpu4x_both_055"] = sample(page, 4)
    page.evaluate("window.__stop = true")
    page.evaluate("window.heroDemo.setIntensity(1.2)")
    page.wait_for_timeout(3000)
    res["cpu4x_12"] = sample(page, 4)
    cdp.send("Emulation.setCPUThrottlingRate", {"rate": 1})
    # 6. canvas off entirely (compositing floor)
    page.evaluate("window.heroDemo.pause(); document.getElementById('leaf-canvas').style.display='none'")
    page.evaluate(DRIVE)
    res["parallax_no_canvas"] = sample(page, 3)
    page.evaluate("window.__stop = true; document.getElementById('leaf-canvas').style.display=''")
    # 7. masks off
    page.evaluate("""() => {
      document.querySelectorAll('#fuji picture,#pagoda picture,#tree picture')
        .forEach(e => { e.style.webkitMaskImage='none'; e.style.maskImage='none'; });
    }""")
    page.evaluate(DRIVE)
    res["parallax_no_masks"] = sample(page, 3)
    page.evaluate("window.__stop = true")

    # heap, exactly
    try:
        cdp.send("HeapProfiler.enable")
        cdp.send("HeapProfiler.collectGarbage")
        page.wait_for_timeout(500)
        res["heap_bytes"] = cdp.send("Runtime.getHeapUsage")["usedSize"]
        res["heap_total"] = cdp.send("Runtime.getHeapUsage")["totalSize"]
    except Exception as e:
        res["heap_bytes"] = str(e)
    res["refresh_hint"] = page.evaluate("""() => new Promise(r => {
        let n=0, t0=performance.now();
        const f=()=>{ if(++n>=30) return r(Math.round(29000/(performance.now()-t0)));
                      requestAnimationFrame(f); };
        requestAnimationFrame(f); })""")
    print(json.dumps(res, indent=1))
    b.close()
