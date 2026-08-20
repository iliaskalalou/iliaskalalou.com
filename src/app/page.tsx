import HeroV2 from "@/components/heroes/HeroV2";
import Magnetic from "@/components/Magnetic";
import Marquee from "@/components/Marquee";
import Reveal, { RevealText } from "@/components/Reveal";
import WorkList, { type Work } from "@/components/WorkList";

// Descriptions are written from what is publicly verifiable. Ilias's exact
// contribution on the site, and the specifics of the AI process, are still
// to be filled in — deliberately not invented here.
const workItems: Work[] = [
  {
    index: "01",
    title: "Kohen Avocats",
    meta: "Web · Paris",
    description:
      "The site of a Paris criminal-law firm: eight languages, around eighty pages, expertise sections by practice area, and a full structured-data layer built for local search.",
    href: "/work/kohen-avocats",
  },
  {
    index: "02",
    title: "AI process automation",
    meta: "In production · under NDA",
    description:
      "An internal AI system running day to day at the same firm. The mechanism stays confidential; what it replaced was manual, repetitive and slow.",
    href: "/work/ai-automation",
  },
  {
    index: "03",
    title: "Fishing net inspection",
    meta: "Computer vision",
    description:
      "Nets are laid flat in a hangar under ceiling cameras. A vision model locates every hole to repair and shows the crew where to work.",
    href: "/work/fishing-nets",
  },
];

const skills = [
  "Machine Learning",
  "Data Engineering",
  "Python",
  "C",
  "C++",
  "Java",
  "ASM",
  "PyTorch",
  "Spark",
  "SQL",
  "Linux",
  "Nix",
  "Git",
  "AWS",
  "Azure",
  "Next.js",
];

export default function Home() {
  return (
    <main className="relative">
      <HeroV2 />

      <Marquee items={skills} />

      <section id="work" className="scroll-mt-24 py-24">
        <Reveal className="px-6 md:px-12">
          <p className="mb-10 text-sm uppercase tracking-[0.25em] text-muted">
            Selected work
          </p>
        </Reveal>
        <WorkList items={workItems} />
      </section>

      <section id="about" className="scroll-mt-24 px-6 py-24 md:px-12">
        <Reveal>
          <p className="mb-10 text-sm uppercase tracking-[0.25em] text-muted">
            About
          </p>
        </Reveal>
        <Reveal delay={0.08}>
          <p className="max-w-2xl text-xl leading-relaxed text-muted md:text-2xl">
            A year of freelance work for an AI startup: data pipelines, model
            training, and shipping machine learning systems that hold up in
            production. Currently completing an engineering degree at EPITA,
            AI &amp; Big Data major. This section is a placeholder — we will
            write the real story together.
          </p>
        </Reveal>
      </section>

      <section
        id="contact"
        className="scroll-mt-24 px-6 pt-24 pb-12 md:px-12 md:pt-28"
      >
        <Reveal>
          <p className="mb-6 text-sm uppercase tracking-[0.25em] text-muted">
            Contact
          </p>
        </Reveal>
        <h2 className="text-[10vw] leading-[0.95] font-semibold tracking-tight md:text-[6vw]">
          <RevealText text="Let's work together" />
        </h2>
        <Reveal delay={0.2}>
          <div className="mt-10 flex flex-wrap gap-4">
            <Magnetic>
              <a
                href="mailto:ilias.kalalou@gmail.com"
                className="rounded-full bg-foreground px-6 py-3 text-sm font-medium text-background"
              >
                ilias.kalalou@gmail.com
              </a>
            </Magnetic>
            <Magnetic>
              <a
                href="https://github.com/iliaskalalou"
                className="rounded-full border border-line px-6 py-3 text-sm transition-colors hover:border-foreground"
              >
                GitHub
              </a>
            </Magnetic>
            <Magnetic>
              <a
                href="https://www.linkedin.com/"
                className="rounded-full border border-line px-6 py-3 text-sm transition-colors hover:border-foreground"
              >
                LinkedIn
              </a>
            </Magnetic>
          </div>
        </Reveal>
        <p className="mt-20 text-xs text-muted">
          © 2026 Ilias Kalalou · Built from scratch with Next.js
        </p>
      </section>
    </main>
  );
}
