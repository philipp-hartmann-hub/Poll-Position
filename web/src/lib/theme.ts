/** UI-Chrome-Farben (nicht Partei-/Fraktionsfarben). Spiegel von tailwind.config.js */

export const INK = "#e8eaed";
export const PAPER = "#17191d";
export const MIST = "#23262b";
export const ACCENT = "#d77842";
export const SEA = "#26d997";

/** „Keine Daten“ / unbekannter Stance auf Karten (Dark-Chrome). */
export const NEUTRAL_MUTED = "#565b64";

/**
 * Kategorialpalette für dunklen Grund (heller/gesättigter).
 * OKLab-ΔE ≳ 10 vs. PARTY_COLORS und paarweise (siehe web/scripts/check-dark-palette.mjs).
 */
export const CATEGORICAL_COLORS = [
  "#fa90f8",
  "#5beb8e",
  "#f87582",
  "#a195f7",
  "#a3c003",
  "#28bdad",
  "#22e7e2",
  "#d487c1",
  "#ccd373",
  "#FAB1A0",
] as const;

/** Tailwind-Klassen für Partei-Farbpunkte: immer mit Ring + Name daneben. */
export const PARTY_SWATCH_CLASS =
  "inline-block shrink-0 rounded-full ring-1 ring-ink/30";
