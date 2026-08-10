"use client";

import { motion } from "framer-motion";

import Ambience from "@/components/Ambience";
import Magnetic from "@/components/Magnetic";
import Portrait from "@/components/Portrait";
import RotatingBadge from "@/components/RotatingBadge";

const container = {
  hidden: {},
  show: {
    transition: { staggerChildren: 0.12, delayChildren: 0.2 },
  },
};

const item = {
  hidden: { y: 32, opacity: 0 },
  show: {
    y: 0,
    opacity: 1,
    transition: { duration: 0.8, ease: [0.16, 1, 0.3, 1] as const },
  },
};

export default function Hero() {
  return (
    <section className="relative flex min-h-svh flex-col justify-center px-6 py-28 md:px-12 md:py-0">
      <Ambience />

      <div className="grid items-center gap-14 md:grid-cols-[1.2fr_0.8fr] md:gap-10">
        <motion.div variants={container} initial="hidden" animate="show">
          <motion.p
            variants={item}
            className="mb-6 text-sm uppercase tracking-[0.25em] text-muted"
          >
            Freelance Machine Learning Engineer — Paris
          </motion.p>

          <motion.h1
            variants={item}
            className="text-[13vw] leading-[0.95] font-semibold tracking-tight md:text-[7vw]"
          >
            Ilias Kalalou
          </motion.h1>

          <motion.h2
            variants={item}
            className="mt-2 text-[8vw] leading-[0.95] font-semibold tracking-tight text-muted md:text-[4vw]"
          >
            AI &amp; Data Engineer
          </motion.h2>

          <motion.p variants={item} className="mt-8 max-w-xl text-base text-muted md:text-lg">
            Final-year AI &amp; Big Data student at EPITA. For the past year I have
            been working as a freelance ML engineer for an AI startup — building
            data pipelines and machine learning systems that ship.
          </motion.p>

          <motion.div variants={item} className="mt-10 flex flex-wrap items-center gap-3">
            <span className="flex items-center gap-2 rounded-full border border-line px-4 py-2 text-sm">
              <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-400" />
              Open to freelance missions
            </span>
            <span className="rounded-full border border-line px-4 py-2 text-sm">
              Final-year internship · 2027
            </span>
          </motion.div>

          <motion.div variants={item} className="mt-12 flex flex-wrap gap-4">
            <Magnetic>
              <a
                href="mailto:ilias.kalalou@gmail.com"
                className="rounded-full bg-foreground px-6 py-3 text-sm font-medium text-background"
              >
                Get in touch
              </a>
            </Magnetic>
            <Magnetic>
              <a
                href="#work"
                className="rounded-full border border-line px-6 py-3 text-sm transition-colors hover:border-foreground"
              >
                See my work
              </a>
            </Magnetic>
          </motion.div>
        </motion.div>

        <div className="relative mx-auto w-full max-w-sm md:max-w-md">
          <Portrait className="w-full" />
          <RotatingBadge href="#work" className="absolute -bottom-8 -left-6" />
        </div>
      </div>

      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.6, duration: 1 }}
        className="absolute bottom-8 left-6 hidden text-xs uppercase tracking-[0.25em] text-muted md:left-12 md:block"
      >
        Scroll
      </motion.p>
    </section>
  );
}
