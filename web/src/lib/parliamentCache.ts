/**
 * Stale-while-revalidate für Parlament-Ansichten (localStorage).
 * Ohne Zod: strukturelle Guards; Fehler/Private Mode brechen die App nie.
 */

export const PARLIAMENT_CACHE_PREFIX = "poll-position:parliament-v1:";
export const PARLIAMENT_CACHE_MAX_AGE_MS = 24 * 60 * 60 * 1000;

export type ParliamentCacheEnvelope<T> = {
  parliamentId: string;
  updatedAt: number;
  data: T;
};

export type OverviewCacheData = {
  lastElection: unknown;
  pollSeats: unknown;
  averages: unknown;
  incumbent: { label: string; parties: string[] } | null;
  reelectionProbability: number | null;
};

export type CoalitionsCacheData = {
  coalitions: unknown;
  seats: unknown;
};

export type LastElectionCacheData = {
  election: unknown;
  coalitions: unknown;
};

let storageOk: boolean | null = null;

export function canUseStorage(): boolean {
  if (storageOk != null) return storageOk;
  if (typeof window === "undefined") {
    storageOk = false;
    return false;
  }
  try {
    const key = `${PARLIAMENT_CACHE_PREFIX}__probe`;
    window.localStorage.setItem(key, "1");
    window.localStorage.removeItem(key);
    storageOk = true;
  } catch {
    storageOk = false;
  }
  return storageOk;
}

function cacheKey(kind: string, parliamentId: string): string {
  return `${PARLIAMENT_CACHE_PREFIX}${kind}:${parliamentId}`;
}

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v != null && !Array.isArray(v);
}

function isEnvelope(raw: unknown): raw is ParliamentCacheEnvelope<unknown> {
  if (!isRecord(raw)) return false;
  return (
    typeof raw.parliamentId === "string" &&
    typeof raw.updatedAt === "number" &&
    Number.isFinite(raw.updatedAt) &&
    "data" in raw
  );
}

function isOverviewData(data: unknown): data is OverviewCacheData {
  if (!isRecord(data)) return false;
  if (!("lastElection" in data && "pollSeats" in data && "averages" in data)) {
    return false;
  }
  if (data.incumbent != null) {
    if (!isRecord(data.incumbent)) return false;
    if (typeof data.incumbent.label !== "string") return false;
    if (!Array.isArray(data.incumbent.parties)) return false;
  }
  if (
    data.reelectionProbability != null &&
    typeof data.reelectionProbability !== "number"
  ) {
    return false;
  }
  return true;
}

function isCoalitionsData(data: unknown): data is CoalitionsCacheData {
  return isRecord(data) && "coalitions" in data && "seats" in data;
}

function isLastElectionData(data: unknown): data is LastElectionCacheData {
  return isRecord(data) && "election" in data && "coalitions" in data;
}

function readRaw(
  kind: string,
  parliamentId: string,
): ParliamentCacheEnvelope<unknown> | null {
  if (!canUseStorage()) return null;
  try {
    const raw = window.localStorage.getItem(cacheKey(kind, parliamentId));
    if (!raw) return null;
    const parsed: unknown = JSON.parse(raw);
    if (!isEnvelope(parsed)) return null;
    if (parsed.parliamentId !== parliamentId) return null;
    if (Date.now() - parsed.updatedAt > PARLIAMENT_CACHE_MAX_AGE_MS) return null;
    return parsed;
  } catch {
    return null;
  }
}

function writeRaw(
  kind: string,
  parliamentId: string,
  data: unknown,
  updatedAt: number = Date.now(),
): void {
  if (!canUseStorage()) return;
  try {
    const envelope: ParliamentCacheEnvelope<unknown> = {
      parliamentId,
      updatedAt,
      data,
    };
    window.localStorage.setItem(
      cacheKey(kind, parliamentId),
      JSON.stringify(envelope),
    );
  } catch {
    // Quota / Private Mode — still ignorieren
  }
}

export function readOverviewCache(
  parliamentId: string,
): ParliamentCacheEnvelope<OverviewCacheData> | null {
  const env = readRaw("overview", parliamentId);
  if (!env || !isOverviewData(env.data)) return null;
  return { ...env, data: env.data };
}

export function writeOverviewCache(
  parliamentId: string,
  data: OverviewCacheData,
  updatedAt?: number,
): void {
  writeRaw("overview", parliamentId, data, updatedAt);
}

export function readCoalitionsCache(
  parliamentId: string,
): ParliamentCacheEnvelope<CoalitionsCacheData> | null {
  const env = readRaw("coalitions", parliamentId);
  if (!env || !isCoalitionsData(env.data)) return null;
  return { ...env, data: env.data };
}

export function writeCoalitionsCache(
  parliamentId: string,
  data: CoalitionsCacheData,
  updatedAt?: number,
): void {
  writeRaw("coalitions", parliamentId, data, updatedAt);
}

export function readLastElectionCache(
  parliamentId: string,
): ParliamentCacheEnvelope<LastElectionCacheData> | null {
  const env = readRaw("last-election", parliamentId);
  if (!env || !isLastElectionData(env.data)) return null;
  return { ...env, data: env.data };
}

export function writeLastElectionCache(
  parliamentId: string,
  data: LastElectionCacheData,
  updatedAt?: number,
): void {
  writeRaw("last-election", parliamentId, data, updatedAt);
}

/** Inhalts-Signatur: gleiche Daten → gleiche State-Referenz behalten. */
export function contentSignature(value: unknown): string {
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

export function formatCacheAge(updatedAt: number, now: number = Date.now()): string {
  const sec = Math.max(0, Math.floor((now - updatedAt) / 1000));
  if (sec < 60) return "gerade eben";
  const min = Math.floor(sec / 60);
  if (min < 60) return `vor ${min} Min.`;
  const h = Math.floor(min / 60);
  if (h < 48) return `vor ${h} Std.`;
  const d = Math.floor(h / 24);
  return `vor ${d} Tagen`;
}

export function isAbortError(e: unknown): boolean {
  if (e instanceof DOMException && e.name === "AbortError") return true;
  if (e instanceof Error && e.name === "AbortError") return true;
  return false;
}
