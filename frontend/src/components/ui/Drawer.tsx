import { useEffect, useId, useRef } from 'react';
import type { ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { copy } from '../../lib/copy';
import { useDialogBehavior } from '../../hooks/useDialogBehavior';

export interface DrawerProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
}

/** Side panel (bottom-aligned full width on phones). Esc closes, Tab stays inside, focus returns to the opener. */
export function Drawer({ open, onClose, title, children }: DrawerProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const titleId = useId();
  useDialogBehavior(panelRef, open, onClose);

  useEffect(() => {
    if (!open) return undefined;
    const previous = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = previous;
    };
  }, [open]);

  if (!open) return null;

  return createPortal(
    <div className="fixed inset-0 z-50">
      <div className="absolute inset-0 animate-fade bg-peacock-950/55 backdrop-blur-[2px]" onClick={onClose} aria-hidden="true" />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        className="absolute inset-x-0 bottom-0 flex max-h-[92vh] animate-slide-in-up flex-col rounded-t-3xl bg-paper shadow-lift sm:inset-y-0 sm:left-auto sm:right-0 sm:max-h-none sm:w-[36rem] sm:animate-slide-in-right sm:rounded-none sm:rounded-l-3xl"
      >
        <div className="jali flex items-center justify-between gap-3 px-4 py-4 text-white sm:rounded-tl-3xl sm:px-6">
          <h2 id={titleId} className="font-display text-xl font-bold">
            {title}
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label={copy.common.close}
            className="inline-flex h-10 w-10 items-center justify-center rounded-full text-white transition-transform duration-200 hover:rotate-90 hover:bg-white/10"
          >
            <span aria-hidden="true">✕</span>
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-4 py-4 sm:px-6">{children}</div>
      </div>
    </div>,
    document.body,
  );
}
