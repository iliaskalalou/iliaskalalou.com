"use client";

import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";

const EASE = [0.16, 1, 0.3, 1] as const;

export type Work = {
  index: string;
  title: string;
  meta: string;
  description: string;
  href?: string;
};

function Row({ work, i, still }: { work: Work; i: number; still: boolean }) {
  const inner = (
    <div className="grid items-baseline gap-3 py-10 md:grid-cols-[auto_1fr_auto] md:gap-10 md:py-12">
      <span className="font-mono text-[11px] tracking-[0.18em] text-muted md:pt-2">
        {work.index}
      </span>

      <div>
        <h3 className="text-2xl font-medium tracking-[-0.02em] transition-colors duration-300 group-hover:text-accent md:text-[34px]">
          {work.title}
        </h3>
        <p className="mt-3 max-w-[54ch] text-[15px] leading-relaxed text-muted md:text-base">
          {work.description}
        </p>
      </div>

      <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted md:pt-2 md:text-right">
        {work.meta}
      </span>
    </div>
  );

  return (
    <motion.li
      className="group border-t border-line last:border-b"
      initial={still ? false : { y: 22 }}
      whileInView={still ? undefined : { y: 0 }}
      viewport={{ once: true, margin: "0px 0px -12% 0px" }}
      transition={still ? { duration: 0 } : { duration: 0.7, delay: i * 0.06, ease: EASE }}
    >
      {work.href ? (
        <Link
          href={work.href}
          className="block outline-none focus-visible:bg-foreground/[0.03]"
        >
          {inner}
        </Link>
      ) : (
        inner
      )}
    </motion.li>
  );
}

export default function WorkList({ items }: { items: Work[] }) {
  const still = useReducedMotion() ?? false;
  return (
    <ul className="mx-auto w-full max-w-[1400px] px-6 md:px-12">
      {items.map((w, i) => (
        <Row key={w.title} work={w} i={i} still={still} />
      ))}
    </ul>
  );
}
