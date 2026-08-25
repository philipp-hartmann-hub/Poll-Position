/**
 * Links-Rechts-Heuristik aus data_pipeline/config/coalition_rules.yaml
 * (party_positions.left_right). Für Hemicycle-Sortierung links→rechts.
 * Unbekannte Parteien: +Infinity (ans rechte Ende).
 */
import { labelPartyId } from "@/lib/colors";

const BY_ID: Record<string, number> = {
  "de:linke": 1.0,
  "de:bsw": 2.5,
  "de:gruene": 3.0,
  "de:spd": 3.5,
  "de:ssw": 4.0,
  "de:sonstige": 5.0,
  "de:fdp": 6.0,
  "de:cdu": 6.5,
  "de:cdu_csu": 6.7,
  "de:csu": 7.0,
  "de:fw": 7.2,
  "de:afd": 9.5,
  "at:spo": 3.5,
  "at:grune": 3.0,
  "at:neos": 5.5,
  "at:ovp": 6.5,
  "at:fpo": 9.0,
};

const BY_NAME: Record<string, number> = {
  Linke: 1.0,
  BSW: 2.5,
  Grüne: 3.0,
  SPD: 3.5,
  SSW: 4.0,
  Sonstige: 5.0,
  FDP: 6.0,
  CDU: 6.5,
  "CDU/CSU": 6.7,
  CSU: 7.0,
  "Freie Wähler": 7.2,
  AfD: 9.5,
  SPÖ: 3.5,
  ÖVP: 6.5,
  FPÖ: 9.5,
  NEOS: 5.5,
};

export function leftRightPosition(partyKey: string): number {
  if (BY_ID[partyKey] != null) return BY_ID[partyKey];
  if (BY_NAME[partyKey] != null) return BY_NAME[partyKey];
  const labeled = labelPartyId(partyKey);
  if (labeled !== partyKey && BY_NAME[labeled] != null) return BY_NAME[labeled];
  const lower = partyKey.toLowerCase();
  for (const [id, v] of Object.entries(BY_ID)) {
    if (id.endsWith(`:${lower}`) || id.split(":")[1] === lower) return v;
  }
  return Number.POSITIVE_INFINITY;
}
