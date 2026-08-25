import { CoalitionsSection } from "@/components/CoalitionsSection";

export default async function ParlamentKoalitionenPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <CoalitionsSection parliamentId={id} />;
}
