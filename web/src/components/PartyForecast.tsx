"use client";

import { useEffect, useState } from "react";
import {
  fetchPartyForecast,
  type PartyForecastParty,
} from "@/lib/api";
import { displayPartyName, partyColor } from "@/lib/colors";
import { InfoTooltip } from "@/components/InfoTooltip";

function ForecastTile({
  party,
  thresholdLabel,
}: {
  party: PartyForecastParty;
  thresholdLabel: string;
}) {
  const name = displayPartyName(party.party_id, party.party_name);
  const strongestPct = Math.round(party.probability_strongest * 100);
  const abovePct = Math.round(party.probability_above_threshold * 100);

  return (
    <div className="rounded-2xl border border-accent/25 bg-accent/5 px-4 py-4 transition hover:border-accent/50">
      <p className="flex items-center gap-2 text-sm font-medium text-ink">
        <span
          className="inline-block h-2.5 w-2.5 shrink-0 rounded-full"
          style={{ background: partyColor(name) }}
        />
        {name}
      </p>
      <p className="mt-1 text-xs text-ink/45">
        Mittel {party.average_share.toFixed(1)} %
      </p>
      <div className="mt-3 grid grid-cols-2 gap-3">
        <div>
          <p className="font-display text-3xl tabular-nums text-accent">
            {strongestPct} %
          </p>
          <p className="mt-1 text-sm text-ink/70">stärkste Kraft</p>
        </div>
        <div>
          <p className="font-display text-3xl tabular-nums text-ink/80">
            {abovePct} %
          </p>
          <p className="mt-1 text-sm text-ink/70">
            über {thresholdLabel}&nbsp;%
          </p>
        </div>
      </div>
    </div>
  );
}

export function PartyForecast({ parliamentId }: { parliamentId: string }) {
  const [parties, setParties] = useState<PartyForecastParty[] | null>(null);
  const [threshold, setThreshold] = useState<number>(5);

  useEffect(() => {
    let cancelled = false;
    void fetchPartyForecast(parliamentId)
      .then((d) => {
        if (cancelled) return;
        setParties(d.parties);
        setThreshold(d.threshold_percent);
      })
      .catch(() => {
        if (!cancelled) setParties([]);
      });
    return () => {
      cancelled = true;
    };
  }, [parliamentId]);

  if (!parties || parties.length === 0) return null;

  const thrLabel = Number.isInteger(threshold)
    ? String(threshold)
    : threshold.toFixed(1);

  return (
    <section className="space-y-3">
      <h2 className="font-display text-2xl text-ink">
        Prognose je Partei
        <InfoTooltip text="P(stärkste Kraft) = Anteil der Simulationen, in denen diese Partei den höchsten Stimmenanteil hätte. P(über Hürde) = Anteil der Simulationen über der gesetzlichen Sperrklausel. Beides aus denselben 400 Monte-Carlo-Ziehungen — keine Wahlprognose, sondern eine Unsicherheitsabschätzung um den aktuellen Umfragestand." />
      </h2>
      <p className="text-sm text-ink/55">
        Monte-Carlo aus dem Umfragemittel — Wahrscheinlichkeit, stärkste Kraft
        zu sein bzw. die {thrLabel}-%-Hürde zu schaffen.
      </p>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {parties.map((p) => (
          <ForecastTile
            key={p.party_id}
            party={p}
            thresholdLabel={thrLabel}
          />
        ))}
      </div>
    </section>
  );
}
