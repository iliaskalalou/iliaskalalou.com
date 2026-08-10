"use client";

import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";

const GREETINGS = [
  "Hello",
  "Bonjour",
  "Ciao",
  "Hola",
  "Olá",
  "こんにちは",
  "مرحبا",
  "Namaste",
];

const EASE = [0.16, 1, 0.3, 1] as const;
const STEP_MS = 110;
const EXIT_DURATION = 0.6;

export default function Preloader() {
  const shouldReduceMotion = useReducedMotion();
  const shouldPlay = useRef<boolean | null>(null);
  const [active, setActive] = useState(false);
  const [index, setIndex] = useState(0);

  useEffect(() => {
    const root = document.documentElement;

    if (shouldPlay.current === null) {
      shouldPlay.current =
        root.dataset.preloader === "pending" && !shouldReduceMotion;
    }

    if (!shouldPlay.current) {
      delete root.dataset.preloader;
      return;
    }

    setActive(true);

    const step = setInterval(() => {
      setIndex((i) => Math.min(i + 1, GREETINGS.length - 1));
    }, STEP_MS);

    const end = setTimeout(() => {
      clearInterval(step);
      delete root.dataset.preloader;
      setActive(false);
    }, GREETINGS.length * STEP_MS);

    return () => {
      clearInterval(step);
      clearTimeout(end);
      delete root.dataset.preloader;
    };
  }, [shouldReduceMotion]);

  return (
    <AnimatePresence>
      {active && (
        <motion.div
          key="preloader"
          data-preloader-overlay=""
          aria-hidden="true"
          exit={{ y: "-100%" }}
          transition={{ duration: EXIT_DURATION, ease: EASE }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-background will-change-transform"
        >
          <motion.div
            exit={{ opacity: 0, y: -24 }}
            transition={{ duration: 0.3, ease: EASE }}
            className="flex items-center gap-4 px-6"
          >
            <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-foreground md:h-2 md:w-2" />
            <motion.span
              key={index}
              dir="auto"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.18, ease: EASE }}
              className="text-3xl font-medium tracking-tight md:text-5xl"
            >
              {GREETINGS[index]}
            </motion.span>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
