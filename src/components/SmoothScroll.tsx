"use client";

import { useEffect, type ReactNode } from "react";
import { useReducedMotion } from "framer-motion";
import Lenis from "lenis";
import "lenis/dist/lenis.css";

const easeOutExpo = (t: number) => (t === 1 ? 1 : 1 - Math.pow(2, -10 * t));

export default function SmoothScroll({ children }: { children: ReactNode }) {
  const reduceMotion = useReducedMotion();

  useEffect(() => {
    if (reduceMotion) return;

    const root = document.documentElement;
    const previousScrollBehavior = root.style.scrollBehavior;
    root.style.scrollBehavior = "auto";

    const lenis = new Lenis({
      lerp: 0.1,
      syncTouch: false,
      autoRaf: false,
    });

    let frame = 0;
    const raf = (time: number) => {
      lenis.raf(time);
      frame = requestAnimationFrame(raf);
    };
    frame = requestAnimationFrame(raf);

    const onClick = (event: MouseEvent) => {
      if (
        event.defaultPrevented ||
        event.button !== 0 ||
        event.metaKey ||
        event.ctrlKey ||
        event.shiftKey ||
        event.altKey
      ) {
        return;
      }

      const node = event.target;
      if (!(node instanceof Element)) return;

      const anchor = node.closest("a[href]");
      if (!(anchor instanceof HTMLAnchorElement)) return;
      if (anchor.hasAttribute("download")) return;
      if (anchor.target && anchor.target !== "_self") return;

      const href = anchor.getAttribute("href");
      if (!href?.includes("#")) return;

      const url = new URL(anchor.href, window.location.href);
      if (
        url.origin !== window.location.origin ||
        url.pathname !== window.location.pathname ||
        url.search !== window.location.search
      ) {
        return;
      }

      const id = decodeURIComponent(url.hash.slice(1));
      const target = id ? document.getElementById(id) : null;
      if (id && !target) return;

      event.preventDefault();
      lenis.scrollTo(target ?? 0, { duration: 1.2, easing: easeOutExpo });
      window.history.pushState(null, "", href);

      if (target) {
        if (!target.hasAttribute("tabindex")) {
          target.setAttribute("tabindex", "-1");
        }
        target.focus({ preventScroll: true });
      }
    };

    document.addEventListener("click", onClick);

    return () => {
      cancelAnimationFrame(frame);
      document.removeEventListener("click", onClick);
      lenis.destroy();
      root.style.scrollBehavior = previousScrollBehavior;
    };
  }, [reduceMotion]);

  return <>{children}</>;
}
