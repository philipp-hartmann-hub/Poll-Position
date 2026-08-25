import { notFound, redirect } from "next/navigation";
import { ParliamentAnalysis } from "@/components/ParliamentAnalysis";
import { EUROPE_COUNTRIES } from "@/lib/europe";
import { features } from "@/lib/features";

export function generateStaticParams() {
  if (!features.europe) return [];
  return Object.keys(EUROPE_COUNTRIES)
    .filter((iso) => iso !== "de")
    .map((country) => ({ country }));
}

export default async function EuropaCountryPage({
  params,
}: {
  params: Promise<{ country: string }>;
}) {
  if (!features.europe) redirect("/");

  const { country } = await params;
  const meta = EUROPE_COUNTRIES[country.toLowerCase()];
  if (!meta || meta.iso === "DE") notFound();

  const pollsOnly = meta.approximation === "majority";

  return (
    <div className="space-y-4">
      <p className="text-sm uppercase tracking-wide text-ink/45">Europa</p>
      <ParliamentAnalysis
        parliamentId={meta.parliamentId}
        title={meta.name}
        disclaimer={meta.badge}
        includeSeats={!pollsOnly}
      />
    </div>
  );
}
