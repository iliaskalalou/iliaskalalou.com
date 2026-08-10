# iliaskalalou.com

Personal site of Ilias Kalalou — AI & Data engineer, EPITA (AI & Big Data major),
freelance machine learning engineer.

## Stack

- [Next.js 16](https://nextjs.org) (App Router) + TypeScript
- [Tailwind CSS 4](https://tailwindcss.com) — CSS-first config, no `tailwind.config.js`
- [Framer Motion](https://motion.dev) for the interaction layer
- [Lenis](https://lenis.darkroom.engineering) for smooth scrolling

## Development

```bash
npm install
npm run dev
```

The site runs at http://localhost:3000.

```bash
npm run build   # production build
npx tsc --noEmit
npx eslint src/
```

## Notes

Motion is opt-out: every animated component honours
`prefers-reduced-motion`, rendering the final state instantly for visitors who
ask for it.

Search indexing is controlled by a single flag in [`src/lib/site.ts`](src/lib/site.ts).
While `INDEXABLE` is `false`, `robots.txt` disallows crawlers and the pages carry a
`noindex` meta tag.
