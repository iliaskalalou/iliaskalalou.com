import ProjectPage, { type Project } from "@/components/ProjectPage";

// Tout ce qui est affirmé ici a été vérifié sur le site en ligne, pas supposé.
// La contribution exacte d'Ilias reste à préciser : il ne l'a pas fait seul et
// il vaut mieux le dire clairement une fois qu'il aura confirmé ce qui est de lui.
const project: Project = {
  index: "01 / 03",
  title: "Un cabinet qui devait être trouvé en huit langues",
  lead:
    "Kohen Avocats est un cabinet pénaliste parisien. On ne cherche pas un avocat pénaliste comme on cherche un prestataire : on le cherche dans l’urgence, souvent au pire moment, et fréquemment pas en français. Le site devait répondre à ça.",
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
      heading: "Le problème",
      body: [
        "Quelqu’un cherche à deux heures du matin, depuis un commissariat ou le téléphone d’un proche, avec les mots de sa propre langue et de sa propre panique : garde à vue, comparution immédiate, mise en examen.",
        "Le site devait donc faire deux choses à la fois : ressortir sur ces recherches précises, et rester lisible par des gens qui ne parlent pas français.",
      ],
    },
    {
      heading: "Ce que fait le site",
      body: [
        "Huit langues — français, anglais, arabe, turc, russe, portugais, chinois et luxembourgeois — chacune déclarée correctement, pour que les moteurs servent la bonne version au lieu de deviner.",
        "Environ quatre-vingts pages, organisées par domaine d’intervention plutôt que par logique interne. Quelqu’un qui cherche une situation précise arrive sur la page de cette situation, pas sur un accueil généraliste.",
        "Une couche complète de données structurées : le cabinet comme service juridique, ses domaines, ses questions fréquentes, ses avis, son fil d’ariane. C’est la moitié invisible du travail, et c’est elle qui place un cabinet devant les résultats cartographiques plutôt qu’en troisième page.",
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
