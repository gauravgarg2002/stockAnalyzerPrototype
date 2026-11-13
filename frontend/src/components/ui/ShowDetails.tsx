import { useId, useState } from 'react';
import type { ReactNode } from 'react';
import { copy } from '../../lib/copy';

export interface ShowDetailsProps {
  children: ReactNode;
  label?: string;
  hideLabel?: string;
  defaultOpen?: boolean;
}

/** Disclosure toggle: full tables live behind it. */
export function ShowDetails({ children, label = copy.common.showDetails, hideLabel = copy.common.hideDetails, defaultOpen = false }: ShowDetailsProps) {
  const [open, setOpen] = useState(defaultOpen);
  const panelId = useId();
  return (
    <div className="mt-4">
      <button
        type="button"
        className="inline-flex min-h-[44px] items-center gap-1.5 rounded-lg px-1 text-sm font-medium text-indigo-700 hover:text-indigo-900 sm:min-h-[36px]"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((o) => !o)}
      >
        <svg
          viewBox="0 0 20 20"
          className={`h-4 w-4 transition-transform motion-reduce:transition-none ${open ? 'rotate-90' : ''}`}
          fill="currentColor"
          aria-hidden="true"
        >
          <path d="M7 4l6 6-6 6V4z" />
        </svg>
        {open ? hideLabel : label}
      </button>
      <div id={panelId} hidden={!open} className="mt-2">
        {open ? children : null}
      </div>
    </div>
  );
}
