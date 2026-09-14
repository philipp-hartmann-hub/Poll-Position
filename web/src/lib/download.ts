/** Client-seitiger Datei-Download (Blob + temporärer <a download>). */

export function downloadBlob(filename: string, blob: Blob): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.rel = "noopener";
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

/** Deutsches Zahlenformat für Excel (Komma als Dezimaltrenner). */
export function formatDeNumber(
  value: number | null | undefined,
  digits = 1,
): string {
  if (value == null || Number.isNaN(value)) return "";
  return value.toFixed(digits).replace(".", ",");
}

/** CSV mit Semikolon (Excel DE) und UTF-8-BOM. */
export function toCsv(
  headers: string[],
  rows: (string | number | null | undefined)[][],
): string {
  const escape = (cell: string | number | null | undefined): string => {
    const raw =
      cell == null
        ? ""
        : typeof cell === "number"
          ? String(cell)
          : String(cell);
    if (/[;"\n\r]/.test(raw)) {
      return `"${raw.replace(/"/g, '""')}"`;
    }
    return raw;
  };
  const lines = [
    headers.map(escape).join(";"),
    ...rows.map((row) => row.map(escape).join(";")),
  ];
  return `\uFEFF${lines.join("\r\n")}\r\n`;
}

export function downloadCsv(filename: string, csv: string): void {
  downloadBlob(
    filename,
    new Blob([csv], { type: "text/csv;charset=utf-8" }),
  );
}

export function downloadJson(filename: string, data: unknown): void {
  const body = `${JSON.stringify(data, null, 2)}\n`;
  downloadBlob(
    filename,
    new Blob([body], { type: "application/json;charset=utf-8" }),
  );
}

export function exportBasename(parliamentId: string, kind: string): string {
  const day = new Date().toISOString().slice(0, 10);
  const safeId = parliamentId.replace(/[^a-zA-Z0-9_-]+/g, "_");
  return `poll-position-${safeId}-${kind}-${day}`;
}
