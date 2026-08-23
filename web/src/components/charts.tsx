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

/** Halbkreis-/Hemicycle aus Sitzzahlen (SVG). */
export function Hemicycle({ seats }: { seats: Record<string, number> }) {
  const items = Object.entries(seats)
    .filter(([, n]) => n > 0)
    .sort((a, b) => b[1] - a[1]);
  const total = items.reduce((s, [, n]) => s + n, 0) || 1;
  const seatList: string[] = [];
  for (const [name, n] of items) {
    for (let i = 0; i < n; i++) seatList.push(name);
  }
  const rows = Math.max(4, Math.ceil(Math.sqrt(total / 2)));
  const points: { x: number; y: number; party: string }[] = [];
  let idx = 0;
  for (let row = 0; row < rows; row++) {
    let nInRow = Math.max(1, Math.floor(((row + 1) / rows) * ((total * 2) / rows)));
    nInRow = Math.min(nInRow, total - idx);
    if (nInRow <= 0) break;
    const radius = 0.45 + (0.55 * row) / Math.max(rows - 1, 1);
    for (let i = 0; i < nInRow; i++) {
      if (idx >= seatList.length) break;
      const angle = (Math.PI * (i + 0.5)) / nInRow;
      points.push({
        x: radius * Math.cos(angle),
        y: radius * Math.sin(angle),
        party: seatList[idx],
      });
      idx++;
    }
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
          >
            <title>{p.party}</title>
          </circle>
        ))}
      </svg>
      <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm text-ink/80">
        {items.map(([name, n]) => (
          <li key={name} className="flex items-center gap-1.5">
            <span
              className="inline-block h-2.5 w-2.5 rounded-full"
              style={{ background: partyColor(name) }}
            />
            <span className="font-medium">{name}</span>
            <span className="text-ink/50">{n}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
