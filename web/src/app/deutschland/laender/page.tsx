import Link from "next/link";
import { LaenderIndex } from "@/components/LaenderIndex";

export default function LaenderPage() {
  return (
    <div className="space-y-6">
      <div className="space-y-4">
        <p className="text-sm uppercase tracking-wide text-ink/45">Deutschland</p>
        <h1 className="font-display text-3xl tracking-tight text-ink md:text-4xl">
          Land wählen
        </h1>
        <p className="max-w-2xl text-ink/60">
          Landtag auswählen — danach Sitze, Koalitionen und Szenarien im
          Tab-System. Über den Parlament-Switcher kannst du jederzeit wechseln.
        </p>
        <p className="text-sm text-ink/55">
          Oder direkt zum{" "}
          <Link className="text-sea underline-offset-2 hover:underline" href="/parlament/de_bundestag">
            Bundestag
          </Link>
          .
        </p>
      </div>
      <LaenderIndex />
    </div>
  );
}
