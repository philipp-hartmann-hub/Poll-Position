"use client";

import { useEffect, useState } from "react";
import { fetchTrendSeries, type TrendSeriesResponse } from "@/lib/api";
import { TrendLineChart } from "@/components/charts";
import { InfoTooltip } from "@/components/InfoTooltip";
import { RawSurveysTable } from "@/components/RawSurveysTable";
import { TIP_TREND_SERIES } from "@/lib/tooltipCopy";

/** Trendverlauf und einzelne Rohumfragen. */
export function SurveysSection({ parliamentId }: { parliamentId: string }) {
  const [trends, setTrends] = useState<TrendSeriesResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    (async () => {
      try {
        const t = await fetchTrendSeries(parliamentId).catch(() => null);
        if (cancelled) return;
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

      <RawSurveysTable parliamentId={parliamentId} defaultOpen />
    </section>
  );
}
