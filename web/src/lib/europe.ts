export type ApproximationKind = "national" | "district" | "mixed" | "majority";

export type EuropeCountryMeta = {
  iso: string;
  name: string;
  parliamentId: string;
  href: string;
  approximation: ApproximationKind;
  badge: string;
};

export const EUROPE_COUNTRIES: Record<string, EuropeCountryMeta> = {
  de: {
    iso: "DE",
    name: "Deutschland",
    parliamentId: "de_bundestag",
    href: "/parlament/de_bundestag",
    approximation: "national",
    badge: "",
  },
  at: {
    iso: "AT",
    name: "Österreich",
    parliamentId: "at_nationalrat",
    href: "/europa/at",
    approximation: "national",
    badge:
      "Nationale Näherung: 183 Sitze, 4 %-Hürde, d’Hondt. Das echte Verfahren hat drei Ermittlungsstufen (Regional/Land/Bund).",
  },
  nl: {
    iso: "NL",
    name: "Niederlande",
    parliamentId: "nl_tweede_kamer",
    href: "/europa/nl",
    approximation: "national",
    badge:
      "Nationale Näherung: 150 Sitze, d’Hondt, de-facto-Hürde der Kiesdeler (~0,67 %). Keine regionalen Wahlkreise.",
  },
  se: {
    iso: "SE",
    name: "Schweden",
    parliamentId: "se_riksdag",
    href: "/europa/se",
    approximation: "national",
    badge:
      "Nationale Näherung: 349 Sitze, 4 %-Hürde, Sainte-Laguë. Amtlich gilt die jämkade uddatalsmetod (erster Divisor 1,4) plus Ausgleichsmandate.",
  },
  it: {
    iso: "IT",
    name: "Italien",
    parliamentId: "it_camera",
    href: "/europa/it",
    approximation: "mixed",
    badge:
      "Nationale Verhältniswahl-Näherung — Italien wählt gemischt (Rosatellum), keine Wahlkreis-Ebene.",
  },
  es: {
    iso: "ES",
    name: "Spanien",
    parliamentId: "es_congreso",
    href: "/europa/es",
    approximation: "district",
    badge: "Nationale Näherung, keine Wahlkreis-Ebene.",
  },
  pl: {
    iso: "PL",
    name: "Polen",
    parliamentId: "pl_sejm",
    href: "/europa/pl",
    approximation: "district",
    badge: "Nationale Näherung, keine Wahlkreis-Ebene.",
  },
  pt: {
    iso: "PT",
    name: "Portugal",
    parliamentId: "pt_assembleia",
    href: "/europa/pt",
    approximation: "district",
    badge: "Nationale Näherung, keine Wahlkreis-Ebene.",
  },
  fr: {
    iso: "FR",
    name: "Frankreich",
    parliamentId: "fr_assemblee",
    href: "/europa/fr",
    approximation: "majority",
    badge:
      "Keine Sitzprojektion: die Assemblée nationale wird in 577 Wahlkreisen per Mehrheitswahl mit Stichwahl gewählt — nationale Umfragewerte lassen sich nicht seriös in Sitze umrechnen.",
  },
};

export function europeHref(iso: string): string {
  const meta = EUROPE_COUNTRIES[iso.toLowerCase()];
  return meta?.href ?? `/europa/${iso.toLowerCase()}`;
}
