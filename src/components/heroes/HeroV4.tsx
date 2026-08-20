"use client";

import Image from "next/image";
import { motion, MotionConfig } from "framer-motion";
import type { CSSProperties } from "react";

import Magnetic from "@/components/Magnetic";

const EASE = [0.16, 1, 0.3, 1] as const;

const stage = {
  hidden: {},
  show: { transition: { staggerChildren: 0.07, delayChildren: 0.12 } },
};

/* Transforms only — never opacity on the display type, so the prerendered
   HTML is already readable if hydration is slow or never happens. */
const rise = {
  hidden: { y: 22 },
  show: { y: 0, transition: { duration: 0.85, ease: EASE } },
};

const card = {
  hidden: { y: 34, scale: 0.985 },
  show: { y: 0, scale: 1, transition: { duration: 1.05, ease: EASE } },
};

/* The separation problem: an off-white linen shirt on a #fafaf9 page.
   Three stacked fixes live in this one style —
   1. a warm stone panel several steps darker than the shirt,
   2. a top-to-bottom darkening so the brightest part of the shirt sits
      against the darkest part of the panel,
   3. a faint engineering grid that gives the panel material, so the cut-out
      never looks like it is floating on nothing.
   A silhouette-tracing drop-shadow on the <img> itself does the rest. */
const panel: CSSProperties = {
  backgroundColor: "#dad3c6",
  backgroundImage: [
    "linear-gradient(180deg, rgba(255,255,255,0.26) 0%, rgba(255,255,255,0) 44%)",
    "linear-gradient(180deg, rgba(20,17,15,0) 30%, rgba(20,17,15,0.17) 100%)",
    "linear-gradient(to right, rgba(20,17,15,0.05) 1px, transparent 1px)",
    "linear-gradient(to bottom, rgba(20,17,15,0.05) 1px, transparent 1px)",
  ].join(","),
  backgroundSize: "100% 100%, 100% 100%, 34px 34px, 34px 34px",
};

const portraitShadow: CSSProperties = {
  filter:
    "drop-shadow(0 0 12px rgba(20,17,15,0.20)) drop-shadow(0 22px 32px rgba(20,17,15,0.28))",
};

const css = `
@keyframes ik4-rise {
  from { transform: translateY(106%); }
  to   { transform: translateY(0); }
}
.ik4-rise { animation: ik4-rise 1s cubic-bezier(0.16, 1, 0.3, 1) both; }
@keyframes ik4-pulse {
  0%   { transform: scale(1);   opacity: 0.45; }
  70%  { transform: scale(2.8); opacity: 0; }
  100% { transform: scale(2.8); opacity: 0; }
}
.ik4-ping { animation: ik4-pulse 2.6s cubic-bezier(0.16, 1, 0.3, 1) infinite; }
@media (prefers-reduced-motion: reduce) {
  .ik4-rise { animation: none; }
  .ik4-ping { animation: none; opacity: 0; }
}
`;

const nav = [
  { label: "Work", href: "#work" },
  { label: "About", href: "#about" },
  { label: "Contact", href: "#contact" },
];

const rail = [
  { label: "Open to", value: "Freelance work · 2027 internship" },
  { label: "Currently", value: "Freelance ML engineer, AI startup" },
  { label: "Focus", value: "ML systems · Data pipelines · Delivery" },
];

const META = "font-mono text-[10px] uppercase tracking-[0.18em]";

