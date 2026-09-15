"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import {
  fetchLastElection,
  fetchLastElectionCoalitions,
  type CoalitionsResponse,
  type LastElectionResponse,
} from "@/lib/api";
import {
  CoalitionPanel,
  type ExclusionUiState,
} from "@/components/CoalitionPanel";
import { PollShareBarChart } from "@/components/charts";
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
  readLastElectionCache,
  writeLastElectionCache,
} from "@/lib/parliamentCache";
import { TIP_ELECTION_COALITIONS } from "@/lib/tooltipCopy";

export function LastElectionSection({
  parliamentId,
}: {
  parliamentId: string;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const prevParliamentId = useRef<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const dataSigRef = useRef<string>("");

  const [election, setElection] = useState<LastElectionResponse | null>(null);
  const [coalitions, setCoalitions] = useState<CoalitionsResponse | null>(null);
  const [exclusionState, setExclusionState] = useState<ExclusionUiState>(() =>
    exclusionFromSearchParams(searchParams),
  );
  const [missing, setMissing] = useState(false);
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

    setMissing(false);

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
      ? readLastElectionCache(parliamentId)
      : null;

    if (cached?.data.election) {
      setElection(cached.data.election as LastElectionResponse);
      setCoalitions(
        (cached.data.coalitions as CoalitionsResponse | null) ?? null,
      );
      dataSigRef.current = contentSignature(cached.data);
      setCacheUpdatedAt(cached.updatedAt);
      setLoading(false);
      setRefreshing(true);
    } else {
      setLoading(true);
      setRefreshing(false);
      setCacheUpdatedAt(null);
      setElection(null);
      setCoalitions(null);
      dataSigRef.current = "";
    }

    (async () => {
      try {
        const el = await fetchLastElection(parliamentId, { signal });
        if (signal.aborted) return;
        let coal: CoalitionsResponse | null = null;
        try {
          coal = await fetchLastElectionCoalitions(parliamentId, {
            apply_exclusions: nextExclusion.applyExclusions,
            disabled_rule_ids: nextExclusion.applyExclusions
              ? nextExclusion.disabledRuleIds
              : [],
            signal,
          });
        } catch (e) {
          if (isAbortError(e)) throw e;
          coal = null;
        }
        if (signal.aborted) return;
        const next = { election: el, coalitions: coal };
        const sig = contentSignature(next);
        if (sig !== dataSigRef.current) {
          dataSigRef.current = sig;
          setElection(el);
          setCoalitions(coal);
        }
        if (useDefaultExclusions) {
          const now = Date.now();
          writeLastElectionCache(parliamentId, next, now);
          setCacheUpdatedAt(now);
        }
      } catch (e) {
        if (isAbortError(e) || signal.aborted) return;
        if (!cached) {
          setMissing(true);
          setElection(null);
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

  if (loading) {
    return <p className="text-sm text-ink/50">Lade Wahlergebnis…</p>;
  }
  if (missing || !election) {
    return (
      <p className="rounded-lg border border-dashed border-ink/15 px-4 py-6 text-sm text-ink/55">
        Kein hinterlegtes Wahlergebnis für dieses Parlament.
      </p>
    );
  }

  const voteParties = Object.entries(election.vote_share_by_name ?? {})
    .filter(([name, share]) => share > 0 && !/sonstige/i.test(name))
    .map(([party_name, share]) => ({ party_name, share }))
    .sort((a, b) => b.share - a.share);

  return (
    <div className="space-y-8">
      {cacheUpdatedAt != null ? (
        <p className="text-xs text-ink/45">
          Stand: {formatCacheAge(cacheUpdatedAt)}
          {refreshing ? " · aktualisiert…" : ""}
        </p>
      ) : null}
      <section>
        <h2 className="mb-1 font-display text-2xl text-ink">
          {election.label}
        </h2>
        <p className="mb-4 text-sm text-ink/55">
          Amtliches Ergebnis vom {election.election_date}
          {election.source ? ` · ${election.source}` : ""}
        </p>

        <div className="rounded-xl border border-ink/10 bg-mist/50 p-4">
          <h3 className="mb-1 text-sm font-semibold text-ink">
            Stimmenanteil in %
          </h3>
          <p className="mb-3 text-xs text-ink/55">
            Letztes amtliches Wahlergebnis ·{" "}
            <span className="font-display tabular-nums">
              {election.total_seats}
            </span>{" "}
            Sitze im Parlament
          </p>
          <PollShareBarChart parties={voteParties} />
        </div>
      </section>

      {coalitions ? (
        <CoalitionPanel
          key={`election-${parliamentId}`}
          parliamentId={parliamentId}
          seatsByName={election.seats_by_name}
          fetchCoalitionsFn={fetchLastElectionCoalitions}
          title="Koalitionen nach Wahlergebnis"
          tipText={TIP_ELECTION_COALITIONS}
          initialExclusion={exclusionState}
          onExclusionStateChange={onExclusionStateChange}
          initial={{
            majority_threshold: coalitions.majority_threshold,
            excluded_by_rules: coalitions.excluded_by_rules,
            coalitions: coalitions.coalitions,
          }}
        />
      ) : null}
    </div>
  );
}
