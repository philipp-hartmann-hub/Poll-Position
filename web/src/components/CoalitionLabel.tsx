import { labelPartyId, partyColor } from "@/lib/colors";
import { PARTY_SWATCH_CLASS } from "@/lib/theme";

const DOT_SIZE = {
  sm: "h-2.5 w-2.5",
  md: "h-3 w-3",
} as const;

export function CoalitionLabel({
  partyIds,
  size = "sm",
  compactOnNarrow = true,
  className = "",
}: {
  partyIds: string[];
  size?: "sm" | "md";
  /** Schmale Viewports: Punkte + Kurznamen ohne „ + “-Leerzeichen. */
  compactOnNarrow?: boolean;
  className?: string;
}) {
  const names = partyIds.map(labelPartyId);
  const full = names.join(" + ");
  const compact = names.join("+");
  const dot = DOT_SIZE[size];

  return (
    <span
      className={`inline-flex min-w-0 max-w-full items-center gap-1.5 ${className}`.trim()}
      role="group"
      aria-label={full}
    >
      <span className="inline-flex shrink-0 -space-x-1.5" aria-hidden>
        {partyIds.map((id) => (
          <span
            key={id}
            className={`${PARTY_SWATCH_CLASS} ${dot} ring-2 ring-paper`}
            style={{ background: partyColor(id) }}
          />
        ))}
      </span>
      {compactOnNarrow ? (
        <>
          <span className="hidden min-w-0 truncate sm:inline" aria-hidden>
            {full}
          </span>
          <span className="min-w-0 truncate sm:hidden" aria-hidden>
            {compact}
          </span>
        </>
      ) : (
        <span className="min-w-0 truncate" aria-hidden>
          {full}
        </span>
      )}
    </span>
  );
}
