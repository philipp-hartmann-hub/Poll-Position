"use client";

import { Suspense, useCallback, useEffect, useId, useMemo, useRef, useState, type KeyboardEvent } from "react";
import {
  fetchAverages,
  fetchBundesratStatus,
  fetchGovernment,
  fetchLastElection,
  fetchSeats,
  fetchUncertainty,
  type AveragesResponse,
  type LastElectionResponse,
  type SeatsResponse,
} from "@/lib/api";
import { Hemicycle, PollAndSwingAlignedCharts, PollShareBarChart } from "@/components/charts";
import { CoalitionsSection } from "@/components/CoalitionsSection";
import { DataFreshnessBanner } from "@/components/DataFreshnessBanner";
import { InfoTooltip } from "@/components/InfoTooltip";
import { LastElectionSection } from "@/components/LastElectionSection";
import { PartyForecast } from "@/components/PartyForecast";
import { SurveysSection } from "@/components/SurveysSection";
import { labelPartyId, partyColor } from "@/lib/colors";
import { PARTY_SWATCH_CLASS } from "@/lib/theme";
import {
  TIP_AVERAGES_TREND,
  TIP_REELECTION,
  TIP_SEAT_PROJECTION,
} from "@/lib/tooltipCopy";
import {
  contentSignature,
  formatCacheAge,
  isAbortError,
  readOverviewCache,
  writeOverviewCache,
  type OverviewCacheData,
} from "@/lib/parliamentCache";

type TagKey = "umfragen" | "koalitionen" | "prognose" | "letzte-wahl";

const TAGS: { key: TagKey; label: string }[] = [
  { key: "umfragen", label: "Umfragen" },
  { key: "koalitionen", label: "Koalitionen" },
  { key: "prognose", label: "Prognose" },
  { key: "letzte-wahl", label: "Letzte Wahl" },
];

type IncumbentGov = {
  label: string;
  parties: string[];
};

function SeatCompareBlock({
  lastElection,
  pollSeats,
  averages,
  gov,
  reelectionProbability,
}: {
  lastElection: LastElectionResponse | null;
  pollSeats: SeatsResponse | null;
  averages: AveragesResponse | null;
  gov: IncumbentGov | null;
  reelectionProbability: number | null;
}) {
  const pollParties =
    averages?.parties.map((p) => ({
      party_name: p.party_name,
      share: p.average_share,
    })) ?? [];

  const electionShares = lastElection?.vote_share_by_name ?? {};
  const alignedRows =
    averages?.parties
      .map((p) => {
        const electionShare = electionShares[p.party_name];
        if (electionShare == null) return null;
        return {
          party_name: p.party_name,
          poll_share: p.average_share,
          election_share: electionShare,
          delta_pp: p.average_share - electionShare,
        };
      })
      .filter(
        (
          r,
        ): r is {
          party_name: string;
          poll_share: number;
          election_share: number;
          delta_pp: number;
        } => r != null,
      ) ?? [];

  return (
    <div className="space-y-4">
      {alignedRows.length > 0 ? (
        <PollAndSwingAlignedCharts
          rows={alignedRows}
          electionDate={lastElection?.election_date}
        />
      ) : pollParties.length > 0 ? (
        <div className="rounded-xl border border-ink/10 bg-mist/50 p-4">
          <h3 className="text-sm font-semibold text-ink">
            Aktueller Umfrageanteil
            <InfoTooltip text={TIP_AVERAGES_TREND} />
          </h3>
          <p className="mb-3 text-xs text-ink/55">
            Gewichteter Mittelwert
            {averages?.as_of ? ` · Stand ${averages.as_of}` : ""} · Prozent
          </p>
          <PollShareBarChart parties={pollParties} />
        </div>
      ) : null}

      <div className="grid gap-4 md:grid-cols-2">
        {pollSeats && Object.keys(pollSeats.seats_by_name).length > 0 ? (
          <div className="rounded-xl border border-ink/10 bg-mist/50 p-4">
            <h3 className="text-sm font-semibold text-ink">
              Sitzprojektion nach Umfragen
              <InfoTooltip text={TIP_SEAT_PROJECTION} />
            </h3>
            <p className="mb-3 text-xs text-ink/55">
              Nach aktuellen Umfragen ·{" "}
              <span className="font-display tabular-nums">
                {pollSeats.total_seats}
              </span>{" "}
              Sitze
            </p>
            <Hemicycle
              seats={pollSeats.seats_by_name}
              size="sm"
              style="projection"
            />
          </div>
        ) : (
          <div className="rounded-xl border border-dashed border-ink/15 p-4 text-sm text-ink/45">
            Keine Umfrage-Sitzprojektion verfügbar.
          </div>
        )}
        <IncumbentCoalitionCard
          gov={gov}
          reelectionProbability={reelectionProbability}
        />
      </div>
    </div>
  );
}

