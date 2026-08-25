/**
 * Produkt-Feature-Flags (Web).
 *
 * Europa ist vorerst aus — Code und Routen bleiben erhalten.
 * Wieder aktivieren:
 *   1) NEXT_PUBLIC_ENABLE_EUROPE=true  (z. B. in Vercel / .env.local), oder
 *   2) `europe: true` unten als Default setzen.
 */
export const features = {
  europe: process.env.NEXT_PUBLIC_ENABLE_EUROPE === "true",
} as const;
