"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { features } from "@/lib/features";

const links = [
  { href: "/", label: "Übersicht", match: "exact" as const },
  {
    href: "/parlament/de_bundestag",
    label: "Deutschland",
    match: "parlament" as const,
  },
  {
    href: "/deutschland/laender",
    label: "Länder",
    match: "laender" as const,
  },
  { href: "/bundesrat", label: "Bundesrat", match: "prefix" as const },
  ...(features.europe
    ? [{ href: "/europa", label: "Europa", match: "prefix" as const }]
    : []),
  { href: "/institute", label: "Institute", match: "prefix" as const },
];

function isActive(
  pathname: string,
  href: string,
  match: "exact" | "prefix" | "parlament" | "laender",
): boolean {
  if (match === "exact") return pathname === href;
  if (match === "laender") {
    return pathname === href || pathname.startsWith(`${href}/`);
  }
  if (match === "parlament") {
    return pathname === "/parlament" || pathname.startsWith("/parlament/");
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function SiteNav() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-40 border-b border-ink/10 bg-paper/80 backdrop-blur">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-3">
        <Link href="/" className="font-display text-xl tracking-tight text-ink">
          Poll-Position
        </Link>
        <nav className="flex flex-wrap gap-1 text-sm">
          {links.map((l) => {
            const active = isActive(pathname, l.href, l.match);
            return (
              <Link
                key={l.href}
                href={l.href}
                className={
                  active
                    ? "rounded-md bg-mist/70 px-2.5 py-1.5 font-medium text-ink underline decoration-sea decoration-2 underline-offset-4"
                    : "rounded-md px-2.5 py-1.5 text-ink/70 transition hover:bg-mist/60 hover:text-ink"
                }
                aria-current={active ? "page" : undefined}
              >
                {l.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
