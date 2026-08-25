"use client";

import { OverviewSection } from "@/components/OverviewSection";
import { SeatsSection } from "@/components/SeatsSection";
import { CoalitionsSection } from "@/components/CoalitionsSection";

/** Komfort-Wrapper für die alten Bund-/Länder-/Europa-Seiten. */
export function ParliamentAnalysis({
  parliamentId,
  title,
  disclaimer,
  includeSeats = true,
}: {
  parliamentId: string;
  title?: string;
  disclaimer?: string;
  includeSeats?: boolean;
}) {
  return (
    <div className="space-y-10">
      {title && (
        <h1 className="font-display text-3xl tracking-tight text-ink md:text-4xl">
          {title}
        </h1>
      )}

      {disclaimer ? (
        <p className="rounded-md border border-amber-700/25 bg-amber-50/80 px-3 py-2 text-sm text-ink/80">
          {disclaimer}
        </p>
      ) : null}

      <OverviewSection
        parliamentId={parliamentId}
        showThreshold={includeSeats}
      />

      {includeSeats ? <SeatsSection parliamentId={parliamentId} /> : null}

      {includeSeats ? <CoalitionsSection parliamentId={parliamentId} /> : null}
    </div>
  );
}
