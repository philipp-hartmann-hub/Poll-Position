"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { partyColor } from "@/lib/colors";
import { leftRightPosition } from "@/lib/partyPositions";

type TrendPoint = { as_of: string; [party: string]: string | number };

export function TrendChart({
  series,
  parties,
}: {
  series: TrendPoint[];
  parties: string[];
}) {
  if (!series.length) {
    return <p className="text-sm text-ink/50">Keine Trenddaten.</p>;
  }
  return (
    <div className="h-80 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={series} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#0f1c2e22" />
          <XAxis dataKey="as_of" tick={{ fontSize: 11 }} minTickGap={32} />
          <YAxis tick={{ fontSize: 11 }} unit="%" width={40} />
          <Tooltip />
          <Legend />
          {parties.map((p) => (
            <Line
              key={p}
              type="monotone"
              dataKey={p}
              stroke={partyColor(p)}
              strokeWidth={2}
              dot={false}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function TrendLineChart({
  parties,
}: {
  parties: {
    party_id: string;
    party_name: string;
    points: { as_of: string; trend_share: number }[];
  }[];
}) {
  const dates = Array.from(
    new Set(parties.flatMap((p) => p.points.map((pt) => pt.as_of))),
  ).sort();
  const series: TrendPoint[] = dates.map((as_of) => {
    const row: TrendPoint = { as_of };
    for (const p of parties) {
      const hit = p.points.find((pt) => pt.as_of === as_of);
      if (hit != null) row[p.party_name] = Number(hit.trend_share.toFixed(1));
    }
    return row;
  });
  return <TrendChart series={series} parties={parties.map((p) => p.party_name)} />;
}

export function SeatsBarChart({ seats }: { seats: Record<string, number> }) {
  const data = Object.entries(seats)
    .filter(([, n]) => n > 0)
    .sort((a, b) => b[1] - a[1])
    .map(([name, value]) => ({ name, value }));
  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 40 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#0f1c2e22" />
          <XAxis dataKey="name" tick={{ fontSize: 11 }} angle={-25} textAnchor="end" height={50} />
          <YAxis tick={{ fontSize: 11 }} width={36} />
          <Tooltip />
          <Bar dataKey="value" radius={[4, 4, 0, 0]}>
            {data.map((d) => (
              <Cell key={d.name} fill={partyColor(d.name)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

/** Halbkreis-Flächen (Donut): Keile proportional zu Sitzen, links→rechts. */
export function Hemicycle({
  seats,
  highlightParties,
}: {
  seats: Record<string, number>;
  /** Wenn gesetzt: nur diese Parteien voll sichtbar, übrige mit Opacity 0.25 */
  highlightParties?: string[];
}) {
  const items = Object.entries(seats)
    .filter(([, n]) => n > 0)
    .sort((a, b) => {
      const lr = leftRightPosition(a[0]) - leftRightPosition(b[0]);
      if (lr !== 0) return lr;
      return a[0].localeCompare(b[0], "de");
    });
  const total = items.reduce((s, [, n]) => s + n, 0) || 1;
  const highlightSet =
    highlightParties && highlightParties.length > 0
      ? new Set(highlightParties)
      : null;

  const data = items.map(([name, value]) => ({
    name,
    value,
    pct: (value / total) * 100,
  }));

  return (
    <div className="w-full">
      <div className="h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
            <Pie
              data={data}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="100%"
              startAngle={180}
              endAngle={0}
              innerRadius="55%"
              outerRadius="100%"
              paddingAngle={0.6}
              stroke="#f3efe6"
              strokeWidth={1}
              isAnimationActive={false}
            >
              {data.map((d) => {
                const dimmed = Boolean(
                  highlightSet && !highlightSet.has(d.name),
                );
                return (
                  <Cell
                    key={d.name}
                    fill={partyColor(d.name)}
                    fillOpacity={dimmed ? 0.25 : 1}
                  />
                );
              })}
            </Pie>
            <Tooltip
              formatter={(value: number, name: string, item) => {
                const pct = Number(item?.payload?.pct ?? 0).toFixed(1);
                return [`${value} Sitze (${pct} %)`, name];
              }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm text-ink/80">
        {items.map(([name, n]) => {
          const dimmed = highlightSet && !highlightSet.has(name);
          return (
            <li
              key={name}
              className="flex items-center gap-1.5"
              style={{ opacity: dimmed ? 0.35 : 1 }}
            >
              <span
                className="inline-block h-2.5 w-2.5 rounded-full"
                style={{ background: partyColor(name) }}
              />
              <span className="font-medium">{name}</span>
              <span className="text-ink/50">{n}</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
