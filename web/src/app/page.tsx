import Link from "next/link";
import { ThresholdWatchOverview } from "@/components/ThresholdWatch";
import { features } from "@/lib/features";

export default function HomePage() {
  return (
    <div className="space-y-16">
      <section className="relative overflow-hidden rounded-2xl border border-ink/10 bg-gradient-to-br from-sea/15 via-paper to-accent/10 px-6 py-16 md:px-12 md:py-24">
        <p className="font-display text-5xl tracking-tight text-ink md:text-7xl">
          Poll-Position
        </p>
        <h1 className="mt-4 max-w-xl text-lg text-ink/70 md:text-xl">
          Umfragetrends, Sitzprojektionen und Koalitionsszenarien
          {features.europe ? " — Deutschland und Europa." : " für Deutschland."}
        </h1>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link
            href="/parlament/de_bundestag"
            className="rounded-md bg-ink px-5 py-2.5 text-sm font-semibold text-paper transition hover:bg-sea"
          >
            Deutschland
          </Link>
          {features.europe ? (
            <Link
              href="/europa"
              className="rounded-md border border-ink/20 bg-white/60 px-5 py-2.5 text-sm font-semibold text-ink transition hover:bg-white"
            >
              Europa
            </Link>
          ) : null}
        </div>
      </section>

      <ThresholdWatchOverview />

      <section
        className={
          features.europe ? "grid gap-6 md:grid-cols-2" : "grid gap-6"
        }
      >
        <div>
          <h2 className="font-display text-2xl text-ink">Deutschland</h2>
          <ul className="mt-4 space-y-2 text-ink/75">
            <li>
              <Link className="hover:text-sea" href="/parlament/de_bundestag">
                Bundestag — Trends & Koalitionen
              </Link>
            </li>
            <li>
              <Link className="hover:text-sea" href="/deutschland/laender">
                Länder — Karte & Landtage
              </Link>
            </li>
            <li>
              <Link className="hover:text-sea" href="/bundesrat">
                Bundesrat — Sandbox
              </Link>
            </li>
            <li>
              <Link className="hover:text-sea" href="/institute">
                Institute — Rangliste
              </Link>
            </li>
          </ul>
        </div>
        {features.europe ? (
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
        ) : null}
      </section>
    </div>
  );
}
