"use client";

import { useId } from "react";
import { motion, useReducedMotion } from "framer-motion";

const RING_TEXT = "OPEN TO WORK • AI & DATA • FREELANCE • ";
const RING_LENGTH = 314;
const SPIN = { duration: 21, ease: "linear", repeat: Infinity } as const;

type RotatingBadgeProps = {
  className?: string;
  href?: string;
};

export default function RotatingBadge({ className, href }: RotatingBadgeProps) {
  const reduced = useReducedMotion();
  const pathId = useId();

  const base = "block h-[120px] w-[120px] text-muted";

  const inner = (
    <span className="relative block h-full w-full">
      <motion.span
        aria-hidden
        className="absolute inset-0 block"
        animate={reduced ? { rotate: 0 } : { rotate: 360 }}
        transition={reduced ? { duration: 0 } : SPIN}
      >
        <svg viewBox="0 0 120 120" className="h-full w-full">
          <defs>
            <path
              id={pathId}
              d="M 60 60 m -50 0 a 50 50 0 1 1 100 0 a 50 50 0 1 1 -100 0"
              fill="none"
            />
          </defs>
          <text fill="currentColor" fontSize="10" letterSpacing="2">
            <textPath
              href={`#${pathId}`}
              textLength={RING_LENGTH}
              lengthAdjust="spacing"
            >
              {RING_TEXT}
            </textPath>
          </text>
        </svg>
      </motion.span>
      <svg
        aria-hidden
        viewBox="0 0 16 16"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="absolute top-1/2 left-1/2 h-4 w-4 -translate-x-1/2 -translate-y-1/2"
      >
        <path d="M8 3v10" />
        <path d="M3.5 8.5 8 13l4.5-4.5" />
      </svg>
    </span>
  );

  if (href) {
    return (
      <a
        href={href}
        aria-label="Scroll to work"
        className={className ? `${base} ${className}` : base}
      >
        {inner}
      </a>
    );
  }

  return (
    <span
      aria-hidden
      className={
        className
          ? `${base} pointer-events-none ${className}`
          : `${base} pointer-events-none`
      }
    >
      {inner}
    </span>
  );
}
