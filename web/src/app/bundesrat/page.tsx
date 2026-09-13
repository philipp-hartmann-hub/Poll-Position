import { BundesratSandbox } from "@/components/BundesratSandbox";

export default function BundesratPage() {
  return (
    <div className="space-y-4">
      <p className="text-sm uppercase tracking-wide text-ink/45">Sandbox</p>
      <h1 className="font-display text-3xl tracking-tight text-ink md:text-4xl">
        Bundesrat
      </h1>
      <p className="max-w-2xl text-ink/60">
        Bundesweites Partei-Stimmverhalten (Ja / Enthaltung / Nein) steuert die
        einheitliche Landesstimme — Ausgangspunkt ist Enthaltung. Landes-
        Overrides und Umfrage-Presets überschreiben die Automatik.
      </p>
      <BundesratSandbox />
    </div>
  );
}
