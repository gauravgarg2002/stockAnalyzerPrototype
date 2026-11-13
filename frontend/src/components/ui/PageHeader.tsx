import type { ReactNode } from 'react';
import { copy } from '../../lib/copy';
import { formatDate } from '../../lib/dates';
import { SampleDataBadge } from './SampleDataBadge';

export interface PageHeaderProps {
  title: string;
  subtitle?: ReactNode;
  eyebrow?: ReactNode;
  sampleData?: boolean;
  asOf?: string;
  actions?: ReactNode;
}

export function PageHeader({ title, subtitle, eyebrow, sampleData, asOf, actions }: PageHeaderProps) {
  return (
    <header className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div className="min-w-0">
        {eyebrow ? <p className="mb-1 text-sm font-medium text-slate-600">{eyebrow}</p> : null}
        <h1 className="break-words text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">{title}</h1>
        {subtitle ? <p className="mt-1 text-base text-slate-700">{subtitle}</p> : null}
        {sampleData || asOf ? (
          <p className="mt-2 flex flex-wrap items-center gap-2 text-xs text-slate-600">
            <SampleDataBadge show={sampleData} />
            {asOf ? (
              <span>
                {copy.common.dataAsOf} {formatDate(asOf)}
              </span>
            ) : null}
          </p>
        ) : null}
      </div>
      {actions ? <div className="flex flex-wrap gap-3">{actions}</div> : null}
    </header>
  );
}

export function SectionHeading({ id, title, hint }: { id: string; title: string; hint?: string }) {
  return (
    <div className="mb-3 mt-10 first:mt-0">
      <h2 id={id} className="text-xl font-semibold text-slate-900">
        {title}
      </h2>
      {hint ? <p className="mt-0.5 text-sm text-slate-600">{hint}</p> : null}
    </div>
  );
}
