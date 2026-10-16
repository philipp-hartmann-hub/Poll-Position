import { labelPartyId, partyColor } from "@/lib/colors";
import { PARTY_SWATCH_CLASS } from "@/lib/theme";

const DOT_SIZE = {
  sm: "h-2.5 w-2.5",
  md: "h-3 w-3",
} as const;

export function PartyLabel({
  partyId,
  size = "sm",
  showName = true,
  className = "",
}: {
  /** Kanonische ID oder bekannter Anzeigename (über labelPartyId/partyColor). */
  partyId: string;
  size?: "sm" | "md";
  showName?: boolean;
  className?: string;
}) {
  const name = labelPartyId(partyId);
  const color = partyColor(partyId);

  return (
    <span
      className={`inline-flex min-w-0 items-center gap-1.5 ${className}`.trim()}
    >
      <span
        className={`${PARTY_SWATCH_CLASS} ${DOT_SIZE[size]}`}
        style={{ background: color }}
        aria-hidden
      />
      {showName ? (
        <span className="min-w-0 truncate">{name}</span>
      ) : (
        <span className="sr-only">{name}</span>
      )}
    </span>
  );
}
