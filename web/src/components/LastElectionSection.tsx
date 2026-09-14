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

  const [election, setElection] = useState<LastElectionResponse | null>(null);
  const [coalitions, setCoalitions] = useState<CoalitionsResponse | null>(null);
  const [exclusionState, setExclusionState] = useState<ExclusionUiState>(() =>
    exclusionFromSearchParams(searchParams),
  );
  const [missing, setMissing] = useState(false);
  const [loading, setLoading] = useState(true);

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
    let cancelled = false;
    setLoading(true);
    setMissing(false);
    setElection(null);
    setCoalitions(null);

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

    (async () => {
      try {
        const el = await fetchLastElection(parliamentId);
        if (cancelled) return;
        setElection(el);
        try {
          const coal = await fetchLastElectionCoalitions(parliamentId, {
            apply_exclusions: nextExclusion.applyExclusions,
            disabled_rule_ids: nextExclusion.applyExclusions
              ? nextExclusion.disabledRuleIds
              : [],
          });
          if (!cancelled) setCoalitions(coal);
        } catch {
          if (!cancelled) setCoalitions(null);
        }
      } catch {
        if (!cancelled) {
          setMissing(true);
          setElection(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- Query nur bei Toggle / Parlamentwechsel
  }, [parliamentId]);

  const disabledKey = exclusionState.disabledRuleIds.join("\0");

  // Koalitionsübersicht an Ausschluss-Toggles anbinden (wie Unsicherheit im
  // Koalitionen-Tab): Parent lädt neu, Panel bekommt frisches initial.
  useEffect(() => {
    if (!election) return;
    let cancelled = false;
    const t = setTimeout(() => {
      void fetchLastElectionCoalitions(parliamentId, {
        apply_exclusions: exclusionState.applyExclusions,
        disabled_rule_ids: exclusionState.applyExclusions
          ? exclusionState.disabledRuleIds
          : [],
      })
        .then((coal) => {
          if (!cancelled) setCoalitions(coal);
        })
        .catch(() => {
          if (!cancelled) setCoalitions(null);
        });
    }, 0);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [
    parliamentId,
    election,
    exclusionState.applyExclusions,
    disabledKey,
  ]);

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
          key={`election-${parliamentId}-${exclusionState.applyExclusions}-${disabledKey}`}
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
