"use client";

import { useEffect, useState } from "react";
import {
  fetchAverages,
  fetchCoalitions,
  fetchSeats,
  fetchTrendSeries,
  fetchUncertainty,
  type AveragesResponse,
  type CoalitionsResponse,
  type SeatsResponse,
  type TrendSeriesResponse,
  type UncertaintyResponse,
} from "@/lib/api";
import { Hemicycle, SeatsBarChart, TrendLineChart } from "@/components/charts";
import { CoalitionPanel } from "@/components/CoalitionPanel";
import { RawSurveysTable } from "@/components/RawSurveysTable";
import { ThresholdWatch } from "@/components/ThresholdWatch";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { labelPartyId, partyColor } from "@/lib/colors";

export function ParliamentAnalysis({
  parliamentId,
  title,
}: {
  parliamentId: string;
  title?: string;
}) {
  const [averages, setAverages] = useState<AveragesResponse | null>(null);
  const [trends, setTrends] = useState<TrendSeriesResponse | null>(null);
  const [seats, setSeats] = useState<SeatsResponse | null>(null);
  const [coalitions, setCoalitions] = useState<CoalitionsResponse | null>(null);
  const [uncertainty, setUncertainty] = useState<UncertaintyResponse | null>(
    null,
  );
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    (async () => {
      try {
        const [a, t, s, c, u] = await Promise.all([
          fetchAverages(parliamentId),
          fetchTrendSeries(parliamentId).catch(() => null),
          fetchSeats(parliamentId),
          fetchCoalitions(parliamentId),
          fetchUncertainty(parliamentId, 200).catch(() => null),
        ]);
        if (cancelled) return;
        setAverages(a);
        setTrends(t);
        setSeats(s);
        setCoalitions(c);
        setUncertainty(u);
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
    return <p className="text-sm text-ink/50">Lade Analyse…</p>;
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
  if (!averages || !seats || !coalitions) return null;

  const chartData = averages.parties.map((p) => ({
    name: p.party_name,
    Mittel: Number(p.average_share.toFixed(1)),
    Trend: p.trend_share != null ? Number(p.trend_share.toFixed(1)) : null,
  }));

  return (
    <div className="space-y-10">
      {title && (
        <h1 className="font-display text-3xl tracking-tight text-ink md:text-4xl">
          {title}
        </h1>
      )}

      <ThresholdWatch parliamentId={parliamentId} />

      <section>
        <h2 className="mb-3 font-display text-2xl text-ink">
          Umfragemittelwert & Trend
        </h2>
        <p className="mb-4 text-sm text-ink/55">
          Stand {averages.as_of} · gewichteter Schnitt vs. geglätteter
          Trendanteil
        </p>
        {trends && trends.parties.some((p) => p.points.length > 0) && (
          <div className="mb-4 rounded-xl border border-ink/10 bg-white/50 p-2">
            <TrendLineChart parties={trends.parties} />
          </div>
        )}
        <div className="h-80 w-full rounded-xl border border-ink/10 bg-white/50 p-2">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#0f1c2e22" />
              <XAxis dataKey="name" tick={{ fontSize: 11 }} />
              <YAxis unit="%" tick={{ fontSize: 11 }} width={40} />
              <Tooltip />
              <Legend />
              <Bar dataKey="Mittel" fill="#1a5f7a" radius={[3, 3, 0, 0]} />
              <Bar dataKey="Trend" fill="#c45c26" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="mt-4 overflow-x-auto rounded-lg border border-ink/10">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-ink/5 text-ink/60">
              <tr>
                <th className="px-3 py-2">Partei</th>
                <th className="px-3 py-2">Ø %</th>
                <th className="px-3 py-2">Trend %</th>
                <th className="px-3 py-2">n</th>
                <th className="px-3 py-2">Swing</th>
              </tr>
            </thead>
            <tbody>
              {averages.parties.map((p) => (
                <tr key={p.party_id} className="border-t border-ink/5">
                  <td className="px-3 py-2">
                    <span
                      className="mr-2 inline-block h-2 w-2 rounded-full"
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
        <div className="mt-4">
          <RawSurveysTable parliamentId={parliamentId} />
        </div>
      </section>

      <section>
        <h2 className="mb-3 font-display text-2xl text-ink">Sitzprojektion</h2>
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="rounded-xl border border-ink/10 bg-white/50 p-4">
            <Hemicycle seats={seats.seats_by_name} />
          </div>
          <div className="rounded-xl border border-ink/10 bg-white/50 p-4">
            <SeatsBarChart seats={seats.seats_by_name} />
            <p className="mt-2 text-sm text-ink/50">
              Sitze gesamt: {seats.total_seats}
            </p>
          </div>
        </div>
      </section>

      <CoalitionPanel
        parliamentId={parliamentId}
        initial={{
          majority_threshold: coalitions.majority_threshold,
          excluded_by_rules: coalitions.excluded_by_rules,
          coalitions: coalitions.coalitions,
        }}
      />

      {uncertainty && uncertainty.coalition_probabilities.length > 0 && (
        <section>
          <h2 className="mb-3 font-display text-2xl text-ink">
            Unsicherheit (Monte-Carlo)
          </h2>
          <p className="mb-3 text-sm text-ink/55">
            {uncertainty.n_simulations} Simulationen ·
            Mehrheitswahrscheinlichkeiten
          </p>
          <ul className="space-y-2 text-sm">
            {uncertainty.coalition_probabilities.slice(0, 8).map((c, i) => (
              <li
                key={i}
                className="flex items-center justify-between rounded-lg border border-ink/10 bg-white/40 px-3 py-2"
              >
                <span>{c.parties.map(labelPartyId).join(" + ")}</span>
                <span className="tabular-nums font-medium">
                  {(c.majority_probability * 100).toFixed(0)} %
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
