import type { Metadata } from "next";
import { ParliamentDashboard } from "@/components/ParliamentDashboard";
import { displayNameForParliament } from "@/lib/deParliaments";

type PageProps = {
  params: Promise<{ id: string }>;
};

export async function generateMetadata({
  params,
}: PageProps): Promise<Metadata> {
  const { id } = await params;
  const name = displayNameForParliament(id);
  const title = `${name} · Poll-Position`;
  const description = `Umfragen, Sitzprojektion und Koalitionen für ${name}.`;

  return {
    title,
    description,
    openGraph: {
      title,
      description,
      type: "website",
      locale: "de_DE",
      // opengraph-image.tsx im selben Segment wird von Next automatisch als og:image verknüpft
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
    },
  };
}

export default async function ParlamentPage({ params }: PageProps) {
  const { id } = await params;
  return <ParliamentDashboard parliamentId={id} />;
}
