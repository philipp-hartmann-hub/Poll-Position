import { labelPartyId, partyColor } from "@/lib/colors";
import {
  sortCoalitionParties,
} from "@/lib/sortCoalitionParties";
import { MIST } from "@/lib/theme";

const DOT_PX = {
  sm: 10,
  md: 12,
} as const;

export function CoalitionLabel({
  partyIds,
  size = "sm",
  seatsByParty,
  sharesByParty,
  className = "",
}: {
  partyIds: string[];
  size?: "sm" | "md";
  seatsByParty?: Record<string, number> | null;
  sharesByParty?: Record<string, number> | null;
  className?: string;
}) {
  const ordered = sortCoalitionParties(partyIds, { seatsByParty, sharesByParty });
  const names = ordered.map(labelPartyId);
  const full = names.join(" + ");
  const px = DOT_PX[size];
  const overlap = Math.round(px * 0.25);

  return (
    <span
      className={`inline-flex min-w-0 max-w-full items-center gap-1.5 ${className}`.trim()}
      role="group"
      aria-label={full}
    >
      <span className="inline-flex shrink-0 items-center" aria-hidden>
        {ordered.map((id, i) => (
          <span
            key={`${id}-${i}`}
            className="inline-block shrink-0 rounded-full"
            style={{
              width: px,
              height: px,
              background: partyColor(id),
              boxShadow: `0 0 0 2px ${MIST}`,
              marginLeft: i === 0 ? 0 : -overlap,
            }}
          />
        ))}
      </span>
      <span className="min-w-0 truncate" aria-hidden>
        {full}
      </span>
    </span>
  );
}
