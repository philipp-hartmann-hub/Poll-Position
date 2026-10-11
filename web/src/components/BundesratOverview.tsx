"use client";

import { useEffect, useMemo, useState } from "react";
import {
  fetchBundesratMajorityCheck,
  type BundesratCoalitionBalanceSlice,
  type BundesratMajorityCheckItem,
  type BundesratMajorityCheckResponse,
} from "@/lib/api";
import { labelPartyId, partyColor } from "@/lib/colors";

function MajorityBadge({ ok }: { ok: boolean }) {
  return (
    <span
      className={
        ok
          ? "inline-flex rounded-full bg-emerald-500/15 px-2 py-0.5 text-xs font-medium text-emerald-300 ring-1 ring-inset ring-emerald-500/30"
          : "inline-flex rounded-full bg-stone-500/15 px-2 py-0.5 text-xs font-medium text-ink/55 ring-1 ring-inset ring-ink/10"
      }
    >
      {ok ? "Mehrheit" : "Keine Mehrheit"}
    </span>
  );
}

function coalitionTitle(row: BundesratMajorityCheckItem): string {
  if (row.label?.trim()) return row.label.trim();
  return row.parties.map(labelPartyId).join(" + ");
}

function BalanceBar({
  slices,
  total,
}: {
  slices: BundesratCoalitionBalanceSlice[];
  total: number;
}) {
  const t = Math.max(total, 1);
  return (
    <div className="space-y-3">
      <div
        className="flex h-7 w-full overflow-hidden rounded-md border border-ink/10"
        role="img"
        aria-label="Zusammensetzung der Bundesratsstimmen nach Landeskoalitionen"
      >
        {slices.map((s) => {
          const pct = (s.votes / t) * 100;
          if (pct <= 0) return null;
          const color =
            s.parties_normalized.length > 0
              ? partyColor(s.parties_normalized[0])
              : "#6b7280";
          return (
            <div
              key={s.key}
              title={`${s.label}: ${s.votes} Stimmen`}
              style={{
                width: `${pct}%`,
                background: color,
                opacity: s.matches_federal ? 1 : 0.55,
              }}
            />
          );
        })}
      </div>
      <ul className="space-y-1.5 text-sm">
        {slices.map((s) => (
          <li
            key={s.key}
            className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5"
          >
            <span className="flex min-w-0 items-center gap-2 text-ink/75">
              <span
                className="inline-block h-2.5 w-2.5 shrink-0 rounded-sm"
                style={{
                  background:
                    s.parties_normalized.length > 0
                      ? partyColor(s.parties_normalized[0])
                      : "#6b7280",
                  opacity: s.matches_federal ? 1 : 0.55,
                }}
              />
              <span className="truncate">{s.label}</span>
              {s.matches_federal ? (
                <span className="shrink-0 text-[11px] text-ink/40">
                  (= Bund)
                </span>
              ) : null}
            </span>
            <span className="shrink-0 tabular-nums text-ink/60">
              {s.votes} Stimmen · {s.parliament_ids.length}{" "}
              {s.parliament_ids.length === 1 ? "Land" : "Länder"}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function BundesratOverview() {
  const [data, setData] = useState<BundesratMajorityCheckResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void fetchBundesratMajorityCheck()
      .then((res) => {
        if (!cancelled) setData(res);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "Fehler");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const balance = useMemo(
    () =>
      [...(data?.coalition_balance ?? [])].sort((a, b) => b.votes - a.votes),
    [data],
  );

  if (error) {
    return <p className="text-sm text-red-700">{error}</p>;
  }
  if (!data) {
    return (
      <p className="text-sm text-ink/55">Aktuelle Bundesrats-Lage wird geladen …</p>
    );
  }

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <div className="rounded-xl border border-ink/10 bg-mist/50 p-4">
        <h3 className="text-sm font-semibold text-ink">
          Bundesregierung &amp; Top-Koalitionen
        </h3>
        <p className="mb-3 mt-1 text-xs text-ink/55">
          Hätte die Koalition im Bundesrat eine absolute Mehrheit (≥
          {data.majority_threshold}/69)? Stand {data.as_of}.
        </p>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[20rem] border-collapse text-sm">
            <thead>
              <tr className="border-b border-ink/12 text-left text-ink/45">
                <th className="py-1.5 pr-2 font-medium">Koalition</th>
                <th className="py-1.5 pr-2 font-medium">Ja</th>
                <th className="py-1.5 font-medium">Bundesrat</th>
              </tr>
            </thead>
            <tbody>
              {data.coalitions.map((row) => (
                <tr
                  key={`${row.is_incumbent ? "inc" : "poll"}-${row.parties.join("+")}`}
                  className="border-b border-ink/8"
                >
                  <td className="py-2 pr-2">
                    <span className="font-medium text-ink">
                      {coalitionTitle(row)}
                    </span>
                    {row.is_incumbent ? (
                      <span className="ml-1.5 text-[11px] text-ink/40">
                        amtierend
                      </span>
                    ) : row.bundestag_seats > 0 ? (
                      <span className="ml-1.5 text-[11px] text-ink/40">
                        {row.bundestag_seats} BT-Sitze
                      </span>
                    ) : null}
                  </td>
                  <td className="py-2 pr-2 tabular-nums text-ink/70">
                    {row.yes_votes}
                  </td>
                  <td className="py-2">
                    <div className="flex flex-wrap items-center gap-1.5">
                      <MajorityBadge ok={row.has_majority} />
                      {row.has_two_thirds ? (
                        <span className="text-[11px] text-emerald-300/90">
                          ⅔
                        </span>
                      ) : null}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="rounded-xl border border-ink/10 bg-mist/50 p-4">
        <h3 className="text-sm font-semibold text-ink">
          Zusammensetzung nach Landesregierungen
        </h3>
        <p className="mb-3 mt-1 text-xs text-ink/55">
          {data.total_votes} Stimmen nach aktuellem Koalitionstyp in den Ländern.
        </p>
        {balance.length > 0 ? (
          <BalanceBar slices={balance} total={data.total_votes} />
        ) : (
          <p className="text-sm text-ink/45">Keine Aufschlüsselung verfügbar.</p>
        )}
      </div>
    </div>
  );
}
