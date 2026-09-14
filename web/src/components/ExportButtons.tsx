"use client";

type Props = {
  onCsv: () => void;
  onJson?: () => void;
  disabled?: boolean;
  labelCsv?: string;
  labelJson?: string;
};

export function ExportButtons({
  onCsv,
  onJson,
  disabled = false,
  labelCsv = "Als CSV exportieren",
  labelJson = "Als JSON",
}: Props) {
  return (
    <div className="flex flex-wrap gap-2">
      <button
        type="button"
        disabled={disabled}
        onClick={onCsv}
        className="rounded border border-ink/15 bg-mist/40 px-2.5 py-1 text-xs text-ink/70 transition hover:border-ink/25 hover:text-ink disabled:opacity-40"
      >
        {labelCsv}
      </button>
      {onJson ? (
        <button
          type="button"
          disabled={disabled}
          onClick={onJson}
          className="rounded border border-ink/15 bg-mist/40 px-2.5 py-1 text-xs text-ink/70 transition hover:border-ink/25 hover:text-ink disabled:opacity-40"
        >
          {labelJson}
        </button>
      ) : null}
    </div>
  );
}
