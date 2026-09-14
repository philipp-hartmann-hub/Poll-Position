"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
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
import { displayPartyName, partyColor, relabelSeatMap } from "@/lib/colors";
import { leftRightPosition } from "@/lib/partyPositions";
import { INK, PAPER, PARTY_SWATCH_CLASS } from "@/lib/theme";

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
          <CartesianGrid strokeDasharray="3 3" stroke={`${INK}22`} />
          <XAxis
            dataKey="as_of"
            tick={{ fontSize: 11, fill: INK }}
            minTickGap={32}
          />
          <YAxis tick={{ fontSize: 11, fill: INK }} unit="%" width={40} />
          <Tooltip
            contentStyle={{
              background: PAPER,
              border: `1px solid ${INK}26`,
              borderRadius: 8,
            }}
          />
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
  const data = Object.entries(relabelSeatMap(seats))
    .filter(([, n]) => n > 0)
    .sort((a, b) => b[1] - a[1])
    .map(([name, value]) => ({ name, value }));
  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 40 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={`${INK}22`} />
          <XAxis
            dataKey="name"
            tick={{ fontSize: 11, fill: INK }}
            angle={-25}
            textAnchor="end"
            height={50}
          />
          <YAxis tick={{ fontSize: 11, fill: INK }} width={36} />
          <Tooltip
            contentStyle={{
              background: PAPER,
              border: `1px solid ${INK}26`,
              borderRadius: 8,
            }}
          />
          <Bar dataKey="value" radius={[4, 4, 0, 0]} stroke={INK} strokeOpacity={0.3} strokeWidth={1}>
            {data.map((d) => (
              <Cell key={d.name} fill={partyColor(d.name)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

/** Umfrage-Stimmenanteile (%) — ein Balken je Partei in Parteifarbe, absteigend. */
export function PollShareBarChart({
  parties,
}: {
  parties: { party_name: string; share: number }[];
}) {
  const data = [...parties]
    .filter((p) => p.share > 0)
    .sort((a, b) => b.share - a.share)
    .map((p) => ({
      name: p.party_name,
      share: Number(p.share.toFixed(1)),
    }));
  if (!data.length) {
    return <p className="text-sm text-ink/50">Keine Umfrageanteile.</p>;
  }
  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          margin={{ top: 22, right: 8, left: 0, bottom: 40 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke={`${INK}22`} />
          <XAxis
            dataKey="name"
            tick={{ fontSize: 11, fill: INK }}
            angle={-25}
            textAnchor="end"
            height={50}
          />
          <YAxis
            unit="%"
            tick={{ fontSize: 11, fill: INK }}
            width={40}
            domain={[0, "auto"]}
          />
          <Tooltip
            formatter={(value: number) => [`${value} %`, "Anteil"]}
            contentStyle={{
              background: PAPER,
              border: `1px solid ${INK}26`,
              borderRadius: 8,
            }}
          />
          <Bar
            dataKey="share"
            radius={[4, 4, 0, 0]}
            stroke={INK}
            strokeOpacity={0.3}
            strokeWidth={1}
          >
            <LabelList
              dataKey="share"
              position="top"
              formatter={(v: number) => `${v}%`}
              style={{ fill: INK, fontSize: 11 }}
            />
            {data.map((d) => (
              <Cell key={d.name} fill={partyColor(d.name)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export type HemicycleStyle = "official" | "projection";

/** Halbkreis-Flächen (Donut): Keile proportional zu Sitzen, links→rechts. */
export function Hemicycle({
  seats,
  highlightParties,
  size = "md",
  style = "official",
}: {
  seats: Record<string, number>;
  /** Wenn gesetzt: nur diese Parteien voll sichtbar, übrige mit Opacity 0.25 */
  highlightParties?: string[];
  /** Kompakte Variante für Nebeneinander-Vergleiche */
  size?: "sm" | "md";
  /**
   * ``official``: volle Partei-Farben (amtliches Ergebnis).
   * ``projection``: leichte Schraffur + gestrichelter Rand (Umfrage).
   */
  style?: HemicycleStyle;
}) {
  const labeled = relabelSeatMap(seats);
  const highlightLabeled = highlightParties?.map((p) =>
    displayPartyName(p, p),
  );
  const items = Object.entries(labeled)
    .filter(([, n]) => n > 0)
    .sort((a, b) => {
      const lr = leftRightPosition(a[0]) - leftRightPosition(b[0]);
      if (lr !== 0) return lr;
      return a[0].localeCompare(b[0], "de");
    });
  const total = items.reduce((s, [, n]) => s + n, 0) || 1;
  const highlightSet =
    highlightLabeled && highlightLabeled.length > 0
      ? new Set(highlightLabeled)
      : null;

  const data = items.map(([name, value]) => ({
    name,
    value,
    pct: (value / total) * 100,
  }));

  const chartH = size === "sm" ? "h-40" : "h-72";
  const legendCls =
    size === "sm"
      ? "mt-1.5 flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-ink/80"
      : "mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm text-ink/80";

  const isProjection = style === "projection";
  const hatchId = "hemicycle-proj-hatch";

  return (
    <div className="w-full">
      <div className={`${chartH} w-full`}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
            {isProjection ? (
              <defs>
                <pattern
                  id={hatchId}
                  width="7"
                  height="7"
                  patternUnits="userSpaceOnUse"
                  patternTransform="rotate(40)"
                >
                  <line
                    x1="0"
                    y1="0"
                    x2="0"
                    y2="7"
                    stroke={INK}
                    strokeWidth="1.25"
                    strokeOpacity="0.22"
                  />
                </pattern>
              </defs>
            ) : null}
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
              stroke={isProjection ? INK : PAPER}
              strokeWidth={isProjection ? 1.25 : 1}
              strokeDasharray={isProjection ? "3.5 2.5" : undefined}
              strokeOpacity={isProjection ? 0.55 : 1}
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
                    stroke={INK}
                    strokeOpacity={0.3}
                    strokeWidth={0.75}
                  />
                );
              })}
            </Pie>
            {isProjection ? (
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
                fill={`url(#${hatchId})`}
                stroke="none"
                isAnimationActive={false}
                legendType="none"
                tooltipType="none"
              />
            ) : null}
            <Tooltip
              contentStyle={{
                background: PAPER,
                border: `1px solid ${INK}26`,
                borderRadius: 8,
              }}
              formatter={(value: number, name: string, item) => {
                const pct = Number(item?.payload?.pct ?? 0).toFixed(1);
                return [`${value} Sitze (${pct} %)`, name];
              }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <ul className={legendCls}>
        {items.map(([name, n]) => {
          const dimmed = highlightSet && !highlightSet.has(name);
          return (
            <li
              key={name}
              className="flex items-center gap-1.5"
              style={{ opacity: dimmed ? 0.35 : 1 }}
            >
              <span
                className={`${PARTY_SWATCH_CLASS} h-2.5 w-2.5`}
                style={{ background: partyColor(name) }}
              />
              <span className="font-medium">{name}</span>
              <span className="tabular-nums text-ink/50">{n}</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
