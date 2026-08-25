"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import {
  fetchBundesratMajorityCheck,
  fetchBundesratStatus,
  postBundesratSimulate,
  type BundesratCoalitionBalanceSlice,
  type BundesratLand,
  type BundesratLandVote,
  type BundesratMajorityCheckItem,
  type BundesratMajorityCheckResponse,
  type BundesratStatusResponse,
} from "@/lib/api";
import { labelPartyId } from "@/lib/colors";

const YES_COLOR = "#2f6f4e";
const NO_COLOR = "#a33b2c";
const ABSTAIN_COLOR = "#8a8f98";

const SLICE_COLORS = [
  "#1a5f7a",
  "#c45c26",
  "#2f6f4e",
  "#5c4a7a",
  "#a33b2c",
  "#8a6d3b",
  "#3d6b8a",
  "#6b5b4a",
  "#4a7a6b",
  "#7a4a5c",
];

function StanceBadge({ stance }: { stance: string }) {
  const map: Record<string, { label: string; className: string }> = {
    yes: {
      label: "Ja",
      className: "bg-emerald-100 text-emerald-900 ring-emerald-700/20",
    },
    no: {
      label: "Nein",
      className: "bg-red-100 text-red-900 ring-red-700/20",
    },
    abstain: {
      label: "Enthaltung",
      className: "bg-stone-200 text-stone-800 ring-stone-500/25",
    },
  };
  const m = map[stance] ?? {
    label: stance,
    className: "bg-mist/60 text-ink/70 ring-ink/10",
  };
  return (
    <span
      className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${m.className}`}
    >
      {m.label}
    </span>
  );
}

function VoteBar({
  yes,
  no,
  abstain,
  total,
  majoritySimple,
  majorityTwoThirds,
  compact = false,
}: {
  yes: number;
  no: number;
  abstain: number;
  total: number;
  majoritySimple: number;
  majorityTwoThirds: number;
  compact?: boolean;
}) {
  const t = Math.max(total, 1);
  const yesPct = (yes / t) * 100;
  const noPct = (no / t) * 100;
  const absPct = (abstain / t) * 100;
  const markSimple = (majoritySimple / t) * 100;
  const markTwoThirds = (majorityTwoThirds / t) * 100;
  const h = compact ? 14 : 28;

  return (
    <div className={compact ? "space-y-1" : "space-y-2"}>
      <div
        className="relative w-full overflow-hidden rounded-md border border-ink/10 bg-white/70"
        style={{ height: h }}
        role="img"
        aria-label={`Ja ${yes}, Nein ${no}, Enthaltung ${abstain} von ${total}`}
      >
        <div className="absolute inset-0 flex">
          <div style={{ width: `${yesPct}%`, background: YES_COLOR }} />
          <div style={{ width: `${noPct}%`, background: NO_COLOR }} />
          <div style={{ width: `${absPct}%`, background: ABSTAIN_COLOR }} />
        </div>
        <div
          className="pointer-events-none absolute inset-y-0 w-px bg-ink/80"
          style={{ left: `${markSimple}%` }}
          title={`Mehrheit ${majoritySimple}`}
        />
        <div
          className="pointer-events-none absolute inset-y-0 w-px bg-ink/50"
          style={{ left: `${markTwoThirds}%` }}
          title={`Zwei Drittel ${majorityTwoThirds}`}
        />
      </div>
      {!compact && (
        <div className="relative h-4 text-[10px] text-ink/50">
          <span
            className="absolute -translate-x-1/2"
            style={{ left: `${markSimple}%` }}
          >
            {majoritySimple}
          </span>
          <span
            className="absolute -translate-x-1/2"
            style={{ left: `${markTwoThirds}%` }}
          >
            {majorityTwoThirds}
          </span>
          <span className="absolute right-0"> {total}</span>
        </div>
      )}
      {!compact && (
        <div className="flex flex-wrap gap-3 text-xs text-ink/60">
          <span>
            <span
              className="mr-1 inline-block h-2 w-2 rounded-sm"
              style={{ background: YES_COLOR }}
            />
            Ja {yes}
          </span>
          <span>
            <span
              className="mr-1 inline-block h-2 w-2 rounded-sm"
              style={{ background: NO_COLOR }}
            />
            Nein {no}
          </span>
          <span>
            <span
              className="mr-1 inline-block h-2 w-2 rounded-sm"
              style={{ background: ABSTAIN_COLOR }}
            />
            Enthaltung {abstain}
          </span>
        </div>
      )}
    </div>
  );
}

function CoalitionBalancePie({
  slices,
}: {
  slices: BundesratCoalitionBalanceSlice[];
}) {
  const data = slices.map((s, i) => ({
    ...s,
    name: s.matches_federal ? `${s.label} ★` : s.label,
    fill: SLICE_COLORS[i % SLICE_COLORS.length],
  }));

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              dataKey="votes"
              nameKey="name"
              cx="50%"
              cy="50%"
              innerRadius={48}
              outerRadius={88}
              paddingAngle={1}
              stroke="#f3efe6"
              strokeWidth={2}
            >
              {data.map((entry) => (
                <Cell
                  key={entry.key}
                  fill={entry.fill}
                  stroke={entry.matches_federal ? "#0f1c2e" : "#f3efe6"}
                  strokeWidth={entry.matches_federal ? 3 : 2}
                />
              ))}
            </Pie>
            <Tooltip
              formatter={(value: number, _n, item) => [
                `${value} Stimmen`,
                String(item?.payload?.label ?? ""),
              ]}
            />
            <Legend
              layout="vertical"
              align="right"
              verticalAlign="middle"
              wrapperStyle={{ fontSize: 12 }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <ul className="space-y-1.5 self-center text-sm">
        {data.map((s) => (
          <li
            key={s.key}
            className={
              s.matches_federal
                ? "flex items-baseline justify-between gap-2 rounded-md border border-ink/25 bg-mist/40 px-2 py-1.5 font-medium"
                : "flex items-baseline justify-between gap-2 px-2 py-1 text-ink/75"
            }
          >
            <span className="flex items-center gap-2">
              <span
                className="inline-block h-2.5 w-2.5 rounded-sm"
                style={{ background: s.fill }}
              />
              {s.label}
              {s.matches_federal ? (
                <span className="text-xs font-normal text-ink/50">
                  ★ amtierende Bundesregierung
                </span>
              ) : null}
            </span>
            <span className="tabular-nums text-ink/60">{s.votes}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function samePartySet(a: string[], b: string[]): boolean {
  if (a.length !== b.length) return false;
  const sb = new Set(b);
  return a.every((p) => sb.has(p));
}

function rowKey(item: BundesratMajorityCheckItem): string {
  if (item.is_incumbent) return "incumbent";
  return item.parties.slice().sort().join("+");
}

export function BundesratSandbox() {
  const [status, setStatus] = useState<BundesratStatusResponse | null>(null);
  const [majorityCheck, setMajorityCheck] =
    useState<BundesratMajorityCheckResponse | null>(null);
  const [choices, setChoices] = useState<Record<string, string>>({});
  const [votes, setVotes] = useState<BundesratLandVote[] | null>(null);
  const [yes, setYes] = useState(0);
  const [no, setNo] = useState(0);
  const [abstain, setAbstain] = useState(0);
  const [hasMajority, setHasMajority] = useState(false);
  const [hasTwoThirds, setHasTwoThirds] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [selectedKey, setSelectedKey] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void Promise.all([
      fetchBundesratStatus(),
      fetchBundesratMajorityCheck(8).catch(() => null),
    ])
      .then(([data, check]) => {
        if (cancelled) return;
        setStatus(data);
        setMajorityCheck(check);
        setVotes(data.simulation.by_land);
        setYes(data.simulation.yes_votes);
        setNo(data.simulation.no_votes);
        setAbstain(data.simulation.abstain_votes);
        setHasMajority(data.simulation.has_majority);
        setHasTwoThirds(data.simulation.has_two_thirds);
        const initial: Record<string, string> = {};
        for (const land of data.laender) {
          initial[land.parliament_id] = "default";
        }
        setChoices(initial);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "Fehler");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const choiceKey = useMemo(() => JSON.stringify(choices), [choices]);

  useEffect(() => {
    if (!status || choiceKey === "{}") return;
    const parsed = JSON.parse(choiceKey) as Record<string, string>;
    const nonDefault = Object.fromEntries(
      Object.entries(parsed).filter(([, v]) => v !== "default"),
    );
    const t = setTimeout(() => {
      setBusy(true);
      setError(null);
      void postBundesratSimulate(nonDefault)
        .then((sim) => {
          setVotes(sim.by_land);
          setYes(sim.yes_votes);
          setNo(sim.no_votes);
          setAbstain(sim.abstain_votes);
          setHasMajority(sim.has_majority);
          setHasTwoThirds(sim.has_two_thirds);
        })
        .catch((e) => setError(e instanceof Error ? e.message : "Fehler"))
        .finally(() => setBusy(false));
    }, 200);
    return () => clearTimeout(t);
  }, [choiceKey, status]);

  function setLandChoice(land: BundesratLand, value: string) {
    setSelectedKey(null);
    setChoices((prev) => ({ ...prev, [land.parliament_id]: value }));
  }

  function applyMajorityCheckRow(item: BundesratMajorityCheckItem) {
    if (!status) return;
    setSelectedKey(rowKey(item));
    const next: Record<string, string> = {};
    for (const land of status.laender) {
      const auto = item.choices[land.parliament_id] ?? "default";
      if (auto === "abstain" || auto === "reject") {
        next[land.parliament_id] = auto;
        continue;
      }
      const match = land.coalition_options.find((opt) =>
        samePartySet(opt.parties, item.parties),
      );
      next[land.parliament_id] = match?.key ?? "default";
    }
    setChoices(next);
  }

  if (!status) {
    return (
      <p className="text-sm text-ink/55">
        {error ? error : "Bundesrat wird geladen …"}
      </p>
    );
  }

  const voteById = new Map((votes ?? []).map((v) => [v.parliament_id, v]));
  const balance = majorityCheck?.coalition_balance ?? [];

  return (
    <div className="space-y-8">
      <p className="rounded-md border border-amber-700/25 bg-amber-50/80 px-3 py-2 text-sm text-ink/80">
        {status.disclaimer} Stand der Defaults: {status.as_of}.
      </p>

      <section className="space-y-3">
        <h2 className="font-display text-xl text-ink">Aktuelle Stimmenlage</h2>
        <VoteBar
          yes={yes}
          no={no}
          abstain={abstain}
          total={status.total_votes}
          majoritySimple={status.majority_threshold}
          majorityTwoThirds={status.two_thirds_threshold}
        />
        <div className="flex flex-wrap gap-3 text-sm">
          <span
            className={
              hasMajority ? "font-medium text-emerald-800" : "text-ink/55"
            }
          >
            Absolute Mehrheit (≥{status.majority_threshold}):{" "}
            {hasMajority ? "ja" : "nein"}
          </span>
          <span
            className={
              hasTwoThirds ? "font-medium text-emerald-800" : "text-ink/55"
            }
          >
            Zwei Drittel (≥{status.two_thirds_threshold}):{" "}
            {hasTwoThirds ? "ja" : "nein"}
          </span>
          <span className="text-ink/40">
            von {status.total_votes} Stimmen
            {busy ? " · berechnet …" : ""}
          </span>
        </div>
      </section>

      {balance.length > 0 && (
        <section className="space-y-3">
          <h2 className="font-display text-xl text-ink">
            Kräfteverhältnis nach Koalitionsfarbe
          </h2>
          <p className="max-w-2xl text-sm text-ink/55">
            Stimmen der Länder nach Regierungs-Kombination (Reihenfolge egal;
            CDU/CSU als Union). ★ markiert die Farbe der amtierenden
            Bundesregierung
            {majorityCheck?.federal_government
              ? ` (${majorityCheck.federal_government.label})`
              : ""}
            .
          </p>
          <CoalitionBalancePie slices={balance} />
        </section>
      )}

      {error ? <p className="text-sm text-red-700">{error}</p> : null}

      {majorityCheck && majorityCheck.coalitions.length > 0 && (
        <section className="space-y-3">
          <h2 className="font-display text-xl text-ink">
            Hätte diese Koalition eine Bundesrats-Mehrheit?
          </h2>
          <p className="max-w-2xl text-sm text-ink/55">
            Automatisch nach Art. 51 Abs. 3 GG: volle Übereinstimmung mit der
            Landesregierung → Ja, Teilüberschneidung → Enthaltung, keine →
            Nein. Klick übernimmt die Wahl in die Tabelle darunter.
          </p>
          <ul className="space-y-2">
            {majorityCheck.coalitions.map((row) => {
              const key = rowKey(row);
              const active = selectedKey === key;
              const title =
                row.label?.trim() ||
                row.parties.map(labelPartyId).join(" + ");
              return (
                <li key={key}>
                  <button
                    type="button"
                    onClick={() => applyMajorityCheckRow(row)}
                    className={
                      row.is_incumbent
                        ? active
                          ? "w-full rounded-lg border-2 border-sea bg-sea/10 px-3 py-3 text-left shadow-sm transition"
                          : "w-full rounded-lg border-2 border-ink/20 bg-gradient-to-br from-mist/50 to-white/80 px-3 py-3 text-left shadow-sm transition hover:border-sea/50"
                        : active
                          ? "w-full rounded-lg border border-sea/40 bg-mist/50 px-3 py-2.5 text-left transition"
                          : "w-full rounded-lg border border-ink/10 bg-white/50 px-3 py-2.5 text-left transition hover:border-sea/30 hover:bg-mist/30"
                    }
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <p className="text-sm font-medium text-ink">
                        {title}
                        {row.is_incumbent ? (
                          <span className="ml-2 inline-flex rounded-full bg-ink px-2 py-0.5 text-xs font-medium text-paper">
                            Amtierende Bundesregierung
                          </span>
                        ) : (
                          <span className="ml-2 text-xs font-normal text-ink/45">
                            BT {row.bundestag_seats} Sitze
                          </span>
                        )}
                      </p>
                      <div className="flex flex-wrap gap-1.5">
                        <span
                          className={
                            row.has_majority
                              ? "rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-900"
                              : "rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-900"
                          }
                        >
                          Mehrheit {row.has_majority ? "✓" : "✗"}
                        </span>
                        <span
                          className={
                            row.has_two_thirds
                              ? "rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-900"
                              : "rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-900"
                          }
                        >
                          Zwei Drittel {row.has_two_thirds ? "✓" : "✗"}
                        </span>
                      </div>
                    </div>
                    <div className="mt-2">
                      <VoteBar
                        yes={row.yes_votes}
                        no={row.no_votes}
                        abstain={row.abstain_votes}
                        total={majorityCheck.total_votes}
                        majoritySimple={majorityCheck.majority_threshold}
                        majorityTwoThirds={majorityCheck.two_thirds_threshold}
                        compact
                      />
                    </div>
                  </button>
                </li>
              );
            })}
          </ul>
        </section>
      )}

      <section className="space-y-3">
        <h2 className="font-display text-xl text-ink">Länder im Detail</h2>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[40rem] border-collapse text-sm">
            <thead>
              <tr className="border-b border-ink/15 text-left text-ink/50">
                <th className="py-2 pr-3 font-medium">Land</th>
                <th className="py-2 pr-3 font-medium">Stimmen</th>
                <th className="py-2 pr-3 font-medium">Wahl</th>
                <th className="py-2 pr-3 font-medium">Regierung</th>
                <th className="py-2 font-medium">Stimme</th>
              </tr>
            </thead>
            <tbody>
              {status.laender.map((land) => {
                const vote = voteById.get(land.parliament_id);
                const choice = choices[land.parliament_id] ?? "default";
                return (
                  <tr key={land.parliament_id} className="border-b border-ink/8">
                    <td className="py-2.5 pr-3 font-medium text-ink">
                      {land.name}
                    </td>
                    <td className="py-2.5 pr-3 tabular-nums">{land.votes}</td>
                    <td className="py-2.5 pr-3">
                      <select
                        className="max-w-[16rem] rounded border border-ink/15 bg-white px-2 py-1 text-ink"
                        value={choice}
                        onChange={(e) => setLandChoice(land, e.target.value)}
                      >
                        <option value="default">
                          Amtierend: {land.default_government_label}
                        </option>
                        {land.coalition_options.map((opt) => (
                          <option key={opt.key} value={opt.key}>
                            Umfrage:{" "}
                            {opt.parties.map(labelPartyId).join(" + ")} (
                            {opt.seats} Sitze)
                          </option>
                        ))}
                        <option value="abstain">Enthaltung</option>
                        <option value="reject">Nein</option>
                      </select>
                    </td>
                    <td className="py-2.5 pr-3 text-ink/70">
                      {vote?.government_label ?? land.default_government_label}
                    </td>
                    <td className="py-2.5">
                      <StanceBadge stance={vote?.stance ?? "yes"} />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
