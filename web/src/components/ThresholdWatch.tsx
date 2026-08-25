"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  fetchThresholdWatch,
  fetchThresholdWatchOverview,
  type ThresholdWatchOverviewResponse,
  type ThresholdWatchParty,
} from "@/lib/api";

function parliamentHref(id: string): string {
  if (id === "de_bundestag") return "/deutschland/bund";
  return "/deutschland/laender";
}

function TileCard({
  party,
  href,
  subtitle,
}: {
  party: ThresholdWatchParty;
  href?: string;
  subtitle?: string | null;
}) {
  const pct = Math.round(party.probability_below_threshold * 100);
  const thr = party.threshold_percent.toFixed(0);
  const inner = (
    <>
      <p className="text-sm font-medium text-ink">{party.party_name}</p>
      {subtitle && <p className="text-xs text-ink/50">{subtitle}</p>}
      <p className="mt-2 font-display text-3xl tabular-nums text-accent">
        {pct} %
      </p>
      <p className="mt-1 text-sm text-ink/70">
        Wahrscheinlichkeit unter der {thr}-%-Hürde
      </p>
      <p className="mt-2 text-xs text-ink/45">
        Mittel {party.average_share.toFixed(1)} % · Band um {thr} %
      </p>
    </>
  );
  const className =
    "block rounded-2xl border border-accent/25 bg-accent/5 px-4 py-4 transition hover:border-accent/50";
  if (href) {
    return (
      <Link href={href} className={className}>
        {inner}
      </Link>
    );
  }
  return <div className={className}>{inner}</div>;
}

export function ThresholdWatch({ parliamentId }: { parliamentId: string }) {
  const [parties, setParties] = useState<ThresholdWatchParty[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    void fetchThresholdWatch(parliamentId)
      .then((d) => {
        if (!cancelled) setParties(d.parties);
      })
      .catch(() => {
        if (!cancelled) setParties([]);
      });
    return () => {
      cancelled = true;
    };
  }, [parliamentId]);

  if (!parties || parties.length === 0) return null;

  return (
    <section className="space-y-3">
      <h2 className="font-display text-2xl text-ink">Sperrklausel-Wächter</h2>
      <p className="text-sm text-ink/55">
        Parteien im 3-Punkte-Band um die gesetzliche Hürde — Monte-Carlo, keine
        Prognose.
      </p>
      <div className="grid gap-3 sm:grid-cols-2">
        {parties.map((p) => (
          <TileCard key={p.party_id} party={p} />
        ))}
      </div>
    </section>
  );
}

export function ThresholdWatchOverview() {
  const [data, setData] = useState<ThresholdWatchOverviewResponse | null>(null);

  useEffect(() => {
    let cancelled = false;
    void fetchThresholdWatchOverview()
      .then((d) => {
        if (!cancelled) setData(d);
      })
      .catch(() => {
        if (!cancelled) setData({ band_points: 3, items: [] });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (!data || data.items.length === 0) return null;

  return (
    <section className="space-y-4">
      <h2 className="font-display text-2xl text-ink">Sperrklausel-Wächter</h2>
      <p className="max-w-2xl text-sm text-ink/55">
        Wo die Hürde am unsichersten ist — Parteien nahe der Schwelle, sortiert
        nach Unentschiedenheit der Simulation.
      </p>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {data.items.map((item) => (
          <TileCard
            key={`${item.parliament_id}:${item.party_id}`}
            party={item}
            href={parliamentHref(item.parliament_id)}
            subtitle={item.parliament_name}
          />
        ))}
      </div>
    </section>
  );
}
