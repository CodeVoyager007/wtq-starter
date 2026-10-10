"use client";

import { useState } from "react";

export type Pic = { src: string; fallback: string; alt: string };

/** Shows the Unsplash photo. If it cannot load (offline, blocked), shows the local fallback image. */
export default function Photo({ pic, className = "", priority = false }: { pic: Pic; className?: string; priority?: boolean }) {
  const [src, setSrc] = useState(pic.src);
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={src}
      alt={pic.alt}
      className={className}
      loading={priority ? "eager" : "lazy"}
      decoding="async"
      referrerPolicy="no-referrer"
      onError={() => src !== pic.fallback && setSrc(pic.fallback)}
    />
  );
}
