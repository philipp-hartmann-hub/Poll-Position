export function AttributionFooter() {
  return (
    <footer className="mt-auto border-t border-ink/10 bg-ink/[0.03] px-4 py-6 text-sm text-ink/60">
      <div className="mx-auto max-w-6xl space-y-1">
        <p>
          Datenquellen:{" "}
          <a
            className="underline decoration-ink/20 hover:text-ink"
            href="https://dawum.de/"
            target="_blank"
            rel="noreferrer"
          >
            dawum.de
          </a>{" "}
          (
          <a
            className="underline decoration-ink/20 hover:text-ink"
            href="https://opendatacommons.org/licenses/odbl/1-0/"
            target="_blank"
            rel="noreferrer"
          >
            ODbL
          </a>
          ) · Wikipedia-Mitwirkende (
          <a
            className="underline decoration-ink/20 hover:text-ink"
            href="https://creativecommons.org/licenses/by-sa/4.0/"
            target="_blank"
            rel="noreferrer"
          >
            CC BY-SA 4.0
          </a>
          ) · Wahlrechtsparameter:{" "}
          <a
            className="underline decoration-ink/20 hover:text-ink"
            href="https://www.bundeswahlleiterin.de/"
            target="_blank"
            rel="noreferrer"
          >
            Bundeswahlleiterin
          </a>
          , Landeswahlleitungen /{" "}
          <a
            className="underline decoration-ink/20 hover:text-ink"
            href="https://www.wahlrecht.de/landtage/"
            target="_blank"
            rel="noreferrer"
          >
            wahlrecht.de
          </a>
          {" · "}
          Grenzdaten:{" "}
          <a
            className="underline decoration-ink/20 hover:text-ink"
            href="https://github.com/isellsoap/deutschlandGeoJSON"
            target="_blank"
            rel="noreferrer"
          >
            deutschlandGeoJSON
          </a>{" "}
          (
          <a
            className="underline decoration-ink/20 hover:text-ink"
            href="https://opensource.org/licenses/MIT"
            target="_blank"
            rel="noreferrer"
          >
            MIT
          </a>
          )
        </p>
        <p className="text-xs text-ink/45">
          Persönlicher / nicht-kommerzieller Gebrauch, sofern keine kommerzielle
          Lizenz für europäische Zusatzdaten vorliegt.
        </p>
      </div>
    </footer>
  );
}
