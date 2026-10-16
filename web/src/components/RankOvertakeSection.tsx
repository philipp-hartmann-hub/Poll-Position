"use client";

import { useEffect, useMemo, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import {
  fetchRankOvertake,
  type RankOvertakePair,
} from "@/lib/api";
import { InfoTooltip } from "@/components/InfoTooltip";
import { partyColor } from "@/lib/colors";
import { PARTY_SWATCH_CLASS } from "@/lib/theme";
import { TIP_RANK_OVERTAKE } from "@/lib/tooltipCopy";

const VISIBLE_MIN_PROB = 0.02;
const OPEN_DUEL_MIN = 0.2;

function formatPp(value: number): string {
  return value.toLocaleString("de-DE", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  });
}

function formatPct(prob: number): string {
  return Math.round(prob * 100).toLocaleString("de-DE");
}

function PairRow({
  pair,
  nSimulations,
  expanded,
  onToggle,
}: {
  pair: RankOvertakePair;
  nSimulations: number;
  expanded: boolean;
  onToggle: () => void;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const pct = Math.round(pair.overtake_probability * 100);
  const stayPct = 100 - pct;
  const higherColor = partyColor(pair.higher_party_name);
  const lowerColor = partyColor(pair.lower_party_name);
  const isOpen = pair.overtake_probability >= OPEN_DUEL_MIN;
  const nOvertake = Math.round(pair.overtake_probability * nSimulations);
  const panelId = `overtake-detail-${pair.higher_party_id}-${pair.lower_party_id}`;

  function openScenario() {
    const next = new URLSearchParams(searchParams.toString());
    next.set("tab", "koalitionspruefer");
    next.set(
      "parties",
      [pair.higher_party_id, pair.lower_party_id].sort().join(","),
    );
    const qs = next.toString();
    router.push(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
  }

  return (
    <li className="rounded-lg border border-ink/10 bg-mist/30">
      <button
        type="button"
        className="flex w-full flex-col gap-2 px-3 py-2.5 text-left transition hover:bg-mist/50"
        aria-expanded={expanded}
        aria-controls={panelId}
        onClick={onToggle}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onToggle();
          }
        }}
      >
        <div className="flex flex-wrap items-center gap-x-1.5 gap-y-1 text-sm">
          <span
            className={`${PARTY_SWATCH_CLASS} h-2.5 w-2.5 shrink-0`}
            style={{ background: higherColor }}
            aria-hidden
          />
          <span className="font-medium text-ink">{pair.higher_party_name}</span>
          <span className="text-ink/45">vor</span>
          <span
            className={`${PARTY_SWATCH_CLASS} h-2.5 w-2.5 shrink-0`}
            style={{ background: lowerColor }}
            aria-hidden
          />
          <span className="font-medium text-ink">{pair.lower_party_name}</span>
          {isOpen ? (
            <span className="rounded bg-accent/15 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-accent">
              offen
            </span>
          ) : null}
          <span className="ml-auto tabular-nums font-medium text-ink/80">
            +{formatPp(pair.gap_points)}&nbsp;Pp
          </span>
        </div>

        <div className="flex items-center gap-2">
          <div
            className="h-2 min-w-0 flex-1 overflow-hidden rounded-full bg-ink/10"
            role="img"
            aria-label={`${formatPct(pair.overtake_probability)} Prozent Wahrscheinlichkeit für Platztausch`}
          >
            <div className="flex h-full w-full">
              <div
                className="h-full"
                style={{ width: `${stayPct}%`, background: higherColor }}
              />
              <div
                className="h-full"
                style={{ width: `${pct}%`, background: lowerColor }}
              />
            </div>
          </div>
          <span className="shrink-0 text-sm font-semibold tabular-nums text-ink">
            {formatPct(pair.overtake_probability)}&nbsp;%
          </span>
        </div>
      </button>

      {expanded ? (
        <div
          id={panelId}
          className="space-y-2 border-t border-ink/10 px-3 py-2.5 text-sm text-ink/70"
        >
          {/* TODO: 80%-Intervalle aus Monte-Carlo, sobald API higher/lower_ci liefert */}
          <p>
            In {nOvertake.toLocaleString("de-DE")} von{" "}
            {nSimulations.toLocaleString("de-DE")} simulierten Umfragen liegt{" "}
            {pair.lower_party_name} vor {pair.higher_party_name}.
          </p>
          <p className="text-xs text-ink/45">
            Mittelwerte: {pair.higher_party_name}{" "}
            {formatPp(pair.higher_share)}&nbsp;% · {pair.lower_party_name}{" "}
            {formatPp(pair.lower_share)}&nbsp;%
          </p>
          <button
            type="button"
            className="text-xs font-medium text-sea underline-offset-2 hover:underline"
            onClick={(e) => {
              e.stopPropagation();
              openScenario();
            }}
          >
            Im Szenario durchspielen
          </button>
        </div>
      ) : null}
    </li>
  );
}

export function RankOvertakeSection({
  parliamentId,
}: {
  parliamentId: string;
}) {
  const [pairs, setPairs] = useState<RankOvertakePair[] | null>(null);
  const [nSimulations, setNSimulations] = useState(400);
  const [error, setError] = useState<string | null>(null);
  const [showAll, setShowAll] = useState(false);
  const [expandedKey, setExpandedKey] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setPairs(null);
    setError(null);
    setShowAll(false);
    setExpandedKey(null);
    void fetchRankOvertake(parliamentId)
      .then((res) => {
        if (cancelled) return;
        setPairs(res.pairs);
        setNSimulations(res.n_simulations || 400);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "Fehler");
      });
    return () => {
      cancelled = true;
    };
  }, [parliamentId]);

  const { notable, rest } = useMemo(() => {
    const list = (pairs ?? [])
      .filter(
        (p) =>
          !/sonstige/i.test(p.higher_party_name) &&
          !/sonstige/i.test(p.lower_party_name) &&
          !/sonstige/i.test(p.higher_party_id) &&
          !/sonstige/i.test(p.lower_party_id),
      )
      .slice()
      .sort((a, b) => b.overtake_probability - a.overtake_probability);
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
      <p className="mb-3 mt-0.5 text-xs text-ink/55">
        Wie wahrscheinlich ist ein Platztausch?
      </p>
      {visible.length > 0 ? (
        <ul className="space-y-2">
          {visible.map((p) => {
            const key = `${p.higher_party_id}|${p.lower_party_id}`;
            return (
              <PairRow
                key={key}
                pair={p}
                nSimulations={nSimulations}
                expanded={expandedKey === key}
                onToggle={() =>
                  setExpandedKey((cur) => (cur === key ? null : key))
                }
              />
            );
          })}
        </ul>
      ) : (
        <p className="text-sm text-ink/50">
          Keine knappen Nachbarpaare (≥{Math.round(VISIBLE_MIN_PROB * 100)}
          &nbsp;% Überhol-Chance).
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
