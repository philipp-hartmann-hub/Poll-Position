/** Farben für Ja / Nein / Enthaltung in Bundesrat-UI und -Karte. */
export const YES_COLOR = "#2f6f4e";
export const NO_COLOR = "#a33b2c";
export const ABSTAIN_COLOR = "#8a8f98";

export function stanceFill(stance: string): string {
  if (stance === "yes") return YES_COLOR;
  if (stance === "no") return NO_COLOR;
  if (stance === "abstain") return ABSTAIN_COLOR;
  return "#c5c0b6";
}

export function stanceLabel(stance: string): string {
  if (stance === "yes") return "Ja";
  if (stance === "no") return "Nein";
  if (stance === "abstain") return "Enthaltung";
  return stance;
}
