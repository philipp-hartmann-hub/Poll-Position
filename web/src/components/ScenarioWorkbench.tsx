"use client";

import { useEffect, useMemo, useState } from "react";
import {
  fetchAverages,
  fetchParliaments,
  postScenario,
  type Parliament,
  type ScenarioResponse,
} from "@/lib/api";
import { Hemicycle, SeatsBarChart } from "@/components/charts";
import { labelPartyId } from "@/lib/colors";

export function ScenarioWorkbench() {
  const [parliaments, setParliaments] = useState<Parliament[]>([]);
  const [parliamentId, setParliamentId] = useState("de_bundestag");
  const [shares, setShares] = useState<Record<string, number>>({});
  const [names, setNames] = useState<Record<string, string>>({});
  const [result, setResult] = useState<ScenarioResponse | null>(null);
  const [applyExclusions, setApplyExclusions] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [highlightParties, setHighlightParties] = useState<string[] | null>(
    null,
  );

  useEffect(() => {
    void fetchParliaments().then((list) => {
      setParliaments(list.filter((p) => p.country === "DE"));
    });
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const avg = await fetchAverages(parliamentId, 120);
        if (cancelled) return;
        const next: Record<string, number> = {};
        const nm: Record<string, string> = {};
        for (const p of avg.parties.slice(0, 10)) {
          if (p.party_name === "Sonstige") continue;
          next[p.party_id] = Number(p.average_share.toFixed(1));
          nm[p.party_id] = p.party_name;
        }
        setShares(next);
        setNames(nm);
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Fehler");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [parliamentId]);

  const shareKey = useMemo(() => JSON.stringify(shares), [shares]);

  useEffect(() => {
    if (!shareKey || shareKey === "{}") return;
    const party_shares = JSON.parse(shareKey) as Record<string, number>;
    if (!Object.keys(party_shares).length) return;
    const t = setTimeout(() => {
      setBusy(true);
      setError(null);
      void postScenario({
        parliament_id: parliamentId,
        party_shares,
        apply_exclusions: applyExclusions,
      })
        .then(setResult)
        .catch((e) => setError(e instanceof Error ? e.message : "Fehler"))
        .finally(() => setBusy(false));
    }, 280);
    return () => clearTimeout(t);
  }, [shareKey, parliamentId, applyExclusions]);

  const namedSeats = useMemo(() => {
    if (!result) return {};
    const out: Record<string, number> = {};
    for (const [id, n] of Object.entries(result.seats)) {
      out[names[id] ?? labelPartyId(id)] = n;
    }
    return out;
  }, [result, names]);

  const sum = Object.values(shares).reduce((a, b) => a + b, 0);

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-end gap-4">
        <label className="text-sm">
          <span className="mb-1 block text-ink/50">Parlament</span>
          <select
            className="rounded-md border border-ink/15 bg-white px-3 py-2"
            value={parliamentId}
            onChange={(e) => setParliamentId(e.target.value)}
          >
            {parliaments.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={applyExclusions}
            onChange={(e) => setApplyExclusions(e.target.checked)}
          />
          Ausschlussregeln
        </label>
        <p className="text-sm text-ink/50">
          Summe Slider: <strong className="text-ink">{sum.toFixed(1)} %</strong>
          {busy ? " · berechnet…" : ""}
        </p>
      </div>

      {error && <p className="text-sm text-accent">{error}</p>}

      <div className="grid gap-4 sm:grid-cols-2">
        {Object.entries(shares).map(([id, value]) => (
          <label key={id} className="block text-sm">
            <span className="mb-1 flex justify-between text-ink/70">
              <span>{names[id] ?? id}</span>
              <span className="tabular-nums">{value.toFixed(1)} %</span>
            </span>
            <input
              type="range"
              min={0}
              max={40}
              step={0.1}
              value={value}
              onChange={(e) =>
                setShares((prev) => ({
                  ...prev,
                  [id]: Number(e.target.value),
                }))
              }
              className="w-full accent-sea"
            />
          </label>
        ))}
      </div>

      {result && (
        <>
          <div className="grid gap-6 lg:grid-cols-2">
            <div className="rounded-xl border border-ink/10 bg-white/50 p-4">
              <Hemicycle
                seats={namedSeats}
                highlightParties={highlightParties ?? undefined}
              />
            </div>
            <div className="rounded-xl border border-ink/10 bg-white/50 p-4">
              <SeatsBarChart seats={namedSeats} />
              <p className="mt-2 text-sm text-ink/50">
                Sitze {result.total_seats} · Mehrheit ab{" "}
                {result.majority_threshold}
              </p>
            </div>
          </div>
          <div className="overflow-x-auto rounded-lg border border-ink/10">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-ink/5 text-ink/60">
                <tr>
                  <th className="px-3 py-2">Koalition</th>
                  <th className="px-3 py-2">Sitze</th>
                </tr>
              </thead>
              <tbody>
                {result.coalitions
                  .filter((c) => !c.parties.some((p) => /sonstige$|:others$|:other$/i.test(p)))
                  .slice(0, 15)
                  .map((c, i) => (
                  <tr
                    key={i}
                    className="border-t border-ink/5 transition hover:bg-mist/40"
                    onMouseEnter={() =>
                      setHighlightParties(
                        c.parties.map((p) => names[p] ?? labelPartyId(p)),
                      )
                    }
                    onMouseLeave={() => setHighlightParties(null)}
                  >
                    <td className="px-3 py-2">
                      {c.parties.map((p) => names[p] ?? labelPartyId(p)).join(" + ")}
                    </td>
                    <td className="px-3 py-2 tabular-nums">{c.seats}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