export default function HeroV4() {
  return (
    <MotionConfig reducedMotion="user">
      <style dangerouslySetInnerHTML={{ __html: css }} />

      <main className="w-full bg-background p-3 md:p-5">
        <motion.div
          variants={stage}
          initial="hidden"
          animate="show"
          className="relative flex min-h-[calc(100svh-1.5rem)] flex-col overflow-hidden rounded-[18px] border border-line md:min-h-[calc(100svh-2.5rem)] md:rounded-[24px]"
        >
          {/* ── top bar ───────────────────────────────────────────── */}
          <header className="shrink-0 border-b border-line px-5 md:px-8">
            <div className="mx-auto flex w-full max-w-[1120px] items-center justify-between gap-4 py-3.5 md:py-4">
              <a
                href="#"
                className={`${META} text-muted transition-colors hover:text-foreground`}
              >
                © Ilias Kalalou
              </a>
              <nav className="flex items-center gap-5 md:gap-7">
                {nav.map((n) => (
                  <a
                    key={n.label}
                    href={n.href}
                    className={`${META} text-muted transition-colors hover:text-foreground`}
                  >
                    {n.label}
                  </a>
                ))}
              </nav>
            </div>
          </header>

          {/* ── middle band ───────────────────────────────────────── */}
          <div className="flex flex-1 px-5 md:px-8">
            <div className="mx-auto grid w-full max-w-[1120px] grid-cols-1 gap-y-6 lg:grid-cols-[1fr_minmax(336px,476px)] lg:gap-y-0 lg:divide-x lg:divide-line">
              {/* left — the words */}
              <div className="flex flex-col justify-center pt-7 lg:py-12 lg:pr-14">
                <motion.div variants={rise} className="flex items-center gap-4">
                  <span
                    className={`${META} shrink-0 tracking-[0.26em] text-foreground/75`}
                  >
                    AI &amp; Data Engineer
                  </span>
                  <span aria-hidden className="h-px flex-1 bg-line" />
                </motion.div>

                <h1 className="mt-5 text-[clamp(3.05rem,7.6vw,7rem)] leading-[0.9] font-medium tracking-[-0.045em] md:mt-7">
                  {["Ilias", "Kalalou"].map((word, i) => (
                    <span
                      key={word}
                      className="-mt-[0.1em] -mb-[0.05em] block overflow-hidden pt-[0.1em] pb-[0.05em]"
                    >
                      <span
                        className="ik4-rise block"
                        style={{ animationDelay: `${0.18 + i * 0.08}s` }}
                      >
                        {word}
                      </span>
                    </span>
                  ))}
                </h1>

                <motion.p
                  variants={rise}
                  className="mt-6 max-w-[44ch] text-[15px] leading-[1.62] text-muted md:mt-7 md:text-[17px]"
                >
                  Final year at EPITA in Paris. A year spent building machine
                  learning systems that ship for an AI startup.
                </motion.p>

                <motion.div
                  variants={rise}
                  className="mt-8 flex flex-wrap items-center gap-2.5 md:mt-10 md:gap-3"
                >
                  <Magnetic>
                    <a
                      href="mailto:ilias.kalalou@gmail.com"
                      className="group inline-flex items-center gap-2 rounded-full bg-foreground px-6 py-3 text-[13px] font-medium text-background transition-opacity hover:opacity-90"
                    >
                      Get in touch
                      <span
                        aria-hidden
                        className="transition-transform duration-300 group-hover:translate-x-0.5"
                      >
                        →
                      </span>
                    </a>
                  </Magnetic>
                  <Magnetic>
                    <a
                      href="#work"
                      className="inline-flex items-center rounded-full border border-line px-6 py-3 text-[13px] transition-colors hover:border-foreground"
                    >
                      See my work
                    </a>
                  </Magnetic>
                </motion.div>
              </div>

              {/* right — the frame */}
              <div className="flex items-center justify-start pb-7 md:justify-end lg:py-12 lg:pb-12 lg:pl-14">
                <motion.div
                  variants={card}
                  className="relative w-full max-w-[420px]"
                >
                  <div className="absolute -left-2 top-5 z-10 flex items-center gap-2 rounded-full border border-line bg-background px-3 py-1.5 shadow-[0_10px_24px_-14px_rgba(20,17,15,0.55)] md:-left-5">
                    <span className="relative flex h-1.5 w-1.5 shrink-0">
                      <span className="ik4-ping absolute inset-0 rounded-full bg-accent" />
                      <span className="relative h-1.5 w-1.5 rounded-full bg-accent" />
                    </span>
                    <span className={`${META} tracking-[0.16em]`}>
                      Available
                    </span>
                  </div>

                  <div className="overflow-hidden rounded-[16px] border border-line bg-background shadow-[0_1px_2px_rgba(20,17,15,0.04),0_28px_50px_-34px_rgba(20,17,15,0.5)]">
                    <div
                      className="relative aspect-[4/3] overflow-hidden lg:aspect-[4/5]"
                      style={panel}
                    >
                      <div className="absolute left-1/2 top-[5%] h-[156%] aspect-[1050/1498] -translate-x-1/2 lg:top-[4%] lg:h-[96%] lg:-translate-x-[52%]">
                        <Image
                          src="/ilias.webp"
                          alt="Ilias Kalalou"
                          fill
                          preload
                          sizes="(max-width: 1023px) 92vw, 420px"
                          className="object-contain object-top"
                          style={portraitShadow}
                        />
                      </div>
                    </div>

                    <div className="flex items-center justify-between gap-3 border-t border-line px-4 py-3">
                      <span className={`${META} text-muted`}>
                        Paris · France
                      </span>
                      <span className={`${META} text-muted`}>EPITA ’27</span>
                    </div>
                  </div>
                </motion.div>
              </div>
            </div>
          </div>

          {/* ── spec rail ─────────────────────────────────────────── */}
          <div className="shrink-0 border-t border-line px-5 md:px-8">
            <motion.div
              variants={rise}
              className="mx-auto grid w-full max-w-[1120px] grid-cols-1 lg:grid-cols-[1fr_1fr_476px] lg:divide-x lg:divide-line"
            >
              {rail.map((cell, i) => (
                <div
                  key={cell.label}
                  className={`py-4 lg:py-5 ${
                    i === 0
                      ? "lg:pr-6"
                      : i === 1
                        ? "hidden lg:block lg:px-6"
                        : "hidden lg:block lg:pl-14"
                  }`}
                >
                  <p className={`${META} text-muted`}>{cell.label}</p>
                  <p className="mt-1.5 text-[13px] leading-snug md:text-sm">
                    {cell.value}
                  </p>
                </div>
              ))}
            </motion.div>
          </div>
        </motion.div>
      </main>
    </MotionConfig>
  );
}
