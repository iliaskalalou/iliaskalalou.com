"use client";

import Image from "next/image";
import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";

const EASE = [0.16, 1, 0.3, 1] as const;

export type Fact = { label: string; value: string };
export type Section = { heading: string; body: string[] };
export type Shot = { src: string; caption: string; width: number; height: number; wide?: boolean };

export type Project = {
  index: string;
  title: string;
  lead: string;
  facts: Fact[];
  sections: Section[];
  shots?: Shot[];
  external?: { label: string; href: string };
  next: { title: string; href: string };
};

export default function ProjectPage({ project }: { project: Project }) {
  const still = useReducedMotion() ?? false;
  const rise = (delay: number) =>
    still
      ? {}
      : {
          initial: { y: 22 },
          animate: { y: 0 },
          transition: { duration: 0.8, delay, ease: EASE },
        };

  return (
    <main className="min-h-svh px-6 pb-24 pt-8 md:px-12 md:pb-32">
      <header className="mx-auto flex max-w-[1100px] items-baseline justify-between">
        <Link
          href="/"
          className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted transition-colors hover:text-foreground md:text-xs"
        >
          ← Ilias Kalalou
        </Link>
        <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted md:text-xs">
          {project.index}
        </span>
      </header>

      <article className="mx-auto max-w-[1100px]">
        <motion.h1
          {...rise(0.05)}
          className="mt-20 max-w-[16ch] text-[11vw] leading-[0.92] font-medium tracking-[-0.035em] md:mt-28 md:text-[5.4vw]"
        >
          {project.title}
        </motion.h1>

        <motion.p
          {...rise(0.12)}
          className="mt-8 max-w-[62ch] text-lg leading-relaxed text-muted md:mt-10 md:text-xl"
        >
          {project.lead}
        </motion.p>

        <motion.dl
          {...rise(0.18)}
          className="mt-14 grid gap-x-10 gap-y-6 border-t border-line pt-8 sm:grid-cols-2 md:mt-20 md:grid-cols-4"
        >
          {project.facts.map((f) => (
            <div key={f.label}>
              <dt className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted">
                {f.label}
              </dt>
              <dd className="mt-2 text-[15px] leading-snug">{f.value}</dd>
            </div>
          ))}
        </motion.dl>


        {project.shots?.length ? (
          <section className="mt-20 md:mt-24">
            <div className="grid gap-6 md:grid-cols-2 md:gap-8">
              {project.shots.map((shot) => (
                <motion.figure
                  key={shot.src}
                  initial={still ? false : { y: 26 }}
                  whileInView={still ? undefined : { y: 0 }}
                  viewport={{ once: true, margin: "0px 0px -12% 0px" }}
                  transition={still ? { duration: 0 } : { duration: 0.7, ease: EASE }}
                  className={shot.wide ? "md:col-span-2" : undefined}
                >
                  <div className="overflow-hidden rounded-[3px] border border-line bg-white">
                    <Image
                      src={shot.src}
                      alt={shot.caption}
                      width={shot.width}
                      height={shot.height}
                      sizes="(max-width: 768px) 92vw, 50vw"
                      className="h-auto w-full"
                    />
                  </div>
                  <figcaption className="mt-3 font-mono text-[10px] uppercase tracking-[0.14em] text-muted">
                    {shot.caption}
                  </figcaption>
                </motion.figure>
              ))}
            </div>
          </section>
        ) : null}

        {project.sections.map((s, i) => (
          <motion.section
            key={s.heading}
            initial={still ? false : { y: 24 }}
            whileInView={still ? undefined : { y: 0 }}
            viewport={{ once: true, margin: "0px 0px -14% 0px" }}
            transition={still ? { duration: 0 } : { duration: 0.7, ease: EASE }}
            className="mt-20 grid gap-6 border-t border-line pt-10 md:mt-24 md:grid-cols-[0.32fr_1fr] md:gap-12"
          >
            <h2 className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted md:pt-1">
              {s.heading}
            </h2>
            <div className="max-w-[64ch] space-y-5 text-[17px] leading-[1.7] md:text-[18px]">
              {s.body.map((p, j) => (
                <p key={j}>{p}</p>
              ))}
            </div>
            <span className="hidden md:block" />
            {i === project.sections.length - 1 && project.external ? (
              <a
                href={project.external.href}
                target="_blank"
                rel="noreferrer noopener"
                className="mt-2 inline-flex w-fit items-center gap-2 rounded-full border border-line px-6 py-3 text-sm transition-colors hover:border-foreground"
              >
                {project.external.label} <span aria-hidden>↗</span>
              </a>
            ) : null}
          </motion.section>
        ))}

        <div className="mt-24 border-t border-line pt-10 md:mt-32">
          <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted">
            Next
          </span>
          <Link
            href={project.next.href}
            className="group mt-3 flex items-baseline gap-4 text-3xl font-medium tracking-[-0.02em] md:text-5xl"
          >
            {project.next.title}
            <span
              aria-hidden
              className="text-xl transition-transform duration-300 group-hover:translate-x-1 md:text-2xl"
            >
              →
            </span>
          </Link>
        </div>
      </article>
    </main>
  );
}
