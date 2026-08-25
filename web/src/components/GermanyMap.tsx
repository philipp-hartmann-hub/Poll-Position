"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { geoMercator, geoPath, type GeoPermissibleObjects } from "d3-geo";
import type { Feature, FeatureCollection, Geometry } from "geojson";
import { fetchAverages } from "@/lib/api";
import { partyColor } from "@/lib/colors";
import { DE_PARLIAMENTS } from "@/lib/deParliaments";

const WIDTH = 560;
const HEIGHT = 720;
const NEUTRAL = "#c5c0b6";

type StateFeature = Feature<
  Geometry,
  { id: string; name: string; type?: string }
>;

type LandLeader = {
  parliamentId: string;
  landName: string;
  partyName: string | null;
  share: number | null;
};

function stateParliaments() {
  return DE_PARLIAMENTS.filter((p) => p.level_kind === "state" && p.state_code);
}

export function GermanyMap() {
  const router = useRouter();
  const wrapRef = useRef<HTMLDivElement>(null);
  const [geo, setGeo] = useState<FeatureCollection | null>(null);
  const [leaders, setLeaders] = useState<Map<string, LandLeader>>(new Map());
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

  useEffect(() => {
    let cancelled = false;
    const states = stateParliaments();
    void Promise.all(
      states.map(async (p) => {
        try {
          const avg = await fetchAverages(p.id);
          const top = avg.parties.find(
            (x) =>
              x.party_name !== "Sonstige" &&
              !/sonstige$|:others$|:other$/i.test(x.party_id),
          );
          return {
            stateCode: p.state_code!,
            leader: {
              parliamentId: p.id,
              landName: p.name,
              partyName: top?.party_name ?? null,
              share: top?.average_share ?? null,
            } satisfies LandLeader,
          };
        } catch {
          return {
            stateCode: p.state_code!,
            leader: {
              parliamentId: p.id,
              landName: p.name,
              partyName: null,
              share: null,
            } satisfies LandLeader,
          };
        }
      }),
    ).then((rows) => {
      if (cancelled) return;
      const m = new Map<string, LandLeader>();
      for (const row of rows) m.set(row.stateCode, row.leader);
      setLeaders(m);
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

  const hoverLeader = hoverId ? leaders.get(hoverId) : undefined;
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
        aria-label="Deutschlandkarte: stärkste Partei je Bundesland"
      >
        <title>Deutschlandkarte nach stärkster Partei</title>
        {(geo.features as StateFeature[]).map((feature) => {
          const stateCode = feature.properties.id;
          const parl = byStateCode.get(stateCode);
          const leader = leaders.get(stateCode);
          const fill =
            leader?.partyName != null ? partyColor(leader.partyName) : NEUTRAL;
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
              style={{ cursor: parl ? "pointer" : "default" }}
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
                if (parl) router.push(`/parlament/${parl.id}`);
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
            {hoverFeature?.properties.name ?? hoverLeader?.landName ?? hoverId}
          </p>
          {hoverLeader?.partyName ? (
            <p className="mt-0.5 text-ink/70">
              <span
                className="mr-1.5 inline-block h-2 w-2 rounded-full"
                style={{ background: partyColor(hoverLeader.partyName) }}
              />
              {hoverLeader.partyName}
              {hoverLeader.share != null
                ? ` · ${hoverLeader.share.toFixed(1)} %`
                : ""}
            </p>
          ) : (
            <p className="mt-0.5 text-ink/50">Keine Umfragedaten</p>
          )}
        </div>
      )}
    </div>
  );
}
