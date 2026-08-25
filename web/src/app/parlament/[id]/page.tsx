import { OverviewSection } from "@/components/OverviewSection";

export default async function ParlamentUebersichtPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <OverviewSection parliamentId={id} />;
}
