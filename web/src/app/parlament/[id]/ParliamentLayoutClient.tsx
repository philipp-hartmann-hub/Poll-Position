"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { fetchParliaments, type Parliament } from "@/lib/api";
import { ParliamentIdProvider } from "./parliament-context";

const TABS = [
  { slug: "", label: "Übersicht" },
  { slug: "sitze", label: "Sitze" },
  { slug: "koalitionen", label: "Koalitionen" },
  { slug: "institute", label: "Institute" },
  { slug: "szenario", label: "Szenario" },
] as const;

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

function currentTabSlug(pathname: string, parliamentId: string): string {
  const prefix = `/parlament/${parliamentId}`;
  if (pathname === prefix || pathname === `${prefix}/`) return "";
  if (!pathname.startsWith(`${prefix}/`)) return "";
  return pathname.slice(prefix.length + 1).split("/")[0] ?? "";
}

export function ParliamentLayoutClient({
  parliamentId,
  children,
}: {
  parliamentId: string;
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const [parliaments, setParliaments] = useState<Parliament[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    void fetchParliaments()
      .then((list) => setParliaments(sortDeParliaments(list)))
      .catch((e) =>
        setLoadError(e instanceof Error ? e.message : "Parlamente laden fehlgeschlagen"),
      );
  }, []);

  const { bund, laender } = useMemo(() => {
    const bundList = parliaments.filter((p) => p.level_kind === "national");
    const stateList = parliaments.filter((p) => p.level_kind === "state");
    return { bund: bundList, laender: stateList };
  }, [parliaments]);

  const tabSlug = currentTabSlug(pathname, parliamentId);
  const knownId = parliaments.some((p) => p.id === parliamentId);

  function onParliamentChange(nextId: string) {
    if (!nextId || nextId === parliamentId) return;
    const suffix = tabSlug ? `/${tabSlug}` : "";
    router.push(`/parlament/${nextId}${suffix}`);
  }

  return (
    <ParliamentIdProvider parliamentId={parliamentId}>
      <div className="space-y-6">
        <label className="block max-w-md text-sm">
          <span className="mb-1 block text-ink/50">Parlament wählen</span>
          <select
            className="w-full rounded-md border border-ink/15 bg-white px-3 py-2"
            value={parliamentId}
            onChange={(e) => onParliamentChange(e.target.value)}
            disabled={!parliaments.length}
          >
            {!knownId && (
              <option value={parliamentId}>{parliamentId}</option>
            )}
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

        {loadError && <p className="text-sm text-accent">{loadError}</p>}

        <nav
          className="flex flex-wrap gap-1 border-b border-ink/10"
          aria-label="Parlament-Bereiche"
        >
          {TABS.map((tab) => {
            const href =
              tab.slug === ""
                ? `/parlament/${parliamentId}`
                : `/parlament/${parliamentId}/${tab.slug}`;
            const active = tabSlug === tab.slug;
            return (
              <Link
                key={tab.slug || "uebersicht"}
                href={href}
                className={
                  active
                    ? "border-b-2 border-sea px-3 py-2 text-sm font-medium text-ink"
                    : "border-b-2 border-transparent px-3 py-2 text-sm text-ink/60 transition hover:text-ink"
                }
                aria-current={active ? "page" : undefined}
              >
                {tab.label}
              </Link>
            );
          })}
        </nav>

        <div>{children}</div>
      </div>
    </ParliamentIdProvider>
  );
}
