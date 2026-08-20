"use client";

import { useEffect, useLayoutEffect, useRef, useState, useSyncExternalStore } from "react";
import { motion, useAnimationFrame, useMotionValue } from "framer-motion";

const REDUCED_MOTION_QUERY = "(prefers-reduced-motion: reduce)";

let reducedMotionQuery: MediaQueryList | null = null;

function getReducedMotionQuery() {
  reducedMotionQuery ??= window.matchMedia(REDUCED_MOTION_QUERY);
  return reducedMotionQuery;
}

function subscribeToReducedMotion(onChange: () => void) {
  const query = getReducedMotionQuery();
  query.addEventListener("change", onChange);
  return () => query.removeEventListener("change", onChange);
}

function usePrefersReducedMotion() {
  return useSyncExternalStore(
    subscribeToReducedMotion,
    () => getReducedMotionQuery().matches,
    () => false,
  );
}

const TRACK_CLASS =
  "flex w-max items-center text-sm uppercase tracking-widest text-muted md:text-base";

// Server render and first client render must match, so start at a count that
// already fills a wide desktop; the measured count replaces it after mount.
const INITIAL_COPIES = 4;

type MarqueeProps = {
  items: string[];
  className?: string;
  /** pixels per second */
  speed?: number;
};

function Sequence({ items }: { items: string[] }) {
  return (
    <>
      {items.map((item, i) => (
        <span key={`${item}-${i}`} className="flex shrink-0 items-center">
          <span className="whitespace-nowrap">{item}</span>
          <span className="mx-6 h-1 w-1 shrink-0 rounded-full bg-muted/50" />
        </span>
      ))}
    </>
  );
}

export default function Marquee({ items, className, speed = 70 }: MarqueeProps) {
  const reduced = usePrefersReducedMotion();
  const bandRef = useRef<HTMLDivElement>(null);
  const seqRef = useRef<HTMLDivElement>(null);
  const [copies, setCopies] = useState(INITIAL_COPIES);
  const seqWidth = useRef(0);
  const x = useMotionValue(0);

  // One sequence is measured directly; enough copies are rendered that the
  // track always spans the viewport plus a full sequence, so the seam never
  // reaches the screen and no gap can open.
  useLayoutEffect(() => {
    const measure = () => {
      const seq = seqRef.current;
      const band = bandRef.current;
      if (!seq || !band) return;
      const w = seq.getBoundingClientRect().width;
      if (!w) return;
      seqWidth.current = w;
      setCopies(Math.max(2, Math.ceil(band.clientWidth / w) + 1));
    };
    measure();
    const ro = new ResizeObserver(measure);
    if (bandRef.current) ro.observe(bandRef.current);
    if (seqRef.current) ro.observe(seqRef.current);
    return () => ro.disconnect();
  }, [items]);

  useEffect(() => {
    if (reduced) x.set(0);
  }, [reduced, x]);

  // Advancing by real pixels and wrapping on the measured sequence width keeps
  // the speed identical whatever the words are, and the wrap invisible.
  useAnimationFrame((_, delta) => {
    if (reduced) return;
    const w = seqWidth.current;
    if (!w) return;
    const next = x.get() - (speed * delta) / 1000;
    x.set(next <= -w ? next + w : next);
  });

  const band = `pointer-events-none w-full overflow-hidden border-y border-line py-8${
    className ? ` ${className}` : ""
  }`;

  return (
    <div aria-hidden ref={bandRef} className={band}>
      <motion.div className={TRACK_CLASS} style={reduced ? undefined : { x }}>
        <div ref={seqRef} className="flex shrink-0 items-center">
          <Sequence items={items} />
        </div>
        {Array.from({ length: copies - 1 }, (_, i) => (
          <div key={i} className="flex shrink-0 items-center">
            <Sequence items={items} />
          </div>
        ))}
      </motion.div>
    </div>
  );
}
