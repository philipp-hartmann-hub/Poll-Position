"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  fetchSeats,
  postCoalitionCheck,
  type CoalitionCheckResponse,
  type SeatsResponse,
} from "@/lib/api";
import { Hemicycle } from "@/components/charts";
import { InfoTooltip } from "@/components/InfoTooltip";
import { labelPartyId, partyColor } from "@/lib/colors";
import { leftRightPosition } from "@/lib/partyPositions";
import { PARTY_SWATCH_CLASS } from "@/lib/theme";
import { TIP_COALITION_CHECKER } from "@/lib/tooltipCopy";
import { isAbortError } from "@/lib/parliamentCache";

/** Anzeigename → kanonische ID (wie SHORT_TO_CANONICAL im Backend). */
const NAME_TO_CANONICAL: Record<string, string> = {
  AfD: "de:afd",
  "CDU/CSU": "de:cdu_csu",
  CDU: "de:cdu",
  CSU: "de:csu",
  SPD: "de:spd",
  Grüne: "de:gruene",
  FDP: "de:fdp",
  Linke: "de:linke",
  BSW: "de:bsw",
  "Freie Wähler": "de:fw",
  SSW: "de:ssw",
  BIW: "de:biw",
  "BVB/FW": "de:bvb_freie_waehler",
  "Freie Sachsen": "de:freie_sachsen",
  Volt: "de:volt",
};

function canonicalFromSeatName(name: string): string | null {
  if (NAME_TO_CANONICAL[name]) return NAME_TO_CANONICAL[name];
  if (name.startsWith("de:")) return name;
  return null;
}

type PartyOption = {
  canonicalId: string;
  name: string;
  seats: number;
};

