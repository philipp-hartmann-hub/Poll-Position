"use client";

import { useEffect, useState } from "react";
import { fetchDataFreshness, type DataFreshnessResponse } from "@/lib/api";
import { InfoTooltip } from "@/components/InfoTooltip";
import { TIP_DATA_FRESHNESS } from "@/lib/tooltipCopy";

const DISMISS_KEY = "pp-data-freshness-dismissed";

export function DataFreshnessBanner() {
  const [data, setData] = useState<DataFreshnessResponse | null>(null);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    try {
      if (sessionStorage.getItem(DISMISS_KEY) === "1") {
        setDismissed(true);
      }
    } catch {
      /* ignore */
    }
    let cancelled = false;
    void fetchDataFreshness()
      .then((d) => {
        if (!cancelled) setData(d);
      })
      .catch(() => {
        if (!cancelled) setData(null);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (dismissed || !data) return null;
  const drafts = data.staging_election_drafts ?? [];
  const warnings = data.government_age_warnings ?? [];
  if (drafts.length === 0 && warnings.length === 0) return null;

  function dismiss() {
    setDismissed(true);
    try {
      sessionStorage.setItem(DISMISS_KEY, "1");
    } catch {
      /* ignore */
    }
  }

  return (
    <aside className="rounded-md border border-amber-500/25 bg-amber-500/10 px-3 py-2 text-sm text-ink/80">
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1.5">
          <p className="font-medium text-ink/90">
            Datenpflege — Entwurf prüfen
            <InfoTooltip text={TIP_DATA_FRESHNESS} />
          </p>
          {drafts.length > 0 ? (
            <ul className="list-inside list-disc text-ink/70">
              {drafts.map((d) => (
                <li key={d.path}>
                  Wahlergebnis-Entwurf: {d.label ?? d.parliament_id ?? d.path}
                  {d.election_date ? ` (${d.election_date})` : ""}
                </li>
              ))}
            </ul>
          ) : null}
          {warnings.length > 0 ? (
            <ul className="list-inside list-disc text-ink/70">
              {warnings.map((w) => (
                <li key={w}>{w}</li>
              ))}
            </ul>
          ) : null}
        </div>
        <button
          type="button"
          onClick={dismiss}
          className="shrink-0 text-xs text-ink/45 hover:text-ink"
          aria-label="Hinweis schließen"
        >
          Schließen
        </button>
      </div>
    </aside>
  );
}
