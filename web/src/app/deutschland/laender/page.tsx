import { LaenderPicker } from "@/components/LaenderPicker";

export default function LaenderPage() {
  return (
    <div className="space-y-4">
      <p className="text-sm uppercase tracking-wide text-ink/45">Deutschland</p>
      <h1 className="font-display text-3xl tracking-tight text-ink md:text-4xl">
        Länder
      </h1>
      <p className="max-w-2xl text-ink/60">
        Landtag wählen — Mittelwerte, Sitzprojektion und Koalitionen wie auf
        Bundesebene.
      </p>
      <LaenderPicker />
    </div>
  );
}
