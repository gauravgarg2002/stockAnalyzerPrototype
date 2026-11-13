import { Link } from 'react-router-dom';
import type { ExposureLine } from '../../lib/api-types';
import { copy } from '../../lib/copy';
import { stockPath } from '../../lib/routes';

export interface ExposureBarsProps {
  lines: ExposureLine[];
  /** Show the direct / through-funds split in words under each bar. */
  split?: boolean;
  label: string;
}

/** Horizontal bars, scaled to the largest line. Direct in slate-700, through funds in slate-400, both written out. */
export function ExposureBars({ lines, split = true, label }: ExposureBarsProps) {
  const max = Math.max(0.0001, ...lines.map((l) => l.totalPct));
  return (
    <div>
      <ul className="space-y-4" aria-label={label}>
        {lines.map((l) => (
          <li key={`${l.kind}-${l.key}`}>
            <div className="flex items-baseline justify-between gap-3">
              <span className="min-w-0 break-words font-medium text-slate-900">
                {l.checkAvailable && l.symbol ? (
                  <Link to={stockPath(l.symbol)} className="text-indigo-700 underline decoration-indigo-300 underline-offset-2 hover:decoration-indigo-700">
                    {l.name}
                  </Link>
                ) : (
                  l.name
                )}
              </span>
              <span className="shrink-0 text-right tabular-nums text-slate-900">{l.display}</span>
            </div>
            <div className="mt-1.5 flex h-2.5 overflow-hidden rounded-full bg-slate-100" aria-hidden="true">
              <div className="h-full bg-slate-700" style={{ width: `${(l.directPct / max) * 100}%` }} />
              <div className="h-full bg-slate-400" style={{ width: `${(l.throughFundsPct / max) * 100}%` }} />
            </div>
            {split ? (
              <p className="mt-1 text-sm text-slate-600">
                {copy.exposure.direct}: <span className="tabular-nums text-slate-700">{l.directDisplay}</span>
                <span aria-hidden="true"> · </span>
                <span className="sr-only">, </span>
                {copy.exposure.throughFunds}: <span className="tabular-nums text-slate-700">{l.throughFundsDisplay}</span>
              </p>
            ) : null}
          </li>
        ))}
      </ul>
      {split ? (
        <p className="mt-4 flex flex-wrap gap-x-5 gap-y-1 text-xs text-slate-600" aria-hidden="true">
          <span className="inline-flex items-center gap-1.5">
            <span className="h-2.5 w-5 rounded-full bg-slate-700" />
            {copy.exposure.direct}
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="h-2.5 w-5 rounded-full bg-slate-400" />
            {copy.exposure.throughFunds}
          </span>
        </p>
      ) : null}
    </div>
  );
}
