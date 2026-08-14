import type { ReactNode } from "react";

// An empty full-height stage. The Japanese scene gets composited in here,
// layer by layer. Deliberately holds nothing but the nav above it and the
// slots below, so the composition can be judged without existing copy
// getting in the way.
export default function HeroStage({ children }: { children?: ReactNode }) {
  return (
    <section className="relative min-h-svh w-full overflow-hidden">
      {children}
    </section>
  );
}
