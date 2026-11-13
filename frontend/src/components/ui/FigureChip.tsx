import type { Figure } from '../../lib/api-types';
import { formatDate } from '../../lib/dates';
import { copy } from '../../lib/copy';
import { ExplainPopover } from './ExplainPopover';

export interface FigureChipProps {
  figure: Figure;
  /** Hide the comparison lines (for tight spaces). */
  bare?: boolean;
  className?: string;
}

/** One figure: label, value, comparisons, then source and as-of date in small muted text. */
export function FigureChip({ figure, bare = false, className = '' }: FigureChipProps) {
  const unavailable = figure.value === null;
  return (
    <div className={`rounded-xl bg-slate-50 p-3 ring-1 ring-inset ring-slate-200 ${className}`}>
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm text-slate-700">{figure.label}</p>
        {figure.termId ? <ExplainPopover termId={figure.termId} label={figure.label} /> : null}
      </div>
      <p className={`mt-1 break-words text-xl font-semibold tabular-nums ${unavailable ? 'text-slate-600' : 'text-slate-900'}`}>
        {figure.display}
      </p>
      {!bare && figure.comparisons.length > 0 ? (
        <ul className="mt-2 space-y-0.5 text-sm text-slate-700">
          {figure.comparisons.map((c, i) => (
            <li key={`${c.kind}-${i}`}>
              <span className="text-slate-600">{c.label}: </span>
              <span className="font-medium tabular-nums">{c.display}</span>
            </li>
          ))}
        </ul>
      ) : null}
      <p className="mt-2 text-xs text-slate-600">
        {figure.source} · {copy.common.asOf} {formatDate(figure.asOf)}
      </p>
    </div>
  );
}

function isRupee(f: Figure): boolean {
  return f.unit === 'INR' || f.unit === 'INR_PRICE';
}

/** Rupee amounts first, ratios after; otherwise keeps the backend order. */
export function sortRupeesFirst(figures: Figure[]): Figure[] {
  return figures
    .map((f, i) => ({ f, i }))
    .sort((a, b) => Number(!isRupee(a.f)) - Number(!isRupee(b.f)) || a.i - b.i)
    .map((x) => x.f);
}

export function FigureGrid({ figures, bare = false, single = false, className = '' }: { figures: Figure[]; bare?: boolean; single?: boolean; className?: string }) {
  if (figures.length === 0) return null;
  return (
    <div className={`mt-4 grid gap-3 ${single ? '' : 'sm:grid-cols-2'} ${className}`}>
      {sortRupeesFirst(figures).map((f) => (
        <FigureChip key={f.id} figure={f} bare={bare} />
      ))}
    </div>
  );
}
