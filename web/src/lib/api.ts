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

export type SeatsResponse = {
  parliament_id: string;
  total_seats: number;
  seats: Record<string, number>;
  seats_by_name: Record<string, number>;
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

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${apiBase()}${path}`;
  const res = await fetch(url, {
    ...init,
    headers: {
      Accept: "application/json",
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...init?.headers,
    },
    cache: "no-store",
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status} ${path}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

export function fetchParliaments(): Promise<Parliament[]> {
  return apiFetch("/api/parliaments");
}

export function fetchAverages(
  parliamentId: string,
  days = 365,
): Promise<AveragesResponse> {
  const q = new URLSearchParams({
    parliament_id: parliamentId,
    days: String(days),
  });
  return apiFetch(`/api/parties/averages?${q}`);
}

export function fetchSeats(parliamentId: string): Promise<SeatsResponse> {
  const q = new URLSearchParams({ parliament_id: parliamentId });
  return apiFetch(`/api/seats?${q}`);
}

export function fetchCoalitions(
  parliamentId: string,
  opts?: { apply_exclusions?: boolean; max_parties?: number },
): Promise<CoalitionsResponse> {
  const q = new URLSearchParams({ parliament_id: parliamentId });
  if (opts?.apply_exclusions !== undefined) {
    q.set("apply_exclusions", String(opts.apply_exclusions));
  }
  if (opts?.max_parties !== undefined) {
    q.set("max_parties", String(opts.max_parties));
  }
  return apiFetch(`/api/coalitions?${q}`);
}

export function fetchUncertainty(
  parliamentId: string,
  nSimulations = 400,
): Promise<UncertaintyResponse> {
  const q = new URLSearchParams({
    parliament_id: parliamentId,
    n_simulations: String(nSimulations),
  });
  return apiFetch(`/api/uncertainty?${q}`);
}

export function fetchHouseEffects(
  parliamentId?: string,
  windowDays = 14,
): Promise<HouseEffectsResponse> {
  const q = new URLSearchParams({ window_days: String(windowDays) });
  if (parliamentId) q.set("parliament_id", parliamentId);
  return apiFetch(`/api/institutes/house-effects?${q}`);
}

export function fetchEuropeOverview(): Promise<EuropeOverviewResponse> {
  return apiFetch("/api/europe/overview");
}

export function postScenario(body: ScenarioRequest): Promise<ScenarioResponse> {
  return apiFetch("/api/scenario", {
    method: "POST",
    body: JSON.stringify(body),
  });
}
