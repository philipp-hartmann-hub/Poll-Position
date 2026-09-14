export default function ImpressumPage() {
  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <div className="space-y-2">
        <p className="text-sm uppercase tracking-wide text-ink/45">Rechtliches</p>
        <h1 className="font-display text-3xl tracking-tight text-ink md:text-4xl">
          Impressum
        </h1>
        <p className="text-ink/60">
          Angaben gemäß § 5 TMG / Anbieterkennzeichnung. Platzhalter in eckigen
          Klammern bitte selbst ersetzen.
        </p>
      </div>

      <section className="space-y-2 text-sm leading-relaxed text-ink/80">
        <h2 className="font-display text-xl text-ink">Anbieter</h2>
        <p>
          [Name/Firma]
          <br />
          [Anschrift — Straße, Hausnummer]
          <br />
          [PLZ Ort]
          <br />
          [Land]
        </p>
      </section>

      <section className="space-y-2 text-sm leading-relaxed text-ink/80">
        <h2 className="font-display text-xl text-ink">Kontakt</h2>
        <p>
          E-Mail: [E-Mail]
          <br />
          Telefon: [Telefon, optional]
        </p>
      </section>

      <section className="space-y-2 text-sm leading-relaxed text-ink/80">
        <h2 className="font-display text-xl text-ink">
          Verantwortlich für den Inhalt
        </h2>
        <p>
          [Name der verantwortlichen Person]
          <br />
          [Anschrift, falls abweichend]
        </p>
      </section>

      <section className="space-y-2 text-sm leading-relaxed text-ink/80">
        <h2 className="font-display text-xl text-ink">
          Umsatzsteuer / Register
        </h2>
        <p>
          USt-IdNr.: [falls vorhanden, sonst diesen Abschnitt streichen]
          <br />
          Handelsregister: [falls vorhanden, sonst streichen]
        </p>
      </section>

      <section className="space-y-2 text-sm leading-relaxed text-ink/80">
        <h2 className="font-display text-xl text-ink">Haftungshinweis</h2>
        <p>
          [Kurz: Haftung für eigene Inhalte / Links zu fremden Seiten —
          Text nach Bedarf ergänzen oder durch geprüfte Vorlage ersetzen.]
        </p>
      </section>
    </div>
  );
}
