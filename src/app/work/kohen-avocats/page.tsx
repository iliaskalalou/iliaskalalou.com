import ProjectPage, { type Project } from "@/components/ProjectPage";

// Everything stated here was verified against the live site rather than
// assumed. Ilias's precise contribution is still to be added — he did not
// build it alone and that should be said plainly once he confirms what
// was his.
const project: Project = {
  index: "01 / 03",
  title: "A law firm that had to be found in eight languages",
  lead:
    "Kohen Avocats is a criminal-law practice in Paris. People reach a criminal lawyer in a hurry, often at the worst moment of their life, and frequently not in French. The site had to answer that.",
  facts: [
    { label: "Client", value: "Kohen Avocats, Paris" },
    { label: "Field", value: "Criminal, family and employment law" },
    { label: "Scope", value: "~80 pages, 8 languages" },
    { label: "Stack", value: "WordPress, Elementor, Cloudflare" },
  ],
  sections: [
    {
      heading: "The problem",
      body: [
        "A criminal lawyer is not chosen the way a supplier is. Someone searches at two in the morning, from a police station or a family member's phone, using the words of their own language and their own panic — police custody, immediate appearance, indictment.",
        "So the site had to do two things at once: be found on those exact searches, and be readable by people who do not speak French.",
      ],
    },
    {
      heading: "What the site does",
      body: [
        "Eight languages — French, English, Arabic, Turkish, Russian, Portuguese, Chinese and Luxembourgish — each properly declared so search engines serve the right one instead of guessing.",
        "Around eighty pages, organised by practice area rather than by internal structure: criminal, employment, family. Someone looking for one specific situation lands on the page about that situation, not on a general homepage.",
        "A complete structured-data layer — the firm as a legal service, its practice areas, its FAQs, its reviews, its breadcrumbs. It is the invisible half of the work, and it is what puts a firm in front of the map results rather than on page three.",
      ],
    },
    {
      heading: "My part",
      body: [
        "I did not build this alone, and the detail of what is mine is being written up properly rather than blurred.",
      ],
    },
  ],
  external: { label: "Visit kohenavocats.com", href: "https://kohenavocats.com" },
  next: { title: "AI process automation", href: "/work/ai-automation" },
};

export default function Page() {
  return <ProjectPage project={project} />;
}
