"use client";

import { useEffect, useMemo, useState } from "react";
import {
  fetchBundesratStatus,
  postBundesratSimulate,
  type BundesratLand,
  type BundesratLandVote,
  type BundesratStatusResponse,
} from "@/lib/api";
import { labelPartyId } from "@/lib/colors";

function stanceLabel(stance: string): string {
  if (stance === "yes") return "Ja";
  if (stance === "no") return "Nein";
  if (stance === "abstain") return "Enthaltung";
  return stance;
}

export function BundesratSandbox() {
  const [status, setStatus] = useState<BundesratStatusResponse | null>(null);
  const [choices, setChoices] = useState<Record<string, string>>({});
  const [votes, setVotes] = useState<BundesratLandVote[] | null>(null);
  const [yes, setYes] = useState(0);
  const [no, setNo] = useState(0);
  const [abstain, setAbstain] = useState(0);
  const [hasMajority, setHasMajority] = useState(false);
  const [hasTwoThirds, setHasTwoThirds] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void fetchBundesratStatus()
      .then((data) => {
        if (cancelled) return;
        setStatus(data);
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
    setChoices((prev) => ({ ...prev, [land.parliament_id]: value }));
  }

  if (!status) {
    return (
      <p className="text-sm text-ink/55">
        {error ? error : "Bundesrat wird geladen …"}
      </p>
    );
  }

  const voteById = new Map((votes ?? []).map((v) => [v.parliament_id, v]));

  return (
    <div className="space-y-6">
      <p className="rounded-md border border-amber-700/25 bg-amber-50/80 px-3 py-2 text-sm text-ink/80">
        {status.disclaimer} Stand der Defaults: {status.as_of}.
      </p>

      <div className="grid gap-3 sm:grid-cols-3">
        <div className="rounded-md border border-ink/10 bg-white/60 px-3 py-2">
          <p className="text-xs uppercase tracking-wide text-ink/45">Ja</p>
          <p className="font-display text-2xl tabular-nums">{yes}</p>
        </div>
        <div className="rounded-md border border-ink/10 bg-white/60 px-3 py-2">
          <p className="text-xs uppercase tracking-wide text-ink/45">Nein</p>
          <p className="font-display text-2xl tabular-nums">{no}</p>
        </div>
        <div className="rounded-md border border-ink/10 bg-white/60 px-3 py-2">
          <p className="text-xs uppercase tracking-wide text-ink/45">
            Enthaltung
          </p>
          <p className="font-display text-2xl tabular-nums">{abstain}</p>
        </div>
      </div>

      <div className="flex flex-wrap gap-3 text-sm">
        <span
          className={
            hasMajority
              ? "font-medium text-emerald-800"
              : "text-ink/55"
          }
        >
          Absolute Mehrheit (≥{status.majority_threshold}):{" "}
          {hasMajority ? "ja" : "nein"}
        </span>
        <span
          className={
            hasTwoThirds
              ? "font-medium text-emerald-800"
              : "text-ink/55"
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

      {error ? <p className="text-sm text-red-700">{error}</p> : null}

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
                <tr
                  key={land.parliament_id}
                  className="border-b border-ink/8"
                >
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
                  <td className="py-2.5">{stanceLabel(vote?.stance ?? "yes")}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
