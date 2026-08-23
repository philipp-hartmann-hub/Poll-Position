"use client";

import { useEffect, useState } from "react";
import { fetchParliaments, type Parliament } from "@/lib/api";
import { ParliamentAnalysis } from "@/components/ParliamentAnalysis";

export function LaenderPicker() {
  const [states, setStates] = useState<Parliament[]>([]);
  const [id, setId] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void fetchParliaments()
      .then((list) => {
        const s = list
          .filter((p) => p.level_kind === "state" && p.country === "DE")
          .sort((a, b) => a.name.localeCompare(b.name, "de"));
        setStates(s);
        if (s[0]) setId(s[0].id);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Fehler"));
  }, []);

  if (error) {
    return <p className="text-sm text-accent">{error}</p>;
  }
  if (!states.length) {
    return <p className="text-sm text-ink/50">Lade Landtage…</p>;
  }

  const current = states.find((s) => s.id === id);

  return (
    <div className="space-y-8">
      <label className="block max-w-md text-sm">
        <span className="mb-1 block text-ink/50">Bundesland / Landtag</span>
        <select
          className="w-full rounded-md border border-ink/15 bg-white px-3 py-2"
          value={id}
          onChange={(e) => setId(e.target.value)}
        >
          {states.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
      </label>
      {id && (
        <ParliamentAnalysis parliamentId={id} title={current?.name} />
      )}
    </div>
  );
}
