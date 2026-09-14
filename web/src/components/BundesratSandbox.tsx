"use client";

import { useEffect, useMemo, useState } from "react";
import {
  fetchBundesratStatus,
  fetchGovernment,
  postBundesratSimulate,
  type BundesratLand,
  type BundesratLandVote,
  type BundesratStatusResponse,
  type GovernmentPollPreset,
  type GovernmentResponse,
} from "@/lib/api";
import { InfoTooltip } from "@/components/InfoTooltip";
import { BundesratMap } from "@/components/BundesratMap";
import {
  choicesFromPartyStance,
  mergeLandOverrides,
} from "@/lib/bundesratChoices";
import {
  ABSTAIN_COLOR,
  NO_COLOR,
  YES_COLOR,
} from "@/lib/bundesratColors";
import { labelPartyId } from "@/lib/colors";

type PartyStance = Record<string, "yes" | "no">;

function StanceBadge({ stance }: { stance: string }) {
  const map: Record<string, { label: string; className: string }> = {
    yes: {
      label: "Ja",
      className: "bg-emerald-500/15 text-emerald-300 ring-emerald-500/30",
    },
    no: {
      label: "Nein",
      className: "bg-red-500/15 text-red-300 ring-red-500/30",
    },
    abstain: {
      label: "Enthaltung",
      className: "bg-stone-500/20 text-stone-300 ring-stone-400/25",
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

function VoteCounter({
  yes,
  no,
  abstain,
  total,
  majoritySimple,
  majorityTwoThirds,
  hasMajority,
  hasTwoThirds,
  busy,
}: {
  yes: number;
  no: number;
  abstain: number;
  total: number;
  majoritySimple: number;
  majorityTwoThirds: number;
  hasMajority: boolean;
  hasTwoThirds: boolean;
  busy: boolean;
}) {
  const t = Math.max(total, 1);
  const yesPct = (yes / t) * 100;
  const noPct = (no / t) * 100;
  const absPct = (abstain / t) * 100;
  const markSimple = (majoritySimple / t) * 100;
  const markTwoThirds = (majorityTwoThirds / t) * 100;

  return (
    <div className="flex h-full flex-col justify-center space-y-4">
      <div>
        <p className="text-xs uppercase tracking-wide text-ink/45">Stimmen</p>
        <p className="mt-1 font-display text-3xl tabular-nums text-ink">
          {yes}
          <span className="text-lg text-ink/40"> / {total}</span>
        </p>
        <p className="mt-1 text-sm text-ink/55">
          Ja · Nein {no} · Enthaltung {abstain}
          {busy ? " · …" : ""}
        </p>
      </div>

      <div
        className="relative h-7 w-full overflow-hidden rounded-md border border-ink/10 bg-mist/70"
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
        <span className="absolute right-0">{total}</span>
      </div>

      <ul className="space-y-2 text-sm">
        <li className="flex items-center justify-between gap-3">
          <span className="flex items-center gap-2 text-ink/70">
            <span
              className="inline-block h-2.5 w-2.5 rounded-sm"
              style={{ background: YES_COLOR }}
            />
            Ja
          </span>
          <span className="tabular-nums font-medium text-ink">{yes}</span>
        </li>
        <li className="flex items-center justify-between gap-3">
          <span className="flex items-center gap-2 text-ink/70">
            <span
              className="inline-block h-2.5 w-2.5 rounded-sm"
              style={{ background: NO_COLOR }}
            />
            Nein
          </span>
          <span className="tabular-nums font-medium text-ink">{no}</span>
        </li>
        <li className="flex items-center justify-between gap-3">
          <span className="flex items-center gap-2 text-ink/70">
            <span
              className="inline-block h-2.5 w-2.5 rounded-sm"
              style={{ background: ABSTAIN_COLOR }}
            />
            Enthaltung
          </span>
          <span className="tabular-nums font-medium text-ink">{abstain}</span>
        </li>
      </ul>

      <div className="space-y-1 border-t border-ink/10 pt-3 text-sm">
        <p
          className={
            hasMajority ? "font-medium text-emerald-300" : "text-ink/55"
          }
        >
          Absolute Mehrheit (≥{majoritySimple}/69):{" "}
          {hasMajority ? "ja" : "nein"}
        </p>
        <p
          className={
            hasTwoThirds ? "font-medium text-emerald-300" : "text-ink/55"
          }
        >
          Zwei Drittel (≥{majorityTwoThirds}/69):{" "}
          {hasTwoThirds ? "ja" : "nein"}
        </p>
      </div>
    </div>
  );
}

function PartyStanceChip({
  partyId,
  label,
  value,
  onChange,
}: {
  partyId: string;
  label: string;
  value: "yes" | "no" | null;
  onChange: (next: "yes" | "no" | null) => void;
}) {
  const btn = (
    stance: "yes" | "no" | null,
    text: string,
    activeClass: string,
  ) => (
    <button
      type="button"
      aria-pressed={value === stance}
      onClick={() => onChange(stance)}
      className={
        value === stance
          ? `rounded px-1.5 py-0.5 text-[11px] font-medium ${activeClass}`
          : "rounded px-1.5 py-0.5 text-[11px] text-ink/45 hover:bg-ink/5"
      }
    >
      {text}
    </button>
  );

  return (
    <div
      className="inline-flex items-center gap-1 rounded-lg border border-ink/12 bg-mist/70 px-2 py-1.5"
      data-party={partyId}
    >
      <span className="mr-1 text-xs font-medium text-ink">{label}</span>
      {btn("yes", "Ja", "bg-emerald-500/15 text-emerald-300")}
      {btn(null, "Enth.", "bg-stone-500/20 text-stone-300")}
      {btn("no", "Nein", "bg-red-500/15 text-red-300")}
    </div>
  );
}

function autoLabel(choice: string): string {
  if (choice === "default") return "Ja (Regierung)";
  if (choice === "reject") return "Nein";
  if (choice === "abstain") return "Enthaltung";
  return choice;
}

export function BundesratSandbox() {
  const [status, setStatus] = useState<BundesratStatusResponse | null>(null);
  const [government, setGovernment] = useState<GovernmentResponse | null>(null);
  const [partyStance, setPartyStance] = useState<PartyStance>({});
  const [landOverrides, setLandOverrides] = useState<Record<string, string>>(
    {},
  );
  const [votes, setVotes] = useState<BundesratLandVote[] | null>(null);
  const [yes, setYes] = useState(0);
  const [no, setNo] = useState(0);
  const [abstain, setAbstain] = useState(0);
  const [hasMajority, setHasMajority] = useState(false);
  const [hasTwoThirds, setHasTwoThirds] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [pollPresetKey, setPollPresetKey] = useState("");

  useEffect(() => {
    let cancelled = false;
    void Promise.all([fetchBundesratStatus(), fetchGovernment()])
      .then(([st, gov]) => {
        if (cancelled) return;
        setStatus(st);
        setGovernment(gov);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "Fehler");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const autoChoices = useMemo(() => {
    if (!status) return {};
    return choicesFromPartyStance(status.laender, partyStance);
  }, [status, partyStance]);

  const mergedChoices = useMemo(
    () => mergeLandOverrides(autoChoices, landOverrides),
    [autoChoices, landOverrides],
  );

  const choiceKey = useMemo(
    () => JSON.stringify(mergedChoices),
    [mergedChoices],
  );

  useEffect(() => {
    if (!status) return;
    const parsed = JSON.parse(choiceKey) as Record<string, string>;
    const t = setTimeout(() => {
      setBusy(true);
      setError(null);
      void postBundesratSimulate(parsed)
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
    }, 180);
    return () => clearTimeout(t);
  }, [choiceKey, status]);

  function setPartyValue(partyId: string, next: "yes" | "no" | null) {
    setPollPresetKey("");
    setPartyStance((prev) => {
      const out = { ...prev };
      if (next === null) delete out[partyId];
      else out[partyId] = next;
      return out;
    });
  }

  function applyFederalGovernment() {
    const parties = government?.bundesregierung?.parties ?? [];
    const next: PartyStance = {};
    for (const p of parties) next[p] = "yes";
    setPartyStance(next);
    setLandOverrides({});
    setPollPresetKey("");
  }

  function applyPollPreset(preset: GovernmentPollPreset) {
    const next: PartyStance = {};
    for (const p of preset.parties) next[p] = "yes";
    setPartyStance(next);
    setLandOverrides({});
    setPollPresetKey(preset.parties.slice().sort().join("+"));
  }

  function setLandOverride(land: BundesratLand, value: string) {
    setLandOverrides((prev) => {
      const out = { ...prev };
      if (!value || value === "auto") delete out[land.parliament_id];
      else out[land.parliament_id] = value;
      return out;
    });
  }

  if (!status) {
    return (
      <p className="text-sm text-ink/55">
        {error ? error : "Bundesrat wird geladen …"}
      </p>
    );
  }

  const voteById = new Map((votes ?? []).map((v) => [v.parliament_id, v]));
  const chipParties =
    government?.known_parties?.length ?
      government.known_parties
    : Array.from(
        new Set(status.laender.flatMap((l) => l.default_government)),
      ).map((id) => ({ id, label: labelPartyId(id) }));

  const presets = government?.poll_presets ?? [];

  return (
    <div className="space-y-8">
      <p className="rounded-md border border-amber-500/25 bg-amber-500/10 px-3 py-2 text-sm text-ink/80">
        {status.disclaimer} Stand der Landesregierungen: {status.as_of}.
        Ausgangspunkt ist Enthaltung, bis Parteien auf Ja oder Nein gesetzt
        werden.
      </p>

      <section className="space-y-3">
        <h2 className="font-display text-xl text-ink">
          Partei-Stimmverhalten
          <InfoTooltip text="Bundesweite Voreinstellung: Stimmen alle Regierungsparteien eines Landes mit Ja, gibt das Land Ja ab; alle Nein → Nein; sonst Enthaltung (Art. 51 Abs. 3 GG). Landes-Overrides darunter überschreiben das." />
        </h2>

        <div className="flex flex-wrap gap-2">
          {chipParties.map((p) => (
            <PartyStanceChip
              key={p.id}
              partyId={p.id}
              label={p.label}
              value={partyStance[p.id] ?? null}
              onChange={(next) => setPartyValue(p.id, next)}
            />
          ))}
        </div>

        <div className="flex flex-wrap items-end gap-3 pt-1">
          <button
            type="button"
            onClick={applyFederalGovernment}
            className="rounded-md border border-ink/15 bg-mist px-3 py-2 text-sm font-medium text-ink transition hover:border-sea/40 hover:bg-mist/40"
          >
            Aktuelle Bundesregierung
            {government?.bundesregierung?.label
              ? ` (${government.bundesregierung.label})`
              : ""}
          </button>

          <label className="min-w-[14rem] flex-1 text-sm">
            <span className="mb-1 block text-ink/50">Nach Umfragen</span>
            <select
              className="w-full rounded-md border border-ink/15 bg-mist px-3 py-2 text-ink"
              value={pollPresetKey}
              onChange={(e) => {
                const key = e.target.value;
                if (!key) {
                  setPollPresetKey("");
                  return;
                }
                const preset = presets.find(
                  (p) => p.parties.slice().sort().join("+") === key,
                );
                if (preset) applyPollPreset(preset);
              }}
            >
              <option value="">Koalition wählen …</option>
              {presets.map((p) => {
                const key = p.parties.slice().sort().join("+");
                const pct = Math.round(p.majority_probability * 100);
                return (
                  <option key={key} value={key}>
                    {p.label} ({pct} %)
                  </option>
                );
              })}
            </select>
          </label>
        </div>
      </section>

      {error ? <p className="text-sm text-red-700">{error}</p> : null}

      <section className="grid gap-6 lg:grid-cols-[minmax(0,1.15fr)_minmax(16rem,0.85fr)] lg:items-stretch">
        <BundesratMap
          laender={status.laender}
          votes={votes ?? []}
          onLandClick={(id) =>
            document
              .getElementById(`land-row-${id}`)
              ?.scrollIntoView({ behavior: "smooth", block: "center" })
          }
        />
        <div className="rounded-xl border border-ink/10 bg-gradient-to-b from-mist/20 to-mist/60 p-4">
          <VoteCounter
            yes={yes}
            no={no}
            abstain={abstain}
            total={status.total_votes}
            majoritySimple={status.majority_threshold}
            majorityTwoThirds={status.two_thirds_threshold}
            hasMajority={hasMajority}
            hasTwoThirds={hasTwoThirds}
            busy={busy}
          />
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="font-display text-xl text-ink">Länder</h2>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[42rem] border-collapse text-sm">
            <thead>
              <tr className="border-b border-ink/15 text-left text-ink/50">
                <th className="py-2 pr-3 font-medium">Land</th>
                <th className="py-2 pr-3 font-medium">Stimmen</th>
                <th className="py-2 pr-3 font-medium">Override</th>
                <th className="py-2 pr-3 font-medium">Regierung</th>
                <th className="py-2 font-medium">Stimme</th>
              </tr>
            </thead>
            <tbody>
              {status.laender.map((land) => {
                const vote = voteById.get(land.parliament_id);
                const override = landOverrides[land.parliament_id] ?? "auto";
                const auto = autoChoices[land.parliament_id] ?? "abstain";
                return (
                  <tr
                    key={land.parliament_id}
                    id={`land-row-${land.parliament_id}`}
                    className="border-b border-ink/8"
                  >
                    <td className="py-2.5 pr-3 font-medium text-ink">
                      {land.name}
                    </td>
                    <td className="py-2.5 pr-3 tabular-nums">{land.votes}</td>
                    <td className="py-2.5 pr-3">
                      <select
                        className="max-w-[18rem] rounded border border-ink/15 bg-mist px-2 py-1 text-ink"
                        value={override}
                        onChange={(e) =>
                          setLandOverride(land, e.target.value)
                        }
                      >
                        <option value="auto">
                          Automatisch ({autoLabel(auto)})
                        </option>
                        {land.coalition_options.map((opt) => (
                          <option key={opt.key} value={opt.key}>
                            Umfrage:{" "}
                            {opt.parties.map(labelPartyId).join(" + ")} (
                            {opt.seats} Sitze)
                          </option>
                        ))}
                        <option value="default">Ja</option>
                        <option value="reject">Nein</option>
                        <option value="abstain">Enthaltung</option>
                      </select>
                    </td>
                    <td className="py-2.5 pr-3 text-ink/70">
                      {vote?.government_label ?? land.default_government_label}
                    </td>
                    <td className="py-2.5">
                      <StanceBadge stance={vote?.stance ?? "abstain"} />
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
