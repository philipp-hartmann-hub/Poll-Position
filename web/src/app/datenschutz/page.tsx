export default function DatenschutzPage() {
  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <div className="space-y-2">
        <p className="text-sm uppercase tracking-wide text-ink/45">Rechtliches</p>
        <h1 className="font-display text-3xl tracking-tight text-ink md:text-4xl">
          Datenschutz
        </h1>
        <p className="text-ink/60">
          Datenschutzerklärung — Platzhalter in eckigen Klammern bitte selbst
          ersetzen. Kein Cookie-Banner; Angaben zu Tracking nur ergänzen, wenn
          tatsächlich eingesetzt.
        </p>
      </div>

      <section className="space-y-2 text-sm leading-relaxed text-ink/80">
        <h2 className="font-display text-xl text-ink">
          Verantwortliche Stelle
        </h2>
        <p>
          [Name/Firma]
          <br />
          [Anschrift]
          <br />
          E-Mail: [E-Mail]
        </p>
      </section>

      <section className="space-y-2 text-sm leading-relaxed text-ink/80">
        <h2 className="font-display text-xl text-ink">
          Hosting und Server-Logs
        </h2>
        <p>
          [Hosting-Anbieter, z. B. Vercel / anderer Provider — Ort der
          Verarbeitung, welche technischen Daten (IP, Zeitstempel, User-Agent)
          anfallen und wie lange sie gespeichert werden.]
        </p>
      </section>

      <section className="space-y-2 text-sm leading-relaxed text-ink/80">
        <h2 className="font-display text-xl text-ink">Cookies / Analytics</h2>
        <p>
          [Derzeit kein Tracking/Analytics vorgesehen — oder: eingesetzte
          Dienste, Rechtsgrundlage, Opt-out. Abschnitt anpassen oder streichen.]
        </p>
      </section>

      <section className="space-y-2 text-sm leading-relaxed text-ink/80">
        <h2 className="font-display text-xl text-ink">Ihre Rechte</h2>
        <p>
          [Auskunft, Berichtigung, Löschung, Einschränkung, Widerspruch,
          Beschwerde bei einer Aufsichtsbehörde — Text nach Bedarf ergänzen.]
        </p>
      </section>

      <section className="space-y-2 text-sm leading-relaxed text-ink/80">
        <h2 className="font-display text-xl text-ink">Stand</h2>
        <p>[Datum der letzten Aktualisierung]</p>
      </section>
    </div>
  );
}
