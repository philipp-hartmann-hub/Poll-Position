import { InstituteView } from "@/components/InstituteView";

export default function InstitutePage() {
  return (
    <div className="space-y-4">
      <p className="text-sm uppercase tracking-wide text-ink/45">Vergleich</p>
      <h1 className="font-display text-3xl tracking-tight text-ink md:text-4xl">
        Institute
      </h1>
      <p className="max-w-2xl text-ink/60">
        House Effects gegenüber Peer-Instituten und Backtesting gegen
        Wahlergebnisse.
      </p>
      <InstituteView />
    </div>
  );
}
