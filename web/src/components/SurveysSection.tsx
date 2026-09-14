"use client";

import { useEffect, useState } from "react";
import {
  fetchAverages,
  fetchTrendSeries,
  type AveragesResponse,
  type TrendSeriesResponse,
} from "@/lib/api";
import { TrendLineChart } from "@/components/charts";
import { ExportButtons } from "@/components/ExportButtons";
import { InfoTooltip } from "@/components/InfoTooltip";
import { RawSurveysTable } from "@/components/RawSurveysTable";
import { partyColor } from "@/lib/colors";
import {
  downloadCsv,
  downloadJson,
  exportBasename,
  formatDeNumber,
  toCsv,
} from "@/lib/download";
import { PARTY_SWATCH_CLASS } from "@/lib/theme";
import { TIP_AVERAGES_TREND, TIP_SWING, TIP_TREND_SERIES } from "@/lib/tooltipCopy";

/** Trend, Mittelwert-Tabelle (mit Export) und einzelne Rohumfragen. */
export function SurveysSection({ parliamentId }: { parliamentId: string }) {
  const [averages, setAverages] = useState<AveragesResponse | null>(null);
  const [trends, setTrends] = useState<TrendSeriesResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    (async () => {
      try {
        const [a, t] = await Promise.all([
          fetchAverages(parliamentId),
          fetchTrendSeries(parliamentId).catch(() => null),
        ]);
        if (cancelled) return;
        setAverages(a);
        setTrends(t);
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Laden fehlgeschlagen");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [parliamentId]);

  if (loading) {
    return <p className="text-sm text-ink/50">Lade Umfragen…</p>;
  }
  if (error) {
    return (
      <p className="rounded-lg border border-accent/30 bg-accent/5 px-4 py-3 text-sm text-accent">
        {error}
        <span className="mt-1 block text-ink/50">
          API erreichbar? Lokal:{" "}
          <code className="text-xs">uv run uvicorn backend.main:app</code>
        </span>
      </p>
    );
  }

  const hasTrend =
    trends != null && trends.parties.some((p) => p.points.length > 0);

  const exportAverages = (kind: "csv" | "json") => {
    if (!averages) return;
    const base = exportBasename(parliamentId, "averages");
    if (kind === "json") {
      downloadJson(`${base}.json`, {
        parliament_id: averages.parliament_id,
        as_of: averages.as_of,
        parties: averages.parties.map((p) => ({
          party: p.party_name,
          party_id: p.party_id,
          average_share: p.average_share,
          trend_share: p.trend_share,
          swing: p.swing,
          n_surveys: p.n_surveys,
        })),
      });
      return;
    }
    downloadCsv(
      `${base}.csv`,
      toCsv(
        ["Partei", "Ø %", "Trend %", "Swing", "n"],
        averages.parties.map((p) => [
          p.party_name,
          formatDeNumber(p.average_share),
          formatDeNumber(p.trend_share),
          formatDeNumber(p.swing),
          p.n_surveys,
        ]),
      ),
    );
  };

  return (
    <section className="space-y-6">
      <div>
        <h2 className="mb-3 font-display text-2xl text-ink">
          Trend
          <InfoTooltip text={TIP_TREND_SERIES} />
        </h2>
        <p className="mb-4 text-sm text-ink/55">
          Geglättete Entwicklung der Umfragewerte über die Zeit
        </p>
        {hasTrend ? (
          <div className="rounded-xl border border-ink/10 bg-mist/50 p-2">
            <TrendLineChart parties={trends.parties} />
          </div>
        ) : (
          <p className="text-sm text-ink/50">Kein Trendverlauf verfügbar.</p>
        )}
      </div>

      {averages ? (
        <div>
          <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
            <div>
              <h2 className="font-display text-2xl text-ink">
                Umfragemittelwert
                <InfoTooltip text={TIP_AVERAGES_TREND} />
              </h2>
              <p className="mt-1 text-sm text-ink/55">
                Stand {averages.as_of} · Ø %, Trend und Swing
              </p>
            </div>
            <ExportButtons
              onCsv={() => exportAverages("csv")}
              onJson={() => exportAverages("json")}
            />
          </div>
          <div className="overflow-x-auto rounded-lg border border-ink/10">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-ink/5 text-ink/60">
                <tr>
                  <th className="px-3 py-2">Partei</th>
                  <th className="px-3 py-2">
                    Ø %
                    <InfoTooltip text={TIP_AVERAGES_TREND} />
                  </th>
                  <th className="px-3 py-2">
                    Trend %
                    <InfoTooltip text={TIP_AVERAGES_TREND} />
                  </th>
                  <th className="px-3 py-2">n</th>
                  <th className="px-3 py-2">
                    Swing
                    <InfoTooltip text={TIP_SWING} />
                  </th>
                </tr>
              </thead>
              <tbody>
                {averages.parties.map((p) => (
                  <tr key={p.party_id} className="border-t border-ink/5">
                    <td className="px-3 py-2">
                      <span
                        className={`mr-2 ${PARTY_SWATCH_CLASS} h-2 w-2`}
                        style={{ background: partyColor(p.party_name) }}
                      />
                      {p.party_name}
                    </td>
                    <td className="px-3 py-2 tabular-nums">
                      {p.average_share.toFixed(1)}
                    </td>
                    <td className="px-3 py-2 tabular-nums">
                      {p.trend_share?.toFixed(1) ?? "—"}
                    </td>
                    <td className="px-3 py-2 tabular-nums">{p.n_surveys}</td>
                    <td className="px-3 py-2 tabular-nums">
                      {p.swing != null ? p.swing.toFixed(1) : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}

      <RawSurveysTable parliamentId={parliamentId} defaultOpen />
    </section>
  );
}
