"use client";

import { useEffect, useState } from "react";
import {
  fetchLastElection,
  fetchLastElectionCoalitions,
  type CoalitionsResponse,
  type LastElectionResponse,
} from "@/lib/api";
import { CoalitionPanel } from "@/components/CoalitionPanel";
import { PollShareBarChart } from "@/components/charts";
import { TIP_ELECTION_COALITIONS } from "@/lib/tooltipCopy";

export function LastElectionSection({
  parliamentId,
}: {
  parliamentId: string;
}) {
  const [election, setElection] = useState<LastElectionResponse | null>(null);
  const [coalitions, setCoalitions] = useState<CoalitionsResponse | null>(null);
  const [missing, setMissing] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setMissing(false);
    setElection(null);
    setCoalitions(null);
    (async () => {
      try {
        const el = await fetchLastElection(parliamentId);
        if (cancelled) return;
        setElection(el);
        try {
          const coal = await fetchLastElectionCoalitions(parliamentId);
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
