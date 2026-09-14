import type { ExclusionUiState } from "@/components/CoalitionPanel";

const APPLY_KEY = "apply_exclusions";
const DISABLED_KEY = "disabled_rules";

export const DEFAULT_EXCLUSION_UI: ExclusionUiState = {
  applyExclusions: true,
  disabledRuleIds: [],
};

/** Liest Ausschluss-Toggles aus Query-Parametern (Default: Regeln an, keine aus). */
export function exclusionFromSearchParams(
  params: URLSearchParams | { get: (key: string) => string | null },
): ExclusionUiState {
  const applyRaw = params.get(APPLY_KEY);
  const applyExclusions =
    applyRaw == null ? true : applyRaw !== "false" && applyRaw !== "0";

  const disabledRaw = params.get(DISABLED_KEY) ?? "";
  const disabledRuleIds = disabledRaw
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);

  return { applyExclusions, disabledRuleIds };
}

/** Schreibt Ausschluss-Toggles; Default-Zustand entfernt die Parameter. */
export function searchParamsWithExclusion(
  current: URLSearchParams,
  state: ExclusionUiState,
): URLSearchParams {
  const next = new URLSearchParams(current.toString());
  next.delete(APPLY_KEY);
  next.delete(DISABLED_KEY);

  if (!state.applyExclusions) {
    next.set(APPLY_KEY, "false");
  }
  if (state.disabledRuleIds.length > 0) {
    next.set(DISABLED_KEY, [...state.disabledRuleIds].sort().join(","));
  }
  return next;
}

export function exclusionStatesEqual(
  a: ExclusionUiState,
  b: ExclusionUiState,
): boolean {
  if (a.applyExclusions !== b.applyExclusions) return false;
  if (a.disabledRuleIds.length !== b.disabledRuleIds.length) return false;
  const as = [...a.disabledRuleIds].sort().join("\0");
  const bs = [...b.disabledRuleIds].sort().join("\0");
  return as === bs;
}
