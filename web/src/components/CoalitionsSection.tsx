"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
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
import { InfoTooltip } from "@/components/InfoTooltip";
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
import { TIP_COALITION_UNCERTAINTY } from "@/lib/tooltipCopy";

export function CoalitionsSection({ parliamentId }: { parliamentId: string }) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const prevParliamentId = useRef<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const dataSigRef = useRef<string>("");

  const [coalitions, setCoalitions] = useState<CoalitionsResponse | null>(null);
  const [seats, setSeats] = useState<SeatsResponse | null>(null);
  const [uncertainty, setUncertainty] = useState<UncertaintyResponse | null>(
    null,
  );
  const [exclusionState, setExclusionState] = useState<ExclusionUiState>(() =>
    exclusionFromSearchParams(searchParams),
  );
  const [uncertaintyBusy, setUncertaintyBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [cacheUpdatedAt, setCacheUpdatedAt] = useState<number | null>(null);
  const [refreshing, setRefreshing] = useState(false);

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
        const [c, s] = await Promise.all([
          fetchCoalitions(parliamentId, {
            apply_exclusions: nextExclusion.applyExclusions,
            disabled_rule_ids: nextExclusion.applyExclusions
              ? nextExclusion.disabledRuleIds
              : [],
            signal,
          }),
          fetchSeats(parliamentId, { signal }),
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
    const ac = new AbortController();
    const { signal } = ac;
    let cancelled = false;
    const t = setTimeout(() => {
      setUncertaintyBusy(true);
      void fetchUncertainty(parliamentId, 200, {
        applyExclusions: exclusionState.applyExclusions,
        disabledRuleIds: exclusionState.applyExclusions
          ? exclusionState.disabledRuleIds
          : [],
        signal,
      })
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
      {cacheUpdatedAt != null ? (
        <p className="text-xs text-ink/45">
          Stand: {formatCacheAge(cacheUpdatedAt)}
          {refreshing ? " · aktualisiert…" : ""}
        </p>
      ) : null}
      <CoalitionPanel
        key={parliamentId}
        parliamentId={parliamentId}
        seatsByName={seats.seats_by_name}
        initialExclusion={exclusionState}
        initial={{
          majority_threshold: coalitions.majority_threshold,
          excluded_by_rules: coalitions.excluded_by_rules,
          coalitions: coalitions.coalitions,
        }}
        onExclusionStateChange={onExclusionStateChange}
      />

      {(uncertainty && uncertainty.coalition_probabilities.length > 0) ||
      uncertaintyBusy ? (
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
