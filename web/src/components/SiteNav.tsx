import Link from "next/link";

const links = [
  { href: "/", label: "Übersicht" },
  { href: "/deutschland/bund", label: "Bund" },
  { href: "/deutschland/laender", label: "Länder" },
  { href: "/bundesrat", label: "Bundesrat" },
  { href: "/europa", label: "Europa" },
  { href: "/institute", label: "Institute" },
  { href: "/szenario", label: "Szenario" },
];

export function SiteNav() {
  return (
    <header className="border-b border-ink/10 bg-paper/80 backdrop-blur sticky top-0 z-40">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-3">
        <Link href="/" className="font-display text-xl tracking-tight text-ink">
          Poll-Position
        </Link>
        <nav className="flex flex-wrap gap-1 text-sm">
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className="rounded-md px-2.5 py-1.5 text-ink/70 transition hover:bg-mist/60 hover:text-ink"
            >
              {l.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
