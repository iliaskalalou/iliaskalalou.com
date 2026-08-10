"use client";

import { useSyncExternalStore } from "react";
import { motion } from "framer-motion";

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

const CHAR_WIDTH = 11;
const SEPARATOR_WIDTH = 54;
const TRACK_CLASS =
  "flex w-max items-center text-sm uppercase tracking-widest text-muted md:text-base";

type MarqueeProps = {
  items: string[];
  className?: string;
  speed?: number;
};

function Sequence({ items }: { items: string[] }) {
  return (
    <>
      {items.map((item, i) => (
        <span key={`${item}-${i}`} className="flex shrink-0 items-center">
          <span className="whitespace-nowrap">{item}</span>
          <span className="mx-6 h-1 w-1 rounded-full bg-muted/50" />
        </span>
      ))}
    </>
  );
}

export default function Marquee({ items, className, speed = 80 }: MarqueeProps) {
  const reduced = usePrefersReducedMotion();

  const sequenceWidth = items.reduce(
    (total, item) => total + item.length * CHAR_WIDTH + SEPARATOR_WIDTH,
    0,
  );
  const duration = Math.max(sequenceWidth / Math.max(speed, 1), 5);

  const band = `pointer-events-none w-full overflow-hidden border-y border-line py-8${
    className ? ` ${className}` : ""
  }`;

  return (
    <div aria-hidden className={band}>
      {reduced ? (
        <div className={TRACK_CLASS}>
          <Sequence items={items} />
        </div>
      ) : (
        <motion.div
          className={TRACK_CLASS}
          animate={{ x: ["0%", "-50%"] }}
          transition={{ duration, ease: "linear", repeat: Infinity }}
        >
          <Sequence items={items} />
          <Sequence items={items} />
        </motion.div>
      )}
    </div>
  );
}
