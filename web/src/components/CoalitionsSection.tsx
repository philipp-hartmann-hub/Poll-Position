"use client";

import { useEffect, useState } from "react";
import {
  fetchCoalitions,
  fetchSeats,
  fetchUncertainty,
  type CoalitionsResponse,
  type SeatsResponse,
  type UncertaintyResponse,
} from "@/lib/api";
import { CoalitionPanel } from "@/components/CoalitionPanel";
import { labelPartyId } from "@/lib/colors";

export function CoalitionsSection({ parliamentId }: { parliamentId: string }) {
  const [coalitions, setCoalitions] = useState<CoalitionsResponse | null>(null);
  const [seats, setSeats] = useState<SeatsResponse | null>(null);
  const [uncertainty, setUncertainty] = useState<UncertaintyResponse | null>(
    null,
  );
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    (async () => {
      try {
        const [c, s, u] = await Promise.all([
          fetchCoalitions(parliamentId),
          fetchSeats(parliamentId),
          fetchUncertainty(parliamentId, 200).catch(() => null),
        ]);
        if (cancelled) return;
        setCoalitions(c);
        setSeats(s);
        setUncertainty(u);
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
  if (!coalitions || !seats) return null;

  return (
    <div className="space-y-10">
      <CoalitionPanel
        parliamentId={parliamentId}
        seatsByName={seats.seats_by_name}
        initial={{
          majority_threshold: coalitions.majority_threshold,
          excluded_by_rules: coalitions.excluded_by_rules,
          coalitions: coalitions.coalitions,
        }}
      />

      {uncertainty && uncertainty.coalition_probabilities.length > 0 && (
        <section>
          <h2 className="mb-3 font-display text-2xl text-ink">
            Unsicherheit (Monte-Carlo)
          </h2>
          <p className="mb-3 text-sm text-ink/55">
            {uncertainty.n_simulations} Simulationen ·
            Mehrheitswahrscheinlichkeiten
          </p>
          <ul className="space-y-2 text-sm">
            {uncertainty.coalition_probabilities.slice(0, 8).map((c, i) => (
              <li
                key={i}
                className="flex items-center justify-between rounded-lg border border-ink/10 bg-white/40 px-3 py-2"
              >
                <span>{c.parties.map(labelPartyId).join(" + ")}</span>
                <span className="tabular-nums font-medium">
                  {(c.majority_probability * 100).toFixed(0)} %
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
