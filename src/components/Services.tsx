"use client";

import { motion, useReducedMotion } from "framer-motion";

const EASE = [0.16, 1, 0.3, 1] as const;

const services = [
  {
    title: "IA & machine learning",
    body: "Pipelines de données, entraînement et mise en production de modèles, automatisation de tâches métier répétitives.",
  },
  {
    title: "Développement web",
    body: "Sites vitrines et applications, de la conception à la mise en ligne, avec l’infrastructure qui va avec.",
  },
  {
    title: "Référencement & acquisition",
    body: "SEO technique, données structurées, campagnes publicitaires. Être trouvé par les gens qui vous cherchent.",
  },
];

export default function Services() {
  const still = useReducedMotion() ?? false;

  return (
    <section
      id="services"
      className="scroll-mt-24 border-b border-line px-6 py-24 md:px-12"
    >
      <div className="mx-auto max-w-[1400px]">
        <p className="mb-10 text-sm uppercase tracking-[0.25em] text-muted">
          Ce que je fais
        </p>

        <p className="mb-16 max-w-[58ch] text-xl leading-relaxed md:text-2xl">
          Deux besoins qui vont ensemble : être trouvé par de nouveaux clients,
          et cesser de perdre du temps sur ce qui peut tourner tout seul. Je
          couvre les deux.
        </p>

        <div className="grid gap-x-12 gap-y-12 md:grid-cols-3">
          {services.map((s, i) => (
            <motion.div
              key={s.title}
              initial={still ? false : { y: 20 }}
              whileInView={still ? undefined : { y: 0 }}
              viewport={{ once: true, margin: "0px 0px -12% 0px" }}
              transition={
                still ? { duration: 0 } : { duration: 0.7, delay: i * 0.07, ease: EASE }
              }
              className="border-t border-line pt-6"
            >
              <h3 className="text-xl font-medium tracking-[-0.015em] md:text-2xl">
                {s.title}
              </h3>
              <p className="mt-4 text-[15px] leading-relaxed text-muted md:text-base">
                {s.body}
              </p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
