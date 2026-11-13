import type { ReactNode } from 'react';
import type { Figure } from '../../lib/api-types';
import { copy } from '../../lib/copy';
import { formatDate } from '../../lib/dates';

export interface BeforeAfterSide {
  headline: string;
  caption?: string;
}

/** One metric, two columns: Before and After. Equal visual weight, no direction colouring. */
export function BeforeAfterRow({ title, before, after, children }: { title: string; before: BeforeAfterSide; after: BeforeAfterSide; children?: ReactNode }) {
  return (
    <div className="rounded-xl border border-slate-200 p-4">
      <h3 className="text-sm font-semibold text-slate-800">{title}</h3>
      <dl className="mt-2 grid grid-cols-2 gap-4">
        <div>
          <dt className="text-xs font-medium uppercase tracking-wide text-slate-600">{copy.tryIt.before}</dt>
          <dd className="mt-1 text-lg font-semibold tabular-nums text-slate-900">{before.headline}</dd>
          {before.caption ? <dd className="text-sm text-slate-600">{before.caption}</dd> : null}
        </div>
        <div>
          <dt className="text-xs font-medium uppercase tracking-wide text-slate-600">{copy.tryIt.after}</dt>
          <dd className="mt-1 text-lg font-semibold tabular-nums text-slate-900">{after.headline}</dd>
          {after.caption ? <dd className="text-sm text-slate-600">{after.caption}</dd> : null}
        </div>
      </dl>
      {children}
    </div>
  );
}

export function figureSource(f: Figure): string {
  return `${f.source} · ${copy.common.asOf} ${formatDate(f.asOf)}`;
}
