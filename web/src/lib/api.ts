/** Typisierte API-Client-Funktionen für die FastAPI-Backend-Endpunkte. */

export type Parliament = {
  id: string;
  name: string;
  country: string;
  level_kind: string;
  state_code: string | null;
  seats_total: number | null;
  election_system_key: string | null;
  shortcut: string | null;
  next_election_date?: string | null;
  next_election_note?: string | null;
};

export type PartyAverage = {
  parliament_id: string;
  party_id: string;
  party_name: string;
  average_share: number;
  n_surveys: number;
  swing: number | null;
  trend_share: number | null;
};

export type AveragesResponse = {
  parliament_id: string;
  as_of: string;
  parties: PartyAverage[];
};

export type TrendSeriesResponse = {
  parliament_id: string;
  days: number;
  parties: {
    party_id: string;
    party_name: string;
    points: { as_of: string; trend_share: number }[];
  }[];
};

export type RawSurveysResponse = {
  parliament_id: string;
  total: number;
  limit: number;
  offset: number;
  surveys: {
    id: string;
    institute_id: string;
    institute_name: string | null;
    field_date_from: string | null;
    field_date_to: string | null;
    publication_date: string;
    sample_size: number | null;
    source_url: string | null;
    results: { party_id: string; party_name: string; share: number }[];
  }[];
};

export type SeatsResponse = {
  parliament_id: string;
  total_seats: number;
  seats: Record<string, number>;
  seats_by_name: Record<string, number>;
};

export type LastElectionResponse = {
  parliament_id: string;
  election_date: string;
  label: string;
  source: string | null;
  seats: Record<string, number>;
  seats_by_name: Record<string, number>;
  total_seats: number;
};

export type Coalition = {
  parties: string[];
  seats: number;
  is_minimal_winning: boolean;
  compatibility_span: number | null;
};

export type CoalitionsResponse = {
  parliament_id: string;
  total_seats: number;
  majority_threshold: number;
  excluded_by_rules: number;
  coalitions: Coalition[];
};

export type ExclusionRule = {
  id: string;
  party: string;
  excludes: string[];
  parties: [string, string] | string[];
  note: string | null;
};

export type CoalitionRulesResponse = {
  parliament_id: string;
  rules: ExclusionRule[];
};

export type UncertaintyResponse = {
  parliament_id: string;
  n_simulations: number;
  mean_seats: Record<string, number>;
  coalition_probabilities: {
    parties: string[];
    majority_probability: number;
    n_majority: number;
    n_simulations: number;
  }[];
};

export type ThresholdWatchParty = {
  party_id: string;
  party_name: string;
  average_share: number;
  threshold_percent: number;
  probability_below_threshold: number;
};

export type ThresholdWatchResponse = {
  parliament_id: string;
  threshold_percent: number;
  band_points: number;
  n_simulations: number;
  parties: ThresholdWatchParty[];
};

export type ThresholdWatchOverviewResponse = {
  band_points: number;
  items: (ThresholdWatchParty & {
    parliament_id: string;
    parliament_name: string | null;
    toss_up: number;
  })[];
};

export type PartyForecastParty = {
  party_id: string;
  party_name: string;
  average_share: number;
  threshold_percent: number;
  probability_strongest: number;
  probability_above_threshold: number;
};

export type PartyForecastResponse = {
  parliament_id: string;
  threshold_percent: number;
  n_simulations: number;
  parties: PartyForecastParty[];
};

export type HouseEffectsResponse = {
  parliament_id: string | null;
  effects: {
    institute_id: string;
    institute_name: string | null;
    party_id: string;
    party_name: string | null;
    as_of: string;
    house_effect: number;
    institute_share: number;
    peer_average: number;
  }[];
  accuracy: {
    institute_id: string;
    institute_name: string | null;
    parliament_id: string | null;
    n_comparisons: number;
    mae: number;
    rmse: number;
    score: number;
  }[];
};

export type InstituteLeaderboardResponse = {
  institutes: {
    rank: number;
    institute_id: string;
    institute_name: string | null;
    n_comparisons: number;
    mae: number;
    rmse: number;
    score: number;
    by_parliament: {
      institute_id: string;
      institute_name: string | null;
      parliament_id: string | null;
      n_comparisons: number;
      mae: number;
      rmse: number;
      score: number;
    }[];
  }[];
};

