import ProjectPage, { type Project } from "@/components/ProjectPage";

// Le client n'est volontairement pas nommé. Les chiffres techniques — modèle,
// stack, cadence, précision — restent à fournir par Ilias.
const project: Project = {
  index: "03 / 03",
  title: "Repérer les trous d’un filet de pêche depuis le plafond",
  lead:
    "Une entreprise de pêche avait besoin de savoir où ses filets étaient déchirés. Les filets sont immenses, les trous sont petits, et jusque-là il fallait parcourir toute la surface à la main pour les trouver.",
  facts: [
    { label: "Client", value: "Secteur de la pêche" },
    { label: "Domaine", value: "Vision par ordinateur" },
    { label: "Terrain", value: "Hangar, caméras de plafond" },
    { label: "Entreprise", value: "SCIEN" },
  ],
  sections: [
    {
      heading: "Le dispositif",
      body: [
        "Les filets sont étalés à plat sur le sol d’un hangar, sous des caméras fixées au plafond qui les regardent à la verticale. Un modèle localise chaque trou à réparer et indique aux équipes où intervenir.",
        "L’intérêt du projet tient à sa simplicité : la valeur se comprend sans explication, technique ou pas. Quelqu’un parcourait un filet entier à la recherche de dégâts ; désormais on lui indique où aller.",
      ],
    },
    {
      heading: "Pourquoi c’est plus difficile qu’il n’y paraît",
      body: [
        "Un filet n’est qu’une grille de vides : le défaut, c’est un vide de la mauvaise forme au mauvais endroit. Le modèle doit donc distinguer la maille de la déchirure, à une échelle où les deux ne font que quelques pixels.",
        "S’y ajoutent un sol jamais éclairé uniformément, des filets jamais parfaitement à plat, et des caméras qui voient le même filet sous des angles différents selon la façon dont il retombe.",
      ],
    },
  ],
  next: { title: "Kohen Avocats", href: "/work/kohen-avocats" },
};

export default function Page() {
  return <ProjectPage project={project} />;
}
