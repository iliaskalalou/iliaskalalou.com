"use client";

import {
  useEffect,
  useRef,
  useSyncExternalStore,
  type FocusEvent,
  type UIEvent,
} from "react";
import { motion, useMotionValue, useScroll, useTransform } from "framer-motion";

const HORIZONTAL_QUERY =
  "(min-width: 768px) and (pointer: fine) and (prefers-reduced-motion: no-preference)";

let horizontalQuery: MediaQueryList | null = null;

function getHorizontalQuery() {
  horizontalQuery ??= window.matchMedia(HORIZONTAL_QUERY);
  return horizontalQuery;
}

function subscribeToHorizontal(onChange: () => void) {
  const query = getHorizontalQuery();
  query.addEventListener("change", onChange);
  return () => query.removeEventListener("change", onChange);
}

function useHorizontalGallery() {
  return useSyncExternalStore(
    subscribeToHorizontal,
    () => getHorizontalQuery().matches,
    () => false,
  );
}

export type WorkItem = {
  title: string;
  tag: string;
  year?: string;
  description?: string;
  href?: string;
};

type WorkGalleryProps = {
  items: WorkItem[];
  className?: string;
};

const formatIndex = (value: number) => String(value).padStart(2, "0");

type WorkCardProps = {
  item: WorkItem;
  index: number;
  layout: "row" | "stack";
};

function WorkCard({ item, index, layout }: WorkCardProps) {
  const cardClass = `flex flex-col justify-between gap-10 rounded-2xl border border-line bg-white/[0.03] transition-colors duration-500 hover:border-foreground ${
    layout === "row"
      ? "h-[68svh] w-[75vw] max-w-[900px] shrink-0 p-8 lg:p-12"
      : "min-h-[380px] w-full p-6 md:p-10"
  }`;

  const content = (
    <>
      <div className="flex items-start justify-between gap-6">
        <span
          aria-hidden
          className="font-mono text-7xl font-semibold leading-none text-foreground/10 md:text-8xl lg:text-9xl"
        >
          {formatIndex(index + 1)}
        </span>
        <p className="pt-1 text-right font-mono text-xs uppercase tracking-[0.2em] text-muted">
          {item.tag}
          {item.year ? <span className="mt-1 block">{item.year}</span> : null}
        </p>
      </div>
      <div>
        <h3 className="text-3xl font-semibold tracking-tight md:text-5xl lg:text-6xl">
          {item.title}
        </h3>
        {item.description ? (
          <p className="mt-4 max-w-md text-sm leading-relaxed text-muted md:text-base">
            {item.description}
          </p>
        ) : null}
      </div>
    </>
  );

  if (item.href) {
    return (
      <a
        href={item.href}
        className={`${cardClass} focus-visible:border-foreground focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-foreground`}
      >
        {content}
      </a>
    );
  }

  return <article className={cardClass}>{content}</article>;
}

export default function WorkGallery({ items, className }: WorkGalleryProps) {
  const outerRef = useRef<HTMLDivElement>(null);
  const stageRef = useRef<HTMLDivElement>(null);
  const trackRef = useRef<HTMLDivElement>(null);
  const horizontal = useHorizontalGallery();
  const maxShift = useMotionValue(0);

  const { scrollYProgress } = useScroll({
    target: outerRef,
    offset: ["start start", "end end"],
  });

  const x = useTransform(() => {
    const progress = scrollYProgress.get();
    return Number.isFinite(progress) ? -progress * maxShift.get() : 0;
  });

  const counter = useTransform(scrollYProgress, (value) => {
    const progress = Number.isFinite(value)
      ? Math.min(Math.max(value, 0), 1)
      : 0;
    return formatIndex(
      Math.min(items.length, Math.floor(progress * items.length) + 1),
    );
  });

  useEffect(() => {
    if (!horizontal) return;

    const stage = stageRef.current;
    const track = trackRef.current;
    if (!stage || !track) return;

    const measure = () => {
      maxShift.set(Math.max(0, track.scrollWidth - stage.clientWidth));
    };

    measure();

    const observer = new ResizeObserver(measure);
    observer.observe(stage);
    observer.observe(track);

    let cancelled = false;
    document.fonts.ready.then(() => {
      if (!cancelled) measure();
    });

    return () => {
      cancelled = true;
      observer.disconnect();
    };
  }, [horizontal, maxShift]);

  const keepStagePinned = (event: UIEvent<HTMLDivElement>) => {
    event.currentTarget.scrollLeft = 0;
  };

  const scrollFocusedCardIntoView = (event: FocusEvent<HTMLDivElement>) => {
    const outer = outerRef.current;
    const stage = stageRef.current;
    const card = event.target;
    if (!outer || !stage || !(card instanceof HTMLElement)) return;

    const shift = maxShift.get();
    const range = outer.offsetHeight - stage.offsetHeight;
    if (shift <= 0 || range <= 0) return;

    const targetX = Math.min(
      Math.max(card.offsetLeft + card.offsetWidth / 2 - stage.clientWidth / 2, 0),
      shift,
    );

    window.scrollTo({
      top:
        outer.getBoundingClientRect().top +
        window.scrollY +
        (targetX / shift) * range,
    });
  };

  return (
    <div className={className ? `relative ${className}` : "relative"}>
      <div
        ref={outerRef}
        className="relative hidden md:pointer-fine:motion-safe:block"
        style={{
          height: `${Math.min(320, Math.max(260, 200 + items.length * 25))}svh`,
        }}
      >
        <div
          ref={stageRef}
          className="sticky top-0 flex h-svh items-center overflow-hidden"
          onScroll={keepStagePinned}
          onFocus={scrollFocusedCardIntoView}
        >
          <motion.div
            ref={trackRef}
            className="flex w-max items-center gap-8 px-12 will-change-transform"
            style={{ x }}
          >
            {items.map((item, index) => (
              <WorkCard
                key={`${item.title}-${index}`}
                item={item}
                index={index}
                layout="row"
              />
            ))}
          </motion.div>

          <div
            aria-hidden
            className="pointer-events-none absolute inset-x-12 bottom-8 flex items-center gap-6"
          >
            <p className="font-mono text-xs tracking-[0.2em] text-muted">
              <motion.span>{counter}</motion.span>
              {` / ${formatIndex(items.length)}`}
            </p>
            <div className="h-px flex-1 bg-line">
              <motion.div
                className="h-full origin-left bg-foreground"
                style={{ scaleX: scrollYProgress }}
              />
            </div>
          </div>
        </div>
      </div>

      <div className="flex flex-col gap-6 px-6 md:pointer-fine:motion-safe:hidden md:px-12">
        {items.map((item, index) => (
          <WorkCard
            key={`${item.title}-${index}`}
            item={item}
            index={index}
            layout="stack"
          />
        ))}
      </div>
    </div>
  );
}
