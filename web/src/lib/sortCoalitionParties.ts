import { labelPartyId } from "@/lib/colors";

/** Metrik zu partyId oder Anzeigename (seats_by_name / mean_seats / averages). */
export function lookupPartyMetric(
  partyId: string,
  map: Record<string, number> | undefined | null,
): number {
  if (!map) return 0;
  if (Object.prototype.hasOwnProperty.call(map, partyId)) {
    return Number(map[partyId]) || 0;
  }
  const label = labelPartyId(partyId);
  if (Object.prototype.hasOwnProperty.call(map, label)) {
    return Number(map[label]) || 0;
  }
  for (const [key, value] of Object.entries(map)) {
    if (labelPartyId(key) === label) return Number(value) || 0;
  }
  return 0;
}

/**
 * Einheitliche Koalitions-Reihenfolge: Sitze absteigend, bei Gleichstand/0
 * nach Umfrageanteil, sonst Name.
 */
export function sortCoalitionParties(
  partyIds: string[],
  opts?: {
    seatsByParty?: Record<string, number> | null;
    sharesByParty?: Record<string, number> | null;
  },
): string[] {
  return [...partyIds].sort((a, b) => {
    const seatsA = lookupPartyMetric(a, opts?.seatsByParty);
    const seatsB = lookupPartyMetric(b, opts?.seatsByParty);
    if (seatsA !== seatsB) return seatsB - seatsA;
    const shareA = lookupPartyMetric(a, opts?.sharesByParty);
    const shareB = lookupPartyMetric(b, opts?.sharesByParty);
    if (shareA !== shareB) return shareB - shareA;
    return labelPartyId(a).localeCompare(labelPartyId(b), "de");
  });
}

/** Gleiche Parteienmenge unabhängig von Reihenfolge/ID-Form. */
export function sameCoalitionParties(a: string[], b: string[]): boolean {
  if (a.length !== b.length) return false;
  const setA = new Set(a.map(labelPartyId));
  if (setA.size !== b.length) return false;
  return b.every((id) => setA.has(labelPartyId(id)));
}
