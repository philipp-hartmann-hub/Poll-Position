import { ScenarioWorkbench } from "@/components/ScenarioWorkbench";

export default function SzenarioPage() {
  return (
    <div className="space-y-4">
      <p className="text-sm uppercase tracking-wide text-ink/45">Was wäre wenn</p>
      <h1 className="font-display text-3xl tracking-tight text-ink md:text-4xl">
        Szenario
      </h1>
      <p className="max-w-2xl text-ink/60">
        Anteile per Slider anpassen — Sitze und Koalitionen werden live über{" "}
        <code className="text-xs">POST /api/scenario</code> neu berechnet.
      </p>
      <ScenarioWorkbench />
    </div>
  );
}
