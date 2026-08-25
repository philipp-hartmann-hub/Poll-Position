"use client";

import { useEffect, useState } from "react";
import { fetchSeats, type SeatsResponse } from "@/lib/api";
import { Hemicycle, SeatsBarChart } from "@/components/charts";

export function SeatsSection({ parliamentId }: { parliamentId: string }) {
  const [seats, setSeats] = useState<SeatsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    (async () => {
      try {
        const s = await fetchSeats(parliamentId);
        if (cancelled) return;
        setSeats(s);
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Laden fehlgeschlagen");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [parliamentId]);

  if (loading) {
    return <p className="text-sm text-ink/50">Lade Analyse…</p>;
  }
  if (error) {
    return (
      <p className="rounded-lg border border-accent/30 bg-accent/5 px-4 py-3 text-sm text-accent">
        {error}
        <span className="mt-1 block text-ink/50">
          API erreichbar? Lokal:{" "}
          <code className="text-xs">uv run uvicorn backend.main:app</code>
        </span>
      </p>
    );
  }
  if (!seats) return null;

  return (
    <section>
      <h2 className="mb-3 font-display text-2xl text-ink">Sitzprojektion</h2>
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-xl border border-ink/10 bg-white/50 p-4">
          <Hemicycle seats={seats.seats_by_name} />
        </div>
        <div className="rounded-xl border border-ink/10 bg-white/50 p-4">
          <SeatsBarChart seats={seats.seats_by_name} />
          <p className="mt-2 text-sm text-ink/50">
            Sitze gesamt: {seats.total_seats}
          </p>
        </div>
      </div>
    </section>
  );
}
