import { ParliamentLayoutClient } from "./ParliamentLayoutClient";

export default async function ParliamentLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <ParliamentLayoutClient parliamentId={id}>{children}</ParliamentLayoutClient>
  );
}
