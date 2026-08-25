"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { fetchParliaments, type Parliament } from "@/lib/api";

export function LaenderIndex() {
  const [states, setStates] = useState<Parliament[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void fetchParliaments()
      .then((list) => {
        setStates(
          list
            .filter((p) => p.level_kind === "state" && p.country === "DE")
            .sort((a, b) => a.name.localeCompare(b.name, "de")),
        );
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Fehler"));
  }, []);

  if (error) {
    return <p className="text-sm text-accent">{error}</p>;
  }
  if (!states.length) {
    return <p className="text-sm text-ink/50">Lade Landtage…</p>;
  }

  return (
    <ul className="grid gap-2 sm:grid-cols-2">
      {states.map((s) => (
        <li key={s.id}>
          <Link
            href={`/parlament/${s.id}`}
            className="block rounded-lg border border-ink/10 bg-white/50 px-4 py-3 text-ink transition hover:border-sea/40 hover:bg-mist/40"
          >
            <span className="font-medium">{s.name}</span>
            {s.shortcut ? (
              <span className="ml-2 text-sm text-ink/45">{s.shortcut}</span>
            ) : null}
          </Link>
        </li>
      ))}
    </ul>
  );
}
