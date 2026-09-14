"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { fetchParliaments, type Parliament } from "@/lib/api";
import {
  DE_PARLIAMENTS,
  parliamentIdFromPath,
} from "@/lib/deParliaments";

function sortDeParliaments(list: Parliament[]): Parliament[] {
  return [...list]
    .filter((p) => p.country === "DE")
    .sort((a, b) => {
      const aNat = a.level_kind === "national" ? 0 : 1;
      const bNat = b.level_kind === "national" ? 0 : 1;
      if (aNat !== bNat) return aNat - bNat;
      return a.name.localeCompare(b.name, "de");
    });
}

function mergeDeParliaments(apiList: Parliament[]): Parliament[] {
  const byId = new Map(DE_PARLIAMENTS.map((p) => [p.id, p]));
  for (const p of apiList) {
    if (p.country !== "DE") continue;
    byId.set(p.id, { ...byId.get(p.id), ...p });
  }
  return sortDeParliaments([...byId.values()]);
}

/** Hinweistext für nächste Wahl; bei abgelaufenem Datum null (nichts anzeigen). */
function nextElectionHint(p: Parliament | undefined): string | null {
  if (!p) return null;
  const iso = p.next_election_date?.trim();
  if (iso) {
    const election = new Date(`${iso}T12:00:00`);
    if (Number.isNaN(election.getTime())) {
      return p.next_election_note?.trim() || null;
    }
    const today = new Date();
    today.setHours(12, 0, 0, 0);
    const days = Math.round(
      (election.getTime() - today.getTime()) / (24 * 60 * 60 * 1000),
    );
    if (days < 0) return null;
    const formatted = election.toLocaleDateString("de-DE", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
    if (days === 0) return `Nächste Wahl: heute (${formatted})`;
    return `Nächste Wahl: ${formatted} · in ${days} Tagen`;
  }
  const note = p.next_election_note?.trim();
  return note ? `Nächste Wahl: ${note}` : null;
}

export function ParliamentLayoutClient({
  parliamentId: parliamentIdProp,
  children,
}: {
  parliamentId: string;
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  // URL ist maßgeblich — Layout-Props können bei Client-Navigation kurz hinken.
  const parliamentId = parliamentIdFromPath(pathname) ?? parliamentIdProp;

  const [parliaments, setParliaments] = useState<Parliament[]>(() =>
    sortDeParliaments(DE_PARLIAMENTS),
  );
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    void fetchParliaments()
      .then((list) => setParliaments(mergeDeParliaments(list)))
      .catch((e) =>
        setLoadError(
          e instanceof Error ? e.message : "Parlamente laden fehlgeschlagen",
        ),
      );
  }, []);

  const { bund, laender } = useMemo(() => {
    const bundList = parliaments.filter((p) => p.level_kind === "national");
    const stateList = parliaments.filter((p) => p.level_kind === "state");
    return { bund: bundList, laender: stateList };
  }, [parliaments]);

  const knownId = parliaments.some((p) => p.id === parliamentId);
  const currentParliament = parliaments.find((p) => p.id === parliamentId);
  const electionHint = nextElectionHint(currentParliament);

  function onParliamentChange(nextId: string) {
    if (!nextId || nextId === parliamentId) return;
    router.push(`/parlament/${nextId}`);
  }

  return (
    <div className="space-y-6">
      <div className="flex max-w-xl flex-col gap-1 sm:flex-row sm:items-end sm:gap-4">
        <label className="block min-w-0 flex-1 text-sm">
          <span className="mb-1 block text-ink/50">Parlament wählen</span>
          <select
            className="w-full rounded-md border border-ink/15 bg-mist px-3 py-2"
            value={parliamentId}
            onChange={(e) => onParliamentChange(e.target.value)}
          >
            {!knownId && <option value={parliamentId}>{parliamentId}</option>}
            {bund.length > 0 && (
              <optgroup label="Bund">
                {bund.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </optgroup>
            )}
            {laender.length > 0 && (
              <optgroup label="Länder">
                {laender.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </optgroup>
            )}
          </select>
        </label>
        {electionHint ? (
          <p className="pb-2 text-xs text-ink/55 sm:max-w-[14rem] sm:pb-2.5">
            {electionHint}
          </p>
        ) : null}
      </div>

      {loadError && (
        <p className="text-sm text-ink/45">
          Live-Liste nicht erreichbar — lokale Auswahl wird genutzt.
        </p>
      )}

      <div>{children}</div>
    </div>
  );
}
