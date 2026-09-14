"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  fetchBundesratStatus,
  fetchGovernment,
  fetchLastElection,
  fetchSeats,
  type LastElectionResponse,
  type SeatsResponse,
} from "@/lib/api";
import { Hemicycle } from "@/components/charts";
import { CoalitionsSection } from "@/components/CoalitionsSection";
import { DataFreshnessBanner } from "@/components/DataFreshnessBanner";
import { InstituteView } from "@/components/InstituteView";
import { PartyForecast } from "@/components/PartyForecast";
import { SurveysSection } from "@/components/SurveysSection";
import { ThresholdWatch } from "@/components/ThresholdWatch";
import { labelPartyId, partyColor } from "@/lib/colors";
import { PARTY_SWATCH_CLASS } from "@/lib/theme";

type TagKey = "umfragen" | "koalitionen" | "prognose" | "institute";

const TAGS: { key: TagKey; label: string }[] = [
  { key: "umfragen", label: "Umfragen" },
  { key: "koalitionen", label: "Koalitionen" },
  { key: "prognose", label: "Prognose" },
  { key: "institute", label: "Institute" },
];

type IncumbentGov = {
  label: string;
  parties: string[];
};

function SeatCompareBlock({
  lastElection,
  pollSeats,
}: {
  lastElection: LastElectionResponse | null;
  pollSeats: SeatsResponse | null;
}) {
  return (
    <div className="grid gap-4 md:grid-cols-2">
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
          </h3>
          <p className="mb-3 text-xs text-ink/55">
            Hochrechnung ·{" "}
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
  const [incumbent, setIncumbent] = useState<IncumbentGov | null>(null);
  const [headerError, setHeaderError] = useState<string | null>(null);
  const [headerLoading, setHeaderLoading] = useState(true);

  const [openedTags, setOpenedTags] = useState<Set<TagKey>>(
    () => new Set(["umfragen"]),
  );
  const [activeTags, setActiveTags] = useState<Set<TagKey>>(
    () => new Set(["umfragen"]),
  );

  useEffect(() => {
    let cancelled = false;
    setHeaderLoading(true);
    setHeaderError(null);
    setOpenedTags(new Set(["umfragen"]));
    setActiveTags(new Set(["umfragen"]));

    (async () => {
      try {
        const [election, seats, gov, br] = await Promise.all([
          fetchLastElection(parliamentId).catch(() => null),
          fetchSeats(parliamentId).catch(() => null),
          fetchGovernment().catch(() => null),
          fetchBundesratStatus().catch(() => null),
        ]);
        if (cancelled) return;
        setLastElection(election);
        setPollSeats(seats);

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

  const toggleTag = useCallback((key: TagKey) => {
    setOpenedTags((prev) => {
      const next = new Set(prev);
      next.add(key);
      return next;
    });
    setActiveTags((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }, []);

  const tagPanels = useMemo(
    () =>
      [
        {
          key: "umfragen" as const,
          node: <SurveysSection parliamentId={parliamentId} />,
        },
        {
          key: "koalitionen" as const,
          node: <CoalitionsSection parliamentId={parliamentId} />,
        },
        {
          key: "prognose" as const,
          node: (
            <div className="space-y-10">
              <PartyForecast parliamentId={parliamentId} />
              <ThresholdWatch parliamentId={parliamentId} />
            </div>
          ),
        },
        {
          key: "institute" as const,
          node: <InstituteView parliamentId={parliamentId} />,
        },
      ] as const,
    [parliamentId],
  );

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
          <div className="grid gap-4 lg:grid-cols-[minmax(0,1.6fr)_minmax(14rem,0.7fr)]">
            <SeatCompareBlock
              lastElection={lastElection}
              pollSeats={pollSeats}
            />
            <IncumbentCoalitionCard gov={incumbent} />
          </div>
        )}
      </section>

      <div
        className="flex flex-wrap gap-2"
        role="toolbar"
        aria-label="Analyse-Bereiche"
      >
        {TAGS.map((tag) => {
          const active = activeTags.has(tag.key);
          return (
            <button
              key={tag.key}
              type="button"
              onClick={() => toggleTag(tag.key)}
              aria-pressed={active}
              className={
                active
                  ? "rounded-md border border-sea/40 bg-sea/10 px-3 py-1.5 text-sm font-medium text-ink"
                  : "rounded-md border border-ink/15 bg-mist px-3 py-1.5 text-sm text-ink/65 transition hover:border-ink/25 hover:text-ink"
              }
            >
              {tag.label}
            </button>
          );
        })}
      </div>

      <div className="space-y-10">
        {tagPanels.map(({ key, node }) => {
          if (!openedTags.has(key)) return null;
          const visible = activeTags.has(key);
          return (
            <div
              key={`${parliamentId}-${key}`}
              hidden={!visible}
              className={visible ? "space-y-4" : undefined}
            >
              {node}
            </div>
          );
        })}
      </div>
    </div>
  );
}