function IncumbentCoalitionCard({
  gov,
  reelectionProbability,
}: {
  gov: IncumbentGov | null;
  reelectionProbability: number | null;
}) {
  if (!gov) {
    return (
      <div className="rounded-xl border border-dashed border-ink/15 p-4 text-sm text-ink/45">
        Keine amtierende Regierung hinterlegt.
      </div>
    );
  }
  return (
    <div className="rounded-xl border border-ink/10 bg-mist/50 p-4">
      <p className="text-xs uppercase tracking-wide text-ink/45">
        Aktuelle Regierung
      </p>
      <p className="mt-1 font-display text-xl text-ink">{gov.label}</p>
      <div className="mt-3 flex flex-wrap gap-2">
        {gov.parties.map((pid) => {
          const name = labelPartyId(pid);
          return (
            <span
              key={pid}
              className="inline-flex items-center gap-1.5 rounded-md border border-ink/10 bg-mist/40 px-2 py-1 text-xs font-medium text-ink"
            >
              <span
                className={`${PARTY_SWATCH_CLASS} h-2.5 w-2.5`}
                style={{ background: partyColor(name) }}
              />
              {name}
            </span>
          );
        })}
      </div>
      {reelectionProbability != null ? (
        <div className="mt-4 border-t border-ink/10 pt-3">
          <p className="font-display text-3xl tabular-nums text-accent">
            {Math.round(reelectionProbability * 100)} %
          </p>
          <p className="mt-1 text-sm text-ink/70">
            Wahrscheinlichkeit der Wiederwahl
            <InfoTooltip text={TIP_REELECTION} />
          </p>
        </div>
      ) : null}
    </div>
  );
}

