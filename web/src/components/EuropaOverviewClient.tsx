"use client";

import { useEffect, useState } from "react";
import { EuropeMap } from "@/components/EuropeMap";
import { fetchEuropeOverview, type EuropeOverviewResponse } from "@/lib/api";

export function EuropaOverviewClient() {
  const [data, setData] = useState<EuropeOverviewResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void fetchEuropeOverview()
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : "Fehler"));
  }, []);

  return (
    <div className="space-y-6">
      <p className="text-sm uppercase tracking-wide text-ink/45">Europa</p>
      <h1 className="font-display text-3xl tracking-tight text-ink md:text-4xl">
        Übersicht
      </h1>
      <p className="max-w-2xl text-ink/60">
        Einfärbung nach stärkster europäischer Parteienfamilie je Land.
        Klick öffnet die Länderseite (Sitze wo das Wahlrecht eine nationale
        Näherung zulässt; Frankreich nur Umfragen).
      </p>
      {error && (
        <p className="rounded-lg border border-accent/30 bg-accent/5 px-4 py-3 text-sm text-accent">
          {error}
        </p>
      )}
      {!data && !error && <p className="text-sm text-ink/50">Lade Karte…</p>}
      {data && <EuropeMap data={data} />}
    </div>
  );
}
