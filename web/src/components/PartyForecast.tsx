"use client";

import { useEffect, useState } from "react";
import {
  fetchPartyForecast,
  type PartyForecastParty,
} from "@/lib/api";
import { displayPartyName, partyColor } from "@/lib/colors";
import { InfoTooltip } from "@/components/InfoTooltip";

function PctBadge({ value, tone }: { value: number; tone?: "strong" | "ok" }) {
  const pct = Math.round(value * 100);
  const cls =
    tone === "strong"
      ? "bg-sea/15 text-sea"
      : tone === "ok"
        ? "bg-ink/8 text-ink/80"
        : "bg-ink/5 text-ink/70";
  return (
    <span
      className={`inline-block min-w-[3.25rem] rounded-md px-2 py-0.5 text-center text-xs font-medium tabular-nums ${cls}`}
    >
      {pct} %
    </span>
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
        <InfoTooltip text="P(stärkste Kraft) = Anteil der Simulationen, in denen diese Partei den höchsten Stimmenanteil hätte. P(über Hürde) = Anteil der Simulationen über der gesetzlichen Sperrklausel. Beides aus denselben 400 Monte-Carlo-Ziehungen wie beim Sperrklausel-Wächter." />
      </h2>
      <p className="text-sm text-ink/55">
        Monte-Carlo aus dem Umfragemittel — Wahrscheinlichkeit, stärkste Kraft
        zu sein bzw. die {thrLabel}-%-Hürde zu schaffen. Keine Wahlprognose.
      </p>
      <div className="overflow-x-auto rounded-lg border border-ink/10">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-ink/5 text-ink/60">
            <tr>
              <th className="px-3 py-2">Partei</th>
              <th className="px-3 py-2">Ø %</th>
              <th className="px-3 py-2">P(stärkste Kraft)</th>
              <th className="px-3 py-2">P(über {thrLabel} %)</th>
            </tr>
          </thead>
          <tbody>
            {parties.map((p) => {
              const name = displayPartyName(p.party_id, p.party_name);
              return (
                <tr key={p.party_id} className="border-t border-ink/5">
                  <td className="px-3 py-2">
                    <span
                      className="mr-2 inline-block h-2 w-2 rounded-full"
                      style={{ background: partyColor(name) }}
                    />
                    {name}
                  </td>
                  <td className="px-3 py-2 tabular-nums">
                    {p.average_share.toFixed(1)}
                  </td>
                  <td className="px-3 py-2">
                    <PctBadge
                      value={p.probability_strongest}
                      tone={p.probability_strongest >= 0.5 ? "strong" : "ok"}
                    />
                  </td>
                  <td className="px-3 py-2">
                    <PctBadge
                      value={p.probability_above_threshold}
                      tone={
                        p.probability_above_threshold >= 0.5 ? "strong" : "ok"
                      }
                    />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
