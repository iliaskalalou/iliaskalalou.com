"use client";

import Image from "next/image";
import { MotionConfig, motion } from "framer-motion";

import Magnetic from "@/components/Magnetic";

const EASE = [0.16, 1, 0.3, 1] as const;

// Transform-only reveals. framer-motion serialises `initial` into the
// prerendered HTML, so anything animated from opacity 0 would be invisible
// until hydration — here every element is readable before JS runs, it just
// settles a few pixels.
const stage = {
  hidden: {},
  show: { transition: { staggerChildren: 0.07, delayChildren: 0.1 } },
};

const rise = {
  hidden: { y: 30 },
  show: { y: 0, transition: { duration: 0.95, ease: EASE } },
};

const riseSmall = {
  hidden: { y: 14 },
  show: { y: 0, transition: { duration: 0.8, ease: EASE } },
};

const drawRule = {
  hidden: { scaleX: 0 },
  show: { scaleX: 1, transition: { duration: 1.1, ease: EASE } },
};

// The photograph is a cut-out and his shirt is nearly the colour of the page,
// so the panel behind him carries the separation: warm and light where his
// dark hair falls, deep where the white linen starts. Two calibrated ramps,
// one per crop — the compact crop below `lg` reaches the shirt much lower in
// the frame than the full-figure crop does.
const PANEL_COMPACT =
  "linear-gradient(180deg,#f0ebe3 0%,#e9e3d9 42%,#d5ccc0 57%,#968b7d 70%,#4d453d 85%,#332d28 100%)";

const PANEL_FULL =
  "linear-gradient(180deg,#f0ebe3 0%,#e9e3d9 24%,#d5ccc0 38%,#968b7d 51%,#4d453d 68%,#332d28 100%)";

const NAV = [
  { label: "Work", href: "#work" },
  { label: "About", href: "#about" },
  { label: "Contact", href: "mailto:ilias.kalalou@gmail.com" },
];

const META_CLASS =
  "font-mono text-[10px] uppercase tracking-[0.2em] text-muted";

