import Link from "next/link";
import { InstituteLeaderboard } from "@/components/InstituteLeaderboard";

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
        <p className="max-w-2xl text-sm text-ink/55">
          Detailansicht je Parlament unter{" "}
          <Link
            href="/parlament/de_bundestag/institute"
            className="text-sea underline-offset-2 hover:underline"
          >
            Parlament → Institute
          </Link>
          .
        </p>
      </div>
      <InstituteLeaderboard />
    </div>
  );
}
