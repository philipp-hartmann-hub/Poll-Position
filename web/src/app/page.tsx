import Link from "next/link";
import { ThresholdWatchOverview } from "@/components/ThresholdWatch";

export default function HomePage() {
  return (
    <div className="space-y-16">
      <section className="relative overflow-hidden rounded-2xl border border-ink/10 bg-gradient-to-br from-sea/15 via-paper to-accent/10 px-6 py-16 md:px-12 md:py-24">
        <p className="font-display text-5xl tracking-tight text-ink md:text-7xl">
          Poll-Position
        </p>
        <h1 className="mt-4 max-w-xl text-lg text-ink/70 md:text-xl">
          Umfragetrends, Sitzprojektionen und Koalitionsszenarien — Deutschland
          und Europa.
        </h1>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link
            href="/deutschland/bund"
            className="rounded-md bg-ink px-5 py-2.5 text-sm font-semibold text-paper transition hover:bg-sea"
          >
            Deutschland
          </Link>
          <Link
            href="/europa"
            className="rounded-md border border-ink/20 bg-white/60 px-5 py-2.5 text-sm font-semibold text-ink transition hover:bg-white"
          >
            Europa
          </Link>
        </div>
      </section>

      <ThresholdWatchOverview />

      <section className="grid gap-6 md:grid-cols-2">
        <div>
          <h2 className="font-display text-2xl text-ink">Deutschland</h2>
          <ul className="mt-4 space-y-2 text-ink/75">
            <li>
              <Link className="hover:text-sea" href="/deutschland/bund">
                Bundestag — Trends & Koalitionen
              </Link>
            </li>
            <li>
              <Link className="hover:text-sea" href="/deutschland/laender">
                Länder — Landtage
              </Link>
            </li>
            <li>
              <Link className="hover:text-sea" href="/institute">
                Institute — House Effects
              </Link>
            </li>
            <li>
              <Link className="hover:text-sea" href="/szenario">
                Was wäre wenn — Szenarien
              </Link>
            </li>
          </ul>
        </div>
        <div>
          <h2 className="font-display text-2xl text-ink">Europa</h2>
          <ul className="mt-4 space-y-2 text-ink/75">
            <li>
              <Link className="hover:text-sea" href="/europa">
                Übersichtskarte nach Parteienfamilie
              </Link>
            </li>
          </ul>
        </div>
      </section>
    </div>
  );
}
