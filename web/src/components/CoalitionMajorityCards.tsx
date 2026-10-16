"use client";

import { CoalitionLabel } from "@/components/CoalitionLabel";
import { partyColor } from "@/lib/colors";
import {
  lookupPartyMetric,
  sortCoalitionParties,
} from "@/lib/sortCoalitionParties";
import type { Coalition } from "@/lib/api";

export function CoalitionMajorityCards({
  coalitions,
  totalSeats,
  majorityThreshold,
  seatsByParty,
  sharesByParty,
  onHighlight,
  maxCards = 20,
}: {
  coalitions: Coalition[];
  totalSeats: number;
  majorityThreshold: number;
  seatsByParty: Record<string, number>;
  sharesByParty?: Record<string, number> | null;
  onHighlight: (partyLabels: string[] | null) => void;
  maxCards?: number;
}) {
  const total = Math.max(totalSeats, 1);
  const list = coalitions
    .filter(
      (c) =>
        !c.parties.some((p) => /sonstige$|:others$|:other$/i.test(p)),
    )
    .slice(0, maxCards);

  if (list.length === 0) {
    return (
      <p className="text-sm text-ink/50">Keine Mehrheitskoalition.</p>
    );
  }

  const thrPct = (majorityThreshold / total) * 100;

  return (
    <ul className="space-y-2">
      {list.map((c, i) => {
        const ordered = sortCoalitionParties(c.parties, {
          seatsByParty,
          sharesByParty,
        });
        const margin = c.seats - majorityThreshold;
        const marginLabel =
          margin >= 0
            ? `+${margin} über Mehrheit`
            : `fehlen ${Math.abs(margin)}`;

        return (
          <li key={`${ordered.join("|")}-${i}`}>
            <button
              type="button"
              className="w-full rounded-lg border border-ink/10 bg-mist/40 px-3 py-2.5 text-left transition hover:bg-mist/55 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink/40"
              onMouseEnter={() => onHighlight(ordered.map((id) => id))}
              onMouseLeave={() => onHighlight(null)}
              onFocus={() => onHighlight(ordered.map((id) => id))}
              onBlur={() => onHighlight(null)}
            >
              <div className="flex items-start justify-between gap-3">
                <CoalitionLabel
                  partyIds={ordered}
                  seatsByParty={seatsByParty}
                  sharesByParty={sharesByParty}
                  className="min-w-0 text-sm font-medium text-ink"
                />
                <span className="shrink-0 font-sans text-sm tabular-nums text-ink">
                  {c.seats} Sitze
                </span>
              </div>

              <div className="relative mt-2">
                <div
                  className="flex h-2 overflow-hidden rounded-full bg-ink/10"
                  role="img"
                  aria-label={`${c.seats} von ${total} Sitzen, Mehrheit ab ${majorityThreshold}`}
                >
                  {ordered.map((id) => {
                    const seats = lookupPartyMetric(id, seatsByParty);
                    if (seats <= 0) return null;
                    return (
                      <div
                        key={id}
                        className="h-full"
                        style={{
                          width: `${(seats / total) * 100}%`,
                          background: partyColor(id),
                        }}
                      />
                    );
                  })}
                </div>
                <div
                  className="pointer-events-none absolute inset-y-0 w-px bg-ink/80"
                  style={{ left: `${thrPct}%` }}
                  aria-hidden
                />
              </div>

              <div className="mt-1.5 flex flex-wrap items-baseline gap-x-2 gap-y-0.5 text-xs text-ink/55">
                <span className="font-sans tabular-nums">{majorityThreshold}</span>
                <span>{marginLabel}</span>
              </div>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
