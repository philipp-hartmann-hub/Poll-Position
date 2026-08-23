"use client";

import { useMemo, useState } from "react";
import type { Coalition } from "@/lib/api";
import { fetchCoalitions } from "@/lib/api";
import { labelPartyId } from "@/lib/colors";

const DEFAULT_RULES: { id: string; label: string; party: string; excludes: string }[] = [
  { id: "union-afd", label: "Union schließt AfD aus", party: "de:cdu_csu", excludes: "de:afd" },
  { id: "spd-afd", label: "SPD schließt AfD aus", party: "de:spd", excludes: "de:afd" },
  { id: "gruene-afd", label: "Grüne schließen AfD aus", party: "de:gruene", excludes: "de:afd" },
  { id: "linke-afd", label: "Linke schließt AfD aus", party: "de:linke", excludes: "de:afd" },
  { id: "afd-linke", label: "AfD schließt Linke aus", party: "de:afd", excludes: "de:linke" },
];

export function CoalitionPanel({
  parliamentId,
  initial,
}: {
  parliamentId: string;
  initial: {
    majority_threshold: number;
    excluded_by_rules: number;
    coalitions: Coalition[];
  };
}) {
  const [applyExclusions, setApplyExclusions] = useState(true);
  const [enabled, setEnabled] = useState<Record<string, boolean>>(
    Object.fromEntries(DEFAULT_RULES.map((r) => [r.id, true])),
  );
  const [data, setData] = useState(initial);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const activeCount = useMemo(
    () => Object.values(enabled).filter(Boolean).length,
    [enabled],
  );

  async function refresh(nextApply: boolean) {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchCoalitions(parliamentId, {
        apply_exclusions: nextApply,
      });
      setData(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Fehler");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="font-display text-2xl text-ink">Koalitionsrechner</h2>
        <label className="flex items-center gap-2 text-sm text-ink/80">
          <input
            type="checkbox"
            checked={applyExclusions}
            onChange={(e) => {
              const v = e.target.checked;
              setApplyExclusions(v);
              void refresh(v);
            }}
          />
          Ausschlussregeln anwenden
        </label>
      </div>
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {DEFAULT_RULES.map((r) => (
          <label
            key={r.id}
            className="flex items-start gap-2 rounded-lg border border-ink/10 bg-white/50 px-3 py-2 text-sm"
          >
            <input
              type="checkbox"
              className="mt-0.5"
              checked={enabled[r.id]}
              disabled={!applyExclusions}
              onChange={(e) =>
                setEnabled((prev) => ({ ...prev, [r.id]: e.target.checked }))
              }
            />
            <span>{r.label}</span>
          </label>
        ))}
      </div>
      <p className="text-xs text-ink/50">
        Mehrheit ab {data.majority_threshold} · {data.excluded_by_rules} Kombinationen
        ausgeschlossen · {activeCount} UI-Regeln markiert
        {loading ? " · lädt…" : ""}
      </p>
      {error && <p className="text-sm text-accent">{error}</p>}
      <div className="overflow-x-auto rounded-lg border border-ink/10">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-ink/5 text-ink/60">
            <tr>
              <th className="px-3 py-2 font-medium">Koalition</th>
              <th className="px-3 py-2 font-medium">Sitze</th>
              <th className="px-3 py-2 font-medium">Span</th>
              <th className="px-3 py-2 font-medium">Minimal</th>
            </tr>
          </thead>
          <tbody>
            {data.coalitions.slice(0, 20).map((c, i) => (
              <tr key={i} className="border-t border-ink/5">
                <td className="px-3 py-2">
                  {c.parties.map(labelPartyId).join(" + ")}
                </td>
                <td className="px-3 py-2 tabular-nums">{c.seats}</td>
                <td className="px-3 py-2 tabular-nums">
                  {c.compatibility_span?.toFixed(1) ?? "—"}
                </td>
                <td className="px-3 py-2">{c.is_minimal_winning ? "ja" : "nein"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
