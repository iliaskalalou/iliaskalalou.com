import ProjectPage, { type Project } from "@/components/ProjectPage";

// The client is deliberately not named. Technical figures — model, stack,
// throughput, accuracy — are still to be supplied by Ilias.
const project: Project = {
  index: "03 / 03",
  title: "Finding the holes in a fishing net from the ceiling",
  lead:
    "A fishing company needed to know where its nets were torn. The nets are enormous, the holes are small, and until then someone had to walk the whole surface looking for them.",
  facts: [
    { label: "Client", value: "Fishing industry" },
    { label: "Field", value: "Computer vision" },
    { label: "Setting", value: "Hangar, ceiling cameras" },
    { label: "Company", value: "SCIEN" },
  ],
  sections: [
    {
      heading: "The setting",
      body: [
        "Nets are spread flat across the floor of a hangar. Cameras mounted on the ceiling look straight down at them. From that view, a model locates every hole that needs repairing and shows the crew where to work.",
        "It is a good problem because it is honest: the value is obvious to anyone, technical or not. Someone was walking a net looking for damage; now they are told where to go.",
      ],
    },
    {
      heading: "Why it is harder than it sounds",
      body: [
        "A net is mostly holes. The whole object is a grid of gaps, and the defect is a gap of the wrong shape in the wrong place — so the model has to learn the difference between the mesh and a tear, at a scale where both are a few pixels.",
        "Add a floor that is never evenly lit, nets that are never laid perfectly flat, and cameras that see the same net at different angles depending on where it falls.",
      ],
    },
  ],
  next: { title: "Kohen Avocats", href: "/work/kohen-avocats" },
};

export default function Page() {
  return <ProjectPage project={project} />;
}
