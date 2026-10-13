"use client";

import { useEffect, useMemo, useState } from "react";
import {
  fetchRankOvertake,
  type RankOvertakePair,
} from "@/lib/api";
import { InfoTooltip } from "@/components/InfoTooltip";
import { TIP_RANK_OVERTAKE } from "@/lib/tooltipCopy";

const VISIBLE_MIN_PROB = 0.02;

function formatPp(value: number): string {
  return value.toLocaleString("de-DE", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  });
}

function formatPct(prob: number): string {
  return Math.round(prob * 100).toLocaleString("de-DE");
}

function PairLine({ pair }: { pair: RankOvertakePair }) {
  return (
    <li className="text-sm text-ink/80">
      <span className="font-medium text-ink">{pair.higher_party_name}</span>
      {" vor "}
      <span className="font-medium text-ink">{pair.lower_party_name}</span>
      <span className="text-ink/50">
        {" "}
        (+{formatPp(pair.gap_points)} Pp)
      </span>
      {" · "}
      <span className="tabular-nums">
        {formatPct(pair.overtake_probability)}&nbsp;%
      </span>{" "}
      Wahrscheinlichkeit, dass sich das dreht
    </li>
  );
}

export function RankOvertakeSection({
  parliamentId,
}: {
  parliamentId: string;
}) {
  const [pairs, setPairs] = useState<RankOvertakePair[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showAll, setShowAll] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setPairs(null);
    setError(null);
    setShowAll(false);
    void fetchRankOvertake(parliamentId)
      .then((res) => {
        if (!cancelled) setPairs(res.pairs);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "Fehler");
      });
    return () => {
      cancelled = true;
    };
  }, [parliamentId]);

  const { notable, rest } = useMemo(() => {
    const list = (pairs ?? []).filter(
      (p) =>
        !/sonstige/i.test(p.higher_party_name) &&
        !/sonstige/i.test(p.lower_party_name) &&
        !/sonstige/i.test(p.higher_party_id) &&
        !/sonstige/i.test(p.lower_party_id),
    );
    const notablePairs = list.filter(
      (p) => p.overtake_probability >= VISIBLE_MIN_PROB,
    );
    const restPairs = list.filter(
      (p) => p.overtake_probability < VISIBLE_MIN_PROB,
    );
    return { notable: notablePairs, rest: restPairs };
  }, [pairs]);

  if (error || pairs == null || pairs.length === 0) {
    return null;
  }

  const visible = showAll ? [...notable, ...rest] : notable;
  if (visible.length === 0 && rest.length === 0) {
    return null;
  }

  return (
    <div className="rounded-xl border border-ink/10 bg-mist/40 px-4 py-3">
      <h3 className="text-sm font-semibold text-ink">
        Knapp vorne?
        <InfoTooltip text={TIP_RANK_OVERTAKE} />
      </h3>
      <p className="mb-2 mt-0.5 text-xs text-ink/55">
        Wahrscheinlichkeit, dass die schwächere Nachbarpartei in einer
        gezogenen Umfrage-Variante überholt
      </p>
      {visible.length > 0 ? (
        <ul className="space-y-1.5">
          {visible.map((p) => (
            <PairLine
              key={`${p.higher_party_id}|${p.lower_party_id}`}
              pair={p}
            />
          ))}
        </ul>
      ) : (
        <p className="text-sm text-ink/50">
          Keine knappen Nachbarpaare (≥{Math.round(VISIBLE_MIN_PROB * 100)}&nbsp;%
          Überhol-Chance).
        </p>
      )}
      {rest.length > 0 ? (
        <button
          type="button"
          className="mt-2 text-xs font-medium text-ink/55 underline-offset-2 hover:text-ink hover:underline"
          onClick={() => setShowAll((v) => !v)}
        >
          {showAll
            ? "Knappste Paare anzeigen"
            : `${rest.length} weitere Paare mit <${Math.round(VISIBLE_MIN_PROB * 100)} % anzeigen`}
        </button>
      ) : null}
    </div>
  );
}
