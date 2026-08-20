"use client";

import Image from "next/image";
import { motion } from "framer-motion";

import Magnetic from "@/components/Magnetic";

const EASE = [0.16, 1, 0.3, 1] as const;

const group = {
  hidden: {},
  show: { transition: { staggerChildren: 0.09, delayChildren: 0.15 } },
};

const item = {
  hidden: { y: 26 },
  show: { y: 0, transition: { duration: 0.85, ease: EASE } },
};

export default function HeroStage() {
  return (
    <section className="relative flex min-h-svh items-center overflow-hidden px-6 pt-28 pb-16 md:px-12 md:pt-32 md:pb-20">
      <div className="relative z-10 mx-auto grid w-full max-w-[1400px] items-center gap-12 md:grid-cols-[1fr_0.52fr] md:gap-8">
        <motion.div variants={group} initial="hidden" animate="show">
          <motion.p
            variants={item}
            className="mb-8 text-[11px] uppercase tracking-[0.32em] text-muted"
          >
            Paris — Freelance &amp; open to a 2027 internship
          </motion.p>

          <motion.h1
            variants={item}
            className="text-[16vw] leading-[0.86] font-medium tracking-[-0.035em] md:text-[7.2vw]"
          >
            Ilias
            <br />
            Kalalou
          </motion.h1>

          <motion.p
            variants={item}
            className="mt-8 max-w-[46ch] text-lg leading-relaxed text-muted md:text-xl"
          >
            AI &amp; Data engineer. Final year at EPITA, and a year spent
            building machine learning systems that actually ship for an AI
            startup.
          </motion.p>

          <motion.div variants={item} className="mt-12 flex flex-wrap gap-3">
            <Magnetic>
              <a
                href="mailto:ilias.kalalou@gmail.com"
                className="rounded-full bg-foreground px-7 py-3.5 text-sm font-medium text-background"
              >
                Get in touch
              </a>
            </Magnetic>
            <Magnetic>
              <a
                href="#work"
                className="rounded-full border border-line px-7 py-3.5 text-sm transition-colors hover:border-foreground"
              >
                See my work
              </a>
            </Magnetic>
          </motion.div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, scale: 1.03 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 1.1, ease: EASE, delay: 0.15 }}
          className="relative mx-auto w-full max-w-[400px] md:-translate-x-28 lg:-translate-x-40"
        >
          <div className="relative aspect-[4/5]">
            <Image
              src="/ilias.webp"
              alt="Ilias Kalalou"
              fill
              priority
              sizes="(max-width: 768px) 90vw, 400px"
              className="object-contain object-bottom"
            />
          </div>
        </motion.div>
      </div>

      {/* The momiji, rendered in Blender from Ilias's own photograph in Japan.
          Anchored to the right edge and allowed to bleed: its right flank is
          cropped in the source, so that cut falls off-screen. */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute right-[-3%] bottom-[4%] hidden h-[76%] w-[34%] select-none md:block lg:right-[0%] lg:w-[32%]"
      >
        <Image
          src="/momiji.webp"
          alt=""
          fill
          sizes="50vw"
          className="object-contain object-bottom"
        />
      </div>
    </section>
  );
}
