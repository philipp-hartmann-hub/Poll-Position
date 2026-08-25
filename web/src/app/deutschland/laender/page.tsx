import { GermanyMap } from "@/components/GermanyMap";
import { LaenderIndex } from "@/components/LaenderIndex";
import Link from "next/link";

export default function LaenderPage() {
  return (
    <div className="space-y-10">
      <div className="space-y-4">
        <p className="text-sm uppercase tracking-wide text-ink/45">Deutschland</p>
        <h1 className="font-display text-3xl tracking-tight text-ink md:text-4xl">
          Land wählen
        </h1>
        <p className="max-w-2xl text-ink/60">
          Karte nach stärkster Partei im aktuellen Umfragemittel — Klick öffnet
          Sitze, Koalitionen und Szenarien. Darunter die vollständige Liste für
          Tastatur und Screenreader.
        </p>
        <p className="text-sm text-ink/55">
          Oder direkt zum{" "}
          <Link
            className="text-sea underline-offset-2 hover:underline"
            href="/parlament/de_bundestag"
          >
            Bundestag
          </Link>
          .
        </p>
      </div>

      <section className="space-y-3">
        <h2 className="font-display text-2xl text-ink">Karte</h2>
        <p className="text-sm text-ink/55">
          Farbe = stärkste Partei (ohne Sonstige). Grau = noch keine Umfragedaten.
        </p>
        <GermanyMap />
      </section>

      <section className="space-y-3">
        <h2 className="font-display text-2xl text-ink">Alle Landtage</h2>
        <LaenderIndex />
      </section>
    </div>
  );
}
