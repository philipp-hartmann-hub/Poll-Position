"use client";

import { Suspense, useCallback, useEffect, useId, useMemo, useRef, useState, type KeyboardEvent } from "react";
import {
  fetchAverages,
  fetchBundesratStatus,
  fetchGovernment,
  fetchLastElection,
  fetchSeats,
  type AveragesResponse,
  type LastElectionResponse,
  type SeatsResponse,
} from "@/lib/api";
import { Hemicycle, PollAndSwingAlignedCharts, PollShareBarChart } from "@/components/charts";
import { CoalitionsSection } from "@/components/CoalitionsSection";
import { DataFreshnessBanner } from "@/components/DataFreshnessBanner";
import { InfoTooltip } from "@/components/InfoTooltip";
import { PartyForecast } from "@/components/PartyForecast";
import { SurveysSection } from "@/components/SurveysSection";
import { labelPartyId, partyColor } from "@/lib/colors";
import { PARTY_SWATCH_CLASS } from "@/lib/theme";
import { TIP_AVERAGES_TREND, TIP_SEAT_PROJECTION } from "@/lib/tooltipCopy";

type TagKey = "umfragen" | "koalitionen" | "prognose";

const TAGS: { key: TagKey; label: string }[] = [
  { key: "umfragen", label: "Umfragen" },
  { key: "koalitionen", label: "Koalitionen" },
  { key: "prognose", label: "Prognose" },
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
}: {
  lastElection: LastElectionResponse | null;
  pollSeats: SeatsResponse | null;
  averages: AveragesResponse | null;
  gov: IncumbentGov | null;
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

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {lastElection ? (
          <div className="rounded-xl border border-ink/10 bg-mist/50 p-4">
            <h3 className="text-sm font-semibold text-ink">
              Ergebnis der letzten Wahl
            </h3>
            <p className="mb-3 text-xs text-ink/55">
              {lastElection.label} ({lastElection.election_date}) ·{" "}
              <span className="font-display tabular-nums">
                {lastElection.total_seats}
              </span>{" "}
              Sitze
            </p>
            <Hemicycle
              seats={lastElection.seats_by_name}
              size="sm"
              style="official"
            />
          </div>
        ) : (
          <div className="rounded-xl border border-dashed border-ink/15 p-4 text-sm text-ink/45">
            Kein hinterlegtes Wahlergebnis für dieses Parlament.
          </div>
        )}
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
        <IncumbentCoalitionCard gov={gov} />
      </div>
    </div>
  );
}

function IncumbentCoalitionCard({ gov }: { gov: IncumbentGov | null }) {
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
  const [headerError, setHeaderError] = useState<string | null>(null);
  const [headerLoading, setHeaderLoading] = useState(true);

  const [activeTag, setActiveTag] = useState<TagKey>("umfragen");
  const baseId = useId();
  const tabRefs = useRef<Partial<Record<TagKey, HTMLButtonElement | null>>>({});

  useEffect(() => {
    let cancelled = false;
    setHeaderLoading(true);
    setHeaderError(null);
    setActiveTag("umfragen");

    (async () => {
      try {
        const [election, seats, avg, gov, br] = await Promise.all([
          fetchLastElection(parliamentId).catch(() => null),
          fetchSeats(parliamentId).catch(() => null),
          fetchAverages(parliamentId).catch(() => null),
          fetchGovernment().catch(() => null),
          fetchBundesratStatus().catch(() => null),
        ]);
        if (cancelled) return;
        setLastElection(election);
        setPollSeats(seats);
        setAverages(avg);

        if (parliamentId === "de_bundestag" && gov?.bundesregierung) {
          setIncumbent({
            label: gov.bundesregierung.label,
            parties: gov.bundesregierung.parties,
          });
        } else {
          const land = br?.laender.find((l) => l.parliament_id === parliamentId);
          if (land) {
            setIncumbent({
              label: land.default_government_label,
              parties: land.default_government,
            });
          } else {
            setIncumbent(null);
          }
        }
      } catch (e) {
        if (!cancelled) {
          setHeaderError(e instanceof Error ? e.message : "Laden fehlgeschlagen");
        }
      } finally {
        if (!cancelled) setHeaderLoading(false);
      }
    })();

    return () => {
      cancelled = true;
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
    }
  }, [activeTag, parliamentId]);

  const tabId = (key: TagKey) => `${baseId}-tab-${key}`;
  const panelId = (key: TagKey) => `${baseId}-panel-${key}`;

  return (
    <div className="space-y-8">
      <DataFreshnessBanner />

      <section className="space-y-4">
        <h2 className="font-display text-2xl text-ink">
          Sitze & aktuelle Regierung
        </h2>
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
