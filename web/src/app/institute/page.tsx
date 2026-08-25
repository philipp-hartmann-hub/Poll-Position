import { InstituteLeaderboard } from "@/components/InstituteLeaderboard";
import { InstituteView } from "@/components/InstituteView";

export default function InstitutePage() {
  return (
    <div className="space-y-10">
      <div className="space-y-4">
        <p className="text-sm uppercase tracking-wide text-ink/45">Vergleich</p>
        <h1 className="font-display text-3xl tracking-tight text-ink md:text-4xl">
          Institute
        </h1>
        <p className="max-w-2xl text-ink/60">
          Wer lag bei vergangenen Wahlen am nächsten am Ergebnis — und wie
          weichen Institute voneinander ab (House Effects).
        </p>
      </div>
      <InstituteLeaderboard />
      <section className="space-y-3">
        <h2 className="font-display text-xl text-ink">
          House Effects nach Parlament
        </h2>
        <p className="text-sm text-ink/55">
          Detailansicht: Abweichung vom Peer-Schnitt im Zeitfenster, plus
          Backtest nur für das gewählte Parlament.
        </p>
        <InstituteView />
      </section>
    </div>
  );
}
