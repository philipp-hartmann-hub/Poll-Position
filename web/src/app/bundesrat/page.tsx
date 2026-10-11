import { BundesratOverview } from "@/components/BundesratOverview";
import { BundesratSandbox } from "@/components/BundesratSandbox";
import { DataFreshnessBanner } from "@/components/DataFreshnessBanner";

export default function BundesratPage() {
  return (
    <div className="space-y-8">
      <div className="space-y-4">
        <p className="text-sm uppercase tracking-wide text-ink/45">Bundesrat</p>
        <h1 className="font-display text-3xl tracking-tight text-ink md:text-4xl">
          Bundesrat
        </h1>
        <p className="max-w-2xl text-ink/60">
          Wie stehen amtierende Bundesregierung und mögliche Bundestags-Koalitionen
          im Bundesrat da — und wie setzen sich die 69 Stimmen heute zusammen?
        </p>
        <DataFreshnessBanner />
      </div>

      <section className="space-y-3">
        <h2 className="font-display text-2xl text-ink">Aktuelle Lage</h2>
        <p className="max-w-2xl text-sm text-ink/55">
          Snapshot nach aktuellen Landesregierungen und Bundestags-Umfragen —
          ohne Simulation.
        </p>
        <BundesratOverview />
      </section>

      <section className="space-y-3">
        <h2 className="font-display text-2xl text-ink">Selbst ausprobieren</h2>
        <p className="max-w-2xl text-sm text-ink/55">
          Partei-Stimmverhalten (Ja / Enthaltung / Nein) steuert die einheitliche
          Landesstimme. Landes-Overrides und Umfrage-Presets überschreiben die
          Automatik.
        </p>
        <BundesratSandbox />
      </section>
    </div>
  );
}
