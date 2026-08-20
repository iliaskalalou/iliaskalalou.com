"use client";

import Image from "next/image";
import { useCallback, useEffect, useState } from "react";
import type { CSSProperties, PointerEvent as ReactPointerEvent } from "react";
import {
  motion,
  useMotionValue,
  useReducedMotion,
  useSpring,
  useTransform,
} from "framer-motion";
import Magnetic from "@/components/Magnetic";

/* House easing. */
const EASE = [0.16, 1, 0.3, 1] as const;
const DRIFT = { stiffness: 52, damping: 18, mass: 1 } as const;

/*
 * The photograph is a cut-out wearing a nearly white shirt on a nearly white
 * page: measured, the shirt sits at rgb(230,233,232) against a rgb(250,250,249)
 * background, so his silhouette all but disappears. Three things fix it here.
 *
 * 1. A tonal field anchored to the right edge (bottom edge on mobile) that
 *    lands near rgb(205,199,190) exactly where his body is widest — roughly a
 *    30-point luminance drop behind the brightest part of him.
 * 2. The field is masked so it dissolves toward the top, where his dark hair
 *    already carries all the contrast it needs. Tone goes where the subject is
 *    light and gets out of the way where the subject is dark.
 * 3. A directional drop-shadow that follows the cut-out's own alpha, so his
 *    edge is drawn by light rather than by an outline.
 */
const TONE = "138,124,106";

const MASK_DESKTOP =
  "linear-gradient(to top, #000 0%, #000 18%, rgba(0,0,0,0.56) 46%, rgba(0,0,0,0.16) 74%, rgba(0,0,0,0) 96%)";

const FIELD_DESKTOP: CSSProperties = {
  backgroundImage: [
    "radial-gradient(56% 42% at 94% 98%, rgba(193,68,14,0.07) 0%, rgba(193,68,14,0) 70%)",
    "linear-gradient(to left," +
      ` rgba(${TONE},0.60) 0%,` +
      ` rgba(${TONE},0.56) 20%,` +
      ` rgba(${TONE},0.46) 38%,` +
      ` rgba(${TONE},0.30) 54%,` +
      ` rgba(${TONE},0.14) 68%,` +
      ` rgba(${TONE},0.04) 82%,` +
      ` rgba(${TONE},0) 94%)`,
  ].join(","),
  maskImage: MASK_DESKTOP,
  WebkitMaskImage: MASK_DESKTOP,
};

const FIELD_MOBILE: CSSProperties = {
  backgroundImage: [
    "radial-gradient(76% 32% at 74% 100%, rgba(193,68,14,0.07) 0%, rgba(193,68,14,0) 72%)",
    "linear-gradient(to top," +
      ` rgba(${TONE},0.60) 0%,` +
      ` rgba(${TONE},0.55) 14%,` +
      ` rgba(${TONE},0.40) 28%,` +
      ` rgba(${TONE},0.22) 40%,` +
      ` rgba(${TONE},0.08) 52%,` +
      ` rgba(${TONE},0) 66%)`,
  ].join(","),
};

const PORTRAIT_SHADOW: CSSProperties = {
  filter:
    "drop-shadow(-34px 26px 44px rgba(34,26,18,0.22)) drop-shadow(-3px 4px 4px rgba(34,26,18,0.28))",
};

const NAV = [
  { label: "Projets", href: "#work" },
  { label: "À propos", href: "#about" },
  { label: "Contact", href: "#contact" },
];

