"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { siteConfig } from "@/lib/config";

const links = [
  { href: "/", label: "Home" },
  { href: "/app", label: "Workspace" },
  { href: "/how-it-works", label: "How it works" },
];

export default function Nav() {
  const pathname = usePathname();
  return (
    <header className="sticky top-0 z-20 border-b border-line bg-mist/90 backdrop-blur">
      <nav className="mx-auto flex max-w-6xl items-center justify-between px-5 py-3">
        <Link href="/" className="script whitespace-nowrap text-2xl text-teal sm:text-3xl">
          {siteConfig.name}
        </Link>
        <ul className="flex items-center gap-1 sm:gap-2">
          {links.map((l) => {
            const active = l.href === "/" ? pathname === "/" : pathname.startsWith(l.href);
            return (
              <li key={l.href}>
                <Link
                  href={l.href}
                  className={`whitespace-nowrap rounded-full px-2.5 py-1.5 text-base transition sm:px-4 ${
                    active ? "bg-sky font-bold text-teal-dark" : "text-muted hover:text-teal"
                  }`}
                >
                  {l.label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </header>
  );
}
