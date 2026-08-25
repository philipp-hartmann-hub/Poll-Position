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
import {
  CoalitionPanel,
  type ExclusionUiState,
} from "@/components/CoalitionPanel";
import { labelPartyId } from "@/lib/colors";

export function CoalitionsSection({ parliamentId }: { parliamentId: string }) {
  const [coalitions, setCoalitions] = useState<CoalitionsResponse | null>(null);
  const [seats, setSeats] = useState<SeatsResponse | null>(null);
  const [uncertainty, setUncertainty] = useState<UncertaintyResponse | null>(
    null,
  );
  const [exclusionState, setExclusionState] = useState<ExclusionUiState>({
    applyExclusions: true,
    disabledRuleIds: [],
  });
  const [uncertaintyBusy, setUncertaintyBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setExclusionState({ applyExclusions: true, disabledRuleIds: [] });
    (async () => {
      try {
        const [c, s] = await Promise.all([
          fetchCoalitions(parliamentId),
          fetchSeats(parliamentId),
        ]);
        if (cancelled) return;
        setCoalitions(c);
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

  const disabledKey = exclusionState.disabledRuleIds.join("\0");

  useEffect(() => {
    let cancelled = false;
    const t = setTimeout(() => {
      setUncertaintyBusy(true);
      void fetchUncertainty(parliamentId, 200, {
        applyExclusions: exclusionState.applyExclusions,
        disabledRuleIds: exclusionState.disabledRuleIds,
      })
        .then((u) => {
          if (!cancelled) setUncertainty(u);
        })
        .catch(() => {
          if (!cancelled) setUncertainty(null);
        })
        .finally(() => {
          if (!cancelled) setUncertaintyBusy(false);
        });
    }, 200);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [parliamentId, exclusionState.applyExclusions, disabledKey]);

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
        key={parliamentId}
        parliamentId={parliamentId}
        seatsByName={seats.seats_by_name}
        initial={{
          majority_threshold: coalitions.majority_threshold,
          excluded_by_rules: coalitions.excluded_by_rules,
          coalitions: coalitions.coalitions,
        }}
        onExclusionStateChange={setExclusionState}
      />

      {(uncertainty && uncertainty.coalition_probabilities.length > 0) ||
      uncertaintyBusy ? (
        <section>
          <h2 className="mb-3 font-display text-2xl text-ink">
            Unsicherheit (Monte-Carlo)
          </h2>
          <p className="mb-3 text-sm text-ink/55">
            {uncertainty
              ? `${uncertainty.n_simulations} Simulationen · Mehrheitswahrscheinlichkeiten`
              : "Simulation lädt…"}
            {uncertaintyBusy ? " · aktualisiert…" : ""}
            {!exclusionState.applyExclusions
              ? " · ohne Ausschlussregeln"
              : exclusionState.disabledRuleIds.length > 0
                ? ` · ${exclusionState.disabledRuleIds.length} Regeln aus`
                : ""}
          </p>
          {uncertainty && uncertainty.coalition_probabilities.length > 0 ? (
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
          ) : (
            <p className="text-sm text-ink/50">Keine Mehrheitskoalitionen in der Simulation.</p>
          )}
        </section>
      ) : null}
    </div>
  );
}
