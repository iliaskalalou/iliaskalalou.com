"use client";

import { Fragment, useSyncExternalStore, type ReactNode } from "react";
import { motion, type Variants } from "framer-motion";

const EASE = [0.16, 1, 0.3, 1] as const;
const VIEWPORT = { once: true, margin: "0px 0px -12% 0px" } as const;
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

type RevealProps = {
  children: ReactNode;
  delay?: number;
  className?: string;
};

export default function Reveal({ children, delay = 0, className }: RevealProps) {
  const reduced = usePrefersReducedMotion();

  return (
    <motion.div
      className={className}
      initial={reduced ? false : { y: 28, opacity: 0 }}
      animate={reduced ? { y: 0, opacity: 1 } : undefined}
      whileInView={reduced ? undefined : { y: 0, opacity: 1 }}
      viewport={VIEWPORT}
      transition={
        reduced ? { duration: 0 } : { duration: 0.8, delay, ease: EASE }
      }
    >
      {children}
    </motion.div>
  );
}

const line: Variants = {
  hidden: {},
  show: (delay: number) => ({
    transition: { staggerChildren: 0.05, delayChildren: delay },
  }),
};

const wordItem: Variants = {
  hidden: { y: "130%" },
  show: { y: "0%", transition: { duration: 0.8, ease: EASE } },
};

type RevealTextProps = {
  text: string;
  className?: string;
  delay?: number;
};

export function RevealText({ text, className, delay = 0 }: RevealTextProps) {
  const reduced = usePrefersReducedMotion();

  if (reduced) {
    return <span className={className}>{text}</span>;
  }

  const words = text.trim().split(/\s+/);

  return (
    <motion.span
      className={className}
      custom={delay}
      variants={line}
      initial="hidden"
      whileInView="show"
      viewport={VIEWPORT}
    >
      <span className="sr-only">{text}</span>
      {words.map((word, i) => (
        <Fragment key={`${word}-${i}`}>
          {i > 0 ? " " : null}
          <span
            aria-hidden
            className="inline-block -mb-[0.15em] overflow-hidden pb-[0.15em]"
          >
            <motion.span variants={wordItem} className="inline-block">
              {word}
            </motion.span>
          </span>
        </Fragment>
      ))}
    </motion.span>
  );
}
