export const PARTY_COLORS: Record<string, string> = {
  AfD: "#009EE0",
  "CDU/CSU": "#000000",
  CDU: "#000000",
  CSU: "#0080C8",
  SPD: "#E3000F",
  Grüne: "#64A12D",
  FDP: "#FFED00",
  Linke: "#BE3075",
  BSW: "#7B2D8E",
  "Freie Wähler": "#F7A800",
  Sonstige: "#A0A0A0",
  SSW: "#A0C8E0",
};

export const FAMILY_COLORS: Record<string, string> = {
  EPP: "#003399",
  "S&D": "#e60023",
  Renew: "#ffcc00",
  "Greens/EFA": "#64a12d",
  ECR: "#0050a0",
  ID: "#009ee0",
  Left: "#be3075",
  NI: "#8c8c8c",
};

export function partyColor(name: string): string {
  return PARTY_COLORS[name] ?? "#6b7280";
}

export function familyColor(family: string): string {
  return FAMILY_COLORS[family] ?? "#6b7280";
}

/** Lesbare Labels für kanonische / Dawum-IDs. */
export function labelPartyId(id: string): string {
  const map: Record<string, string> = {
    "de:afd": "AfD",
    "de:cdu_csu": "CDU/CSU",
    "de:cdu": "CDU",
    "de:csu": "CSU",
    "de:spd": "SPD",
    "de:gruene": "Grüne",
    "de:fdp": "FDP",
    "de:linke": "Linke",
    "de:bsw": "BSW",
    "de:fw": "Freie Wähler",
    "de:sonstige": "Sonstige",
    "dawum:party:1": "CDU/CSU",
    "dawum:party:2": "SPD",
    "dawum:party:3": "FDP",
    "dawum:party:4": "Grüne",
    "dawum:party:5": "Linke",
    "dawum:party:7": "AfD",
    "dawum:party:8": "Freie Wähler",
    "dawum:party:23": "BSW",
  };
  if (map[id]) return map[id];
  if (id.startsWith("dawum:party:")) return id;
  if (id.includes(":")) return id.split(":").pop()!.replace(/_/g, " ");
  return id;
}

/** Anzeigename: API-Name, sonst Label-Map — nie rohe dawum:party:N wenn bekannt. */
export function displayPartyName(
  partyId: string,
  partyName?: string | null,
): string {
  if (
    partyName &&
    partyName.trim() &&
    partyName !== partyId &&
    !partyName.startsWith("dawum:party:")
  ) {
    return partyName.trim();
  }
  return labelPartyId(partyId);
}
