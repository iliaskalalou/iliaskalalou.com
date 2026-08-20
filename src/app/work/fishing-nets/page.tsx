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
        "Les filets sont étalés à plat sur le sol d’un hangar. Des caméras fixées au plafond les regardent à la verticale. Depuis ce point de vue, un modèle localise chaque trou à réparer et indique aux équipes où intervenir.",
        "C’est un bon problème parce qu’il est honnête : la valeur est évidente pour n’importe qui, technique ou non. Quelqu’un parcourait un filet à la recherche de dégâts ; maintenant on lui dit où aller.",
      ],
    },
    {
      heading: "Pourquoi c’est plus difficile qu’il n’y paraît",
      body: [
        "Un filet n’est qu’une succession de trous. L’objet entier est une grille de vides, et le défaut est un vide de la mauvaise forme au mauvais endroit — le modèle doit donc apprendre la différence entre la maille et la déchirure, à une échelle où les deux font quelques pixels.",
        "Ajoutez un sol jamais éclairé uniformément, des filets jamais parfaitement à plat, et des caméras qui voient le même filet sous des angles différents selon l’endroit où il tombe.",
      ],
    },
  ],
  next: { title: "Kohen Avocats", href: "/work/kohen-avocats" },
};

export default function Page() {
  return <ProjectPage project={project} />;
}
