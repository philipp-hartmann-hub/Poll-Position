import { ScenarioWorkbench } from "@/components/ScenarioWorkbench";

export default async function ParlamentSzenarioPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <ScenarioWorkbench parliamentId={id} />;
}
