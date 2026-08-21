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
    meta: "Site vitrine · SEO",
    description:
      "Un site vitrine construit pour être trouvé : environ quatre-vingts pages organisées par situation, données structurées complètes, référencement local. L’objectif était d’amener des dossiers, pas de faire joli.",
    href: "/work/kohen-avocats",
  },
  {
    index: "02",
    title: "Automatisation IA",
    meta: "En production · sous NDA",
    description:
      "Un système d’IA interne qui tourne au quotidien dans le même cabinet. Le mécanisme reste confidentiel ; ce qu’il remplaçait était manuel, répétitif et lent.",
    href: "/work/ai-automation",
  },
  {
    index: "03",
    title: "Inspection de filets de pêche",
    meta: "Vision par ordinateur",
    description:
      "Les filets sont étalés au sol d’un hangar, sous des caméras de plafond. Un modèle de vision localise chaque trou à réparer et indique aux équipes où intervenir.",
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
            Projets
          </p>
        </Reveal>
        <WorkList items={workItems} />
      </section>

      <section id="about" className="scroll-mt-24 px-6 py-24 md:px-12">
        <Reveal>
          <p className="mb-10 text-sm uppercase tracking-[0.25em] text-muted">
            À propos
          </p>
        </Reveal>
        <Reveal delay={0.08}>
          <p className="max-w-2xl text-xl leading-relaxed text-muted md:text-2xl">
            Un an de freelance pour une startup d’IA : pipelines de données,
            entraînement de modèles, et mise en production de systèmes de
            machine learning qui tiennent dans la durée. Actuellement en fin de
            cycle ingénieur à l’EPITA, majeure IA &amp; Big Data. Cette section
            est provisoire — le vrai texte reste à écrire.
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
          <RevealText text="Travaillons ensemble" />
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
          © 2026 Ilias Kalalou · Conçu et développé avec Next.js
        </p>
      </section>
    </main>
  );
}
