import { useId, useState } from 'react';
import type { ReactNode } from 'react';
import { copy } from '../../lib/copy';

export interface ShowDetailsProps {
  children: ReactNode;
  label?: string;
  hideLabel?: string;
  defaultOpen?: boolean;
}

/** Disclosure toggle: full tables live behind it. The panel grows open instead of jumping. */
export function ShowDetails({ children, label = copy.common.showDetails, hideLabel = copy.common.hideDetails, defaultOpen = false }: ShowDetailsProps) {
  const [open, setOpen] = useState(defaultOpen);
  const panelId = useId();
  return (
    <div className="mt-4">
      <button
        type="button"
        className="group inline-flex min-h-[44px] items-center gap-2 rounded-lg px-1 text-sm font-semibold text-peacock-700 hover:text-peacock-900 sm:min-h-[36px]"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((o) => !o)}
      >
        <span
          aria-hidden="true"
          className={`flex h-6 w-6 items-center justify-center rounded-full transition-[transform,background-color] duration-300 ${open ? 'rotate-45 bg-marigold-400 text-peacock-950' : 'bg-lagoon-100 text-peacock-800 group-hover:bg-lagoon-200'}`}
        >
          <svg viewBox="0 0 16 16" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
            <path d="M8 3v10M3 8h10" />
          </svg>
        </span>
        {open ? hideLabel : label}
      </button>
      <div id={panelId} className="collapsible" data-open={open} aria-hidden={!open} {...({ inert: open ? undefined : '' } as Record<string, string | undefined>)}>
        <div>
          <div className="pt-2">{children}</div>
        </div>
      </div>
    </div>
  );
}
