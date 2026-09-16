"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  fetchAverages,
  fetchCoalitionRules,
  fetchLastElection,
  postElectionNight,
  type ElectionNightResponse,
  type ExclusionRule,
} from "@/lib/api";
import { Hemicycle } from "@/components/charts";
import { InfoTooltip } from "@/components/InfoTooltip";
import { displayPartyName, labelPartyId, partyColor } from "@/lib/colors";
import { leftRightPosition } from "@/lib/partyPositions";
import { PARTY_SWATCH_CLASS } from "@/lib/theme";
import {
  TIP_COALITION_UNCERTAINTY,
  TIP_ELECTION_NIGHT,
  TIP_PARTY_FORECAST,
  TIP_PARTY_INDISPENSABLE,
  TIP_POSSIBLE_COALITIONS,
} from "@/lib/tooltipCopy";
import { isAbortError } from "@/lib/parliamentCache";

const STORAGE_PREFIX = "poll-position:election-night-v1:";

type StoredState = {
  shares: Record<string, string>;
  countProgress: number;
  applyExclusions: boolean;
  disabledRuleIds: string[];
};

function storageKey(parliamentId: string): string {
  return `${STORAGE_PREFIX}${parliamentId}`;
}

function readStored(parliamentId: string): StoredState | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = sessionStorage.getItem(storageKey(parliamentId));
    if (!raw) return null;
    const parsed = JSON.parse(raw) as StoredState;
    if (!parsed || typeof parsed !== "object") return null;
    return {
      shares: parsed.shares ?? {},
      countProgress:
        typeof parsed.countProgress === "number" ? parsed.countProgress : 20,
      applyExclusions: parsed.applyExclusions !== false,
      disabledRuleIds: Array.isArray(parsed.disabledRuleIds)
        ? parsed.disabledRuleIds
        : [],
    };
  } catch {
    return null;
  }
}

function writeStored(parliamentId: string, state: StoredState): void {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.setItem(storageKey(parliamentId), JSON.stringify(state));
  } catch {
    /* quota / private mode */
  }
}

type PartyRow = {
  partyId: string;
  partyName: string;
  pollShare: number | null;
  electionShare: number | null;
};

function pairParties(rule: ExclusionRule): [string, string] {
  if (rule.parties && rule.parties.length >= 2) {
    return [rule.parties[0], rule.parties[1]];
  }
  return [rule.party, rule.excludes[0] ?? rule.party];
}

function formatDeltaPp(delta: number | null): string {
  if (delta == null || !Number.isFinite(delta)) return "—";
  const rounded = Math.round(delta * 10) / 10;
  const sign = rounded > 0 ? "+" : "";
  return `${sign}${rounded.toFixed(1)}`;
}

function deltaClass(delta: number | null): string {
  if (delta == null || !Number.isFinite(delta)) return "text-ink/40";
  if (Math.abs(delta) < 0.05) return "text-ink/50";
  return delta > 0 ? "text-sea" : "text-accent";
}

function parseShare(raw: string | undefined): number | null {
  if (raw == null) return null;
  const t = raw.trim().replace(",", ".");
  if (t === "") return null;
  const n = Number(t);
  return Number.isFinite(n) ? n : null;
}

