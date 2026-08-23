import { ParliamentAnalysis } from "@/components/ParliamentAnalysis";

export default function BundPage() {
  return (
    <div className="space-y-4">
      <p className="text-sm uppercase tracking-wide text-ink/45">Deutschland</p>
      <ParliamentAnalysis
        parliamentId="de_bundestag"
        title="Bundestag"
      />
    </div>
  );
}
