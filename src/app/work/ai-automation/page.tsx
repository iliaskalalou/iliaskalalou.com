import ProjectPage, { type Project } from "@/components/ProjectPage";

// Volontairement court. Le mécanisme est confidentiel, et inventer du détail
// pour remplir la page serait pire que le silence.
const project: Project = {
  index: "02 / 03",
  title: "Automatiser le travail que personne ne devrait faire à la main",
  lead:
    "Dans le même cabinet, un ensemble de systèmes d’IA qui tournent chaque jour sur des tâches auparavant manuelles, répétitives et lentes. Ce qu’ils font est couvert par la confidentialité ; le fait qu’ils tournent en production ne l’est pas.",
  facts: [
    { label: "Client", value: "Kohen Avocats, Paris" },
    { label: "État", value: "En production" },
    { label: "Détail", value: "Sous NDA" },
    { label: "Secteur", value: "Services professionnels" },
  ],
  sections: [
    {
      heading: "Pourquoi c’est court",
      body: [
        "Les processus internes d’un cabinet lui appartiennent. Je ne vais pas les décrire pour gagner une page de portfolio, et un client qui m’évalue devrait y voir une garantie plutôt qu’une frustration.",
        "Ce que je peux dire : il s’agit de systèmes qui ont pris une tâche professionnelle répétitive, faite à la main chaque jour, et l’ont rendue autonome — avec les vérifications qu’un cabinet exige avant de confier quoi que ce soit à ses dossiers.",
      ],
    },
    {
      heading: "Ce que ça dit du travail",
      body: [
        "L’essentiel du travail d’IA dans une structure comme celle-là ne porte pas sur le modèle. Il porte sur tout ce qu’il y a autour : aller chercher la donnée là où elle se trouve vraiment, composer avec des documents qui ne sont jamais tout à fait normalisés, et s’arrêter proprement quand quelque chose cloche.",
        "C’est cette partie-là que je fais, et c’est elle qui détermine si un système tourne encore six mois plus tard.",
      ],
    },
  ],
  next: { title: "Inspection de filets de pêche", href: "/work/fishing-nets" },
};

export default function Page() {
  return <ProjectPage project={project} />;
}
