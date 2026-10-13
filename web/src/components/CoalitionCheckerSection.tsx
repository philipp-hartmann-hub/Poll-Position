"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  coalitionCheckCombinationKey,
  fetchCoalitionCheckAll,
  fetchSeats,
  fetchThresholdScenario,
  fetchThresholdScenarioCoalitionCheckAll,
  fetchThresholdWatch,
  postCoalitionCheck,
  type CoalitionCheckAllEntry,
  type CoalitionCheckResponse,
  type SeatsResponse,
} from "@/lib/api";
import { Hemicycle } from "@/components/charts";
import { InfoTooltip } from "@/components/InfoTooltip";
import {
  ThresholdScenarioChips,
  type ThresholdScenarioCandidate,
} from "@/components/ThresholdScenarioChips";
import { labelPartyId, partyColor } from "@/lib/colors";
import { leftRightPosition } from "@/lib/partyPositions";
import { seatsByNameFromPartyIds } from "@/lib/scenarioShares";
import { PARTY_SWATCH_CLASS } from "@/lib/theme";
import { TIP_COALITION_CHECKER } from "@/lib/tooltipCopy";
import { isAbortError } from "@/lib/parliamentCache";

/** Anzeigename → kanonische ID (wie SHORT_TO_CANONICAL im Backend). */
const NAME_TO_CANONICAL: Record<string, string> = {
  AfD: "de:afd",
  "CDU/CSU": "de:cdu_csu",
  CDU: "de:cdu",
  CSU: "de:csu",
  SPD: "de:spd",
  Grüne: "de:gruene",
  FDP: "de:fdp",
  Linke: "de:linke",
  BSW: "de:bsw",
  "Freie Wähler": "de:fw",
  SSW: "de:ssw",
  BIW: "de:biw",
  "BVB/FW": "de:bvb_freie_waehler",
  "Freie Sachsen": "de:freie_sachsen",
  Volt: "de:volt",
};

function canonicalFromSeatName(name: string): string | null {
  if (NAME_TO_CANONICAL[name]) return NAME_TO_CANONICAL[name];
  if (name.startsWith("de:")) return name;
  return null;
}

type PartyOption = {
  canonicalId: string;
  name: string;
  seats: number;
  isScenario?: boolean;
};

type ActiveScenario = {
  partyId: string;
  partyName: string;
  targetShare: number;
  seatsByCanonical: Record<string, number>;
  seatsByName: Record<string, number>;
};

function resultFromStaticEntry(
  parliamentId: string,
  entry: CoalitionCheckAllEntry,
  meta: {
    totalSeats: number;
    majorityThreshold: number;
    nSimulations: number;
    seatsByName: Record<string, number>;
    options: PartyOption[];
  },
): CoalitionCheckResponse {
  const selected = new Set(entry.parties);
  return {
    parliament_id: parliamentId,
    parties: entry.parties,
    total_seats: meta.totalSeats,
    majority_threshold: meta.majorityThreshold,
    point_seats: entry.point_seats,
    point_has_majority: entry.point_has_majority,
    majority_probability: entry.majority_probability,
    n_majority: entry.n_majority,
    n_simulations: meta.nSimulations,
    seats_by_party: meta.options
      .filter((o) => selected.has(o.canonicalId))
      .map((o) => ({
        party_id: o.canonicalId,
        party_name: o.name,
        seats: o.seats,
      })),
    seats_by_name: meta.seatsByName,
  };
}

