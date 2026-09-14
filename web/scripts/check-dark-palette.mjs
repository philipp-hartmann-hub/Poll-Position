/**
 * Wegwerf-Skript: OKLab-ΔE (×100) und WCAG-Kontrast für Dark-Theme vs. PARTY_COLORS.
 * Ausführen: node web/scripts/check-dark-palette.mjs
 */

const PARTY_COLORS = {
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

const THEME = {
  ink: "#e8eaed",
  paper: "#17191d",
  mist: "#23262b",
  accent: "#d77842",
  sea: "#26d997",
  neutralMuted: "#565b64",
};

/** Hellere Kategorialpalette für dunklen Grund (theme.ts CATEGORICAL_COLORS). */
const CATEGORICAL = [
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
];

function hexToRgb(hex) {
  const h = hex.replace("#", "");
  const n = parseInt(h.length === 3 ? h.split("").map((c) => c + c).join("") : h, 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

function srgbToLinear(c) {
  const x = c / 255;
  return x <= 0.04045 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4);
}

function rgbToOklab([r, g, b]) {
  const R = srgbToLinear(r);
  const G = srgbToLinear(g);
  const B = srgbToLinear(b);
  const l = 0.4122214708 * R + 0.5363325363 * G + 0.0514459929 * B;
  const m = 0.2119034982 * R + 0.6806995451 * G + 0.1073969566 * B;
  const s = 0.0883024619 * R + 0.2817188376 * G + 0.6299787005 * B;
  const l_ = Math.cbrt(l);
  const m_ = Math.cbrt(m);
  const s_ = Math.cbrt(s);
  return [
    0.2104542553 * l_ + 0.793617785 * m_ - 0.0040720468 * s_,
    1.9779984951 * l_ - 2.428592205 * m_ + 0.4505937099 * s_,
    0.0259040371 * l_ + 0.7827717662 * m_ - 0.808675766 * s_,
  ];
}

function deltaE(hexA, hexB) {
  const a = rgbToOklab(hexToRgb(hexA));
  const b = rgbToOklab(hexToRgb(hexB));
  const d = Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]);
  return d * 100;
}

function relativeLuminance(hex) {
  const [r, g, b] = hexToRgb(hex).map(srgbToLinear);
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrastRatio(fg, bg) {
  const L1 = relativeLuminance(fg);
  const L2 = relativeLuminance(bg);
  const hi = Math.max(L1, L2);
  const lo = Math.min(L1, L2);
  return (hi + 0.05) / (lo + 0.05);
}

const partyEntries = Object.entries(PARTY_COLORS);
const blues = ["AfD", "CSU", "SSW"];

console.log("=== Theme vs PARTY_COLORS (min ΔE) ===");
const themeWorst = [];
for (const [name, hex] of Object.entries(THEME)) {
  let worst = { de: Infinity, party: "", partyHex: "" };
  for (const [pname, phex] of partyEntries) {
    const de = deltaE(hex, phex);
    if (de < worst.de) worst = { de, party: pname, partyHex: phex };
  }
  themeWorst.push({ name, hex, ...worst });
  const blueHits = blues.map((b) => ({
    b,
    de: deltaE(hex, PARTY_COLORS[b]).toFixed(2),
  }));
  console.log(
    `${name} ${hex}: min ΔE=${worst.de.toFixed(2)} vs ${worst.party} ${worst.partyHex}; blues: ${blueHits.map((x) => `${x.b}=${x.de}`).join(", ")}`,
  );
}

console.log("\n=== WCAG contrast (need ≥ 4.5:1 for text) ===");
const pairs = [
  ["ink", "paper"],
  ["ink", "mist"],
  ["accent", "paper"],
  ["accent", "mist"],
  ["sea", "paper"],
  ["sea", "mist"],
];
for (const [fg, bg] of pairs) {
  const r = contrastRatio(THEME[fg], THEME[bg]);
  console.log(`${fg} on ${bg}: ${r.toFixed(2)}:1 ${r >= 4.5 ? "OK" : "FAIL"}`);
}

console.log("\n=== Categorical vs PARTY_COLORS + pairwise ===");
let catWorstParty = { de: Infinity, a: "", b: "" };
for (const c of CATEGORICAL) {
  for (const [pname, phex] of partyEntries) {
    const de = deltaE(c, phex);
    if (de < catWorstParty.de) catWorstParty = { de, a: c, b: `${pname} ${phex}` };
  }
}
let catWorstPair = { de: Infinity, a: "", b: "" };
for (let i = 0; i < CATEGORICAL.length; i++) {
  for (let j = i + 1; j < CATEGORICAL.length; j++) {
    const de = deltaE(CATEGORICAL[i], CATEGORICAL[j]);
    if (de < catWorstPair.de)
      catWorstPair = { de, a: CATEGORICAL[i], b: CATEGORICAL[j] };
  }
}
console.log(
  `categorical min vs party: ΔE=${catWorstParty.de.toFixed(2)} (${catWorstParty.a} vs ${catWorstParty.b})`,
);
console.log(
  `categorical min pairwise: ΔE=${catWorstPair.de.toFixed(2)} (${catWorstPair.a} vs ${catWorstPair.b})`,
);

const allWorst = [...themeWorst].sort((a, b) => a.de - b.de);
console.log("\n=== Worst theme ΔE (lowest first) ===");
for (const w of allWorst) {
  console.log(`  ${w.name}: ${w.de.toFixed(2)} vs ${w.party}`);
}
