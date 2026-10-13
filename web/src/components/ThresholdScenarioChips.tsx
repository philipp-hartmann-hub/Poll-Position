"use client";

import type { ThresholdWatchParty } from "@/lib/api";

function formatShare(value: number): string {
  return value.toLocaleString("de-DE", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  });
}

export type ThresholdScenarioCandidate = ThresholdWatchParty & {
  /** Zielanteil für die Simulation (= Hürde). */
  targetShare: number;
};

/** Parteien knapp unter der Sperrklausel als klickbare Szenario-Chips. */
export function ThresholdScenarioChips({
  candidates,
  activePartyId,
  busy,
  onSelect,
}: {
  candidates: ThresholdScenarioCandidate[];
  activePartyId?: string | null;
  busy?: boolean;
  onSelect: (party: ThresholdScenarioCandidate) => void;
}) {
  if (candidates.length === 0) return null;

  return (
    <div className="space-y-2">
      <p className="text-xs uppercase tracking-wide text-ink/45">
        Unter der Hürde — Szenario
      </p>
      <div className="flex flex-wrap gap-2">
        {candidates.map((p) => {
          const active = activePartyId === p.party_id;
          return (
            <button
              key={p.party_id}
              type="button"
              disabled={busy}
              onClick={() => onSelect(p)}
              className={
                active
                  ? "rounded-md border border-sea/40 bg-sea/10 px-3 py-1.5 text-sm font-medium text-ink"
                  : "rounded-md border border-ink/15 bg-mist px-3 py-1.5 text-sm text-ink transition hover:border-sea/40 hover:bg-mist/40 disabled:opacity-50"
              }
            >
              {p.party_name} {formatShare(p.average_share)}&nbsp;% →{" "}
              {formatShare(p.targetShare)}&nbsp;% simulieren
            </button>
          );
        })}
      </div>
      <p className="text-xs text-ink/50">
        Deterministischer Punktwert (Sitze &amp; Koalitionen) für genau diese
        hypothetische Verteilung — keine Monte-Carlo-Wahrscheinlichkeit.
      </p>
    </div>
  );
}
