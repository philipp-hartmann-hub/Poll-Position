"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { geoMercator, geoPath, type GeoPermissibleObjects } from "d3-geo";
import type { Feature, FeatureCollection, Geometry } from "geojson";
import { fetchAverages, fetchLastElection } from "@/lib/api";
import { partyColor } from "@/lib/colors";
import { INK, NEUTRAL_MUTED, PAPER, PARTY_SWATCH_CLASS } from "@/lib/theme";
import { DE_PARLIAMENTS } from "@/lib/deParliaments";

const WIDTH = 560;
const HEIGHT = 720;
const NEUTRAL = NEUTRAL_MUTED;

export type GermanyMapMode = "polls" | "last-election";

type StateFeature = Feature<
  Geometry,
  { id: string; name: string; type?: string }
>;

type LandLeader = {
  parliamentId: string;
  landName: string;
  partyName: string | null;
  share: number | null;
  electionDate: string | null;
};

function isResidualPartyName(name: string): boolean {
  return name === "Sonstige" || /sonstige/i.test(name);
}

function isResidualPartyId(id: string): boolean {
  return /sonstige$|:others$|:other$/i.test(id);
}

function stateParliaments() {
  return DE_PARLIAMENTS.filter((p) => p.level_kind === "state" && p.state_code);
}

async function loadLeaderForLand(
  mode: GermanyMapMode,
  parliamentId: string,
  landName: string,
): Promise<LandLeader> {
  const empty: LandLeader = {
    parliamentId,
    landName,
    partyName: null,
    share: null,
    electionDate: null,
  };
  try {
    if (mode === "polls") {
      const avg = await fetchAverages(parliamentId);
      const top = avg.parties.find(
        (x) =>
          !isResidualPartyName(x.party_name) &&
          !isResidualPartyId(x.party_id),
      );
      return {
        ...empty,
        partyName: top?.party_name ?? null,
        share: top?.average_share ?? null,
      };
    }

    const election = await fetchLastElection(parliamentId);
    const top = Object.entries(election.vote_share_by_name ?? {})
      .filter(([name, share]) => share > 0 && !isResidualPartyName(name))
      .sort((a, b) => b[1] - a[1])[0];
    return {
      ...empty,
      partyName: top?.[0] ?? null,
      share: top?.[1] ?? null,
      electionDate: election.election_date ?? null,
    };
  } catch {
    return empty;
  }
}

export function GermanyMap({
  mode = "polls",
}: {
  mode?: GermanyMapMode;
}) {
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
        const leader = await loadLeaderForLand(mode, p.id, p.name);
        return { stateCode: p.state_code!, leader };
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
  }, [mode]);

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
  const ariaLabel =
    mode === "last-election"
      ? "Deutschlandkarte: stärkste Partei bei der letzten Wahl je Bundesland"
      : "Deutschlandkarte: stärkste Partei je Bundesland (Umfragen)";
  const noDataLabel =
    mode === "last-election" ? "Kein Wahlergebnis" : "Keine Umfragedaten";

  return (
    <div
      ref={wrapRef}
      className="relative overflow-hidden rounded-xl border border-ink/10 bg-gradient-to-b from-mist/30 to-mist/70 p-2"
    >
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        className="mx-auto h-auto w-full max-w-lg"
        role="img"
        aria-label={ariaLabel}
      >
        <title>{ariaLabel}</title>
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
              stroke={active ? INK : leader?.partyName != null ? INK : PAPER}
              strokeOpacity={active ? 1 : leader?.partyName != null ? 0.35 : 1}
              strokeWidth={active ? 1.6 : 0.9}
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
            <>
              <p className="mt-0.5 text-ink/70">
                <span
                  className={`mr-1.5 ${PARTY_SWATCH_CLASS} h-2 w-2`}
                  style={{ background: partyColor(hoverLeader.partyName) }}
                />
                {hoverLeader.partyName}
                {hoverLeader.share != null
                  ? ` · ${hoverLeader.share.toFixed(1)} %`
                  : ""}
              </p>
              {mode === "last-election" && hoverLeader.electionDate ? (
                <p className="mt-0.5 text-xs text-ink/45">
                  Wahl vom {hoverLeader.electionDate}
                </p>
              ) : null}
            </>
          ) : (
            <p className="mt-0.5 text-ink/50">{noDataLabel}</p>
          )}
        </div>
      )}
    </div>
  );
}
