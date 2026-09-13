import { ParliamentDashboard } from "@/components/ParliamentDashboard";

export default async function ParlamentPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <ParliamentDashboard parliamentId={id} />;
}
