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
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sheet">
      <h3 className="font-semibold text-peacock-900">{title}</h3>
      <dl className="mt-2 grid grid-cols-2 gap-4">
        <div>
          <dt className="text-sm font-medium text-slate-600">{copy.tryIt.before}</dt>
          <dd className="mt-1 font-display text-xl font-bold tabular-nums text-slate-600">{before.headline}</dd>
          {before.caption ? <dd className="text-sm text-slate-600">{before.caption}</dd> : null}
        </div>
        <div>
          <dt className="text-sm font-medium text-slate-600">{copy.tryIt.after}</dt>
          <dd className="mt-1 font-display text-xl font-bold tabular-nums text-peacock-900"><span key={after.headline} className="inline-block animate-pop">{after.headline}</span></dd>
          {after.caption ? <dd className="text-sm text-slate-600">{after.caption}</dd> : null}
        </div>
      </dl>
      {children}
    </div>
  );
}

export function figureSource(f: Figure): string {
  return `${f.source}, ${copy.common.asOf} ${formatDate(f.asOf)}`;
}
