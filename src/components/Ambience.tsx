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

const GRID_TEXTURE =
  "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='72' height='72'%3E%3Cpath d='M0 .5h72M.5 0v72' fill='none' stroke='%23ededed' stroke-opacity='.045'/%3E%3C/svg%3E\")";

type GlowBlob = {
  className: string;
  background: string;
  x: number[];
  y: number[];
  duration: number;
};

const BLOBS: GlowBlob[] = [
  {
    className:
      "absolute top-[-14%] left-[-10%] h-[max(360px,44vw)] w-[max(360px,44vw)] rounded-full blur-3xl",
    background:
      "radial-gradient(closest-side, rgba(52,211,153,0.07), transparent 72%)",
    x: [0, 60, -40],
    y: [0, 36, -28],
    duration: 38,
  },
  {
    className:
      "absolute right-[-12%] bottom-[-20%] h-[max(420px,52vw)] w-[max(420px,52vw)] rounded-full blur-3xl",
    background:
      "radial-gradient(closest-side, rgba(99,102,241,0.06), transparent 72%)",
    x: [0, -70, 48],
    y: [0, -44, 30],
    duration: 44,
  },
  {
    className:
      "absolute top-[24%] right-[12%] h-[max(260px,30vw)] w-[max(260px,30vw)] rounded-full blur-3xl",
    background:
      "radial-gradient(closest-side, rgba(148,163,184,0.05), transparent 72%)",
    x: [0, 44, -32],
    y: [0, -30, 22],
    duration: 30,
  },
];

type AmbienceProps = {
  className?: string;
};

export default function Ambience({ className = "" }: AmbienceProps) {
  const reduced = usePrefersReducedMotion();

  return (
    <div
      aria-hidden
      className={`pointer-events-none absolute inset-0 -z-10 overflow-hidden ${className}`}
    >
      <div
        className="absolute inset-0"
        style={{ backgroundImage: GRID_TEXTURE }}
      />
      {BLOBS.map(({ className: blobClassName, background, x, y, duration }) =>
        reduced ? (
          <div key={background} className={blobClassName} style={{ background }} />
        ) : (
          <motion.div
            key={background}
            className={blobClassName}
            style={{ background }}
            animate={{ x, y }}
            transition={{
              duration,
              ease: "easeInOut",
              repeat: Infinity,
              repeatType: "mirror",
            }}
          />
        ),
      )}
    </div>
  );
}
