"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import {
  fetchAverages,
  fetchCoalitions,
  fetchSeats,
  fetchThresholdWatch,
  fetchUncertainty,
  postScenario,
  type CoalitionsResponse,
  type PartyAverage,
  type ScenarioResponse,
  type SeatsResponse,
  type UncertaintyResponse,
} from "@/lib/api";
import {
  CoalitionPanel,
  type ExclusionUiState,
} from "@/components/CoalitionPanel";
import { InfoTooltip } from "@/components/InfoTooltip";
import {
  ThresholdScenarioChips,
  type ThresholdScenarioCandidate,
} from "@/components/ThresholdScenarioChips";
import { labelPartyId } from "@/lib/colors";
import {
  DEFAULT_EXCLUSION_UI,
  exclusionFromSearchParams,
  exclusionStatesEqual,
  searchParamsWithExclusion,
} from "@/lib/exclusionUrl";
import {
  contentSignature,
  formatCacheAge,
  isAbortError,
  readCoalitionsCache,
  writeCoalitionsCache,
} from "@/lib/parliamentCache";
import {
  buildThresholdScenarioShares,
  seatsByNameFromPartyIds,
} from "@/lib/scenarioShares";
import { TIP_COALITION_UNCERTAINTY } from "@/lib/tooltipCopy";

type ActiveScenario = {
  partyId: string;
  partyName: string;
  targetShare: number;
  shares: Record<string, number>;
  result: ScenarioResponse;
};

