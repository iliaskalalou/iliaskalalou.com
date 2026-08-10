"use client";

import { useCallback, useEffect, useState, useSyncExternalStore } from "react";
import type { PointerEvent as ReactPointerEvent } from "react";
import Image from "next/image";
import { motion, useMotionValue, useSpring } from "framer-motion";

const EASE = [0.16, 1, 0.3, 1] as const;
const DRIFT_SPRING = { stiffness: 90, damping: 22, mass: 0.8 } as const;
const MAX_DRIFT = 12;
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

const clamp = (value: number, limit: number) =>
  Math.max(-limit, Math.min(limit, value));

type PortraitProps = {
  className?: string;
};

const FRAME_CLASS =
  "group relative aspect-[4/5] overflow-hidden rounded-2xl border border-line bg-[#111111]";

export default function Portrait({ className }: PortraitProps) {
  const reduced = usePrefersReducedMotion();
  const [coarsePointer, setCoarsePointer] = useState(true);
  const [failed, setFailed] = useState(false);

  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const springX = useSpring(x, DRIFT_SPRING);
  const springY = useSpring(y, DRIFT_SPRING);

  useEffect(() => {
    const query = window.matchMedia("(pointer: coarse)");
    const sync = () => setCoarsePointer(query.matches);
    sync();
    query.addEventListener("change", sync);
    return () => query.removeEventListener("change", sync);
  }, []);

  const enabled = !coarsePointer && !reduced;

  useEffect(() => {
    if (enabled) return;
    x.jump(0);
    y.jump(0);
    springX.jump(0);
    springY.jump(0);
  }, [enabled, x, y, springX, springY]);

  const handleMove = useCallback(
    (event: ReactPointerEvent<HTMLDivElement>) => {
      if (event.pointerType === "touch") return;
      const rect = event.currentTarget.getBoundingClientRect();
      const offsetX = (event.clientX - rect.left) / rect.width - 0.5;
      const offsetY = (event.clientY - rect.top) / rect.height - 0.5;
      x.set(clamp(offsetX * MAX_DRIFT * 2, MAX_DRIFT));
      y.set(clamp(offsetY * MAX_DRIFT * 2, MAX_DRIFT));
    },
    [x, y],
  );

  const handleLeave = useCallback(() => {
    x.set(0);
    y.set(0);
  }, [x, y]);

  return (
    <motion.div
      className={className ? `${FRAME_CLASS} ${className}` : FRAME_CLASS}
      initial={reduced ? false : { y: 28, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={
        reduced ? { duration: 0 } : { duration: 0.9, delay: 0.2, ease: EASE }
      }
      onPointerMove={enabled ? handleMove : undefined}
      onPointerLeave={enabled ? handleLeave : undefined}
    >
      <motion.div
        className="pointer-events-none absolute inset-0 scale-[1.08] select-none"
        style={{ x: springX, y: springY }}
      >
        {failed ? (
          <div
            role="img"
            aria-label="Ilias Kalalou"
            className="absolute inset-0 flex items-center justify-center bg-linear-to-br from-[#1a1a1a] via-[#111111] to-background"
          >
            <span
              aria-hidden
              className="text-[clamp(5rem,16vw,9rem)] font-semibold tracking-tight text-muted/35"
            >
              IK
            </span>
          </div>
        ) : (
          <Image
            src="/portrait.jpg"
            alt="Ilias Kalalou"
            fill
            className="object-cover grayscale transition-[filter] duration-700 ease-[cubic-bezier(0.16,1,0.3,1)] pointer-fine:group-hover:grayscale-0 motion-reduce:transition-none"
            onError={() => setFailed(true)}
          />
        )}
      </motion.div>
    </motion.div>
  );
}
