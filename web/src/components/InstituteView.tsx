"use client";

import { useEffect, useMemo, useState } from "react";
import { fetchHouseEffects, type HouseEffectsResponse } from "@/lib/api";

export function InstituteView() {
  const [parliamentId, setParliamentId] = useState("de_bundestag");
  const [data, setData] = useState<HouseEffectsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    void fetchHouseEffects(parliamentId, 14)
      .then((d) => {
        if (!cancelled) setData(d);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "Fehler");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [parliamentId]);

  const pivot = useMemo(() => {
    if (!data) return { institutes: [] as string[], parties: [] as string[], cells: new Map<string, number>() };
    const latest = new Map<string, (typeof data.effects)[0]>();
    for (const e of data.effects) {
      const key = `${e.institute_name ?? e.institute_id}|${e.party_name ?? e.party_id}`;
      const prev = latest.get(key);
      if (!prev || e.as_of >= prev.as_of) latest.set(key, e);
    }
    const institutes = [
      ...new Set(
        [...latest.values()].map((e) => e.institute_name ?? e.institute_id),
      ),
    ].sort();
    const parties = [
      ...new Set(
        [...latest.values()].map((e) => e.party_name ?? e.party_id),
      ),
    ].sort();
    const cells = new Map<string, number>();
    for (const e of latest.values()) {
      cells.set(
        `${e.institute_name ?? e.institute_id}|${e.party_name ?? e.party_id}`,
        e.house_effect,
      );
    }
    return { institutes, parties, cells };
  }, [data]);

  return (
    <div className="space-y-6">
      <label className="text-sm">
        <span className="mb-1 block text-ink/50">Parlament</span>
        <select
          className="rounded-md border border-ink/15 bg-white px-3 py-2"
          value={parliamentId}
          onChange={(e) => setParliamentId(e.target.value)}
        >
          <option value="de_bundestag">Bundestag</option>
          <option value="de_by_landtag">Bayern</option>
          <option value="de_th_landtag">Thüringen</option>
          <option value="de_nw_landtag">NRW</option>
        </select>
      </label>

      {loading && <p className="text-sm text-ink/50">Lade…</p>}
      {error && <p className="text-sm text-accent">{error}</p>}

      {data && !loading && (
        <>
          <section>
            <h2 className="mb-3 font-display text-xl text-ink">
              House Effects (pp)
            </h2>
            {pivot.institutes.length === 0 ? (
              <p className="text-sm text-ink/50">
                Keine House Effects (zu wenige Peer-Institute im Fenster).
              </p>
            ) : (
              <div className="overflow-x-auto rounded-lg border border-ink/10">
                <table className="min-w-full text-left text-sm">
                  <thead className="bg-ink/5 text-ink/60">
                    <tr>
                      <th className="px-3 py-2">Institut</th>
                      {pivot.parties.map((p) => (
                        <th key={p} className="px-3 py-2">
                          {p}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {pivot.institutes.map((inst) => (
                      <tr key={inst} className="border-t border-ink/5">
                        <td className="px-3 py-2 font-medium">{inst}</td>
                        {pivot.parties.map((p) => {
                          const v = pivot.cells.get(`${inst}|${p}`);
                          return (
                            <td key={p} className="px-3 py-2 tabular-nums">
                              {v != null ? v.toFixed(1) : "—"}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <section>
            <h2 className="mb-3 font-display text-xl text-ink">
              Backtesting (dieses Parlament)
            </h2>
            {data.accuracy.length === 0 ? (
              <p className="text-sm text-ink/50">
                Keine Backtest-Treffer für dieses Parlament.
              </p>
            ) : (
              <div className="overflow-x-auto rounded-lg border border-ink/10">
                <table className="min-w-full text-left text-sm">
                  <thead className="bg-ink/5 text-ink/60">
                    <tr>
                      <th className="px-3 py-2">Institut</th>
                      <th className="px-3 py-2">n</th>
                      <th className="px-3 py-2">MAE</th>
                      <th className="px-3 py-2">RMSE</th>
                      <th className="px-3 py-2">Score</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[...data.accuracy]
                      .sort((a, b) => a.mae - b.mae)
                      .map((row) => (
                        <tr
                          key={row.institute_id}
                          className="border-t border-ink/5"
                        >
                          <td className="px-3 py-2">
                            {row.institute_name ?? row.institute_id}
                          </td>
                          <td className="px-3 py-2 tabular-nums">
                            {row.n_comparisons}
                          </td>
                          <td className="px-3 py-2 tabular-nums">
                            {row.mae.toFixed(2)}
                          </td>
                          <td className="px-3 py-2 tabular-nums">
                            {row.rmse.toFixed(2)}
                          </td>
                          <td className="px-3 py-2 tabular-nums">
                            {row.score.toFixed(3)}
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}
