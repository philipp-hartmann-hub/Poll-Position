"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
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

/** Halbkreis: Winkelkeile proportional zu Sitzen, Reihenfolge links→rechts. */
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

  const points: { x: number; y: number; party: string; opacity: number }[] = [];

  // Winkel von π (links) nach 0 (rechts)
  let angleStart = Math.PI;
  for (const [party, n] of items) {
    const wedge = (n / total) * Math.PI;
    const angleEnd = angleStart - wedge;
    const opacity =
      highlightSet && !highlightSet.has(party) ? 0.25 : 1;

    const rows = Math.max(3, Math.ceil(Math.sqrt(n)));
    let remaining = n;
    let placed = 0;
    for (let row = 0; row < rows && remaining > 0; row++) {
      const rowsLeft = rows - row;
      const nInRow = Math.max(1, Math.ceil(remaining / rowsLeft));
      const take = Math.min(nInRow, remaining);
      const radius = 0.42 + (0.52 * row) / Math.max(rows - 1, 1);
      for (let i = 0; i < take; i++) {
        const t = (i + 0.5) / take;
        const angle = angleStart - t * wedge;
        points.push({
          x: radius * Math.cos(angle),
          y: radius * Math.sin(angle),
          party,
          opacity,
        });
        placed += 1;
      }
      remaining -= take;
    }
    // Sicherheitsnetz falls Rundung Sitze übrig lässt
    while (placed < n) {
      const angle = (angleStart + angleEnd) / 2;
      points.push({
        x: 0.95 * Math.cos(angle),
        y: 0.95 * Math.sin(angle),
        party,
        opacity,
      });
      placed += 1;
    }
    angleStart = angleEnd;
  }

  return (
    <div className="w-full">
      <svg viewBox="-1.2 -0.15 2.4 1.4" className="h-72 w-full">
        {points.map((p, i) => (
          <circle
            key={i}
            cx={p.x}
            cy={p.y}
            r={0.028}
            fill={partyColor(p.party)}
            opacity={p.opacity}
          >
            <title>{p.party}</title>
          </circle>
        ))}
      </svg>
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
