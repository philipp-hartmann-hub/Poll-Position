"use client";

import { useEffect, useMemo, useState } from "react";
import type { Coalition, ExclusionRule } from "@/lib/api";
import { fetchCoalitionRules, fetchCoalitions } from "@/lib/api";
import { Hemicycle } from "@/components/charts";
import { labelPartyId } from "@/lib/colors";

function ruleLabel(rule: ExclusionRule): string {
  if (rule.note?.trim()) return rule.note;
  const excl = rule.excludes.map(labelPartyId).join(", ");
  return `${labelPartyId(rule.party)} schließt ${excl} aus`;
}

export function CoalitionPanel({
  parliamentId,
  initial,
  seatsByName,
}: {
  parliamentId: string;
  initial: {
    majority_threshold: number;
    excluded_by_rules: number;
    coalitions: Coalition[];
  };
  seatsByName: Record<string, number>;
}) {
  const [applyExclusions, setApplyExclusions] = useState(true);
  const [rules, setRules] = useState<ExclusionRule[]>([]);
  const [enabled, setEnabled] = useState<Record<string, boolean>>({});
  const [data, setData] = useState(initial);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [highlightParties, setHighlightParties] = useState<string[] | null>(
    null,
  );

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetchCoalitionRules(parliamentId);
        if (cancelled) return;
        setRules(res.rules);
        setEnabled(Object.fromEntries(res.rules.map((r) => [r.id, true])));
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Regeln laden fehlgeschlagen");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [parliamentId]);

  const disabledRuleIds = useMemo(
    () => rules.filter((r) => enabled[r.id] === false).map((r) => r.id),
    [rules, enabled],
  );

  const activeCount = useMemo(
    () => Object.values(enabled).filter(Boolean).length,
    [enabled],
  );

  async function refresh(nextApply: boolean, nextDisabled: string[]) {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchCoalitions(parliamentId, {
        apply_exclusions: nextApply,
        disabled_rule_ids: nextApply ? nextDisabled : [],
      });
      setData(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Fehler");
    } finally {
      setLoading(false);
    }
  }

  function toggleRule(id: string, checked: boolean) {
    const nextEnabled = { ...enabled, [id]: checked };
    setEnabled(nextEnabled);
    const nextDisabled = rules
      .filter((r) => nextEnabled[r.id] === false)
      .map((r) => r.id);
    void refresh(applyExclusions, nextDisabled);
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
              void refresh(v, disabledRuleIds);
            }}
          />
          Ausschlussregeln anwenden
        </label>
      </div>
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {rules.map((r) => (
          <label
            key={r.id}
            className="flex items-start gap-2 rounded-lg border border-ink/10 bg-white/50 px-3 py-2 text-sm"
          >
            <input
              type="checkbox"
              className="mt-0.5"
              checked={enabled[r.id] !== false}
              disabled={!applyExclusions}
              onChange={(e) => toggleRule(r.id, e.target.checked)}
            />
            <span>{ruleLabel(r)}</span>
          </label>
        ))}
      </div>
      <p className="text-xs text-ink/50">
        Mehrheit ab {data.majority_threshold} · {data.excluded_by_rules} Kombinationen
        ausgeschlossen · {activeCount}/{rules.length} Regeln aktiv
        {loading ? " · lädt…" : ""}
      </p>
      {error && <p className="text-sm text-accent">{error}</p>}
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-xl border border-ink/10 bg-white/50 p-4">
          <Hemicycle
            seats={seatsByName}
            highlightParties={highlightParties ?? undefined}
          />
        </div>
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
              {data.coalitions
                .filter(
                  (c) =>
                    !c.parties.some((p) =>
                      /sonstige$|:others$|:other$/i.test(p),
                    ),
                )
                .slice(0, 20)
                .map((c, i) => (
                  <tr
                    key={i}
                    className="border-t border-ink/5 transition hover:bg-mist/40"
                    onMouseEnter={() =>
                      setHighlightParties(c.parties.map(labelPartyId))
                    }
                    onMouseLeave={() => setHighlightParties(null)}
                  >
                    <td className="px-3 py-2">
                      {c.parties.map(labelPartyId).join(" + ")}
                    </td>
                    <td className="px-3 py-2 tabular-nums">{c.seats}</td>
                    <td className="px-3 py-2 tabular-nums">
                      {c.compatibility_span?.toFixed(1) ?? "—"}
                    </td>
                    <td className="px-3 py-2">
                      {c.is_minimal_winning ? "ja" : "nein"}
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
