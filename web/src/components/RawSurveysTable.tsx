"use client";

import { useCallback, useEffect, useState } from "react";
import { fetchRawSurveys, type RawSurveysResponse } from "@/lib/api";
import { partyColor } from "@/lib/colors";

const PAGE_SIZE = 20;

function formatRange(from: string | null, to: string | null): string {
  if (from && to) return `${from} – ${to}`;
  return from ?? to ?? "—";
}

export function RawSurveysTable({ parliamentId }: { parliamentId: string }) {
  const [open, setOpen] = useState(false);
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<RawSurveysResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    async (nextOffset: number) => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetchRawSurveys(parliamentId, {
          limit: PAGE_SIZE,
          offset: nextOffset,
        });
        setData(res);
        setOffset(nextOffset);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Laden fehlgeschlagen");
      } finally {
        setLoading(false);
      }
    },
    [parliamentId],
  );

  useEffect(() => {
    if (!open) return;
    void load(0);
  }, [open, load]);

  return (
    <details
      className="rounded-lg border border-ink/10 bg-white/40"
      open={open}
      onToggle={(e) => setOpen((e.target as HTMLDetailsElement).open)}
    >
      <summary className="cursor-pointer px-3 py-2 text-sm font-medium text-ink/80">
        Einzelne Umfragen anzeigen
      </summary>
      <div className="border-t border-ink/10 px-3 py-3">
        {error && <p className="text-sm text-accent">{error}</p>}
        {loading && !data && (
          <p className="text-sm text-ink/50">Lade Umfragen…</p>
        )}
        {data && (
          <>
            <div className="overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead className="bg-ink/5 text-ink/60">
                  <tr>
                    <th className="px-2 py-2 font-medium">Institut</th>
                    <th className="px-2 py-2 font-medium">Zeitraum</th>
                    <th className="px-2 py-2 font-medium">Veröffentlichung</th>
                    <th className="px-2 py-2 font-medium">Stichprobe</th>
                    <th className="px-2 py-2 font-medium">Werte</th>
                    <th className="px-2 py-2 font-medium">Quelle</th>
                  </tr>
                </thead>
                <tbody>
                  {data.surveys.map((s) => (
                    <tr key={s.id} className="border-t border-ink/5 align-top">
                      <td className="px-2 py-2">{s.institute_name ?? s.institute_id}</td>
                      <td className="px-2 py-2 tabular-nums whitespace-nowrap">
                        {formatRange(s.field_date_from, s.field_date_to)}
                      </td>
                      <td className="px-2 py-2 tabular-nums whitespace-nowrap">
                        {s.publication_date}
                      </td>
                      <td className="px-2 py-2 tabular-nums">
                        {s.sample_size?.toLocaleString("de-DE") ?? "—"}
                      </td>
                      <td className="px-2 py-2">
                        <div className="flex flex-wrap gap-x-3 gap-y-1">
                          {s.results.map((r) => (
                            <span key={r.party_id} className="whitespace-nowrap">
                              <span
                                className="mr-1 inline-block h-1.5 w-1.5 rounded-full"
                                style={{ background: partyColor(r.party_name) }}
                              />
                              {r.party_name} {r.share.toFixed(1)}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td className="px-2 py-2">
                        {s.source_url ? (
                          <a
                            href={s.source_url}
                            className="text-accent underline-offset-2 hover:underline"
                            target="_blank"
                            rel="noreferrer"
                          >
                            Link
                          </a>
                        ) : (
                          "—"
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="mt-3 flex items-center justify-between text-xs text-ink/55">
              <span>
                {data.total === 0
                  ? "Keine Umfragen"
                  : `${data.offset + 1}–${Math.min(data.offset + data.surveys.length, data.total)} von ${data.total}`}
                {loading ? " · lädt…" : ""}
              </span>
              <div className="flex gap-2">
                <button
                  type="button"
                  className="rounded border border-ink/15 px-2 py-1 disabled:opacity-40"
                  disabled={offset === 0 || loading}
                  onClick={() => void load(Math.max(0, offset - PAGE_SIZE))}
                >
                  Zurück
                </button>
                <button
                  type="button"
                  className="rounded border border-ink/15 px-2 py-1 disabled:opacity-40"
                  disabled={offset + PAGE_SIZE >= data.total || loading}
                  onClick={() => void load(offset + PAGE_SIZE)}
                >
                  Weiter
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </details>
  );
}
