import { useEffect, useId, useLayoutEffect, useRef, useState } from 'react';
import type { CSSProperties, RefObject } from 'react';
import { createPortal } from 'react-dom';
import { getExplain } from '../../lib/api-client';
import { formatDate } from '../../lib/dates';
import { copy, fill } from '../../lib/copy';
import { useApi } from '../../hooks/useApi';
import { useDialogBehavior } from '../../hooks/useDialogBehavior';
import { useExplainScope } from '../../context/ExplainContext';
import { Skeleton } from './Skeleton';
import { ErrorState } from './ErrorState';

export interface ExplainPopoverProps {
  termId: string;
  /** What is being explained, used in the button's accessible name. */
  label: string;
}

/** A "?" button that opens a small dialog: meaning, the figure for this stock or fund, what is typical. */
export function ExplainPopover({ termId, label }: ExplainPopoverProps) {
  const [open, setOpen] = useState(false);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const panelId = useId();

  return (
    <>
      <button
        ref={buttonRef}
        type="button"
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-controls={open ? panelId : undefined}
        aria-label={fill(copy.explain.buttonLabel, { label })}
        title={copy.explain.button}
        onClick={() => setOpen((o) => !o)}
        className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-slate-300 bg-white text-sm font-semibold text-indigo-700 hover:bg-indigo-50"
      >
        <span aria-hidden="true">?</span>
      </button>
      {open ? (
        <ExplainPanel
          id={panelId}
          termId={termId}
          anchor={buttonRef}
          onClose={() => setOpen(false)}
        />
      ) : null}
    </>
  );
}

function ExplainPanel({
  id,
  termId,
  anchor,
  onClose,
}: {
  id: string;
  termId: string;
  anchor: RefObject<HTMLButtonElement | null>;
  onClose: () => void;
}) {
  const scope = useExplainScope();
  const ref = useRef<HTMLDivElement>(null);
  const titleId = useId();
  const [style, setStyle] = useState<CSSProperties>({ visibility: 'hidden' });
  const { data, loading, error, reload } = useApi(
    (signal) => getExplain(termId, scope.kind, scope.id, { signal }),
    [termId, scope.kind, scope.id],
  );

  useDialogBehavior(ref, true, onClose);

  // Position under the button on wide screens; bottom sheet on phones.
  useLayoutEffect(() => {
    function place() {
      const btn = anchor.current;
      if (!btn) return;
      if (window.innerWidth < 640) {
        setStyle({ left: 8, right: 8, bottom: 8 });
        return;
      }
      const r = btn.getBoundingClientRect();
      const width = 360;
      const left = Math.max(8, Math.min(r.right - width, window.innerWidth - width - 8));
      const spaceBelow = window.innerHeight - r.bottom;
      if (spaceBelow < 260 && r.top > spaceBelow) {
        setStyle({ left, width, bottom: window.innerHeight - r.top + 8 });
      } else {
        setStyle({ left, width, top: r.bottom + 8 });
      }
    }
    place();
    window.addEventListener('resize', place);
    window.addEventListener('scroll', place, true);
    return () => {
      window.removeEventListener('resize', place);
      window.removeEventListener('scroll', place, true);
    };
  }, [anchor]);

  // Close when clicking elsewhere.
  useEffect(() => {
    function onPointerDown(e: MouseEvent) {
      const t = e.target as Node;
      if (ref.current?.contains(t) || anchor.current?.contains(t)) return;
      onClose();
    }
    document.addEventListener('mousedown', onPointerDown);
    return () => document.removeEventListener('mousedown', onPointerDown);
  }, [anchor, onClose]);

  return createPortal(
    <div
      ref={ref}
      id={id}
      role="dialog"
      aria-modal="false"
      aria-labelledby={titleId}
      tabIndex={-1}
      style={style}
      className="fixed z-50 max-h-[70vh] overflow-y-auto rounded-2xl border border-slate-200 bg-white p-4 text-left shadow-xl sm:max-h-[60vh]"
    >
      <div className="flex items-start justify-between gap-3">
        <h2 id={titleId} className="text-base font-semibold text-slate-900">
          {data ? data.term.term : copy.explain.title}
        </h2>
        <button
          type="button"
          onClick={onClose}
          aria-label={copy.common.close}
          className="-mr-1 -mt-1 inline-flex h-9 w-9 items-center justify-center rounded-full text-slate-700 hover:bg-slate-100"
        >
          <span aria-hidden="true">✕</span>
        </button>
      </div>

      <div aria-live="polite">
        {loading ? (
          <div className="mt-3 space-y-2" role="status">
            <span className="sr-only">{copy.common.loading}</span>
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-5/6" />
            <Skeleton className="h-10 w-full" />
          </div>
        ) : null}
        {error ? (
          <div className="mt-3">
            <ErrorState error={error} onRetry={reload} compact />
          </div>
        ) : null}
        {data ? (
          <div className="mt-2 space-y-3 text-sm text-slate-800">
            <section>
              <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-600">{copy.explain.meaning}</h3>
              <p className="mt-1 text-base">{data.term.meaning}</p>
            </section>
            {data.thisFigure ? (
              <section>
                <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-600">
                  {data.instrument ? fill(copy.explain.forThis, { name: data.instrument.name }) : copy.explain.thisFigure}
                </h3>
                <p className="mt-1 text-lg font-semibold tabular-nums text-slate-900">{data.thisFigure.display}</p>
                <p className="text-xs text-slate-600">
                  {data.thisFigure.source} · {copy.common.asOf} {formatDate(data.thisFigure.asOf)}
                </p>
              </section>
            ) : null}
            {data.typical ? (
              <section>
                <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-600">{copy.explain.typical}</h3>
                <p className="mt-1">
                  {data.typical.label}: <span className="font-semibold tabular-nums">{data.typical.display}</span>
                </p>
              </section>
            ) : null}
            {data.sentence ? <p className="text-slate-700">{data.sentence.text}</p> : null}
            {!data.thisFigure ? <p className="text-xs text-slate-600">{copy.explain.noFigure}</p> : null}
          </div>
        ) : null}
      </div>
    </div>,
    document.body,
  );
}

/** Inline term with an Explain button next to it, for use in running headings and labels. */
export function TermLabel({ text, termId }: { text: string; termId: string | null }) {
  return (
    <span className="inline-flex items-center gap-2">
      <span>{text}</span>
      {termId ? <ExplainPopover termId={termId} label={text} /> : null}
    </span>
  );
}
