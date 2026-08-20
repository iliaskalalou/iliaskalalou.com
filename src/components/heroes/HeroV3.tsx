"use client";

import Image from "next/image";
import { MotionConfig, motion } from "framer-motion";
import type { CSSProperties } from "react";

import Magnetic from "@/components/Magnetic";

const EASE = [0.16, 1, 0.3, 1] as const;

/* Transforms only. framer-motion serialises `initial` into the prerendered
   HTML, so anything faded in from zero would be invisible until hydration —
   fatal for the name. Every reveal here moves, none of them fade the display
   type. */
const stage = {
  hidden: {},
  show: { transition: { staggerChildren: 0.07, delayChildren: 0.12 } },
};

const rise = {
  hidden: { y: 26 },
  show: { y: 0, transition: { duration: 0.9, ease: EASE } },
};

const riseFade = {
  hidden: { y: 14, opacity: 0 },
  show: { y: 0, opacity: 1, transition: { duration: 0.8, ease: EASE } },
};

/* The alcove. A warm charcoal ground with a soft glow lifted behind the head:
   the shirt reads as light against dark, and the hair keeps a lighter field
   directly behind it instead of merging into flat black. */
const ALCOVE_GROUND: CSSProperties = {
  backgroundImage:
    "radial-gradient(112% 74% at 50% 30%, #41382f 0%, #29221c 40%, #181310 74%, #110e0b 100%)",
};

/* Feathers the bottom crop into the ground so the figure is framed, not sliced. */
const ALCOVE_HEM: CSSProperties = {
  backgroundImage:
    "linear-gradient(to top, rgba(17,14,11,0.94) 0%, rgba(17,14,11,0.5) 8%, rgba(17,14,11,0) 22%)",
};

/* Optical centring, measured off the cut-out's alpha channel rather than guessed.
   His face sits at 0.412 of the image width but his mass at 0.471 — he is turned,
   so no crop puts both on the axis. Centring the window on 0.455 runs both
   shoulders off the arch's edges, which reads as balanced; the face then falls a
   hair left of the axis, which reads as a photograph. Vertically the crown lands
   12% down, tucked inside the arch's semicircular head. */
const PORTRAIT_PLACEMENT: CSSProperties = { top: "6.6%", left: "-14.3%" };

const NAV = [
  { label: "Work", href: "#work" },
  { label: "About", href: "#about" },
  { label: "Contact", href: "#contact" },
];

