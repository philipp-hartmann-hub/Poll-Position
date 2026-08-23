"use client";

import { useMemo, useState } from "react";
import type { EuropeOverviewResponse } from "@/lib/api";
import { familyColor } from "@/lib/colors";

/** Lon/lat → SVG (einfache Äquirectangular-Näherung für Mitteleuropa). */
const CENTROIDS: Record<string, [number, number]> = {
  DE: [10.45, 51.16],
  AT: [14.55, 47.52],
  FR: [2.21, 46.23],
  IT: [12.57, 41.87],
  ES: [-3.75, 40.46],
  NL: [5.29, 52.13],
  PL: [19.15, 51.92],
  SE: [18.64, 60.13],
  PT: [-8.22, 39.4],
  BE: [4.47, 50.5],
};

function project(lon: number, lat: number): [number, number] {
  const x = ((lon + 12) / 36) * 800;
  const y = ((62 - lat) / 28) * 520;
  return [x, y];
}

export function EuropeMap({ data }: { data: EuropeOverviewResponse }) {
  const [selected, setSelected] = useState<string | null>(
    data.countries.find((c) => c.country === "DE")?.country ??
      data.countries[0]?.country ??
      null,
  );

  const byCountry = useMemo(() => {
    return new Map(data.countries.map((c) => [c.country, c]));
  }, [data]);

  const detail = selected ? byCountry.get(selected) : undefined;

  return (
    <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
      <div className="overflow-hidden rounded-xl border border-ink/10 bg-gradient-to-b from-mist/40 to-white/60 p-2">
        <svg viewBox="0 0 800 520" className="h-auto w-full" role="img">
          <title>Europa nach Parteienfamilie</title>
          <rect width="800" height="520" fill="transparent" />
          {data.countries.map((c) => {
            const coords = CENTROIDS[c.country];
            if (!coords) return null;
            const [x, y] = project(coords[0], coords[1]);
            const r = 18 + Math.min(c.family_share, 40) * 0.35;
            const active = selected === c.country;
            return (
              <g
                key={c.country}
                onClick={() => setSelected(c.country)}
                style={{ cursor: "pointer" }}
              >
                <circle
                  cx={x}
                  cy={y}
                  r={r}
                  fill={familyColor(c.top_family)}
                  fillOpacity={active ? 0.95 : 0.75}
                  stroke={active ? "#0f1c2e" : "#fff"}
                  strokeWidth={active ? 2.5 : 1.5}
                />
                <text
                  x={x}
                  y={y + 4}
                  textAnchor="middle"
                  className="fill-white text-[11px] font-semibold"
                  style={{ pointerEvents: "none" }}
                >
                  {c.country}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
      <div>
        <h2 className="font-display text-2xl text-ink">
          {detail ? `Detail: ${detail.country}` : "Land wählen"}
        </h2>
        {detail ? (
          <dl className="mt-4 space-y-3 text-sm">
            <div>
              <dt className="text-ink/50">Stärkste Partei</dt>
              <dd className="text-lg text-ink">
                {detail.top_party_name}{" "}
                <span className="text-ink/50">
                  ({detail.top_party_share.toFixed(1)} %)
                </span>
              </dd>
            </div>
            <div>
              <dt className="text-ink/50">Parteienfamilie</dt>
              <dd className="flex items-center gap-2 text-lg text-ink">
                <span
                  className="inline-block h-3 w-3 rounded-full"
                  style={{ background: familyColor(detail.top_family) }}
                />
                {detail.top_family} ({detail.family_share.toFixed(1)} %)
              </dd>
            </div>
            <p className="text-xs text-ink/45">Stand: {data.as_of}</p>
          </dl>
        ) : (
          <p className="mt-2 text-sm text-ink/50">Klicke ein Land auf der Karte.</p>
        )}
        <ul className="mt-6 space-y-1 text-sm">
          {data.countries.map((c) => (
            <li key={c.country}>
              <button
                type="button"
                onClick={() => setSelected(c.country)}
                className={`w-full rounded-md px-2 py-1.5 text-left transition hover:bg-mist/50 ${
                  selected === c.country ? "bg-mist/70" : ""
                }`}
              >
                <span className="font-medium">{c.country}</span> — {c.top_family} /{" "}
                {c.top_party_name}
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
