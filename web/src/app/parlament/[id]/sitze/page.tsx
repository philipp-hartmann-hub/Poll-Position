import { SeatsSection } from "@/components/SeatsSection";

export default async function ParlamentSitzePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <SeatsSection parliamentId={id} />;
}