export function CoalitionCheckerSection({
  parliamentId,
}: {
  parliamentId: string;
}) {
  const [seats, setSeats] = useState<SeatsResponse | null>(null);
  const [baseSeats, setBaseSeats] = useState<SeatsResponse | null>(null);
  const [thresholdCandidates, setThresholdCandidates] = useState<
    ThresholdScenarioCandidate[]
  >([]);
  const [scenario, setScenario] = useState<ActiveScenario | null>(null);
  const [scenarioBusy, setScenarioBusy] = useState(false);
  const [comboMap, setComboMap] = useState<Map<string, CoalitionCheckAllEntry>>(
    () => new Map(),
  );
  const [baseComboMap, setBaseComboMap] = useState<
    Map<string, CoalitionCheckAllEntry>
  >(() => new Map());
  const [comboMeta, setComboMeta] = useState<{
    nSimulations: number;
    totalSeats: number;
    majorityThreshold: number;
  } | null>(null);
  const [baseComboMeta, setBaseComboMeta] = useState<{
    nSimulations: number;
    totalSeats: number;
    majorityThreshold: number;
  } | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [result, setResult] = useState<CoalitionCheckResponse | null>(null);
  const [loadingSeats, setLoadingSeats] = useState(true);
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    let cancelled = false;
    const ac = new AbortController();
    setLoadingSeats(true);
    setError(null);
    setSelected(new Set());
    setResult(null);
    setScenario(null);
    setComboMap(new Map());
    setBaseComboMap(new Map());
    setComboMeta(null);
    setBaseComboMeta(null);
    (async () => {
      try {
        const [data, all, watch] = await Promise.all([
          fetchSeats(parliamentId, { signal: ac.signal }),
          fetchCoalitionCheckAll(parliamentId, { signal: ac.signal }).catch(
            () => null,
          ),
          fetchThresholdWatch(parliamentId).catch(() => null),
        ]);
        if (cancelled || ac.signal.aborted) return;
        setSeats(data);
        setBaseSeats(data);
        const thr = watch?.threshold_percent ?? 5;
        setThresholdCandidates(
          (watch?.parties ?? [])
            .filter((p) => p.average_share < p.threshold_percent)
            .map((p) => ({ ...p, targetShare: thr })),
        );
        if (all?.combinations) {
          const map = new Map(Object.entries(all.combinations));
          const meta = {
            nSimulations: all.n_simulations,
            totalSeats: all.total_seats,
            majorityThreshold: all.majority_threshold,
          };
          setComboMap(map);
          setBaseComboMap(map);
          setComboMeta(meta);
          setBaseComboMeta(meta);
        }
      } catch (e) {
        if (cancelled || isAbortError(e)) return;
        setError(e instanceof Error ? e.message : "Sitze laden fehlgeschlagen");
        setSeats(null);
        setBaseSeats(null);
      } finally {
        if (!cancelled && !ac.signal.aborted) setLoadingSeats(false);
      }
    })();
    return () => {
      cancelled = true;
      ac.abort();
    };
  }, [parliamentId]);

  const options: PartyOption[] = useMemo(() => {
    if (!seats?.seats_by_name) return [];
    const base: PartyOption[] = [];
    for (const [name, n] of Object.entries(seats.seats_by_name)) {
      if (n <= 0 || /sonstige/i.test(name)) continue;
      const canonicalId = canonicalFromSeatName(name);
      if (!canonicalId) continue;
      base.push({ canonicalId, name, seats: n });
    }

    if (scenario) {
      const without = base.filter((o) => o.canonicalId !== scenario.partyId);
      const scenarioSeats = scenario.seatsByCanonical[scenario.partyId] ?? 0;
      if (scenarioSeats > 0) {
        without.push({
          canonicalId: scenario.partyId,
          name: scenario.partyName,
          seats: scenarioSeats,
          isScenario: true,
        });
      }
      without.sort((a, b) => {
        const lr = leftRightPosition(a.name) - leftRightPosition(b.name);
        if (lr !== 0) return lr;
        return a.name.localeCompare(b.name, "de");
      });
      return without;
    }

    base.sort((a, b) => {
      const lr = leftRightPosition(a.name) - leftRightPosition(b.name);
      if (lr !== 0) return lr;
      return a.name.localeCompare(b.name, "de");
    });
    return base;
  }, [seats, scenario]);

  const displaySeatsByName = useMemo(
    () => scenario?.seatsByName ?? seats?.seats_by_name ?? {},
    [scenario, seats],
  );

  const selectedList = useMemo(
    () =>
      options
        .filter((o) => selected.has(o.canonicalId))
        .map((o) => o.canonicalId),
    [options, selected],
  );

  const highlightNames = useMemo(
    () => options.filter((o) => selected.has(o.canonicalId)).map((o) => o.name),
    [options, selected],
  );

  const localPoint = useMemo(() => {
    if (!seats || selectedList.length === 0) return null;
    const total = scenario
      ? Object.values(displaySeatsByName).reduce((s, n) => s + n, 0) ||
        seats.total_seats
      : seats.total_seats;
    const thr =
      comboMeta?.majorityThreshold ||
      (total > 0 ? Math.floor(total / 2) + 1 : 0);
    const sum = options
      .filter((o) => selected.has(o.canonicalId))
      .reduce((s, o) => s + o.seats, 0);
    return {
      seats: sum,
      threshold: thr,
      total,
      hasMajority: thr > 0 && sum >= thr,
    };
  }, [
    seats,
    selected,
    selectedList.length,
    options,
    scenario,
    displaySeatsByName,
    comboMeta,
  ]);

  const selectedKey = coalitionCheckCombinationKey(selectedList);

  useEffect(() => {
    if (selectedList.length === 0) {
      setResult(null);
      setChecking(false);
      return;
    }

    const cached = comboMap.get(selectedKey);
    if (cached && comboMeta && seats) {
      abortRef.current?.abort();
      setResult(
        resultFromStaticEntry(parliamentId, cached, {
          totalSeats: comboMeta.totalSeats || seats.total_seats,
          majorityThreshold:
            comboMeta.majorityThreshold ||
            Math.floor(seats.total_seats / 2) + 1,
          nSimulations: comboMeta.nSimulations,
          seatsByName: displaySeatsByName,
          options,
        }),
      );
      setChecking(false);
      setError(null);
      return;
    }

    // Im Szenario: nur vorberechnete Kombis — kein Live-POST ohne Szenario-MC.
    if (scenario) {
      setResult(null);
      setChecking(false);
      return;
    }

    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;
    setChecking(true);
    setError(null);
    const parties = selectedList;
    (async () => {
      try {
        const res = await postCoalitionCheck(parliamentId, parties, {
          n_simulations: 400,
          signal: ac.signal,
        });
        if (ac.signal.aborted) return;
        setResult(res);
      } catch (e) {
        if (isAbortError(e) || ac.signal.aborted) return;
        setError(
          e instanceof Error ? e.message : "Prüfung fehlgeschlagen",
        );
        setResult(null);
      } finally {
        if (!ac.signal.aborted) setChecking(false);
      }
    })();
    return () => {
      ac.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- selectedKey
  }, [
    parliamentId,
    selectedKey,
    comboMap,
    comboMeta,
    seats,
    options,
    scenario,
    displaySeatsByName,
  ]);

  function toggle(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  const runScenario = useCallback(
    async (candidate: ThresholdScenarioCandidate) => {
      setScenarioBusy(true);
      setError(null);
      try {
        const [res, all] = await Promise.all([
          fetchThresholdScenario(parliamentId, candidate.party_id, {
            targetShare: candidate.targetShare,
          }),
          fetchThresholdScenarioCoalitionCheckAll(
            parliamentId,
            candidate.party_id,
            { targetShare: candidate.targetShare },
          ),
        ]);
        const byName = seatsByNameFromPartyIds(res.seats);
        const seatsByCanonical: Record<string, number> = {};
        for (const [pid, n] of Object.entries(res.seats)) {
          if (n > 0) seatsByCanonical[pid] = n;
        }
        setScenario({
          partyId: candidate.party_id,
          partyName: candidate.party_name,
          targetShare: res.target_share,
          seatsByCanonical,
          seatsByName: byName,
        });
        setSeats({
          parliament_id: parliamentId,
          seats: res.seats,
          seats_by_name: byName,
          total_seats: res.total_seats,
        });
        setComboMap(new Map(Object.entries(all.combinations ?? {})));
        setComboMeta({
          nSimulations: all.n_simulations,
          totalSeats: all.total_seats,
          majorityThreshold: all.majority_threshold,
        });
        setSelected((prev) => new Set(prev).add(candidate.party_id));
      } catch (e) {
        setError(e instanceof Error ? e.message : "Szenario fehlgeschlagen");
        setScenario(null);
      } finally {
        setScenarioBusy(false);
      }
    },
    [parliamentId],
  );

  function resetScenario() {
    if (!scenario) return;
    const partyId = scenario.partyId;
    setScenario(null);
    if (baseSeats) setSeats(baseSeats);
    setComboMap(baseComboMap);
    setComboMeta(baseComboMeta);
    setSelected((prev) => {
      const next = new Set(prev);
      next.delete(partyId);
      return next;
    });
  }

  if (loadingSeats) {
    return <p className="text-sm text-ink/50">Lade Parteien…</p>;
  }
  if (!seats || (options.length === 0 && thresholdCandidates.length === 0)) {
    return (
      <p className="rounded-lg border border-dashed border-ink/15 px-4 py-6 text-sm text-ink/55">
        Keine Sitzprojektion verfügbar — der Koalitionsprüfer braucht aktuelle
        Umfrage-Sitze.
      </p>
    );
  }

  const probability =
    result && selectedList.length > 0 ? result.majority_probability : null;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-display text-2xl text-ink">
          Koalitionsprüfer
          <InfoTooltip text={TIP_COALITION_CHECKER} />
        </h2>
        <p className="mt-1 max-w-2xl text-sm text-ink/55">
          Wähle selbst eine oder mehrere Parteien (Alleinregierung ist erlaubt).
          Geprüft wird die reine Sitzsumme — nicht die inklusionsminimalen
          Mehrheiten aus dem Tab „Koalitionen“.
        </p>
        <p className="mt-2 max-w-2xl text-sm text-ink/55">
          Zeigt die Wahrscheinlichkeit für genau diese Auswahl — auch wenn eine
          der Parteien für die Mehrheit gar nicht nötig wäre.
        </p>
      </div>

      <ThresholdScenarioChips
        candidates={thresholdCandidates}
        activePartyId={scenario?.partyId}
        busy={scenarioBusy}
        onSelect={(p) => void runScenario(p)}
      />
      {scenario ? (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-sea/30 bg-sea/10 px-3 py-2 text-sm text-ink">
          <span>
            Szenario aktiv: {scenario.partyName} auf{" "}
            {scenario.targetShare.toLocaleString("de-DE", {
              maximumFractionDigits: 1,
            })}
            &nbsp;% (inkl. Unsicherheit).
          </span>
          <button
            type="button"
            className="rounded-md border border-ink/15 bg-mist px-2.5 py-1 text-xs font-medium text-ink hover:border-sea/40"
            onClick={resetScenario}
          >
            Zurücksetzen
          </button>
        </div>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
        <fieldset className="space-y-2">
          <legend className="mb-2 text-sm font-medium text-ink">
            Parteien auswählen
          </legend>
          <ul className="space-y-1.5">
            {options.map((o) => {
              const on = selected.has(o.canonicalId);
              return (
                <li key={o.canonicalId}>
                  <label className="flex cursor-pointer items-center gap-2 rounded-md border border-ink/10 bg-mist/40 px-3 py-2 text-sm transition hover:border-ink/20">
                    <input
                      type="checkbox"
                      className="size-4 accent-sea"
                      checked={on}
                      onChange={() => toggle(o.canonicalId)}
                    />
                    <span
                      className={`${PARTY_SWATCH_CLASS} h-2.5 w-2.5 shrink-0`}
                      style={{ background: partyColor(o.name) }}
                    />
                    <span className="font-medium text-ink">{o.name}</span>
                    {o.isScenario ? (
                      <span className="rounded bg-sea/15 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-sea">
                        Szenario
                      </span>
                    ) : null}
                    <span className="ml-auto tabular-nums text-ink/50">
                      {o.seats}
                    </span>
                  </label>
                </li>
              );
            })}
          </ul>
        </fieldset>

        <div className="space-y-4">
          {selectedList.length === 0 ? (
            <p className="rounded-lg border border-dashed border-ink/15 px-4 py-6 text-sm text-ink/55">
              Mindestens eine Partei auswählen.
            </p>
          ) : (
            <>
              <div className="rounded-xl border border-ink/10 bg-mist/50 p-4">
                <p className="text-xs uppercase tracking-wide text-ink/45">
                  {scenario ? "Szenario-Punktwert" : "Aktueller Umfrage-Stand"}
                </p>
                <p className="mt-1 font-display text-2xl text-ink">
                  {localPoint?.hasMajority ? "Mehrheit" : "Keine Mehrheit"}
                </p>
                <p className="mt-1 text-sm text-ink/65">
                  {localPoint?.seats ?? 0} Sitze · Mehrheit ab{" "}
                  {localPoint?.threshold ?? "—"}
                  {localPoint?.total
                    ? ` (von ${localPoint.total})`
                    : ""}
                </p>
                <p className="mt-2 text-xs text-ink/45">
                  {selectedList.map(labelPartyId).join(" + ")}
                </p>
              </div>

              <div className="rounded-xl border border-ink/10 bg-mist/50 p-4">
                <p className="text-xs uppercase tracking-wide text-ink/45">
                  Monte-Carlo-Wahrscheinlichkeit
                </p>
                {checking && probability == null ? (
                  <p className="mt-2 text-sm text-ink/50">Berechne…</p>
                ) : (
                  <>
                    <p className="mt-1 font-display text-3xl tabular-nums text-accent">
                      {probability != null
                        ? `${Math.round(probability * 100)} %`
                        : "—"}
                    </p>
                    <p className="mt-1 text-sm text-ink/65">
                      Chance, dass genau diese Auswahl eine Mehrheit hat
                      {result
                        ? ` · ${result.n_majority} / ${result.n_simulations} Ziehungen`
                        : ""}
                      {checking ? " · aktualisiert…" : ""}
                      {scenario ? " · Szenario-Ziehungen" : ""}
                    </p>
                  </>
                )}
              </div>

              <div className="rounded-xl border border-ink/10 bg-mist/50 p-4">
                <h3 className="mb-2 text-sm font-semibold text-ink">
                  Sitzverteilung
                </h3>
                <Hemicycle
                  seats={displaySeatsByName}
                  highlightParties={highlightNames}
                  collapseOthers
                  style="projection"
                />
              </div>
            </>
          )}
        </div>
      </div>

      {error ? (
        <p className="rounded-lg border border-accent/30 bg-accent/5 px-4 py-3 text-sm text-accent">
          {error}
        </p>
      ) : null}
    </div>
  );
}
