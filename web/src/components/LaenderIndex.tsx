"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { fetchParliaments, type Parliament } from "@/lib/api";
import { DE_PARLIAMENTS } from "@/lib/deParliaments";

function deStates(list: Parliament[]): Parliament[] {
  return list
    .filter((p) => p.level_kind === "state" && p.country === "DE")
    .sort((a, b) => a.name.localeCompare(b.name, "de"));
}

export function LaenderIndex() {
  const [states, setStates] = useState<Parliament[]>(() => deStates(DE_PARLIAMENTS));

  useEffect(() => {
    void fetchParliaments()
      .then((list) => setStates(deStates(list)))
      .catch(() => {
        /* statische Liste bleibt */
      });
  }, []);

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