export type EuropeOverviewResponse = {
  as_of: string;
  countries: {
    country: string;
    top_party_name: string;
    top_party_share: number;
    top_family: string;
    family_share: number;
  }[];
};

export type ScenarioRequest = {
  parliament_id: string;
  party_shares: Record<string, number>;
  apply_exclusions?: boolean;
  disabled_rule_ids?: string[];
  max_coalition_parties?: number;
};

export type ScenarioResponse = {
  parliament_id: string;
  party_shares: Record<string, number>;
  seats: Record<string, number>;
  total_seats: number;
  majority_threshold: number;
  coalitions: Coalition[];
};

function apiBase(): string {
  const base = process.env.NEXT_PUBLIC_API_BASE?.trim();
  if (base) return base.replace(/\/$/, "");
  return "";
}

/** Next.js Data-Cache: 10 min — passend zur täglichen Pipeline. */
const REVALIDATE_SECONDS = 600;

type ApiFetchInit = RequestInit & {
  next?: { revalidate?: number | false };
  /** Erzwingt cache: "no-store" (Nutzerinteraktion / POST). */
  noStore?: boolean;
};

async function apiFetch<T>(path: string, init?: ApiFetchInit): Promise<T> {
  const url = `${apiBase()}${path}`;
  const { noStore, next: _next, cache: _cache, headers, ...rest } = init ?? {};
  const method = (rest.method ?? "GET").toUpperCase();
  const useNoStore = Boolean(noStore) || method !== "GET";

  const res = await fetch(url, {
    ...rest,
    headers: {
      Accept: "application/json",
      ...(rest.body ? { "Content-Type": "application/json" } : {}),
      ...headers,
    },
    ...(useNoStore
      ? { cache: "no-store" as const }
      : { next: { revalidate: REVALIDATE_SECONDS } }),
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status} ${path}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

/**
 * Zuerst Pipeline-Static unter /data/… (kein Cold-Start), bei 404 → FastAPI.
 * Nur für die täglich exportierten Default-Payloads.
 */
async function fetchStaticOrApi<T>(
  staticPath: string,
  apiPath: string,
  init?: ApiFetchInit,
): Promise<T> {
  try {
    const res = await fetch(staticPath, {
      headers: { Accept: "application/json" },
      next: { revalidate: REVALIDATE_SECONDS },
    });
    if (res.ok) {
      return (await res.json()) as T;
    }
  } catch {
    // Netzwerk / lokal ohne Export → API
  }
  return apiFetch<T>(apiPath, init);
}

/** Spiegel zu data_pipeline.export_static.static_path_segment (Artifact/NTFS). */
function staticParliamentSegment(parliamentId: string): string {
  return parliamentId.replace(/[":<>|*?\r\n\\/]/g, "_");
}

export function fetchParliaments(): Promise<Parliament[]> {
  return fetchStaticOrApi("/data/parliaments.json", "/api/parliaments");
}

export type GermanyMapLeader = {
  party_id: string;
  party_name: string;
  average_share: number;
};
export type GermanyMapLeadersResponse = {
  as_of: string;
  leaders: Record<string, GermanyMapLeader | null>;
};

export function fetchGermanyMapLeaders(): Promise<GermanyMapLeadersResponse> {
  return fetchStaticOrApi(
    "/data/germany-map-leaders.json",
    "/api/germany/map-leaders",
  );
}

export function fetchAverages(
  parliamentId: string,
  days = 365,
): Promise<AveragesResponse> {
  const q = new URLSearchParams({
    parliament_id: parliamentId,
    days: String(days),
  });
  const apiPath = `/api/parties/averages?${q}`;
  if (days !== 365) {
    return apiFetch(apiPath);
  }
  return fetchStaticOrApi(
    `/data/${encodeURIComponent(staticParliamentSegment(parliamentId))}/averages.json`,
    apiPath,
  );
}

export function fetchTrendSeries(
  parliamentId: string,
  days = 365,
): Promise<TrendSeriesResponse> {
  const q = new URLSearchParams({
    parliament_id: parliamentId,
    days: String(days),
  });
  const apiPath = `/api/parties/trend-series?${q}`;
  if (days !== 365) {
    return apiFetch(apiPath);
  }
  return fetchStaticOrApi(
    `/data/${encodeURIComponent(staticParliamentSegment(parliamentId))}/trend.json`,
    apiPath,
  );
}

export function fetchRawSurveys(
  parliamentId: string,
  opts?: { limit?: number; offset?: number },
): Promise<RawSurveysResponse> {
  const q = new URLSearchParams({
    parliament_id: parliamentId,
    limit: String(opts?.limit ?? 50),
    offset: String(opts?.offset ?? 0),
  });
  return apiFetch(`/api/surveys?${q}`);
}

export function fetchSeats(parliamentId: string): Promise<SeatsResponse> {
  const q = new URLSearchParams({ parliament_id: parliamentId });
  return fetchStaticOrApi(
    `/data/${encodeURIComponent(staticParliamentSegment(parliamentId))}/seats.json`,
    `/api/seats?${q}`,
  );
}

export function fetchLastElection(
  parliamentId: string,
): Promise<LastElectionResponse> {
  const q = new URLSearchParams({ parliament_id: parliamentId });
  return apiFetch(`/api/parliaments/last-election?${q}`);
}

export function fetchCoalitions(
  parliamentId: string,
  opts?: {
    apply_exclusions?: boolean;
    max_parties?: number;
    disabled_rule_ids?: string[];
  },
): Promise<CoalitionsResponse> {
  const q = new URLSearchParams({ parliament_id: parliamentId });
  if (opts?.apply_exclusions !== undefined) {
    q.set("apply_exclusions", String(opts.apply_exclusions));
  }
  if (opts?.max_parties !== undefined) {
    q.set("max_parties", String(opts.max_parties));
  }
  const disabled = opts?.disabled_rule_ids ?? [];
  for (const id of disabled) {
    q.append("disabled_rule_ids", id);
  }
  const apiPath = `/api/coalitions?${q}`;
  // Static-JSON nur für den Default-Export (kein opts). Jede UI-Interaktion
  // (Ausschluss an/aus, einzelne Regeln, max_parties) muss die API treffen —
  // sonst bleibt die Übersicht auf dem gecachten Snapshot mit Exclusions.
  const interactive =
    opts !== undefined &&
    (opts.apply_exclusions !== undefined ||
      disabled.length > 0 ||
      (opts.max_parties !== undefined && opts.max_parties !== 4));
  if (interactive) {
    return apiFetch(apiPath, { noStore: true });
  }
  return fetchStaticOrApi(
    `/data/${encodeURIComponent(staticParliamentSegment(parliamentId))}/coalitions.json`,
    apiPath,
  );
}

export function fetchCoalitionRules(
  parliamentId: string,
): Promise<CoalitionRulesResponse> {
  const q = new URLSearchParams({ parliament_id: parliamentId });
  return apiFetch(`/api/coalitions/rules?${q}`);
}

export function fetchUncertainty(
  parliamentId: string,
  nSimulations = 400,
  opts?: {
    applyExclusions?: boolean;
    disabledRuleIds?: string[];
  },
): Promise<UncertaintyResponse> {
  const q = new URLSearchParams({
    parliament_id: parliamentId,
    n_simulations: String(nSimulations),
  });
  if (opts?.applyExclusions !== undefined) {
    q.set("apply_exclusions", String(opts.applyExclusions));
  }
  const disabled = opts?.disabledRuleIds ?? [];
  for (const id of disabled) {
    q.append("disabled_rule_ids", id);
  }
  const interactive =
    opts !== undefined &&
    (opts.applyExclusions !== undefined || disabled.length > 0);
  return apiFetch(`/api/uncertainty?${q}`, interactive ? { noStore: true } : undefined);
}

export function fetchThresholdWatch(
  parliamentId: string,
  band = 3,
): Promise<ThresholdWatchResponse> {
  const q = new URLSearchParams({
    parliament_id: parliamentId,
    band: String(band),
  });
  return apiFetch(`/api/threshold-watch?${q}`);
}

export function fetchPartyForecast(
  parliamentId: string,
): Promise<PartyForecastResponse> {
  const q = new URLSearchParams({ parliament_id: parliamentId });
  return apiFetch(`/api/party-forecast?${q}`);
}

export function fetchThresholdWatchOverview(
  band = 3,
): Promise<ThresholdWatchOverviewResponse> {
  const q = new URLSearchParams({ band: String(band) });
  return apiFetch(`/api/threshold-watch/overview?${q}`);
}

export function fetchHouseEffects(
  parliamentId?: string,
  windowDays = 14,
): Promise<HouseEffectsResponse> {
  const q = new URLSearchParams({ window_days: String(windowDays) });
  if (parliamentId) q.set("parliament_id", parliamentId);
  return apiFetch(`/api/institutes/house-effects?${q}`);
}

export function fetchInstituteLeaderboard(): Promise<InstituteLeaderboardResponse> {
  return apiFetch("/api/institutes/leaderboard");
}

export function fetchEuropeOverview(): Promise<EuropeOverviewResponse> {
  return apiFetch("/api/europe/overview");
}

export type BundesratCoalitionOption = {
  key: string;
  parties: string[];
  seats: number;
  is_minimal_winning: boolean;
};

export type BundesratLand = {
  parliament_id: string;
  name: string;
  votes: number;
  default_government: string[];
  default_government_label: string;
  coalition_options: BundesratCoalitionOption[];
};

export type BundesratLandVote = {
  parliament_id: string;
  name: string;
  votes: number;
  stance: string;
  government: string[];
  government_label: string;
  source: string;
};

export type BundesratStatusResponse = {
  as_of: string;
  disclaimer: string;
  sources: string[];
  total_votes: number;
  majority_threshold: number;
  two_thirds_threshold: number;
  laender: BundesratLand[];
  simulation: {
    yes_votes: number;
    no_votes: number;
    abstain_votes: number;
    has_majority: boolean;
    has_two_thirds: boolean;
    by_land: BundesratLandVote[];
  };
};

export type BundesratSimulateResponse = {
  as_of: string;
  disclaimer: string;
  total_votes: number;
  majority_threshold: number;
  two_thirds_threshold: number;
  yes_votes: number;
  no_votes: number;
  abstain_votes: number;
  has_majority: boolean;
  has_two_thirds: boolean;
  by_land: BundesratLandVote[];
};

export type BundesratMajorityCheckItem = {
  parties: string[];
  label?: string | null;
  bundestag_seats: number;
  is_minimal_winning: boolean;
  is_incumbent?: boolean;
  choices: Record<string, string>;
  yes_votes: number;
  no_votes: number;
  abstain_votes: number;
  has_majority: boolean;
  has_two_thirds: boolean;
};

export type BundesratCoalitionBalanceSlice = {
  key: string;
  label: string;
  parties_normalized: string[];
  votes: number;
  parliament_ids: string[];
  matches_federal: boolean;
};

export type BundesratMajorityCheckResponse = {
  as_of: string;
  total_votes: number;
  majority_threshold: number;
  two_thirds_threshold: number;
  federal_government?: {
    stand: string;
    parties: string[];
    label: string;
  } | null;
  coalition_balance?: BundesratCoalitionBalanceSlice[];
  coalitions: BundesratMajorityCheckItem[];
};

export function fetchBundesratStatus(): Promise<BundesratStatusResponse> {
  return apiFetch("/api/bundesrat/status");
}

export function fetchBundesratMajorityCheck(
  limit = 8,
): Promise<BundesratMajorityCheckResponse> {
  const q = new URLSearchParams({ limit: String(limit) });
  return apiFetch(`/api/bundesrat/majority-check?${q}`);
}

export function postBundesratSimulate(
  choices: Record<string, string>,
): Promise<BundesratSimulateResponse> {
  return apiFetch("/api/bundesrat/simulate", {
    method: "POST",
    body: JSON.stringify({ choices }),
  });
}

export function postScenario(body: ScenarioRequest): Promise<ScenarioResponse> {
  return apiFetch("/api/scenario", {
    method: "POST",
    body: JSON.stringify(body),
  });
}