export function CoalitionsSection({ parliamentId }: { parliamentId: string }) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const prevParliamentId = useRef<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const dataSigRef = useRef<string>("");
  const scenarioSharesRef = useRef<Record<string, number> | null>(null);

  const [coalitions, setCoalitions] = useState<CoalitionsResponse | null>(null);
  const [seats, setSeats] = useState<SeatsResponse | null>(null);
  const [uncertainty, setUncertainty] = useState<UncertaintyResponse | null>(
    null,
  );
  const [averages, setAverages] = useState<PartyAverage[] | null>(null);
  const [thresholdCandidates, setThresholdCandidates] = useState<
    ThresholdScenarioCandidate[]
  >([]);
  const [scenario, setScenario] = useState<ActiveScenario | null>(null);
  const [scenarioBusy, setScenarioBusy] = useState(false);
  const [scenarioError, setScenarioError] = useState<string | null>(null);
  const [exclusionState, setExclusionState] = useState<ExclusionUiState>(() =>
    exclusionFromSearchParams(searchParams),
  );
  const [uncertaintyBusy, setUncertaintyBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [cacheUpdatedAt, setCacheUpdatedAt] = useState<number | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  scenarioSharesRef.current = scenario?.shares ?? null;

  const syncExclusionToUrl = useCallback(
    (state: ExclusionUiState) => {
      const next = searchParamsWithExclusion(searchParams, state);
      const qs = next.toString();
      const href = qs ? `${pathname}?${qs}` : pathname;
      if (qs === searchParams.toString()) return;
      router.replace(href, { scroll: false });
    },
    [pathname, router, searchParams],
  );

  const onExclusionStateChange = useCallback(
    (state: ExclusionUiState) => {
      setExclusionState((prev) =>
        exclusionStatesEqual(prev, state) ? prev : state,
      );
      syncExclusionToUrl(state);
    },
    [syncExclusionToUrl],
  );

  useEffect(() => {
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;
    const { signal } = ac;

    setError(null);
    setScenario(null);
    setScenarioError(null);

    const switchedParliament =
      prevParliamentId.current != null &&
      prevParliamentId.current !== parliamentId;
    prevParliamentId.current = parliamentId;

    const hasExclusionQuery =
      searchParams.has("apply_exclusions") ||
      searchParams.has("disabled_rules");
    const nextExclusion =
      switchedParliament && !hasExclusionQuery
        ? DEFAULT_EXCLUSION_UI
        : exclusionFromSearchParams(searchParams);
    setExclusionState(nextExclusion);

    const useDefaultExclusions =
      nextExclusion.applyExclusions &&
      nextExclusion.disabledRuleIds.length === 0;
    const cached = useDefaultExclusions
      ? readCoalitionsCache(parliamentId)
      : null;

    if (cached) {
      const c = cached.data.coalitions as CoalitionsResponse;
      const s = cached.data.seats as SeatsResponse;
      setCoalitions(c);
      setSeats(s);
      dataSigRef.current = contentSignature(cached.data);
      setCacheUpdatedAt(cached.updatedAt);
      setLoading(false);
      setRefreshing(true);
    } else {
      setLoading(true);
      setRefreshing(false);
      setCacheUpdatedAt(null);
      setCoalitions(null);
      setSeats(null);
      dataSigRef.current = "";
    }

    (async () => {
      try {
        const [c, s, avg, watch] = await Promise.all([
          fetchCoalitions(parliamentId, {
            apply_exclusions: nextExclusion.applyExclusions,
            disabled_rule_ids: nextExclusion.applyExclusions
              ? nextExclusion.disabledRuleIds
              : [],
            signal,
          }),
          fetchSeats(parliamentId, { signal }),
          fetchAverages(parliamentId, 365, { signal }).catch(() => null),
          fetchThresholdWatch(parliamentId).catch(() => null),
        ]);
        if (signal.aborted) return;
        const next = { coalitions: c, seats: s };
        const sig = contentSignature(next);
        if (sig !== dataSigRef.current) {
          dataSigRef.current = sig;
          setCoalitions(c);
          setSeats(s);
        }
        if (useDefaultExclusions) {
          const now = Date.now();
          writeCoalitionsCache(parliamentId, next, now);
          setCacheUpdatedAt(now);
        }
        setAverages(avg?.parties ?? null);
        const thr = watch?.threshold_percent ?? 5;
        setThresholdCandidates(
          (watch?.parties ?? [])
            .filter((p) => p.average_share < p.threshold_percent)
            .map((p) => ({ ...p, targetShare: thr })),
        );
      } catch (e) {
        if (isAbortError(e) || signal.aborted) return;
        if (!cached) {
          setError(e instanceof Error ? e.message : "Laden fehlgeschlagen");
        }
      } finally {
        if (!signal.aborted) {
          setLoading(false);
          setRefreshing(false);
        }
      }
    })();

    return () => {
      ac.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- Query nur bei Toggle / Parlamentwechsel
  }, [parliamentId]);

  const disabledKey = exclusionState.disabledRuleIds.join("\0");

  useEffect(() => {
    if (scenario) return;
    const ac = new AbortController();
    const { signal } = ac;
    let cancelled = false;
    const isDefaultExclusion =
      exclusionState.applyExclusions &&
      exclusionState.disabledRuleIds.length === 0;
    const t = setTimeout(() => {
      setUncertaintyBusy(true);
      void fetchUncertainty(
        parliamentId,
        200,
        isDefaultExclusion
          ? { signal }
          : {
              applyExclusions: exclusionState.applyExclusions,
              disabledRuleIds: exclusionState.applyExclusions
                ? exclusionState.disabledRuleIds
                : [],
              signal,
            },
      )
        .then((u) => {
          if (!cancelled && !signal.aborted) setUncertainty(u);
        })
        .catch((e) => {
          if (isAbortError(e) || cancelled || signal.aborted) return;
          setUncertainty(null);
        })
        .finally(() => {
          if (!cancelled && !signal.aborted) setUncertaintyBusy(false);
        });
    }, 200);
    return () => {
      cancelled = true;
      clearTimeout(t);
      ac.abort();
    };
  }, [parliamentId, exclusionState.applyExclusions, disabledKey, scenario]);

  const runScenario = useCallback(
    async (candidate: ThresholdScenarioCandidate) => {
      if (!averages || averages.length === 0) {
        setScenarioError("Keine Umfrageanteile für das Szenario verfügbar.");
        return;
      }
      setScenarioBusy(true);
      setScenarioError(null);
      try {
        const shares = buildThresholdScenarioShares(
          averages,
          candidate.party_id,
          candidate.targetShare,
        );
        const result = await postScenario({
          parliament_id: parliamentId,
          party_shares: shares,
          apply_exclusions: exclusionState.applyExclusions,
          disabled_rule_ids: exclusionState.applyExclusions
            ? exclusionState.disabledRuleIds
            : [],
        });
        setScenario({
          partyId: candidate.party_id,
          partyName: candidate.party_name,
          targetShare: candidate.targetShare,
          shares,
          result,
        });
      } catch (e) {
        setScenarioError(
          e instanceof Error ? e.message : "Szenario fehlgeschlagen",
        );
        setScenario(null);
      } finally {
        setScenarioBusy(false);
      }
    },
    [averages, parliamentId, exclusionState],
  );

  const scenarioFetchCoalitions = useCallback(
    async (
      pid: string,
      opts?: {
        apply_exclusions?: boolean;
        disabled_rule_ids?: string[];
        signal?: AbortSignal;
      },
    ) => {
      const shares = scenarioSharesRef.current;
      if (!shares) {
        return fetchCoalitions(pid, opts);
      }
      const res = await postScenario({
        parliament_id: pid,
        party_shares: shares,
        apply_exclusions: opts?.apply_exclusions,
        disabled_rule_ids: opts?.disabled_rule_ids,
      });
      if (opts?.signal?.aborted) {
        const err = new Error("Aborted");
        err.name = "AbortError";
        throw err;
      }
      setScenario((prev) =>
        prev && prev.shares === shares ? { ...prev, result: res } : prev,
      );
      return {
        parliament_id: pid,
        total_seats: res.total_seats,
        majority_threshold: res.majority_threshold,
        excluded_by_rules: 0,
        coalitions: res.coalitions,
      };
    },
    [],
  );

  const panelSeatsByName = useMemo(() => {
    if (scenario) return seatsByNameFromPartyIds(scenario.result.seats);
    return seats?.seats_by_name ?? {};
  }, [scenario, seats]);

  const panelInitial = useMemo(() => {
    if (scenario) {
      return {
        majority_threshold: scenario.result.majority_threshold,
        excluded_by_rules: 0,
        coalitions: scenario.result.coalitions,
      };
    }
    if (!coalitions) return null;
    return {
      majority_threshold: coalitions.majority_threshold,
      excluded_by_rules: coalitions.excluded_by_rules,
      coalitions: coalitions.coalitions,
    };
  }, [scenario, coalitions]);

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
  if (!coalitions || !seats || !panelInitial) return null;

  return (
    <div className="space-y-10">
      {cacheUpdatedAt != null && !scenario ? (
        <p className="text-xs text-ink/45">
          Stand: {formatCacheAge(cacheUpdatedAt)}
          {refreshing ? " · aktualisiert…" : ""}
        </p>
      ) : null}

      <ThresholdScenarioChips
        candidates={thresholdCandidates}
        activePartyId={scenario?.partyId}
        busy={scenarioBusy}
        onSelect={(p) => void runScenario(p)}
      />
      {scenarioError ? (
        <p className="text-sm text-accent">{scenarioError}</p>
      ) : null}
      {scenario ? (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-sea/30 bg-sea/10 px-3 py-2 text-sm text-ink">
          <span>
            Szenario aktiv: {scenario.partyName} auf{" "}
            {scenario.targetShare.toLocaleString("de-DE", {
              maximumFractionDigits: 1,
            })}
            &nbsp;% gesetzt (Punktwert, keine Unsicherheits-%).
          </span>
          <button
            type="button"
            className="rounded-md border border-ink/15 bg-mist px-2.5 py-1 text-xs font-medium text-ink hover:border-sea/40"
            onClick={() => {
              setScenario(null);
              setScenarioError(null);
            }}
          >
            Zurücksetzen
          </button>
        </div>
      ) : null}

      <CoalitionPanel
        key={
          scenario
            ? `${parliamentId}-scenario-${scenario.partyId}`
            : parliamentId
        }
        parliamentId={parliamentId}
        seatsByName={panelSeatsByName}
        initialExclusion={exclusionState}
        initial={panelInitial}
        onExclusionStateChange={onExclusionStateChange}
        fetchCoalitionsFn={
          scenario ? scenarioFetchCoalitions : fetchCoalitions
        }
      />

      {!scenario &&
      ((uncertainty && uncertainty.coalition_probabilities.length > 0) ||
        uncertaintyBusy) ? (
        <section>
          <h2 className="mb-3 font-display text-2xl text-ink">
            Wie sicher ist die Mehrheit?
            <InfoTooltip text={TIP_COALITION_UNCERTAINTY} />
          </h2>
          <p className="mb-3 text-sm text-ink/55">
            {uncertainty
              ? `Aus ${uncertainty.n_simulations} leicht schwankenden Varianten des heutigen Umfragestands`
              : "Wird gerade berechnet…"}
            {uncertaintyBusy ? " · aktualisiert…" : ""}
            {!exclusionState.applyExclusions
              ? " · ohne Ausschlussregeln"
              : exclusionState.disabledRuleIds.length > 0
                ? ` · ${exclusionState.disabledRuleIds.length} Regeln aus`
                : ""}
          </p>
          {uncertainty && uncertainty.coalition_probabilities.length > 0 ? (
            <ul className="space-y-2 text-sm">
              {uncertainty.coalition_probabilities.slice(0, 10).map((c, i) => (
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
          ) : (
            <p className="text-sm text-ink/50">
              Keine Mehrheitskoalitionen bei diesem Umfragestand.
            </p>
          )}
        </section>
      ) : null}
    </div>
  );
}