export default function HeroV3() {
  return (
    <MotionConfig reducedMotion="user">
      <section className="flex min-h-svh flex-col overflow-x-clip bg-background">
        {/* ── colophon, top ── */}
        <header className="mx-auto flex w-full max-w-[1180px] shrink-0 items-baseline justify-between px-6 py-5 md:px-10">
          <a
            href="#"
            className="font-mono text-[11px] tracking-[0.12em] text-muted transition-colors hover:text-foreground"
          >
            © Ilias Kalalou
          </a>
          <nav className="flex gap-5 font-mono text-[11px] tracking-[0.12em] text-muted md:gap-7">
            {NAV.map((link) => (
              <a
                key={link.label}
                href={link.href}
                className="transition-colors hover:text-foreground"
              >
                {link.label}
              </a>
            ))}
          </nav>
        </header>

        {/* ── the poster ── */}
        <motion.div
          variants={stage}
          initial="hidden"
          animate="show"
          className="mx-auto flex w-full max-w-[1180px] flex-1 flex-col justify-center px-6 pb-2 md:px-10"
        >
          <motion.p
            variants={riseFade}
            className="text-center font-mono text-[10px] uppercase tracking-[0.34em] text-muted md:text-[11px]"
          >
            AI &amp; Data Engineer
          </motion.p>

          <motion.h1
            variants={rise}
            className="mt-5 text-center text-[19vw] font-medium leading-[0.86] tracking-[-0.045em] text-foreground sm:text-[11.2vw] sm:leading-[0.9] xl:text-[10.2rem]"
          >
            <span className="block sm:inline">Ilias</span>{" "}
            <span className="block sm:inline">Kalalou</span>
          </motion.h1>

          {/* full-width rule the alcove breaks through — the one move that ties
              the type and the photograph into a single object */}
          <div className="relative mt-[clamp(112px,15vh,150px)] lg:mt-[clamp(150px,23.5vh,224px)] w-full">
            <motion.div
              variants={riseFade}
              aria-hidden
              className="absolute inset-x-0 top-0 h-px origin-center bg-line"
            />

            {/* two columns on the phone, three around the alcove on the desk —
                the flanks stay a matched pair rather than collapsing to a stack */}
            <div className="grid grid-cols-2 items-start justify-items-center gap-x-6 gap-y-8 lg:grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] lg:gap-x-10 xl:gap-x-14">
              <motion.figure
                variants={rise}
                className="relative z-10 order-1 col-span-2 -mt-[clamp(90px,12.5vh,124px)] aspect-5/6 h-[clamp(216px,30vh,296px)] shrink-0 overflow-hidden rounded-t-full rounded-b-[24px] shadow-[0_38px_72px_-40px_rgba(20,17,15,0.55)] ring-1 ring-white/10 ring-inset lg:order-2 lg:col-span-1 lg:-mt-[clamp(112px,19.6vh,177px)] lg:h-[clamp(268px,47vh,424px)]"
                style={ALCOVE_GROUND}
              >
                <div className="relative h-full w-full">
                  <Image
                    src="/ilias.webp"
                    alt="Ilias Kalalou"
                    width={1050}
                    height={1498}
                    priority
                    style={PORTRAIT_PLACEMENT}
                    className="absolute h-[168%] w-auto max-w-none select-none [filter:saturate(0.88)_contrast(1.05)]"
                  />
                  <div
                    aria-hidden
                    className="absolute inset-0"
                    style={ALCOVE_HEM}
                  />
                </div>
              </motion.figure>

              <motion.div
                variants={riseFade}
                className="order-2 flex flex-col lg:order-1 lg:ml-auto lg:items-end lg:pt-9 lg:text-right"
              >
                <span className="font-mono text-[10px] uppercase tracking-[0.26em] text-muted/75">
                  Now
                </span>
                <p className="mt-2.5 text-[13px] leading-[1.7] text-muted lg:max-w-[27ch] lg:text-[13.5px]">
                  Final year at EPITA. A year spent building machine learning
                  systems that ship for an AI startup.
                </p>
              </motion.div>

              <motion.div
                variants={riseFade}
                className="order-3 flex flex-col lg:mr-auto lg:items-start lg:pt-9 lg:text-left"
              >
                <span className="font-mono text-[10px] uppercase tracking-[0.26em] text-muted/75">
                  Next
                </span>
                <p className="mt-2.5 text-[13px] leading-[1.7] text-muted lg:max-w-[27ch] lg:text-[13.5px]">
                  Open to freelance engagements, and to a final-year internship
                  in 2027.
                </p>
              </motion.div>
            </div>
          </div>

          <motion.div
            variants={riseFade}
            className="mt-[clamp(26px,4.4vh,50px)] flex flex-wrap items-center justify-center gap-3"
          >
            <Magnetic>
              <a
                href="mailto:ilias.kalalou@gmail.com"
                className="rounded-full bg-foreground px-7 py-3.5 text-sm font-medium text-background transition-opacity hover:opacity-88"
              >
                Get in touch
              </a>
            </Magnetic>
            <Magnetic>
              <a
                href="#work"
                className="rounded-full border border-line px-7 py-3.5 text-sm text-foreground transition-colors hover:border-foreground"
              >
                See my work
              </a>
            </Magnetic>
          </motion.div>
        </motion.div>

        {/* ── colophon, bottom ── */}
        <div className="mx-auto w-full max-w-[1180px] shrink-0 px-6 md:px-10">
          <div className="flex items-center justify-between border-t border-line py-5 font-mono text-[10px] uppercase tracking-[0.26em] text-muted">
            <span className="flex items-center gap-2">
              <span
                aria-hidden
                className="inline-block size-1.5 rounded-full bg-accent"
              />
              Available now
            </span>
            <span>Paris, France</span>
          </div>
        </div>
      </section>
    </MotionConfig>
  );
}
