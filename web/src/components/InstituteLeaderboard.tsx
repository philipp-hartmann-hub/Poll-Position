"use client";

import { useEffect, useState } from "react";
import {
  fetchInstituteLeaderboard,
  type InstituteLeaderboardResponse,
} from "@/lib/api";

export function InstituteLeaderboard() {
  const [data, setData] = useState<InstituteLeaderboardResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    void fetchInstituteLeaderboard()
      .then((d) => {
        if (!cancelled) setData(d);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "Fehler");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section className="space-y-4 rounded-2xl border border-ink/10 bg-white/60 p-5 shadow-sm">
      <h2 className="font-display text-2xl text-ink md:text-3xl">
        Wer lag zuletzt am genauesten?
      </h2>
      <p className="max-w-2xl text-sm text-ink/55">
        Rangliste über alle Parlamente mit Backtest gegen Wahlergebnisse.
        Score gewichtet nach Zahl der Vergleiche — nicht nur eine Liste
        einzeln nebeneinander.
      </p>
      {loading && <p className="text-sm text-ink/50">Lade Rangliste…</p>}
      {error && <p className="text-sm text-accent">{error}</p>}
      {data && !loading && data.institutes.length === 0 && (
        <p className="text-sm text-ink/50">
          Noch keine Backtest-Treffer (fehlende Umfragen kurz vor Wahlen).
        </p>
      )}
      {data && data.institutes.length > 0 && (
        <ol className="space-y-3">
          {data.institutes.map((row) => (
            <li
              key={row.institute_id}
              className="flex flex-col gap-2 rounded-xl border border-ink/10 bg-paper/80 px-4 py-3 sm:flex-row sm:items-center sm:justify-between"
            >
              <div className="flex items-baseline gap-3">
                <span className="font-display text-3xl tabular-nums text-accent">
                  {row.rank}
                </span>
                <div>
                  <p className="font-medium text-ink">
                    {row.institute_name ?? row.institute_id}
                  </p>
                  <p className="text-xs text-ink/50">
                    {row.n_comparisons} Vergleiche · MAE {row.mae.toFixed(2)} pp
                    {row.by_parliament.length > 1
                      ? ` · ${row.by_parliament.length} Parlamente`
                      : ""}
                  </p>
                </div>
              </div>
              <p className="tabular-nums text-lg font-medium text-ink">
                {(row.score * 100).toFixed(1)}
                <span className="ml-1 text-xs font-normal text-ink/45">
                  Score
                </span>
              </p>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
