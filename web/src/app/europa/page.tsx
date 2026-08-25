import { redirect } from "next/navigation";
import { EuropaOverviewClient } from "@/components/EuropaOverviewClient";
import { features } from "@/lib/features";

export default function EuropaPage() {
  if (!features.europe) redirect("/");
  return <EuropaOverviewClient />;
}
