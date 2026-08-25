"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { geoMercator, geoPath, type GeoPermissibleObjects } from "d3-geo";
import type { Feature, FeatureCollection, Geometry } from "geojson";
import type { BundesratLand, BundesratLandVote } from "@/lib/api";
import {
  stanceFill,
  stanceLabel,
} from "@/lib/bundesratColors";
import { DE_PARLIAMENTS } from "@/lib/deParliaments";

const WIDTH = 560;
const HEIGHT = 720;
const NEUTRAL = "#c5c0b6";

type StateFeature = Feature<
  Geometry,
  { id: string; name: string; type?: string }
>;

function stateParliaments() {
  return DE_PARLIAMENTS.filter((p) => p.level_kind === "state" && p.state_code);
}

export function BundesratMap({
  laender,
  votes,
  onLandClick,
}: {
  laender: BundesratLand[];
  votes: BundesratLandVote[];
  onLandClick?: (parliamentId: string) => void;
}) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const [geo, setGeo] = useState<FeatureCollection | null>(null);
  const [hoverId, setHoverId] = useState<string | null>(null);
  const [tip, setTip] = useState<{ x: number; y: number } | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const byStateCode = useMemo(() => {
    const m = new Map<string, (typeof DE_PARLIAMENTS)[number]>();
    for (const p of stateParliaments()) {
      if (p.state_code) m.set(p.state_code, p);
    }
    return m;
  }, []);

  const landByParliamentId = useMemo(() => {
    const m = new Map<string, BundesratLand>();
    for (const land of laender) m.set(land.parliament_id, land);
    return m;
  }, [laender]);

  const voteByParliamentId = useMemo(() => {
    const m = new Map<string, BundesratLandVote>();
    for (const v of votes) m.set(v.parliament_id, v);
    return m;
  }, [votes]);

  useEffect(() => {
    let cancelled = false;
    void fetch("/geo/bundeslaender.geojson")
      .then(async (r) => {
        if (!r.ok) throw new Error(`GeoJSON ${r.status}`);
        return r.json() as Promise<FeatureCollection>;
      })
      .then((g) => {
        if (!cancelled) setGeo(g);
      })
      .catch((e) => {
        if (!cancelled) {
          setLoadError(
            e instanceof Error ? e.message : "Karte laden fehlgeschlagen",
          );
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const pathGen = useMemo(() => {
    if (!geo) return null;
    const projection = geoMercator().fitExtent(
      [
        [12, 12],
        [WIDTH - 12, HEIGHT - 12],
      ],
      geo as GeoPermissibleObjects,
    );
    return geoPath(projection);
  }, [geo]);

  function updateTip(clientX: number, clientY: number) {
    const rect = wrapRef.current?.getBoundingClientRect();
    if (!rect) return;
    setTip({ x: clientX - rect.left, y: clientY - rect.top });
  }

  const hoverParl = hoverId ? byStateCode.get(hoverId) : undefined;
  const hoverLand = hoverParl
    ? landByParliamentId.get(hoverParl.id)
    : undefined;
  const hoverVote = hoverParl
    ? voteByParliamentId.get(hoverParl.id)
    : undefined;
  const hoverFeature = geo?.features.find(
    (f) => (f as StateFeature).properties?.id === hoverId,
  ) as StateFeature | undefined;

  if (loadError) {
    return <p className="text-sm text-accent">{loadError}</p>;
  }
  if (!geo || !pathGen) {
    return <p className="text-sm text-ink/50">Lade Karte…</p>;
  }

  const tipMaxLeft = Math.max((wrapRef.current?.clientWidth ?? 320) - 170, 8);

  return (
    <div
      ref={wrapRef}
      className="relative overflow-hidden rounded-xl border border-ink/10 bg-gradient-to-b from-mist/30 to-white/70 p-2"
    >
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        className="mx-auto h-auto w-full max-w-lg"
        role="img"
        aria-label="Deutschlandkarte: Bundesratsstimmen je Land"
      >
        <title>Bundesrat nach Ja / Nein / Enthaltung</title>
        {(geo.features as StateFeature[]).map((feature) => {
          const stateCode = feature.properties.id;
          const parl = byStateCode.get(stateCode);
          const vote = parl ? voteByParliamentId.get(parl.id) : undefined;
          const fill = vote ? stanceFill(vote.stance) : NEUTRAL;
          const active = hoverId === stateCode;
          const d = pathGen(feature as GeoPermissibleObjects) ?? "";
          return (
            <path
              key={stateCode}
              d={d}
              fill={fill}
              fillOpacity={active ? 0.95 : 0.82}
              stroke={active ? "#0f1c2e" : "#f3efe6"}
              strokeWidth={active ? 1.6 : 0.8}
              style={{ cursor: parl && onLandClick ? "pointer" : "default" }}
              onMouseEnter={(e) => {
                setHoverId(stateCode);
                updateTip(e.clientX, e.clientY);
              }}
              onMouseMove={(e) => updateTip(e.clientX, e.clientY)}
              onMouseLeave={() => {
                setHoverId(null);
                setTip(null);
              }}
              onClick={() => {
                if (parl && onLandClick) onLandClick(parl.id);
              }}
            />
          );
        })}
      </svg>

      {hoverId && tip && (
        <div
          className="pointer-events-none absolute z-10 max-w-[14rem] rounded-md border border-ink/10 bg-paper/95 px-3 py-2 text-sm shadow-sm backdrop-blur"
          style={{
            left: Math.min(tip.x + 14, tipMaxLeft),
            top: Math.max(tip.y - 12, 8),
          }}
        >
          <p className="font-medium text-ink">
            {hoverFeature?.properties.name ??
              hoverLand?.name ??
              hoverVote?.name ??
              hoverId}
          </p>
          <p className="mt-0.5 text-ink/70">
            {hoverVote?.government_label ??
              hoverLand?.default_government_label ??
              "—"}
          </p>
          {hoverVote ? (
            <p className="mt-1 text-ink/70">
              <span
                className="mr-1.5 inline-block h-2 w-2 rounded-full"
                style={{ background: stanceFill(hoverVote.stance) }}
              />
              {stanceLabel(hoverVote.stance)}
              {hoverVote.votes != null ? ` · ${hoverVote.votes} Stimmen` : ""}
            </p>
          ) : (
            <p className="mt-0.5 text-ink/50">Keine Stimmdaten</p>
          )}
        </div>
      )}

      <ul className="mt-2 flex flex-wrap gap-3 px-1 text-xs text-ink/60">
        <li className="flex items-center gap-1.5">
          <span
            className="inline-block h-2.5 w-2.5 rounded-sm"
            style={{ background: stanceFill("yes") }}
          />
          Ja
        </li>
        <li className="flex items-center gap-1.5">
          <span
            className="inline-block h-2.5 w-2.5 rounded-sm"
            style={{ background: stanceFill("no") }}
          />
          Nein
        </li>
        <li className="flex items-center gap-1.5">
          <span
            className="inline-block h-2.5 w-2.5 rounded-sm"
            style={{ background: stanceFill("abstain") }}
          />
          Enthaltung
        </li>
      </ul>
    </div>
  );
}
