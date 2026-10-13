import type { PartyAverage } from "@/lib/api";
import { labelPartyId } from "@/lib/colors";

/**
 * Setzt eine Partei auf ``targetShare`` und skaliert die übrigen Anteile so,
 * dass die Summe 100 bleibt (analog zu Uncertainty-Renormalisierung).
 */
export function buildThresholdScenarioShares(
  parties: PartyAverage[],
  targetPartyId: string,
  targetShare: number,
): Record<string, number> {
  const current = Object.fromEntries(
    parties.map((p) => [p.party_id, p.average_share]),
  );
  const oldShare = current[targetPartyId] ?? 0;
  const rest = 100 - oldShare;
  const newRest = 100 - targetShare;
  const scale = rest > 0 ? newRest / rest : 1;
  const out: Record<string, number> = {};
  for (const [pid, share] of Object.entries(current)) {
    out[pid] = pid === targetPartyId ? targetShare : share * scale;
  }
  return out;
}

/** Scenario-Sitze (party_id → Sitze) → Anzeigenamen-Map für Hemicycle / Panel. */
export function seatsByNameFromPartyIds(
  seats: Record<string, number>,
): Record<string, number> {
  const out: Record<string, number> = {};
  for (const [pid, n] of Object.entries(seats)) {
    if (n <= 0) continue;
    const name = labelPartyId(pid);
    if (/sonstige/i.test(name) || /sonstige/i.test(pid)) continue;
    out[name] = (out[name] ?? 0) + n;
  }
  return out;
}
