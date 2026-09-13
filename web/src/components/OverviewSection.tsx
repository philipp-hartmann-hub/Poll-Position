"use client";

import { useEffect, useState } from "react";
import {
  fetchLastElection,
  fetchSeats,
  type LastElectionResponse,
  type SeatsResponse,
} from "@/lib/api";
import { Hemicycle } from "@/components/charts";
import { PartyForecast } from "@/components/PartyForecast";
import { SurveysSection } from "@/components/SurveysSection";

export function OverviewSection({
  parliamentId,
  showThreshold = true,
}: {
  parliamentId: string;
  /** Parteien-Prognose (Default an; aus z. B. für reine Poll-Länder). */
  showThreshold?: boolean;
}) {
  const [lastElection, setLastElection] = useState<LastElectionResponse | null>(
    null,
  );
  const [pollSeats, setPollSeats] = useState<SeatsResponse | null>(null);
  const [seatsReady, setSeatsReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setSeatsReady(false);
    (async () => {
      const [election, seats] = await Promise.all([
        fetchLastElection(parliamentId).catch(() => null),
        fetchSeats(parliamentId).catch(() => null),
      ]);
      if (cancelled) return;
      setLastElection(election);
      setPollSeats(seats);
      setSeatsReady(true);
    })();
    return () => {
      cancelled = true;
    };
  }, [parliamentId]);

  const showSeatCompare = seatsReady && Boolean(lastElection || pollSeats);

  return (
    <div className="space-y-10">
      {!seatsReady ? (
        <p className="text-sm text-ink/50">Lade Sitzvergleich…</p>
      ) : showSeatCompare ? (
        <section>
          <h2 className="mb-3 font-display text-2xl text-ink">
            Sitze: letzte Wahl vs. Umfrage-Projektion
          </h2>
          <div className="grid gap-6 md:grid-cols-2">
            {lastElection ? (
              <div className="rounded-xl border border-ink/10 bg-white/50 p-4">
                <h3 className="text-sm font-semibold text-ink">
                  Ergebnis der letzten Wahl
                </h3>
                <p className="mb-3 text-xs text-ink/55">
                  Stand: {lastElection.label} ({lastElection.election_date}) ·{" "}
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
              <div className="rounded-xl border border-ink/10 bg-white/50 p-4">
                <h3 className="text-sm font-semibold text-ink">
                  Sitzprojektion nach aktuellen Umfragen
                </h3>
                <p className="mb-3 text-xs text-ink/55">
                  Hochrechnung ·{" "}
                  <span className="font-display tabular-nums">
                    {pollSeats.total_seats}
                  </span>{" "}
                  Sitze (gesetzliche Größe)
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
        </section>
      ) : null}

      <SurveysSection parliamentId={parliamentId} />

      {showThreshold ? <PartyForecast parliamentId={parliamentId} /> : null}
    </div>
  );
}
