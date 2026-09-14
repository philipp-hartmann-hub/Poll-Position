import { Suspense } from "react";
import { LastElectionSection } from "@/components/LastElectionSection";
import { displayNameForParliament } from "@/lib/deParliaments";
import type { Metadata } from "next";
import Link from "next/link";

type PageProps = {
  params: Promise<{ id: string }>;
};

export async function generateMetadata({
  params,
}: PageProps): Promise<Metadata> {
  const { id } = await params;
  const name = displayNameForParliament(id);
  return {
    title: `Letzte Wahl · ${name} · Poll-Position`,
    description: `Amtliches Wahlergebnis, Sitze und mögliche Koalitionen für ${name}.`,
  };
}

export default async function LetzteWahlPage({ params }: PageProps) {
  const { id } = await params;
  return (
    <div className="space-y-6">
      <p className="text-sm text-ink/55">
        <Link
          href={`/parlament/${id}`}
          className="text-sea underline-offset-2 hover:underline"
        >
          ← Zurück zur Übersicht
        </Link>
      </p>
      <Suspense
        fallback={<p className="text-sm text-ink/50">Lade Wahlergebnis…</p>}
      >
        <LastElectionSection parliamentId={id} />
      </Suspense>
    </div>
  );
}