export default function HeroV1() {
  return (
    <MotionConfig reducedMotion="user">
      <section className="relative flex min-h-svh flex-col overflow-x-clip px-5 py-6 sm:px-8 lg:px-12 lg:py-8 xl:px-16">
        <header className="flex items-baseline justify-between border-b border-line pb-4">
          <span className={META_CLASS}>&copy; Ilias Kalalou</span>
          <nav className="flex items-baseline gap-5 sm:gap-7">
            {NAV.map((entry) => (
              <a
                key={entry.label}
                href={entry.href}
                className={`${META_CLASS} transition-colors duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] hover:text-foreground`}
              >
                {entry.label}
              </a>
            ))}
          </nav>
        </header>

        <motion.div
          variants={stage}
          initial="hidden"
          animate="show"
          className="flex flex-1 items-center py-7 lg:py-6"
        >
          <div className="grid w-full grid-cols-1 gap-y-8 lg:grid-cols-[minmax(0,1fr)_minmax(300px,405px)] lg:items-stretch lg:gap-x-16 lg:gap-y-7 xl:gap-x-20">
            {/* ── Masthead: kicker, rule, name ─────────────────────────── */}
            <div className="lg:col-start-1 lg:row-start-1">
              <motion.div
                variants={riseSmall}
                className="flex items-baseline justify-between gap-6"
              >
                <p className={META_CLASS}>AI &amp; Data Engineer</p>
                <p className={META_CLASS}>Paris &middot; FR</p>
              </motion.div>

              <motion.div
                variants={drawRule}
                style={{ transformOrigin: "left" }}
                className="mt-3.5 h-px w-full bg-line"
              />

              <h1 className="mt-6 text-[clamp(3.25rem,15vw,4.5rem)] font-medium leading-[0.86] tracking-[-0.035em] lg:mt-10 lg:text-[clamp(3rem,6.8vw,6rem)]">
                <span className="block">
                  <motion.span variants={rise} className="block">
                    Ilias
                  </motion.span>
                </span>
                <span className="block">
                  <motion.span variants={rise} className="block">
                    Kalalou
                  </motion.span>
                </span>
              </h1>
            </div>

            {/* ── The plate ────────────────────────────────────────────── */}
            <motion.figure
              variants={rise}
              className="ml-auto flex w-full max-w-[380px] flex-col sm:max-w-[420px] lg:col-start-2 lg:row-start-1 lg:row-span-2 lg:ml-0 lg:max-w-none lg:self-stretch"
            >
              <div className="relative w-full lg:min-h-0 lg:flex-1">
                <div
                  aria-hidden
                  className="pointer-events-none absolute -left-2.5 -top-2.5 h-full w-full border border-line lg:-left-4 lg:-top-4"
                />

                <div className="relative aspect-[21/20] w-full overflow-hidden border border-[#dbd5cc] lg:aspect-auto lg:h-full">
                  <div
                    aria-hidden
                    className="absolute inset-0 lg:hidden"
                    style={{ background: PANEL_COMPACT }}
                  />
                  <div
                    aria-hidden
                    className="absolute inset-0 hidden lg:block"
                    style={{ background: PANEL_FULL }}
                  />

                  <motion.div
                    className="absolute inset-x-0 bottom-0 top-[4%] lg:top-[7%]"
                    initial={{ scale: 1.035 }}
                    animate={{ scale: 1 }}
                    transition={{ duration: 1.4, ease: EASE, delay: 0.15 }}
                    style={{ transformOrigin: "bottom center" }}
                  >
                    <Image
                      src="/ilias.webp"
                      alt="Ilias Kalalou"
                      fill
                      priority
                      sizes="(max-width: 1024px) 92vw, 405px"
                      className="object-cover object-top [filter:saturate(0.92)_contrast(1.03)_drop-shadow(0_0_26px_rgba(28,23,19,0.28))_drop-shadow(0_16px_30px_rgba(28,23,19,0.22))] lg:object-contain lg:object-bottom"
                    />
                  </motion.div>
                </div>
              </div>

              <figcaption className="mt-3 flex items-baseline justify-between gap-4 border-t border-line pt-2.5">
                <span className={META_CLASS}>Portrait, Paris</span>
                <span className={META_CLASS}>2026</span>
              </figcaption>
            </motion.figure>

            {/* ── Body: sentence, availability, actions ────────────────── */}
            <div className="flex flex-col lg:col-start-1 lg:row-start-2 lg:block">
              <motion.p
                variants={riseSmall}
                className="max-w-[46ch] text-[15px] leading-[1.65] text-muted lg:text-[17px]"
              >
                Final year at EPITA in AI &amp; Big Data. For the past year I
                have been building machine learning systems that ship
                <span className="hidden sm:inline">
                  {" "}
                  — data pipelines, models and the plumbing around them
                </span>{" "}
                for an AI startup.
              </motion.p>

              <motion.dl
                variants={riseSmall}
                className="order-3 mt-14 border-t border-line lg:mt-10"
              >
                <div className="flex items-baseline justify-between gap-6 border-b border-line py-2.5">
                  <dt className={`${META_CLASS} shrink-0`}>Available</dt>
                  <dd className="flex items-baseline gap-2 text-right text-[14px]">
                    <span
                      aria-hidden
                      className="size-[5px] shrink-0 translate-y-[-2px] rounded-full bg-accent"
                    />
                    Freelance work, from now
                  </dd>
                </div>
                <div className="flex items-baseline justify-between gap-6 border-b border-line py-2.5">
                  <dt className={`${META_CLASS} shrink-0`}>Seeking</dt>
                  <dd className="text-right text-[14px]">
                    Final-year internship, 2027
                  </dd>
                </div>
              </motion.dl>

              <motion.div
                variants={riseSmall}
                className="order-2 mt-7 flex flex-wrap items-center gap-x-8 gap-y-4 lg:mt-10"
              >
                <Magnetic>
                  <a
                    href="mailto:ilias.kalalou@gmail.com"
                    className="rounded-full bg-foreground px-6 py-3 text-[13px] font-medium tracking-[0.01em] text-background transition-opacity duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] hover:opacity-90"
                  >
                    Get in touch
                  </a>
                </Magnetic>

                <a
                  href="#work"
                  className="group inline-flex items-center gap-2 border-b border-line pb-1 text-[13px] text-muted transition-colors duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] hover:border-foreground hover:text-foreground"
                >
                  See my work
                  <span
                    aria-hidden
                    className="transition-transform duration-500 ease-[cubic-bezier(0.16,1,0.3,1)] group-hover:translate-y-0.5"
                  >
                    &darr;
                  </span>
                </a>
              </motion.div>
            </div>
          </div>
        </motion.div>
      </section>
    </MotionConfig>
  );
}
