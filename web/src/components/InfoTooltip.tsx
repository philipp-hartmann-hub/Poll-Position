"use client";

import { useId, useState } from "react";

export function InfoTooltip({ text }: { text: string }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  return (
    <span className="relative inline-flex align-middle">
      <button
        type="button"
        aria-describedby={id}
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        onBlur={() => setOpen(false)}
        className="ml-1.5 inline-flex h-4 w-4 items-center justify-center rounded-full border border-ink/30 text-[10px] leading-none text-ink/60 transition hover:border-ink/60 hover:text-ink"
      >
        i
      </button>
      {open && (
        <span
          id={id}
          role="tooltip"
          className="absolute bottom-full left-1/2 z-20 mb-1.5 w-64 -translate-x-1/2 rounded-lg border border-ink/15 bg-white px-3 py-2 text-xs leading-relaxed text-ink/80 shadow-lg"
        >
          {text}
        </span>
      )}
    </span>
  );
}
