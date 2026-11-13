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
  /** Extra content inside the band, under the title (for example key figures). */
  children?: ReactNode;
}

/**
 * The page title sits on a full-width peacock-ink band that continues the header's lattice,
 * so every screen opens on the same solid surface before the paper content below.
 */
export function PageHeader({ title, subtitle, eyebrow, sampleData, asOf, actions, children }: PageHeaderProps) {
  return (
    <header className="relative isolate mb-8 pb-8 pt-7 text-white before:absolute before:inset-y-0 before:left-1/2 before:-z-10 before:w-screen before:-translate-x-1/2 before:jali sm:pb-10 sm:pt-9">
      <div className="flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
        <div className="min-w-0 animate-rise">
          {eyebrow ? (
            <p className="mb-2 inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-sm font-semibold text-lagoon-200">
              <span aria-hidden="true" className="h-1.5 w-1.5 rounded-full bg-marigold-400" />
              {eyebrow}
            </p>
          ) : null}
          <h1 className="break-words font-display text-3xl font-extrabold leading-[1.05] tracking-tight sm:text-5xl">{title}</h1>
          {subtitle ? <p className="mt-2 max-w-2xl text-lg text-lagoon-200">{subtitle}</p> : null}
          {sampleData || asOf ? (
            <p className="mt-3 flex flex-wrap items-center gap-3 text-sm text-lagoon-200/90">
              <SampleDataBadge show={sampleData} tone="dark" />
              {asOf ? (
                <span>
                  {copy.common.dataAsOf} {formatDate(asOf)}
                </span>
              ) : null}
            </p>
          ) : null}
        </div>
        {actions ? <div className="flex flex-wrap gap-3 animate-rise [animation-delay:120ms]">{actions}</div> : null}
      </div>
      {children ? <div className="mt-6 animate-rise [animation-delay:160ms]">{children}</div> : null}
    </header>
  );
}

export function SectionHeading({ id, title, hint }: { id: string; title: string; hint?: string }) {
  return (
    <div className="mb-4 mt-12 first:mt-0">
      <h2 id={id} className="flex items-center gap-3 font-display text-2xl font-bold text-peacock-900">
        <span aria-hidden="true" className="h-6 w-1.5 rounded-full bg-marigold-400" />
        {title}
      </h2>
      {hint ? <p className="mt-1 pl-[1.125rem] text-[0.95rem] text-slate-600">{hint}</p> : null}
    </div>
  );
}