export function CoalitionCheckerSection({
  parliamentId,
}: {
  parliamentId: string;
}) {
  const [seats, setSeats] = useState<SeatsResponse | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [result, setResult] = useState<CoalitionCheckResponse | null>(null);
  const [loadingSeats, setLoadingSeats] = useState(true);
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    let cancelled = false;
    const ac = new AbortController();
    setLoadingSeats(true);
    setError(null);
    setSelected(new Set());
    setResult(null);
    (async () => {
      try {
        const data = await fetchSeats(parliamentId, { signal: ac.signal });
        if (cancelled || ac.signal.aborted) return;
        setSeats(data);
      } catch (e) {
        if (cancelled || isAbortError(e)) return;
        setError(e instanceof Error ? e.message : "Sitze laden fehlgeschlagen");
        setSeats(null);
      } finally {
        if (!cancelled && !ac.signal.aborted) setLoadingSeats(false);
      }
    })();
    return () => {
      cancelled = true;
      ac.abort();
    };
  }, [parliamentId]);

  const options: PartyOption[] = useMemo(() => {
    if (!seats?.seats_by_name) return [];
    return Object.entries(seats.seats_by_name)
      .filter(([name, n]) => n > 0 && !/sonstige/i.test(name))
      .map(([name, n]) => {
        const canonicalId = canonicalFromSeatName(name);
        return canonicalId
          ? { canonicalId, name, seats: n }
          : null;
      })
      .filter((x): x is PartyOption => x != null)
      .sort((a, b) => {
        const lr = leftRightPosition(a.name) - leftRightPosition(b.name);
        if (lr !== 0) return lr;
        return a.name.localeCompare(b.name, "de");
      });
  }, [seats]);

  const selectedList = useMemo(
    () => options.filter((o) => selected.has(o.canonicalId)).map((o) => o.canonicalId),
    [options, selected],
  );

  const highlightNames = useMemo(
    () => options.filter((o) => selected.has(o.canonicalId)).map((o) => o.name),
    [options, selected],
  );

  // Sofortige Punktschätzer-Anzeige aus lokalen Sitzen (ohne API-Wartezeit)
  const localPoint = useMemo(() => {
    if (!seats || selectedList.length === 0) return null;
    const thr =
      seats.total_seats > 0 ? Math.floor(seats.total_seats / 2) + 1 : 0;
    const sum = options
      .filter((o) => selected.has(o.canonicalId))
      .reduce((s, o) => s + o.seats, 0);
    return {
      seats: sum,
      threshold: thr,
      total: seats.total_seats,
      hasMajority: thr > 0 && sum >= thr,
    };
  }, [seats, selected, selectedList.length, options]);

  const selectedKey = selectedList.join("|");

  useEffect(() => {
    if (selectedList.length === 0) {
      setResult(null);
      setChecking(false);
      return;
    }
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;
    setChecking(true);
    setError(null);
    const parties = selectedList;
    (async () => {
      try {
        const res = await postCoalitionCheck(parliamentId, parties, {
          n_simulations: 400,
          signal: ac.signal,
        });
        if (ac.signal.aborted) return;
        setResult(res);
      } catch (e) {
        if (isAbortError(e) || ac.signal.aborted) return;
        setError(
          e instanceof Error ? e.message : "Prüfung fehlgeschlagen",
        );
        setResult(null);
      } finally {
        if (!ac.signal.aborted) setChecking(false);
      }
    })();
    return () => {
      ac.abort();
    };
    // selectedKey spiegelt selectedList; bewusst nicht selectedList als Array-Dep.
    // eslint-disable-next-line react-hooks/exhaustive-deps -- selectedKey
  }, [parliamentId, selectedKey]);

  function toggle(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  if (loadingSeats) {
    return <p className="text-sm text-ink/50">Lade Parteien…</p>;
  }
  if (!seats || options.length === 0) {
    return (
      <p className="rounded-lg border border-dashed border-ink/15 px-4 py-6 text-sm text-ink/55">
        Keine Sitzprojektion verfügbar — der Koalitionsprüfer braucht aktuelle
        Umfrage-Sitze.
      </p>
    );
  }

  const probability =
    result && selectedList.length > 0 ? result.majority_probability : null;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-display text-2xl text-ink">
          Koalitionsprüfer
          <InfoTooltip text={TIP_COALITION_CHECKER} />
        </h2>
        <p className="mt-1 max-w-2xl text-sm text-ink/55">
          Wähle selbst eine oder mehrere Parteien (Alleinregierung ist erlaubt).
          Geprüft wird die reine Sitzsumme — nicht die inklusionsminimalen
          Mehrheiten aus dem Tab „Koalitionen“.
        </p>
        <p className="mt-2 max-w-2xl text-sm text-ink/55">
          Zeigt die Wahrscheinlichkeit für genau diese Auswahl — auch wenn eine
          der Parteien für die Mehrheit gar nicht nötig wäre.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
        <fieldset className="space-y-2">
          <legend className="mb-2 text-sm font-medium text-ink">
            Parteien auswählen
          </legend>
          <ul className="space-y-1.5">
            {options.map((o) => {
              const on = selected.has(o.canonicalId);
              return (
                <li key={o.canonicalId}>
                  <label className="flex cursor-pointer items-center gap-2 rounded-md border border-ink/10 bg-mist/40 px-3 py-2 text-sm transition hover:border-ink/20">
                    <input
                      type="checkbox"
                      className="size-4 accent-sea"
                      checked={on}
                      onChange={() => toggle(o.canonicalId)}
                    />
                    <span
                      className={`${PARTY_SWATCH_CLASS} h-2.5 w-2.5 shrink-0`}
                      style={{ background: partyColor(o.name) }}
                    />
                    <span className="font-medium text-ink">{o.name}</span>
                    <span className="ml-auto tabular-nums text-ink/50">
                      {o.seats}
                    </span>
                  </label>
                </li>
              );
            })}
          </ul>
        </fieldset>

        <div className="space-y-4">
          {selectedList.length === 0 ? (
            <p className="rounded-lg border border-dashed border-ink/15 px-4 py-6 text-sm text-ink/55">
              Mindestens eine Partei auswählen.
            </p>
          ) : (
            <>
              <div className="rounded-xl border border-ink/10 bg-mist/50 p-4">
                <p className="text-xs uppercase tracking-wide text-ink/45">
                  Aktueller Umfrage-Stand
                </p>
                <p className="mt-1 font-display text-2xl text-ink">
                  {localPoint?.hasMajority ? "Mehrheit" : "Keine Mehrheit"}
                </p>
                <p className="mt-1 text-sm text-ink/65">
                  {localPoint?.seats ?? 0} Sitze · Mehrheit ab{" "}
                  {localPoint?.threshold ?? "—"}
                  {localPoint?.total
                    ? ` (von ${localPoint.total})`
                    : ""}
                </p>
                <p className="mt-2 text-xs text-ink/45">
                  {selectedList.map(labelPartyId).join(" + ")}
                </p>
              </div>

              <div className="rounded-xl border border-ink/10 bg-mist/50 p-4">
                <p className="text-xs uppercase tracking-wide text-ink/45">
                  Monte-Carlo-Wahrscheinlichkeit
                </p>
                {checking && probability == null ? (
                  <p className="mt-2 text-sm text-ink/50">Berechne…</p>
                ) : (
                  <>
                    <p className="mt-1 font-display text-3xl tabular-nums text-accent">
                      {probability != null
                        ? `${Math.round(probability * 100)} %`
                        : "—"}
                    </p>
                    <p className="mt-1 text-sm text-ink/65">
                      Chance, dass genau diese Auswahl eine Mehrheit hat
                      {result
                        ? ` · ${result.n_majority} / ${result.n_simulations} Ziehungen`
                        : ""}
                      {checking ? " · aktualisiert…" : ""}
                    </p>
                  </>
                )}
              </div>

              <div className="rounded-xl border border-ink/10 bg-mist/50 p-4">
                <h3 className="mb-2 text-sm font-semibold text-ink">
                  Sitzverteilung
                </h3>
                <Hemicycle
                  seats={seats.seats_by_name}
                  highlightParties={highlightNames}
                  collapseOthers
                  style="projection"
                />
              </div>
            </>
          )}
        </div>
      </div>

      {error ? (
        <p className="rounded-lg border border-accent/30 bg-accent/5 px-4 py-3 text-sm text-accent">
          {error}
        </p>
      ) : null}
    </div>
  );
}
