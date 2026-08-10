"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { PointerEvent as ReactPointerEvent, ReactNode } from "react";
import { motion, useMotionValue, useReducedMotion, useSpring } from "framer-motion";

const spring = { stiffness: 150, damping: 20, mass: 0.6 } as const;

const MAX_SHIFT = 28;

const clamp = (value: number, limit: number) =>
  Math.max(-limit, Math.min(limit, value));

export type MagneticProps = {
  children: ReactNode;
  strength?: number;
  className?: string;
};

export default function Magnetic({
  children,
  strength = 0.2,
  className,
}: MagneticProps) {
  const ref = useRef<HTMLSpanElement>(null);
  const prefersReducedMotion = useReducedMotion();
  const [coarsePointer, setCoarsePointer] = useState(true);

  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const springX = useSpring(x, spring);
  const springY = useSpring(y, spring);

  useEffect(() => {
    const query = window.matchMedia("(pointer: coarse)");
    const sync = () => setCoarsePointer(query.matches);
    sync();
    query.addEventListener("change", sync);
    return () => query.removeEventListener("change", sync);
  }, []);

  const enabled = !coarsePointer && !prefersReducedMotion;

  useEffect(() => {
    if (enabled) return;
    x.jump(0);
    y.jump(0);
    springX.jump(0);
    springY.jump(0);
  }, [enabled, x, y, springX, springY]);

  const handleMove = useCallback(
    (event: ReactPointerEvent<HTMLSpanElement>) => {
      const element = ref.current;
      if (!element || event.pointerType === "touch") return;

      const rect = element.getBoundingClientRect();
      const restCenterX = rect.left + rect.width / 2 - springX.get();
      const restCenterY = rect.top + rect.height / 2 - springY.get();
      const offsetX = event.clientX - restCenterX;
      const offsetY = event.clientY - restCenterY;

      x.set(clamp(offsetX * strength, Math.min(rect.width * 0.25, MAX_SHIFT)));
      y.set(clamp(offsetY * strength, Math.min(rect.height * 0.5, MAX_SHIFT)));
    },
    [strength, x, y, springX, springY],
  );

  const handleLeave = useCallback(() => {
    x.set(0);
    y.set(0);
  }, [x, y]);

  return (
    <motion.span
      ref={ref}
      className={className ? `inline-flex ${className}` : "inline-flex"}
      style={{ x: springX, y: springY }}
      onPointerMove={enabled ? handleMove : undefined}
      onPointerLeave={enabled ? handleLeave : undefined}
    >
      {children}
    </motion.span>
  );
}