export default function HeroV2() {
  const reduced = useReducedMotion();
  const [finePointer, setFinePointer] = useState(false);

  useEffect(() => {
    const query = window.matchMedia("(pointer: fine)");
    const sync = () => setFinePointer(query.matches);
    sync();
    query.addEventListener("change", sync);
    return () => query.removeEventListener("change", sync);
  }, []);

  /* -0.5 .. 0.5 across the viewport. */
  const px = useMotionValue(0);
  const py = useMotionValue(0);
  const sx = useSpring(px, DRIFT);
  const sy = useSpring(py, DRIFT);

  /* The one quiet reward: the portrait and the tone behind it drift in
     opposite directions on pointer move, so the two layers separate. */
  const portraitX = useTransform(sx, (v) => v * 26);
  const portraitY = useTransform(sy, (v) => v * 16);
  const fieldX = useTransform(sx, (v) => v * -14);
  const fieldY = useTransform(sy, (v) => v * -9);

  const drift = finePointer && !reduced;

  useEffect(() => {
    if (drift) return;
    px.jump(0);
    py.jump(0);
  }, [drift, px, py]);

  const handleMove = useCallback(
    (event: ReactPointerEvent<HTMLElement>) => {
      if (event.pointerType === "touch") return;
      const rect = event.currentTarget.getBoundingClientRect();
      px.set((event.clientX - rect.left) / rect.width - 0.5);
      py.set((event.clientY - rect.top) / rect.height - 0.5);
    },
    [px, py],
  );

  const handleLeave = useCallback(() => {
    px.set(0);
    py.set(0);
  }, [px, py]);

  /* Transform-only entrances. Nothing animates from opacity 0, so the
     prerendered HTML already carries every word at full contrast.
     Reduced motion still needs `animate`, otherwise the offset that was
     serialised into the HTML would never be cleared and the layout would
     simply sit a few pixels low forever. */
  const enter = (delay: number, distance: number | string = 22) =>
    reduced
      ? { initial: false as const, animate: { y: 0 }, transition: { duration: 0 } }
      : {
          initial: { y: distance },
          animate: { y: 0 },
          transition: { duration: 1.15, delay, ease: EASE },
        };

  return (
    <section
      onPointerMove={drift ? handleMove : undefined}
      onPointerLeave={drift ? handleLeave : undefined}
      className="relative isolate flex min-h-svh w-full flex-col overflow-hidden bg-background"
    >
      {/* Tonal field — the thing he emerges from. */}
      <motion.div
        aria-hidden
        style={drift ? { x: fieldX, y: fieldY } : undefined}
        className="pointer-events-none absolute inset-0 z-0"
      >
        <div className="absolute inset-0 md:hidden" style={FIELD_MOBILE} />
        <div className="absolute inset-0 hidden md:block" style={FIELD_DESKTOP} />
      </motion.div>

      {/* Top bar */}
      <header className="relative z-30 flex items-baseline justify-between px-6 pt-6 md:px-12 md:pt-8">
        <a
          href="#"
          className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted transition-colors hover:text-foreground md:text-xs md:tracking-[0.18em]"
        >
          © Ilias Kalalou
        </a>
        <nav className="flex items-baseline gap-5 font-mono text-[10px] uppercase tracking-[0.16em] text-muted md:gap-8 md:text-xs md:tracking-[0.18em]">
          {NAV.map((item) => (
            <a
              key={item.label}
              href={item.href}
              className="transition-colors hover:text-foreground"
            >
              {item.label}
            </a>
          ))}
        </nav>
      </header>

      {/* Type */}
      <div className="relative z-10 mt-8 flex flex-col px-6 pb-6 md:mt-auto md:px-12 md:pb-10">
        <h1 className="order-4 mt-4 text-[24vw] font-medium leading-[0.84] tracking-[-0.045em] md:mt-6 md:text-[min(17.6vw,35svh)] md:leading-[0.82]">
          <span className="block">
            <motion.span className="block" {...enter(0.28, "16%")}>
              Ilias
            </motion.span>
          </span>
          <span className="block">
            <motion.span className="block" {...enter(0.35, "16%")}>
              Kalalou
            </motion.span>
          </span>
        </h1>
        <div className="order-2 max-w-[28rem] md:max-w-[32rem]">
          <motion.p
            className="font-mono text-[10px] uppercase tracking-[0.24em] text-muted md:text-[11px] md:tracking-[0.26em]"
            {...enter(0, 14)}
          >
            Ingénieur IA &amp; Data
            <span className="mx-2.5 text-foreground/25 md:mx-3">/</span>
            Paris
          </motion.p>

          <motion.p
            className="mt-4 text-[15px] leading-[1.58] text-muted md:mt-6 md:text-[17px] md:leading-[1.62]"
            {...enter(0.06, 18)}
          >
            Je conçois et je mets en production des systèmes de machine
            learning — pipelines de données, entraînement de modèles, et toute
            la tuyauterie qui les fait tourner dans la durée. Depuis un an, en
            freelance pour une startup d’IA.
          </motion.p>

          <motion.p
            className="mt-4 flex items-center gap-2.5 font-mono text-[10px] uppercase tracking-[0.13em] text-muted md:mt-6 md:text-[11px] md:tracking-[0.16em]"
            {...enter(0.12, 16)}
          >
            <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />
            Disponible en freelance
          </motion.p>

          <motion.div
            className="mt-6 flex flex-wrap items-center gap-3 md:mt-9 md:gap-4"
            {...enter(0.18, 20)}
          >
            <Magnetic>
              <a
                href="mailto:ilias.kalalou@gmail.com"
                className="group inline-flex items-center gap-2 rounded-full bg-foreground px-6 py-3 text-[13px] font-medium text-background transition-colors hover:bg-accent md:text-sm"
              >
                Me contacter
                <span
                  aria-hidden
                  className="transition-transform duration-500 ease-[cubic-bezier(0.16,1,0.3,1)] group-hover:translate-x-1"
                >
                  →
                </span>
              </a>
            </Magnetic>
            <Magnetic>
              <a
                href="#work"
                className="inline-flex items-center rounded-full border border-foreground/20 px-6 py-3 text-[13px] transition-colors hover:border-foreground/60 md:text-sm"
              >
                Voir mes projets
              </a>
            </Magnetic>
          </motion.div>
        </div>

        {/* The rule runs the full width and disappears behind him — one horizon
            shared by the type and the photograph. */}
        <motion.div
          className="order-3 -mx-6 mt-6 h-px bg-foreground/10 md:-mx-12 md:mt-12"
          {...enter(0.24, 12)}
        />
      </div>

      {/* Portrait — cropped by the frame, bleeding off the right edge.
          On mobile it closes the page; on desktop it owns the right half.
          The desktop height is min(68vw, 92svh): 48/68 keeps the box a hair
          wider than the photograph's own 1050/1498 ratio at every viewport, so
          object-cover always crops the bottom and never the sides. Clamping by
          92svh only widens that ratio further, so tall windows stay safe. */}
      <div
        className="pointer-events-none relative z-20 mt-1 ml-[6vw] -mr-[16vw] min-h-[230px] w-auto flex-1 md:absolute md:top-auto md:right-[-2vw] md:bottom-0 md:left-auto md:mt-0 md:mr-0 md:ml-0 md:h-[min(68vw,92svh)] md:w-[48vw] md:flex-none"
      >
        <motion.div className="absolute inset-0" {...enter(0.1, 40)}>
          <motion.div
            className="absolute inset-0"
            style={drift ? { x: portraitX, y: portraitY } : undefined}
          >
            <div className="absolute inset-0" style={PORTRAIT_SHADOW}>
              <Image
                src="/ilias.webp"
                alt="Portrait d’Ilias Kalalou"
                fill
                sizes="(min-width: 768px) 48vw, 106vw"
                loading="eager"
                fetchPriority="high"
                className="select-none object-cover object-top contrast-[1.05] brightness-[0.985]"
              />
            </div>
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
}
