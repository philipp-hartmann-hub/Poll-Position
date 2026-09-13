import Link from "next/link";
import { features } from "@/lib/features";

/** Fallback, falls der Redirect in next.config.ts nicht greift. */
export default function HomePage() {
  return (
    <div className="space-y-6 py-12">
      <p className="text-sm text-ink/55">Weiterleitung zum Bundestag …</p>
      <ul className="space-y-2 text-ink/75">
        <li>
          <Link className="text-sea hover:underline" href="/parlament/de_bundestag">
            Bundestag
          </Link>
        </li>
        <li>
          <Link className="hover:text-sea" href="/deutschland/laender">
            Länder
          </Link>
        </li>
        <li>
          <Link className="hover:text-sea" href="/bundesrat">
            Bundesrat
          </Link>
        </li>
        <li>
          <Link className="hover:text-sea" href="/institute">
            Institute
          </Link>
        </li>
        {features.europe ? (
          <li>
            <Link className="hover:text-sea" href="/europa">
              Europa
            </Link>
          </li>
        ) : null}
      </ul>
    </div>
  );
}
