import type { Metadata } from "next";
import "./globals.css";
import { SiteNav } from "@/components/SiteNav";
import { AttributionFooter } from "@/components/AttributionFooter";

export const metadata: Metadata = {
  title: "Poll-Position",
  description: "Umfragen, Sitze und Koalitionen für Deutschland und Europa",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="de">
      <body className="min-h-screen bg-paper bg-grid-fade text-ink antialiased">
        <div className="flex min-h-screen flex-col">
          <SiteNav />
          <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 md:py-12">
            {children}
          </main>
          <AttributionFooter />
        </div>
      </body>
    </html>
  );
}
