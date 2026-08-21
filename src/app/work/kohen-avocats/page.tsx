import ProjectPage, { type Project } from "@/components/ProjectPage";

// Tout ce qui est affirmé ici a été vérifié sur le site en ligne, pas supposé.
// La contribution exacte d'Ilias reste à préciser : il ne l'a pas fait seul et
// il vaut mieux le dire clairement une fois qu'il aura confirmé ce qui est de lui.
const project: Project = {
  index: "01 / 03",
  title: "Exister sur « avocat pénaliste à Paris »",
  lead:
    "Kohen Avocats est un cabinet pénaliste parisien. L’objectif du site n’était pas d’être joli : c’était d’être trouvé. Ressortir sur les recherches qui amènent des dossiers, dans une ville où la concurrence sur ces mots-clés est féroce, et transformer ces visites en appels.",
  facts: [
    { label: "Client", value: "Kohen Avocats, Paris" },
    { label: "Domaines", value: "Pénal, famille, social" },
    { label: "Périmètre", value: "~80 pages, 8 langues" },
    { label: "Stack", value: "WordPress, Elementor, Cloudflare" },
  ],
  shots: [
    {
      src: "/work/kohen/home.webp",
      caption: "L’accueil — les huit drapeaux en haut à droite, la note Google en bas à gauche",
      width: 1400,
      height: 875,
      wide: true,
    },
    {
      src: "/work/kohen/reviews.webp",
      caption: "Les domaines d’intervention, puis les avis Google et Trustpilot agrégés en direct",
      width: 1400,
      height: 875,
    },
    {
      src: "/work/kohen/arabic.webp",
      caption: "La version arabe est en vraie droite-à-gauche : toute la mise en page bascule",
      width: 1400,
      height: 875,
    },
    {
      src: "/work/kohen/mobile.webp",
      caption: "Le mobile, d’où vient l’essentiel du trafic",
      width: 390,
      height: 844,
    },
  ],
  sections: [
    {
      heading: "L’objectif",
      body: [
        "Un cabinet d’avocats se fait connaître par la recommandation et par la recherche. La recommandation, il l’avait déjà. La recherche, non : sans présence en ligne construite, un cabinet n’existe pas pour les gens qui ne le connaissent pas encore.",
        "Le brief était donc commercial avant d’être technique : ressortir sur les requêtes qui amènent réellement des dossiers — garde à vue, comparution immédiate, mise en examen — et convertir ces visites en prises de contact.",
      ],
    },
    {
      heading: "Ce qui a été construit pour ça",
      body: [
        "Environ quatre-vingts pages, organisées par situation plutôt que par logique interne au cabinet. Quelqu’un qui cherche un cas précis arrive sur la page de ce cas, pas sur un accueil généraliste — c’est ce qui fait la différence entre une visite et un appel.",
        "Une couche complète de données structurées : le cabinet comme service juridique, ses domaines, ses questions fréquentes, ses avis, son fil d’ariane. C’est la moitié invisible du travail, celle qui décide si un cabinet apparaît dans les résultats cartographiques ou en troisième page.",
        "Et huit langues, correctement déclarées, pour élargir l’audience au-delà des francophones. Ce n’est pas le cœur du sujet, mais dans une ville comme Paris ça ouvre une part de marché que la plupart des cabinets laissent de côté.",
      ],
    },
    {
      heading: "Deux détails qui comptent",
      body: [
        "La version arabe n’est pas une traduction posée dans une maquette française. Le sens de lecture s’inverse, la navigation passe en miroir, le bouton d’appel change de côté — tout se lit de droite à gauche, comme il se doit.",
        "Les avis sont tirés de deux sources en même temps, Google et Trustpilot, avec leurs compteurs réels. Pour un pénaliste ce n’est pas décoratif : c’est la première chose que cherche quelqu’un d’inquiet.",
      ],
    },
    {
      heading: "Ma part",
      body: [
        "Je n’ai pas fait ce site seul, et le détail de ce qui est de moi est en cours de rédaction plutôt que noyé dans le flou.",
      ],
    },
  ],
  external: { label: "Voir kohenavocats.com", href: "https://kohenavocats.com" },
  next: { title: "Automatisation IA", href: "/work/ai-automation" },
};

export default function Page() {
  return <ProjectPage project={project} />;
}
