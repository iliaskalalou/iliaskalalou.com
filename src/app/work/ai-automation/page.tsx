import ProjectPage, { type Project } from "@/components/ProjectPage";

// Deliberately short. The mechanism is confidential and inventing detail
// to fill the page would be worse than the silence.
const project: Project = {
  index: "02 / 03",
  title: "Automating the work nobody should be doing by hand",
  lead:
    "Inside the same firm, a set of AI systems that run every day on work that used to be manual, repetitive and slow. What they do is covered by confidentiality; that they run in production is not.",
  facts: [
    { label: "Client", value: "Kohen Avocats, Paris" },
    { label: "Status", value: "In production" },
    { label: "Detail", value: "Under NDA" },
    { label: "Field", value: "Professional services" },
  ],
  sections: [
    {
      heading: "Why it is short",
      body: [
        "A law firm's internal processes are its own. I am not going to describe them to win a page of portfolio, and a client who is considering me should probably find that reassuring rather than frustrating.",
        "What can be said: these are systems that took a repetitive professional task, one done by hand every day, and made it run on its own — with the checks that a firm needs before it will trust anything with its files.",
      ],
    },
    {
      heading: "What it says about the work",
      body: [
        "Most AI work in a firm like this is not about the model. It is about the plumbing around it: getting the data out of the places it actually lives, handling documents that are never quite standard, and failing safely when something is off.",
        "That is the part I do, and it is the part that decides whether a system is still running six months later.",
      ],
    },
  ],
  next: { title: "Fishing net inspection", href: "/work/fishing-nets" },
};

export default function Page() {
  return <ProjectPage project={project} />;
}
