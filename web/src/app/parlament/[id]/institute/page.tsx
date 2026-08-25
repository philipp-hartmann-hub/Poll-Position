import { InstituteView } from "@/components/InstituteView";

export default async function ParlamentInstitutePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <InstituteView parliamentId={id} />;
}
