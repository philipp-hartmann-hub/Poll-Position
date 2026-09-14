import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Methodik · Poll-Position",
  description:
    "Wie Poll-Position Umfragen, Sitze, Unsicherheit und Koalitionen berechnet — in Alltagssprache.",
};

export default function MethodikPage() {
  return (
    <article className="mx-auto max-w-2xl space-y-10">
      <header className="space-y-3">
        <p className="text-sm uppercase tracking-wide text-ink/45">Hintergrund</p>
        <h1 className="font-display text-3xl tracking-tight text-ink md:text-4xl">
          Wie funktioniert diese Seite?
        </h1>
        <p className="text-ink/65">
          Kurzfassung der Berechnung: was die Zahlen bedeuten, warum sie
          schwanken können — und was sie ausdrücklich nicht sind. Keine
          Wahlprognose, sondern Momentaufnahmen auf Basis veröffentlichter
          Umfragen und der geltenden Sitzregeln.
        </p>
      </header>

      <section className="space-y-3">
        <h2 className="font-display text-2xl text-ink">
          Umfrage-Mittelwert &amp; Trend
        </h2>
        <p className="text-sm leading-relaxed text-ink/80">
          Der Ø-%-Wert ist der gewichtete Durchschnitt der letzten Umfragen.
          Neuere und — wo sinnvoll — verlässlichere Institute fließen etwas
          stärker ein. Manche Institute liegen im Schnitt systematisch etwas
          höher oder niedriger für bestimmte Parteien als der Durchschnitt
          aller Institute (Haus-Effekt); das wird beim Mittelwert leicht
          ausgeglichen, damit einzelne Institute den Gesamtschnitt nicht
          verzerren.
        </p>
        <p className="text-sm leading-relaxed text-ink/80">
          Trend % und die Trendlinie glätten kurzfristiges Auf und Ab
          zusätzlich heraus und zeigen eher die längerfristige Richtung — sie
          können deshalb leicht vom aktuellen Durchschnitt abweichen. Das ist
          der Verlauf der veröffentlichten Umfragen, keine Vorhersage der
          nächsten Wahl.
        </p>
        <p className="text-sm leading-relaxed text-ink/80">
          „Swing“ bzw. Gewinne &amp; Verluste seit der letzten Wahl: Unterschied
          in Prozentpunkten zwischen dem heutigen Umfrage-Durchschnitt und dem
          tatsächlichen Ergebnis bei der letzten Wahl. Plus heißt: in Umfragen
          aktuell stärker als beim letzten Wahlergebnis, Minus heißt schwächer.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="font-display text-2xl text-ink">Sitzprojektion</h2>
        <p className="text-sm leading-relaxed text-ink/80">
          Die Sitzprojektion zeigt, wie viele Sitze jede Partei bekäme, wenn
          heute gewählt würde — auf Basis der aktuellen Umfragewerte und der
          echten Sitzverteilungsregeln dieses Parlaments (Schwellen, Sitzzahl,
          Zuteilungsverfahren). Keine Vorhersage des tatsächlichen
          Wahlausgangs, sondern eine Momentaufnahme. Wo das nationale Wahlrecht
          keine sinnvolle Umrechnung aus landesweiten Umfragen zulässt (z. B.
          Frankreich), zeigen wir nur Umfragen, keine Sitze.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="font-display text-2xl text-ink">
          Sperrklausel &amp; Unsicherheit
        </h2>
        <p className="text-sm leading-relaxed text-ink/80">
          Unter „Prognose je Partei“ lassen wir den aktuellen Umfragewert
          tausendfach leicht zufällig schwanken — so wie echte Umfragen von
          Umfrage zu Umfrage auch schwanken — und zählen, wie oft jede Partei
          dabei die meisten Stimmen hätte bzw. über die 5-%-Hürde (oder die
          jeweilige Hürde des Parlaments) käme. Die Zahl ist also keine
          Wahlprognose, sondern zeigt, wie sicher oder unsicher der heutige
          Umfragestand selbst ist.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="font-display text-2xl text-ink">
          Koalitions-Wahrscheinlichkeit
        </h2>
        <p className="text-sm leading-relaxed text-ink/80">
          Die Liste möglicher Koalitionen nennt Parteien-Kombinationen, die
          nach der aktuellen Sitzhochrechnung gemeinsam mehr als die Hälfte der
          Sitze hätten. Ob sie politisch zustande kämen, sagt die Liste nicht —
          nur, dass die Sitze rechnerisch reichen würden.
        </p>
        <p className="text-sm leading-relaxed text-ink/80">
          Unter „Wie sicher ist die Mehrheit?“ fragen wir: Wie oft käme genau
          diese Parteien-Kombination auf eine Mehrheit der Sitze, wenn man den
          heutigen Umfragestand tausendfach leicht schwanken lässt? Gezählt wird
          nur, wenn wirklich jede genannte Partei dafür gebraucht wird —
          reicht schon ein Teil der Kombination für die Mehrheit, zählt das
          nicht mit, damit keine Partei nur mitgelistet wird, ohne wirklich
          etwas beizutragen.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="font-display text-2xl text-ink">Bundesrat-Modell</h2>
        <p className="text-sm leading-relaxed text-ink/80">
          Das Grundgesetz schreibt vor: Sind sich die Regierungsparteien eines
          Landes bei einer Bundesratsabstimmung nicht einig, muss sich das Land
          enthalten. Deshalb hier: Stimmen alle Regierungsparteien eines Landes
          auf Bundesebene derselben Linie zu → Ja-Stimme. Sind sie sich nicht
          einig → Enthaltung. Lehnen alle gemeinsam ab → Nein-Stimme. Das ist
          ein Modell aus den amtierenden bzw. angenommenen Landesregierungen,
          keine echte Abstimmungs-Prognose.
        </p>
        <p className="text-sm leading-relaxed text-ink/80">
          Im Bundesrat braucht ein Beschluss die Mehrheit der Stimmen aller
          Länder (mindestens 35 von 69). Ja-Stimmen zählen für den Beschluss,
          Enthaltungen und Nein-Stimmen nicht — Enthaltung wirkt deshalb wie
          ein Nein gegen die Vorlage.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="font-display text-2xl text-ink">Datenquellen</h2>
        <p className="text-sm leading-relaxed text-ink/80">
          Umfragen und Institute stammen vor allem von{" "}
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
          ). Paneuropäische bzw. ergänzende Umfragen kommen von
          Wikipedia-Mitwirkenden (
          <a
            className="underline decoration-ink/20 hover:text-ink"
            href="https://creativecommons.org/licenses/by-sa/4.0/"
            target="_blank"
            rel="noreferrer"
          >
            CC BY-SA 4.0
          </a>
          ). Wahlrechtsparameter (Sitzzahlen, Schwellen, Verfahren) orientieren
          sich an Angaben der{" "}
          <a
            className="underline decoration-ink/20 hover:text-ink"
            href="https://www.bundeswahlleiterin.de/"
            target="_blank"
            rel="noreferrer"
          >
            Bundeswahlleiterin
          </a>
          , der Landeswahlleitungen und{" "}
          <a
            className="underline decoration-ink/20 hover:text-ink"
            href="https://www.wahlrecht.de/landtage/"
            target="_blank"
            rel="noreferrer"
          >
            wahlrecht.de
          </a>
          . Grenzdaten der Deutschlandkarte:{" "}
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
          ).
        </p>
        <p className="text-sm leading-relaxed text-ink/80">
          Persönlicher / nicht-kommerzieller Gebrauch, sofern keine
          kommerzielle Lizenz für europäische Zusatzdaten vorliegt. Hinterlegte
          Wahlergebnisse oder Regierungsdaten können veralten; die App zeigt
          dann ggf. einen Hinweis — ohne die Zahlen automatisch zu
          korrigieren.
        </p>
      </section>

      <p className="border-t border-ink/10 pt-6 text-sm text-ink/55">
        Kurzinfos zu einzelnen Kennzahlen stehen auch als „i“-Hinweise neben
        den jeweiligen Diagrammen.{" "}
        <Link href="/parlament/de_bundestag" className="text-sea hover:underline">
          Zurück zur Übersicht
        </Link>
      </p>
    </article>
  );
}
