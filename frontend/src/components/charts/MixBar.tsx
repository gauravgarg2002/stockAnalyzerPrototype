import type { MixLine } from '../../lib/api-types';

const SHADES = ['bg-slate-800', 'bg-slate-500', 'bg-slate-300', 'bg-slate-200', 'bg-stone-300', 'bg-stone-200'];

/** One stacked bar for a mix. Every segment is also written out in the legend. */
export function MixBar({ lines, label }: { lines: MixLine[]; label: string }) {
  return (
    <div>
      <div className="flex h-4 overflow-hidden rounded-full bg-slate-100" role="img" aria-label={`${label}: ${lines.map((l) => `${l.label} ${l.display}`).join(', ')}`}>
        {lines.map((l, i) =>
          l.pct > 0 ? (
            <div
              key={l.key}
              className={`h-full border-r-2 border-white last:border-r-0 ${SHADES[i % SHADES.length]}`}
              style={{ width: `${l.pct}%` }}
            />
          ) : null,
        )}
      </div>
      <ul className="mt-3 grid gap-x-6 gap-y-1.5 text-sm sm:grid-cols-2" aria-label={label}>
        {lines.map((l, i) => (
          <li key={l.key} className="flex items-center justify-between gap-3">
            <span className="flex items-center gap-2 text-slate-700">
              <span aria-hidden="true" className={`h-3 w-3 shrink-0 rounded-sm ring-1 ring-inset ring-slate-400 ${SHADES[i % SHADES.length]}`} />
              {l.label}
            </span>
            <span className="tabular-nums text-slate-900">{l.display}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
