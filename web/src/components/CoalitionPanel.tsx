"use client";

import { useEffect, useMemo, useState } from "react";
import type { Coalition, ExclusionRule, FetchCoalitionsFn } from "@/lib/api";
import { fetchCoalitionRules, fetchCoalitions } from "@/lib/api";
import { Hemicycle } from "@/components/charts";
import { InfoTooltip } from "@/components/InfoTooltip";
import { labelPartyId } from "@/lib/colors";
import { TIP_POSSIBLE_COALITIONS } from "@/lib/tooltipCopy";

export type ExclusionUiState = {
  applyExclusions: boolean;
  disabledRuleIds: string[];
};

function pairParties(rule: ExclusionRule): [string, string] {
  if (rule.parties && rule.parties.length >= 2) {
    return [rule.parties[0], rule.parties[1]];
  }
  return [rule.party, rule.excludes[0] ?? rule.party];
}

function pairLabel(rule: ExclusionRule): string {
  const [a, b] = pairParties(rule);
  return `${labelPartyId(a)} + ${labelPartyId(b)}`;
}

export function CoalitionPanel({
  parliamentId,
  initial,
  seatsByName,
  initialExclusion,
  onExclusionStateChange,
  fetchCoalitionsFn = fetchCoalitions,
  title = "Koalitionsrechner",
  tipText = TIP_POSSIBLE_COALITIONS,
}: {
  parliamentId: string;
  initial: {
    majority_threshold: number;
    excluded_by_rules: number;
    coalitions: Coalition[];
  };
  seatsByName: Record<string, number>;
  /** Zustand aus URL / Parent — steuert Checkboxen nach dem Laden der Regeln. */
  initialExclusion?: ExclusionUiState;
  onExclusionStateChange?: (state: ExclusionUiState) => void;
  /** Default: aktuelle Umfrage-Sitze; Wahlergebnis: fetchLastElectionCoalitions. */
  fetchCoalitionsFn?: FetchCoalitionsFn;
  title?: string;
  tipText?: string;
}) {
  const [applyExclusions, setApplyExclusions] = useState(
    initialExclusion?.applyExclusions ?? true,
  );
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
        const disabled = new Set(initialExclusion?.disabledRuleIds ?? []);
        setEnabled(
          Object.fromEntries(res.rules.map((r) => [r.id, !disabled.has(r.id)])),
        );
        setApplyExclusions(initialExclusion?.applyExclusions ?? true);
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Regeln laden fehlgeschlagen");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
    // Nur bei Parlamentwechsel neu laden; initialExclusion kommt mit key={parliamentId} + Remount.
    // eslint-disable-next-line react-hooks/exhaustive-deps -- intentional: URL-State nur beim Mount / Parlamentwechsel
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
    onExclusionStateChange?.({
      applyExclusions: nextApply,
      disabledRuleIds: nextDisabled,
    });
    setLoading(true);
    setError(null);
    try {
      const res = await fetchCoalitionsFn(parliamentId, {
        apply_exclusions: nextApply,
        disabled_rule_ids: nextApply ? nextDisabled : [],
      });
      setData({
        majority_threshold: res.majority_threshold,
        excluded_by_rules: res.excluded_by_rules,
        coalitions: res.coalitions,
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Fehler");
    } finally {
      setLoading(false);
    }
  }

  function togglePair(pairId: string, checked: boolean) {
    const nextEnabled = { ...enabled, [pairId]: checked };
    setEnabled(nextEnabled);
    const nextDisabled = rules
      .filter((r) => nextEnabled[r.id] === false)
      .map((r) => r.id);
    void refresh(applyExclusions, nextDisabled);
  }

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="font-display text-2xl text-ink">
          {title}
          <InfoTooltip text={tipText} />
        </h2>
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
        {rules.length === 0 ? (
          <p className="text-sm text-ink/50 sm:col-span-2 lg:col-span-3">
            Keine Ausschlussregeln für dieses Parlament konfiguriert.
          </p>
        ) : (
          rules.map((r) => (
            <label
              key={r.id}
              className="flex items-start gap-2 rounded-lg border border-ink/10 bg-mist/50 px-3 py-2 text-sm"
            >
              <input
                type="checkbox"
                className="mt-0.5"
                checked={enabled[r.id] !== false}
                disabled={!applyExclusions}
                onChange={(e) => togglePair(r.id, e.target.checked)}
              />
              <span>{pairLabel(r)}</span>
            </label>
          ))
        )}
      </div>
      <p className="text-xs text-ink/50">
        Mehrheit ab {data.majority_threshold} · {data.excluded_by_rules} Kombinationen
        ausgeschlossen · {activeCount}/{rules.length} Paare aktiv
        {loading ? " · lädt…" : ""}
      </p>
      {error && <p className="text-sm text-accent">{error}</p>}
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-xl border border-ink/10 bg-mist/50 p-4">
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
                    <td className="px-3 py-2 font-display tabular-nums">
                      {c.seats}
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
