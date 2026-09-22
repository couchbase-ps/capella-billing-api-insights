import { ChevronDown, Download } from "lucide-react";
import type { JSX } from "react";
import { useEffect, useRef, useState } from "react";

export interface DownloadOption {
  label: string;
  href: string;
}

/** "Download as…" button that opens a small menu of formats (each entry is a plain link). */
export function DownloadMenu({ options }: { options: DownloadOption[] }): JSX.Element {
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) {
      return;
    }
    const close = (event: MouseEvent) => {
      if (root.current && !root.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [open]);
  return (
    <div ref={root} className="relative">
      <button
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
        className="inline-flex items-center gap-1 rounded-sm border border-border px-2.5 py-1 text-label-sm hover:bg-surface-alt"
      >
        <Download size={14} aria-hidden="true" />
        Download as
        <ChevronDown size={14} aria-hidden="true" />
      </button>
      {open && (
        <div
          role="menu"
          className="absolute right-0 z-10 mt-1 min-w-32 rounded-sm border border-border bg-surface py-1 shadow-float"
        >
          {options.map((option) => (
            <a
              key={option.label}
              role="menuitem"
              href={option.href}
              download
              onClick={() => setOpen(false)}
              className="block px-3 py-1.5 text-body-sm hover:bg-surface-alt"
            >
              {option.label}
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
