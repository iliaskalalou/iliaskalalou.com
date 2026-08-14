import json,time,sys
from playwright.sync_api import sync_playwright
URL="http://127.0.0.1:8777/hero_css/demo.html"
DRIVE="""()=>{window.__stop=false;const t=()=>{if(window.__stop)return;const q=performance.now()/700;
 window.heroDemo._dev.setPointer(Math.sin(q),Math.cos(q*0.7));requestAnimationFrame(t);};requestAnimationFrame(t);}"""
JANK="""()=>{window.__d=[];let p=performance.now();window.__jankStop=false;
 const f=(t)=>{if(window.__jankStop)return;window.__d.push(t-p);p=t;requestAnimationFrame(f);};requestAnimationFrame(f);}"""
def run(w,h,dsf,mob,label,headless):
    o={"label":label,"vp":[w,h],"dpr":dsf,"headless":headless}
    with sync_playwright() as p:
        b=p.chromium.launch(headless=headless,args=["--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding","--disable-features=CalculateNativeWinOcclusion"])
        ctx=b.new_context(viewport={"width":w,"height":h},device_scale_factor=dsf,
                          is_mobile=mob,has_touch=mob)
        pg=ctx.new_page(); cdp=ctx.new_cdp_session(pg); cdp.send("Network.enable")
        tot={}
        cdp.on("Network.loadingFinished",lambda e: tot.__setitem__(e["requestId"],e.get("encodedDataLength",0)))
        pg.goto(URL,wait_until="load"); pg.wait_for_timeout(2500)
        o["bytes_wire"]=sum(tot.values())
        o["bytes_rows"]=pg.evaluate("""()=>{const n=performance.getEntriesByType('navigation')[0];
          const r=[['demo.html',n.transferSize,n.decodedBodySize]];
          performance.getEntriesByType('resource').forEach(e=>r.push([e.name.split('/').pop(),e.transferSize,e.decodedBodySize]));
          return r;}""")
        def block(sec=5.0):
            pg.evaluate("window.heroDemo._dev.resetWork()"); pg.evaluate(JANK)
            f0=pg.evaluate("window.heroDemo._dev.frames()"); t0=time.time()
            pg.wait_for_timeout(int(sec*1000)); dt=time.time()-t0
            pg.evaluate("window.__jankStop=true")
            d=pg.evaluate("window.__d.slice(2)")
            d=sorted(d)
            st=pg.evaluate("window.heroDemo._dev.frameWork()") or {}
            n=len(d)
            return {"fps":round((pg.evaluate("window.heroDemo._dev.frames()")-f0)/dt,1),
                    "leaves":pg.evaluate("window.heroDemo._dev.count()"),
                    "dt_p50":round(d[n//2],2) if n else None,
                    "dt_p99":round(d[min(n-1,int(n*0.99))],2) if n else None,
                    "dt_max":round(d[-1],2) if n else None,
                    "work_mean":st.get("mean"),"work_p95":st.get("p95"),"work_max":st.get("max")}
        pg.evaluate("window.heroDemo.setIntensity(0.55)"); pg.wait_for_timeout(3000)
        o["idle_leaves_only"]=block()
        pg.evaluate(DRIVE); o["leaves_plus_parallax"]=block(); pg.evaluate("window.__stop=true")
        pg.evaluate("window.heroDemo.setIntensity(1.2)"); pg.wait_for_timeout(3500)
        pg.evaluate(DRIVE); o["max_intensity_plus_parallax"]=block()
        cdp.send("Emulation.setCPUThrottlingRate",{"rate":4}); pg.wait_for_timeout(1500)
        o["cpu4x_max_intensity"]=block()
        pg.evaluate("window.__stop=true"); pg.evaluate("window.heroDemo.setIntensity(0.55)")
        pg.wait_for_timeout(2500); pg.evaluate(DRIVE)
        o["cpu4x_nominal"]=block()
        cdp.send("Emulation.setCPUThrottlingRate",{"rate":1}); pg.evaluate("window.__stop=true")
        busy="()=>{const t0=performance.now();let x=0;for(let i=0;i<4e6;i++)x+=Math.sqrt(i);return performance.now()-t0;}"
        o["busy_1x_ms"]=round(pg.evaluate(busy),1)
        cdp.send("Emulation.setCPUThrottlingRate",{"rate":4}); pg.wait_for_timeout(300)
        o["busy_4x_ms"]=round(pg.evaluate(busy),1)
        cdp.send("Emulation.setCPUThrottlingRate",{"rate":1})
        cdp.send("HeapProfiler.enable"); cdp.send("HeapProfiler.collectGarbage"); pg.wait_for_timeout(500)
        hu=cdp.send("Runtime.getHeapUsage")
        o["heap_used_bytes"]=int(hu["usedSize"]); o["heap_total_bytes"]=int(hu["totalSize"])
        b.close()
    return o
res=[]
for args in [(1440,900,2,False,"desktop 1440x900 @2dpr"),(1440,900,1,False,"desktop 1440x900 @1dpr"),
             (390,844,3,True,"mobile 390x844 @3dpr")]:
    for k in range(3):
        try: res.append(run(*args,headless=False)); break
        except Exception as e: print("retry",args[4],str(e)[:60],file=sys.stderr); time.sleep(2)
open("m_final.json","w").write(json.dumps(res,indent=1))
for r in res:
    print("\n== %s  dpr=%s  wire=%d B (%.1f KB)  heap=%d B"%(r["label"],r["dpr"],r["bytes_wire"],r["bytes_wire"]/1024,r["heap_used_bytes"]))
    print("   busy loop 1x=%sms 4x=%sms"%(r["busy_1x_ms"],r["busy_4x_ms"]))
    for k in ["idle_leaves_only","leaves_plus_parallax","max_intensity_plus_parallax","cpu4x_max_intensity","cpu4x_nominal"]:
        v=r[k]; print("   %-28s fps %5.1f  frame dt p50 %5.2f p99 %6.2f max %6.2f | js work mean %s p95 %s | %d leaves"%(
            k,v["fps"],v["dt_p50"],v["dt_p99"],v["dt_max"],v["work_mean"],v["work_p95"],v["leaves"]))