export function ElectionNightSection({
  parliamentId,
}: {
  parliamentId: string;
}) {
  const [parties, setParties] = useState<PartyRow[]>([]);
  const [electionDate, setElectionDate] = useState<string | null>(null);
  const [shares, setShares] = useState<Record<string, string>>({});
  const [countProgress, setCountProgress] = useState(20);
  const [rules, setRules] = useState<ExclusionRule[]>([]);
  const [applyExclusions, setApplyExclusions] = useState(true);
  const [enabled, setEnabled] = useState<Record<string, boolean>>({});
  const [result, setResult] = useState<ElectionNightResponse | null>(null);
  const [loadingParties, setLoadingParties] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    let cancelled = false;
    const ac = new AbortController();
    setLoadingParties(true);
    setResult(null);
    setError(null);
    const stored = readStored(parliamentId);
    (async () => {
      try {
        const [avg, rulesRes, election] = await Promise.all([
          fetchAverages(parliamentId, 365, { signal: ac.signal }),
          fetchCoalitionRules(parliamentId, { signal: ac.signal }),
          fetchLastElection(parliamentId, { signal: ac.signal }).catch(() => null),
        ]);
        if (cancelled || ac.signal.aborted) return;
        const electionShares = election?.vote_share_by_name ?? {};
        setElectionDate(election?.election_date ?? null);
        const rows = avg.parties
          .filter(
            (p) =>
              p.party_name !== "Sonstige" &&
              !/sonstige$|:others$|:other$/i.test(p.party_id),
          )
          .map((p) => ({
            partyId: p.party_id,
            partyName: p.party_name,
            pollShare: p.average_share,
            electionShare:
              typeof electionShares[p.party_name] === "number"
                ? electionShares[p.party_name]
                : null,
          }))
          .sort((a, b) => {
            const lr =
              leftRightPosition(a.partyName) - leftRightPosition(b.partyName);
            if (lr !== 0) return lr;
            return a.partyName.localeCompare(b.partyName, "de");
          });
        setParties(rows);
        setRules(rulesRes.rules);
        const nextShares: Record<string, string> = {};
        for (const row of rows) {
          const fromStore = stored?.shares[row.partyId];
          if (fromStore != null && fromStore !== "") {
            nextShares[row.partyId] = fromStore;
          } else {
            const avgParty = avg.parties.find((p) => p.party_id === row.partyId);
            nextShares[row.partyId] =
              avgParty != null ? avgParty.average_share.toFixed(1) : "";
          }
        }
        setShares(nextShares);
        setCountProgress(stored?.countProgress ?? 20);
        setApplyExclusions(stored?.applyExclusions ?? true);
        const disabled = new Set(stored?.disabledRuleIds ?? []);
        setEnabled(
          Object.fromEntries(
            rulesRes.rules.map((r) => [r.id, !disabled.has(r.id)]),
          ),
        );
      } catch (e) {
        if (cancelled || isAbortError(e)) return;
        setError(e instanceof Error ? e.message : "Laden fehlgeschlagen");
        setParties([]);
        setElectionDate(null);
      } finally {
        if (!cancelled && !ac.signal.aborted) setLoadingParties(false);
      }
    })();
    return () => {
      cancelled = true;
      ac.abort();
    };
  }, [parliamentId]);

  const disabledRuleIds = useMemo(
    () => rules.filter((r) => enabled[r.id] === false).map((r) => r.id),
    [rules, enabled],
  );

  const partySharesNumeric = useMemo(() => {
    const out: Record<string, number> = {};
    for (const [pid, raw] of Object.entries(shares)) {
      const t = raw.trim().replace(",", ".");
      if (t === "") continue;
      const n = Number(t);
      if (!Number.isFinite(n) || n < 0) continue;
      out[pid] = n;
    }
    return out;
  }, [shares]);

  const sharesKey = useMemo(
    () => JSON.stringify(partySharesNumeric),
    [partySharesNumeric],
  );
  const disabledKey = disabledRuleIds.slice().sort().join("|");

  useEffect(() => {
    writeStored(parliamentId, {
      shares,
      countProgress,
      applyExclusions,
      disabledRuleIds,
    });
  }, [parliamentId, shares, countProgress, applyExclusions, disabledRuleIds]);

  useEffect(() => {
    const parsed = JSON.parse(sharesKey) as Record<string, number>;
    if (Object.keys(parsed).length === 0) {
      setResult(null);
      return;
    }
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      abortRef.current?.abort();
      const ac = new AbortController();
      abortRef.current = ac;
      setBusy(true);
      setError(null);
      void postElectionNight(
        parliamentId,
        {
          party_shares: parsed,
          count_progress_percent: countProgress,
          n_simulations: 200,
          apply_exclusions: applyExclusions,
          disabled_rule_ids: disabledKey ? disabledKey.split("|") : [],
        },
        { signal: ac.signal },
      )
        .then((res) => {
          if (ac.signal.aborted) return;
          setResult(res);
        })
        .catch((e) => {
          if (isAbortError(e) || ac.signal.aborted) return;
          setError(e instanceof Error ? e.message : "Berechnung fehlgeschlagen");
          setResult(null);
        })
        .finally(() => {
          if (!ac.signal.aborted) setBusy(false);
        });
    }, 450);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      abortRef.current?.abort();
    };
  }, [parliamentId, sharesKey, countProgress, applyExclusions, disabledKey]);

  if (loadingParties) {
    return <p className="text-sm text-ink/50">Lade Parteien…</p>;
  }

  const threshold = result?.party_forecast.threshold_percent ?? 5;
  const coalitions = result?.coalitions.coalitions ?? [];
  const probs = result?.uncertainty.coalition_probabilities ?? [];

  return (
    <div className="space-y-8">
      <div>
        <h2 className="font-display text-2xl text-ink">
          Wahlabend
          <InfoTooltip text={TIP_ELECTION_NIGHT} />
        </h2>
        <p className="mt-1 max-w-2xl text-sm text-ink/55">
          Manuelle Hochrechnung oder Prognose eingeben. Die Summe muss nicht
          100 % ergeben. Unsicherheit folgt einer dokumentierten Modellannahme
          nach Auszählungsstand — enger als bei normalen Umfragen, ohne
          Instituts-Streuung.
        </p>
      </div>

      <section className="space-y-3 rounded-xl border border-ink/10 bg-mist/40 p-4">
        <label className="block text-sm font-medium text-ink">
          Auszählungsstand:{" "}
          <span className="font-display tabular-nums">{countProgress} %</span>
        </label>
        <input
          type="range"
          min={0}
          max={100}
          step={1}
          value={countProgress}
          onChange={(e) => setCountProgress(Number(e.target.value))}
          className="w-full accent-sea"
        />
        <p className="text-xs text-ink/50">
          Modell-SD derzeit ca.{" "}
          {result
            ? `${result.model_sd_pp.toFixed(2)} Pp`
            : "wird berechnet…"}
          {result?.model_note ? ` · ${result.model_note}` : ""}
        </p>
      </section>

      <section className="space-y-3">
        <h3 className="text-sm font-semibold text-ink">Partei-Anteile in %</h3>
        <p className="text-xs text-ink/50">
          Δ Umfrage = Eingabe − aktueller Umfragemittelwert
          {electionDate
            ? ` · Δ Wahl = Eingabe − letzte Wahl (${electionDate})`
            : " · keine letzte Wahl hinterlegt"}
        </p>
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {parties.map((p) => {
            const entered = parseShare(shares[p.partyId]);
            const vsPoll =
              entered != null && p.pollShare != null
                ? entered - p.pollShare
                : null;
            const vsElection =
              entered != null && p.electionShare != null
                ? entered - p.electionShare
                : null;
            return (
              <div
                key={p.partyId}
                className="rounded-md border border-ink/10 bg-mist/50 px-3 py-2"
              >
                <label className="flex items-center gap-2">
                  <span
                    className={`${PARTY_SWATCH_CLASS} h-2.5 w-2.5 shrink-0`}
                    style={{ background: partyColor(p.partyName) }}
                  />
                  <span className="min-w-0 flex-1 truncate text-sm font-medium text-ink">
                    {p.partyName}
                  </span>
                  <input
                    type="number"
                    inputMode="decimal"
                    min={0}
                    max={100}
                    step={0.1}
                    value={shares[p.partyId] ?? ""}
                    onChange={(e) =>
                      setShares((prev) => ({
                        ...prev,
                        [p.partyId]: e.target.value,
                      }))
                    }
                    className="w-20 rounded border border-ink/15 bg-paper px-2 py-1 text-right text-sm tabular-nums text-ink"
                  />
                </label>
                <div className="mt-1.5 flex flex-wrap gap-x-3 gap-y-0.5 pl-4 text-xs tabular-nums">
                  <span className={deltaClass(vsPoll)}>
                    Δ Umfrage {formatDeltaPp(vsPoll)}
                    {p.pollShare != null
                      ? ` (${p.pollShare.toFixed(1)} %)`
                      : ""}
                  </span>
                  <span className={deltaClass(vsElection)}>
                    Δ Wahl {formatDeltaPp(vsElection)}
                    {p.electionShare != null
                      ? ` (${p.electionShare.toFixed(1)} %)`
                      : ""}
                  </span>
                </div>
              </div>
            );
          })}
        </div>

        <div className="overflow-x-auto rounded-xl border border-ink/10">
          <table className="w-full min-w-[28rem] border-collapse text-sm">
            <thead>
              <tr className="border-b border-ink/15 text-left text-ink/50">
                <th className="px-3 py-2 font-medium">Partei</th>
                <th className="px-3 py-2 text-right font-medium">Eingabe</th>
                <th className="px-3 py-2 text-right font-medium">Umfrage</th>
                <th className="px-3 py-2 text-right font-medium">Δ Umfrage</th>
                <th className="px-3 py-2 text-right font-medium">
                  Letzte Wahl
                  {electionDate ? (
                    <span className="block text-[10px] font-normal normal-case tracking-normal text-ink/40">
                      {electionDate}
                    </span>
                  ) : null}
                </th>
                <th className="px-3 py-2 text-right font-medium">Δ Wahl</th>
              </tr>
            </thead>
            <tbody>
              {parties.map((p) => {
                const entered = parseShare(shares[p.partyId]);
                const vsPoll =
                  entered != null && p.pollShare != null
                    ? entered - p.pollShare
                    : null;
                const vsElection =
                  entered != null && p.electionShare != null
                    ? entered - p.electionShare
                    : null;
                return (
                  <tr
                    key={`cmp-${p.partyId}`}
                    className="border-b border-ink/8 last:border-0"
                  >
                    <td className="px-3 py-2">
                      <span className="inline-flex items-center gap-2 font-medium text-ink">
                        <span
                          className={`${PARTY_SWATCH_CLASS} h-2 w-2`}
                          style={{ background: partyColor(p.partyName) }}
                        />
                        {p.partyName}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums text-ink">
                      {entered != null ? `${entered.toFixed(1)} %` : "—"}
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums text-ink/70">
                      {p.pollShare != null ? `${p.pollShare.toFixed(1)} %` : "—"}
                    </td>
                    <td
                      className={`px-3 py-2 text-right tabular-nums ${deltaClass(vsPoll)}`}
                    >
                      {formatDeltaPp(vsPoll)}
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums text-ink/70">
                      {p.electionShare != null
                        ? `${p.electionShare.toFixed(1)} %`
                        : "—"}
                    </td>
                    <td
                      className={`px-3 py-2 text-right tabular-nums ${deltaClass(vsElection)}`}
                    >
                      {formatDeltaPp(vsElection)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      {rules.length > 0 ? (
        <section className="space-y-2">
          <label className="flex items-center gap-2 text-sm text-ink">
            <input
              type="checkbox"
              className="size-4 accent-sea"
              checked={applyExclusions}
              onChange={(e) => setApplyExclusions(e.target.checked)}
            />
            Ausschlussregeln anwenden
          </label>
          {applyExclusions ? (
            <ul className="space-y-1.5">
              {rules.map((rule) => {
                const [a, b] = pairParties(rule);
                return (
                  <li key={rule.id}>
                    <label className="flex items-center gap-2 text-sm text-ink/80">
                      <input
                        type="checkbox"
                        className="size-4 accent-sea"
                        checked={enabled[rule.id] !== false}
                        onChange={(e) =>
                          setEnabled((prev) => ({
                            ...prev,
                            [rule.id]: e.target.checked,
                          }))
                        }
                      />
                      {labelPartyId(a)} + {labelPartyId(b)} ausschließen
                    </label>
                  </li>
                );
              })}
            </ul>
          ) : null}
        </section>
      ) : null}

      {busy ? (
        <p className="text-sm text-ink/50">Berechne Hochrechnung…</p>
      ) : null}
      {error ? (
        <p className="rounded-lg border border-accent/30 bg-accent/5 px-4 py-3 text-sm text-accent">
          {error}
        </p>
      ) : null}

      {result ? (
        <>
          <section className="space-y-3">
            <h3 className="font-display text-xl text-ink">
              Sitzprojektion
            </h3>
            <p className="text-sm text-ink/55">
              Mehrheit ab {result.coalitions.majority_threshold} ·{" "}
              {result.seats.total_seats} Sitze
            </p>
            {Object.keys(result.seats.seats_by_name).length > 0 ? (
              <div className="rounded-xl border border-ink/10 bg-mist/50 p-4">
                <Hemicycle
                  seats={result.seats.seats_by_name}
                  style="projection"
                />
              </div>
            ) : (
              <p className="text-sm text-ink/50">Keine Sitze (Sperrklausel).</p>
            )}
          </section>

          <section className="space-y-3">
            <h3 className="font-display text-xl text-ink">
              Mögliche Mehrheiten
              <InfoTooltip text={TIP_POSSIBLE_COALITIONS} />
            </h3>
            {coalitions.length === 0 ? (
              <p className="text-sm text-ink/50">Keine Mehrheitskoalition.</p>
            ) : (
              <ul className="space-y-2 text-sm">
                {coalitions.slice(0, 12).map((c, i) => (
                  <li
                    key={i}
                    className="flex items-center justify-between rounded-lg border border-ink/10 bg-mist/40 px-3 py-2"
                  >
                    <span>
                      {c.parties.map(labelPartyId).join(" + ")}
                      {c.parties.length === 1 ? (
                        <span className="ml-2 rounded bg-sea/10 px-1.5 py-0.5 text-xs font-medium text-sea">
                          Alleinregierung
                        </span>
                      ) : null}
                    </span>
                    <span className="tabular-nums text-ink/60">{c.seats}</span>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="space-y-3">
            <h3 className="font-display text-xl text-ink">
              Prognose
              <InfoTooltip text={TIP_PARTY_FORECAST} />
            </h3>
            <div className="grid gap-3 sm:grid-cols-2">
              {result.party_forecast.parties.map((party) => {
                const name = displayPartyName(party.party_id, party.party_name);
                return (
                  <div
                    key={party.party_id}
                    className="rounded-2xl border border-accent/25 bg-accent/5 px-4 py-4"
                  >
                    <p className="flex items-center gap-2 text-sm font-medium text-ink">
                      <span
                        className={`${PARTY_SWATCH_CLASS} h-2.5 w-2.5`}
                        style={{ background: partyColor(name) }}
                      />
                      {name}
                    </p>
                    <p className="mt-1 text-xs text-ink/45">
                      Eingabe {party.average_share.toFixed(1)} %
                    </p>
                    <div className="mt-3 grid grid-cols-3 gap-2">
                      <div>
                        <p className="font-display text-2xl tabular-nums text-accent">
                          {Math.round(party.probability_strongest * 100)} %
                        </p>
                        <p className="mt-1 text-xs text-ink/70">stärkste Kraft</p>
                      </div>
                      <div>
                        <p className="font-display text-2xl tabular-nums text-ink/80">
                          {Math.round(party.probability_above_threshold * 100)} %
                        </p>
                        <p className="mt-1 text-xs text-ink/70">
                          über {threshold}&nbsp;%
                        </p>
                      </div>
                      <div>
                        <p className="font-display text-2xl tabular-nums text-ink/80">
                          {Math.round(
                            (party.probability_indispensable ?? 0) * 100,
                          )}{" "}
                          %
                        </p>
                        <p className="mt-1 text-xs text-ink/70">
                          unverzichtbar
                          <InfoTooltip text={TIP_PARTY_INDISPENSABLE} />
                        </p>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>

          <section className="space-y-3">
            <h3 className="font-display text-xl text-ink">
              Wie sicher ist die Mehrheit?
              <InfoTooltip text={TIP_COALITION_UNCERTAINTY} />
            </h3>
            <p className="text-sm text-ink/55">
              Aus {result.n_simulations} Ziehungen mit Wahlabend-SD (
              {result.model_sd_pp.toFixed(2)} Pp)
            </p>
            {probs.length === 0 ? (
              <p className="text-sm text-ink/50">Keine Mehrheitskoalitionen.</p>
            ) : (
              <ul className="space-y-2 text-sm">
                {probs.slice(0, 10).map((c, i) => (
                  <li
                    key={i}
                    className="flex items-center justify-between rounded-lg border border-ink/10 bg-mist/40 px-3 py-2"
                  >
                    <span>
                      {c.parties.map(labelPartyId).join(" + ")}
                      {c.parties.length === 1 ? (
                        <span className="ml-2 rounded bg-sea/10 px-1.5 py-0.5 text-xs font-medium text-sea">
                          Alleinregierung
                        </span>
                      ) : null}
                    </span>
                    <span className="font-display tabular-nums font-medium text-ink">
                      {(c.majority_probability * 100).toFixed(0)} %
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      ) : null}
    </div>
  );
}