export function ParliamentDashboard({
  parliamentId,
}: {
  parliamentId: string;
}) {
  const [lastElection, setLastElection] = useState<LastElectionResponse | null>(
    null,
  );
  const [pollSeats, setPollSeats] = useState<SeatsResponse | null>(null);
  const [averages, setAverages] = useState<AveragesResponse | null>(null);
  const [incumbent, setIncumbent] = useState<IncumbentGov | null>(null);
  const [reelectionProbability, setReelectionProbability] = useState<
    number | null
  >(null);
  const [headerError, setHeaderError] = useState<string | null>(null);
  const [headerLoading, setHeaderLoading] = useState(true);
  const [cacheUpdatedAt, setCacheUpdatedAt] = useState<number | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const [activeTag, setActiveTag] = useState<TagKey>("umfragen");
  const baseId = useId();
  const tabRefs = useRef<Partial<Record<TagKey, HTMLButtonElement | null>>>({});
  const abortRef = useRef<AbortController | null>(null);
  const overviewSigRef = useRef<string>("");

  useEffect(() => {
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;
    const { signal } = ac;

    setHeaderError(null);
    setActiveTag("umfragen");

    const cached = readOverviewCache(parliamentId);
    if (cached) {
      const d = cached.data;
      setLastElection(d.lastElection as LastElectionResponse | null);
      setPollSeats(d.pollSeats as SeatsResponse | null);
      setAverages(d.averages as AveragesResponse | null);
      setIncumbent(d.incumbent);
      setReelectionProbability(d.reelectionProbability);
      setCacheUpdatedAt(cached.updatedAt);
      overviewSigRef.current = contentSignature(d);
      setHeaderLoading(false);
      setRefreshing(true);
    } else {
      setHeaderLoading(true);
      setRefreshing(false);
      setCacheUpdatedAt(null);
      setLastElection(null);
      setPollSeats(null);
      setAverages(null);
      setIncumbent(null);
      setReelectionProbability(null);
      overviewSigRef.current = "";
    }

    (async () => {
      try {
        const [election, seats, avg, gov, br, unc] = await Promise.all([
          fetchLastElection(parliamentId, { signal }).catch((e) => {
            if (isAbortError(e)) throw e;
            return null;
          }),
          fetchSeats(parliamentId, { signal }).catch((e) => {
            if (isAbortError(e)) throw e;
            return null;
          }),
          fetchAverages(parliamentId, 365, { signal }).catch((e) => {
            if (isAbortError(e)) throw e;
            return null;
          }),
          fetchGovernment({ signal }).catch((e) => {
            if (isAbortError(e)) throw e;
            return null;
          }),
          fetchBundesratStatus({ signal }).catch((e) => {
            if (isAbortError(e)) throw e;
            return null;
          }),
          fetchUncertainty(parliamentId, 200, { signal }).catch((e) => {
            if (isAbortError(e)) throw e;
            return null;
          }),
        ]);
        if (signal.aborted) return;

        let nextIncumbent: IncumbentGov | null = null;
        if (parliamentId === "de_bundestag" && gov?.bundesregierung) {
          nextIncumbent = {
            label: gov.bundesregierung.label,
            parties: gov.bundesregierung.parties,
          };
        } else {
          const land = br?.laender.find((l) => l.parliament_id === parliamentId);
          if (land) {
            nextIncumbent = {
              label: land.default_government_label,
              parties: land.default_government,
            };
          }
        }

        const p = unc?.current_government_majority_probability;
        const nextReelect = typeof p === "number" ? p : null;
        const nextData: OverviewCacheData = {
          lastElection: election,
          pollSeats: seats,
          averages: avg,
          incumbent: nextIncumbent,
          reelectionProbability: nextReelect,
        };
        const sig = contentSignature(nextData);
        if (sig !== overviewSigRef.current) {
          overviewSigRef.current = sig;
          setLastElection(election);
          setPollSeats(seats);
          setAverages(avg);
          setIncumbent(nextIncumbent);
          setReelectionProbability(nextReelect);
        }
        const now = Date.now();
        writeOverviewCache(parliamentId, nextData, now);
        setCacheUpdatedAt(now);
      } catch (e) {
        if (isAbortError(e) || signal.aborted) return;
        if (!cached) {
          setHeaderError(e instanceof Error ? e.message : "Laden fehlgeschlagen");
        }
      } finally {
        if (!signal.aborted) {
          setHeaderLoading(false);
          setRefreshing(false);
        }
      }
    })();

    return () => {
      ac.abort();
    };
  }, [parliamentId]);

  const focusTab = useCallback((key: TagKey) => {
    setActiveTag(key);
    tabRefs.current[key]?.focus();
  }, []);

  const onTabKeyDown = useCallback(
    (e: KeyboardEvent<HTMLButtonElement>, key: TagKey) => {
      const idx = TAGS.findIndex((t) => t.key === key);
      if (idx < 0) return;
      let next = -1;
      if (e.key === "ArrowRight" || e.key === "ArrowDown") {
        next = (idx + 1) % TAGS.length;
      } else if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
        next = (idx - 1 + TAGS.length) % TAGS.length;
      } else if (e.key === "Home") {
        next = 0;
      } else if (e.key === "End") {
        next = TAGS.length - 1;
      }
      if (next < 0) return;
      e.preventDefault();
      focusTab(TAGS[next].key);
    },
    [focusTab],
  );

  const activePanel = useMemo(() => {
    switch (activeTag) {
      case "umfragen":
        return <SurveysSection parliamentId={parliamentId} />;
      case "koalitionen":
        return (
          <Suspense
            fallback={<p className="text-sm text-ink/50">Lade Analyse…</p>}
          >
            <CoalitionsSection parliamentId={parliamentId} />
          </Suspense>
        );
      case "prognose":
        return <PartyForecast parliamentId={parliamentId} />;
      case "letzte-wahl":
        return (
          <Suspense
            fallback={<p className="text-sm text-ink/50">Lade Wahlergebnis…</p>}
          >
            <LastElectionSection parliamentId={parliamentId} />
          </Suspense>
        );
    }
  }, [activeTag, parliamentId]);

  const tabId = (key: TagKey) => `${baseId}-tab-${key}`;
  const panelId = (key: TagKey) => `${baseId}-panel-${key}`;

  return (
    <div className="space-y-8">
      <DataFreshnessBanner />

      <section className="space-y-4">
        <div className="flex flex-wrap items-end justify-between gap-2">
          <h2 className="font-display text-2xl text-ink">
            Sitze & aktuelle Regierung
          </h2>
          {cacheUpdatedAt != null && !headerLoading ? (
            <p className="text-xs text-ink/45">
              Stand: {formatCacheAge(cacheUpdatedAt)}
              {refreshing ? " · aktualisiert…" : ""}
            </p>
          ) : null}
        </div>
        {headerLoading ? (
          <p className="text-sm text-ink/50">Lade Übersicht…</p>
        ) : headerError ? (
          <p className="rounded-lg border border-accent/30 bg-accent/5 px-4 py-3 text-sm text-accent">
            {headerError}
          </p>
        ) : (
          <SeatCompareBlock
            lastElection={lastElection}
            pollSeats={pollSeats}
            averages={averages}
            gov={incumbent}
            reelectionProbability={reelectionProbability}
          />
        )}
      </section>

      <div
        className="flex flex-wrap gap-2"
        role="tablist"
        aria-label="Analyse-Bereiche"
      >
        {TAGS.map((tag) => {
          const selected = activeTag === tag.key;
          return (
            <button
              key={tag.key}
              ref={(el) => {
                tabRefs.current[tag.key] = el;
              }}
              type="button"
              role="tab"
              id={tabId(tag.key)}
              aria-selected={selected}
              aria-controls={panelId(tag.key)}
              tabIndex={selected ? 0 : -1}
              onClick={() => setActiveTag(tag.key)}
              onKeyDown={(e) => onTabKeyDown(e, tag.key)}
              className={
                selected
                  ? "rounded-md border border-sea/40 bg-sea/10 px-3 py-1.5 text-sm font-medium text-ink"
                  : "rounded-md border border-ink/15 bg-mist px-3 py-1.5 text-sm text-ink/65 transition hover:border-ink/25 hover:text-ink"
              }
            >
              {tag.label}
            </button>
          );
        })}
      </div>

      <div
        role="tabpanel"
        id={panelId(activeTag)}
        aria-labelledby={tabId(activeTag)}
        className="space-y-4"
      >
        {activePanel}
      </div>
    </div>
  );
}
