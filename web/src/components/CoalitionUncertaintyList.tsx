"use client";

import { useMemo } from "react";
import { CoalitionLabel } from "@/components/CoalitionLabel";
import {
  sameCoalitionParties,
  sortCoalitionParties,
} from "@/lib/sortCoalitionParties";

export type UncertaintyCoalitionRow = {
  parties: string[];
  majority_probability: number;
  n_majority: number;
  n_simulations: number;
};

function formatMajorityPct(probability: number, nMajority: number): string {
  const pct = probability * 100;
  if (pct >= 1) return `${Math.round(pct)} %`;
  if (nMajority > 0) return "<1 %";
  return "0 %";
}

function barWidthPct(probability: number, nMajority: number): number {
  const pct = probability * 100;
  if (pct >= 1) return Math.min(100, Math.round(pct));
  if (nMajority > 0) return 0.5;
  return 0;
}

export function CoalitionUncertaintyList({
  rows,
  seatsByParty,
  sharesByParty,
  governmentParties,
  governmentProbability,
  maxRows = 10,
}: {
  rows: UncertaintyCoalitionRow[];
  seatsByParty?: Record<string, number> | null;
  sharesByParty?: Record<string, number> | null;
  governmentParties?: string[] | null;
  governmentProbability?: number | null;
  maxRows?: number;
}) {
  const displayRows = useMemo(() => {
    const gov = (governmentParties ?? []).filter(Boolean);
    const cleaned = rows.filter(
      (r) => !r.parties.some((p) => /sonstige$|:others$|:other$/i.test(p)),
    );

    let governmentRow: UncertaintyCoalitionRow | null = null;
    if (gov.length > 0) {
      const hit = cleaned.find((r) => sameCoalitionParties(r.parties, gov));
      if (hit) {
        governmentRow = hit;
      } else if (governmentProbability != null) {
        governmentRow = {
          parties: gov,
          majority_probability: governmentProbability,
          n_majority: governmentProbability > 0 ? 1 : 0,
          n_simulations: cleaned[0]?.n_simulations ?? 0,
        };
      }
    }

    const others = cleaned.filter(
      (r) =>
        !governmentRow ||
        !sameCoalitionParties(r.parties, governmentRow.parties),
    );
    const top = others.slice(0, maxRows);

    if (!governmentRow) return top;

    const alreadyInTop = top.some((r) =>
      sameCoalitionParties(r.parties, governmentRow.parties),
    );
    if (alreadyInTop) {
      return top.map((r) =>
        sameCoalitionParties(r.parties, governmentRow.parties)
          ? governmentRow
          : r,
      );
    }
    if (top.length >= maxRows) {
      return [...top.slice(0, maxRows - 1), governmentRow];
    }
    return [...top, governmentRow];
  }, [rows, governmentParties, governmentProbability, maxRows]);

  if (displayRows.length === 0) {
    return (
      <p className="text-sm text-ink/50">
        Keine Mehrheitskoalitionen bei diesem Umfragestand.
      </p>
    );
  }

  return (
    <ul className="space-y-2">
      {displayRows.map((c, i) => {
        const isGov =
          (governmentParties?.length ?? 0) > 0 &&
          sameCoalitionParties(c.parties, governmentParties ?? []);
        const ordered = sortCoalitionParties(c.parties, {
          seatsByParty,
          sharesByParty,
        });
        const label = formatMajorityPct(
          c.majority_probability,
          c.n_majority,
        );
        const width = barWidthPct(c.majority_probability, c.n_majority);
        const showLowGovNote = isGov && c.majority_probability < 0.1;

        return (
          <li
            key={`${ordered.join("|")}-${i}`}
            className={
              isGov
                ? "rounded-lg border border-amber-500/25 bg-amber-500/10 px-3 py-2.5"
                : "rounded-lg border border-ink/10 bg-mist/40 px-3 py-2.5"
            }
          >
            <div className="flex items-start justify-between gap-3">
              <span className="flex min-w-0 flex-wrap items-center gap-2">
                <CoalitionLabel
                  partyIds={ordered}
                  seatsByParty={seatsByParty}
                  sharesByParty={sharesByParty}
                />
                {isGov ? (
                  <span className="rounded bg-amber-500/10 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-ink/70 ring-1 ring-inset ring-amber-500/25">
                    Regierung
                  </span>
                ) : null}
                {c.parties.length === 1 ? (
                  <span className="rounded bg-ink/10 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-ink/60">
                    Alleinregierung
                  </span>
                ) : null}
              </span>
              <span className="shrink-0 font-sans text-sm font-semibold tabular-nums text-ink">
                {label}
              </span>
            </div>
            <div
              className="mt-2 h-2 overflow-hidden rounded-full bg-ink/10"
              role="img"
              aria-label={`${label} Wahrscheinlichkeit für Mehrheit`}
            >
              <div
                className="h-full rounded-full bg-ink"
                style={{ width: `${width}%` }}
              />
            </div>
            {showLowGovNote ? (
              <p className="mt-2 text-xs text-ink/45">
                Die amtierende Koalition hätte derzeit fast nie eine eigene
                Mehrheit.
              </p>
            ) : null}
          </li>
        );
      })}
    </ul>
  );
}
