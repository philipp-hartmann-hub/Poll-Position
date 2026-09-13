/** Client-Spiegel von analysis.bundesrat.choices_from_party_stance. */

export function expandPartyIds(parties: string[]): Set<string> {
  const out = new Set(parties);
  if (out.has("de:cdu_csu") || (out.has("de:cdu") && out.has("de:csu"))) {
    out.add("de:cdu");
    out.add("de:csu");
    out.add("de:cdu_csu");
  }
  return out;
}

function stanceForParty(
  partyId: string,
  partyStance: Record<string, "yes" | "no">,
): "yes" | "no" | null {
  const direct = partyStance[partyId];
  if (direct === "yes" || direct === "no") return direct;

  const partyIds = expandPartyIds([partyId]);
  const found = new Set<"yes" | "no">();
  for (const [key, val] of Object.entries(partyStance)) {
    if (val !== "yes" && val !== "no") continue;
    const keyExp = expandPartyIds([key]);
    for (const id of partyIds) {
      if (keyExp.has(id)) {
        found.add(val);
        break;
      }
    }
  }
  if (found.size === 1) return [...found][0]!;
  return null;
}

export function choicesFromPartyStance(
  laender: { parliament_id: string; default_government: string[] }[],
  partyStance: Record<string, "yes" | "no">,
): Record<string, string> {
  const out: Record<string, string> = {};
  for (const land of laender) {
    const gov = land.default_government;
    if (!gov.length) {
      out[land.parliament_id] = "abstain";
      continue;
    }
    const stances = gov.map((p) => stanceForParty(p, partyStance));
    if (stances.every((s) => s === "yes")) {
      out[land.parliament_id] = "default";
    } else if (stances.every((s) => s === "no")) {
      out[land.parliament_id] = "reject";
    } else {
      out[land.parliament_id] = "abstain";
    }
  }
  return out;
}

export function mergeLandOverrides(
  auto: Record<string, string>,
  overrides: Record<string, string>,
): Record<string, string> {
  const out = { ...auto };
  for (const [pid, value] of Object.entries(overrides)) {
    if (value && value !== "auto") {
      out[pid] = value;
    }
  }
  return out;
}
