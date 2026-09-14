import { readFile } from "node:fs/promises";
import path from "node:path";
import { ImageResponse } from "next/og";
import { headers } from "next/headers";
import { partyColor } from "@/lib/colors";
import { displayNameForParliament } from "@/lib/deParliaments";
import { INK, MIST, PAPER, SEA } from "@/lib/theme";

export const runtime = "nodejs";

export const alt = "Poll-Position Sitzprojektion";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

type SeatsPayload = {
  seats_by_name?: Record<string, number>;
  total_seats?: number;
};

function staticSegment(parliamentId: string): string {
  return parliamentId.replace(/[":<>|*?\r\n\\/]/g, "_");
}

function envSiteOrigin(): string {
  const explicit =
    process.env.NEXT_PUBLIC_SITE_URL?.trim() ||
    process.env.NEXT_PUBLIC_APP_URL?.trim();
  if (explicit) return explicit.replace(/\/$/, "");
  if (process.env.VERCEL_URL) {
    return `https://${process.env.VERCEL_URL.replace(/\/$/, "")}`;
  }
  return "http://127.0.0.1:3000";
}

async function resolveSiteOrigin(): Promise<string> {
  try {
    const h = await headers();
    const host = h.get("x-forwarded-host") ?? h.get("host");
    if (host) {
      const proto = h.get("x-forwarded-proto") ?? "http";
      return `${proto.split(",")[0].trim()}://${host}`;
    }
  } catch {
    // außerhalb Request-Kontext
  }
  return envSiteOrigin();
}

function apiOrigin(site: string): string {
  const base = process.env.NEXT_PUBLIC_API_BASE?.trim();
  if (base) return base.replace(/\/$/, "");
  return site;
}

async function fetchJson<T>(url: string): Promise<T | null> {
  try {
    const res = await fetch(url, {
      headers: { Accept: "application/json" },
    });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

async function loadSeatsFromDisk(
  parliamentId: string,
): Promise<SeatsPayload | null> {
  try {
    const file = path.join(
      process.cwd(),
      "public",
      "data",
      staticSegment(parliamentId),
      "seats.json",
    );
    const raw = await readFile(file, "utf8");
    return JSON.parse(raw) as SeatsPayload;
  } catch {
    return null;
  }
}

async function loadSeats(parliamentId: string): Promise<SeatsPayload | null> {
  const fromDisk = await loadSeatsFromDisk(parliamentId);
  if (
    fromDisk?.seats_by_name &&
    Object.keys(fromDisk.seats_by_name).length > 0
  ) {
    return fromDisk;
  }

  const site = await resolveSiteOrigin();
  const segment = encodeURIComponent(staticSegment(parliamentId));
  const q = new URLSearchParams({ parliament_id: parliamentId });
  const candidates = [
    `${site}/data/${segment}/seats.json`,
    `${apiOrigin(site)}/api/seats?${q}`,
  ];
  for (const url of candidates) {
    const data = await fetchJson<SeatsPayload>(url);
    if (data?.seats_by_name && Object.keys(data.seats_by_name).length > 0) {
      return data;
    }
  }
  return null;
}

function formatDateDe(d = new Date()): string {
  return d.toLocaleDateString("de-DE", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function FallbackCard({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        padding: 64,
        background: PAPER,
        color: INK,
      }}
    >
      <div style={{ display: "flex", fontSize: 28, color: SEA }}>
        Poll-Position
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <div style={{ display: "flex", fontSize: 64, fontWeight: 700 }}>
          {title}
        </div>
        <div style={{ display: "flex", fontSize: 28, color: `${INK}99` }}>
          {subtitle}
        </div>
      </div>
      <div style={{ display: "flex", fontSize: 24, color: `${INK}66` }}>
        Umfragen · Sitze · Koalitionen
      </div>
    </div>
  );
}

export default async function Image({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const title = displayNameForParliament(id);
  const dateLabel = formatDateDe();
  const seats = await loadSeats(id);

  if (!seats?.seats_by_name) {
    return new ImageResponse(
      (
        <FallbackCard
          title={title}
          subtitle={`${dateLabel} · Sitzdaten gerade nicht verfügbar`}
        />
      ),
      { ...size },
    );
  }

  const entries = Object.entries(seats.seats_by_name)
    .filter(([, n]) => n > 0)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 7);
  const maxSeats = Math.max(...entries.map(([, n]) => n), 1);
  const total =
    seats.total_seats ??
    entries.reduce((sum, [, n]) => sum + n, 0);

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          padding: 56,
          background: PAPER,
          color: INK,
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: 28,
          }}
        >
          <div style={{ display: "flex", fontSize: 26, color: SEA }}>
            Poll-Position
          </div>
          <div style={{ display: "flex", fontSize: 24, color: `${INK}88` }}>
            {dateLabel}
          </div>
        </div>

        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 8,
            marginBottom: 32,
          }}
        >
          <div style={{ display: "flex", fontSize: 52, fontWeight: 700 }}>
            {title}
          </div>
          <div style={{ display: "flex", fontSize: 26, color: `${INK}99` }}>
            Sitzprojektion nach aktuellen Umfragen · {total} Sitze
          </div>
        </div>

        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 14,
            flex: 1,
          }}
        >
          {entries.map(([name, n]) => {
            const pct = Math.max(8, Math.round((n / maxSeats) * 100));
            return (
              <div
                key={name}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 18,
                }}
              >
                <div
                  style={{
                    display: "flex",
                    width: 160,
                    fontSize: 26,
                    fontWeight: 600,
                  }}
                >
                  {name}
                </div>
                <div
                  style={{
                    display: "flex",
                    flex: 1,
                    height: 34,
                    background: MIST,
                    borderRadius: 8,
                    overflow: "hidden",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      width: `${pct}%`,
                      height: "100%",
                      background: partyColor(name),
                      borderRadius: 8,
                    }}
                  />
                </div>
                <div
                  style={{
                    display: "flex",
                    width: 72,
                    justifyContent: "flex-end",
                    fontSize: 26,
                    fontVariantNumeric: "tabular-nums",
                  }}
                >
                  {n}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    ),
    { ...size },
  );
}
