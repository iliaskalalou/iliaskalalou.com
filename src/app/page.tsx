import HeroV2 from "@/components/heroes/HeroV2";
import Magnetic from "@/components/Magnetic";
import Marquee from "@/components/Marquee";
import Reveal, { RevealText } from "@/components/Reveal";
import WorkGallery, { type WorkItem } from "@/components/WorkGallery";

const workItems: WorkItem[] = [
  {
    title: "Freelance — AI Startup",
    tag: "ML Engineering",
    year: "2025 — now",
    description:
      "A year of production work: data pipelines, model training and shipping ML systems.",
  },
  { title: "Project Two", tag: "To be added" },
  { title: "Project Three", tag: "To be added" },
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
        <WorkGallery items={workItems} />
      </section>

      <section id="about" className="scroll-mt-24 px-6 py-24 md:px-12">
        <Reveal>
          <p className="mb-10 text-sm uppercase tracking-[0.25em] text-muted">
            About
          </p>
        </Reveal>
        <Reveal delay={0.08}>
          <p className="max-w-2xl text-xl leading-relaxed text-muted md:text-2xl">
            Engineering student at EPITA, AI &amp; Big Data major, class of 2027.
            One year of hands-on freelance experience shipping machine learning
            systems for an AI startup. This section is a placeholder — we will
            write the real story together.
          </p>
        </Reveal>
      </section>

      <section
        id="contact"
        className="scroll-mt-24 flex min-h-[70svh] flex-col justify-center px-6 py-24 md:px-12"
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
        <p className="mt-24 text-xs text-muted">
          © 2026 Ilias Kalalou · Built from scratch with Next.js
        </p>
      </section>
    </main>
  );
}
