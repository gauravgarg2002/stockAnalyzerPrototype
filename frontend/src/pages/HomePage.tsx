import { useCallback } from 'react';
import type { PointerEvent } from 'react';
import { Link } from 'react-router-dom';
import { getHome } from '../lib/api-client';
import type { HomeResponse } from '../lib/api-types';
import { copy } from '../lib/copy';
import { formatDate } from '../lib/dates';
import { ROUTES } from '../lib/routes';
import { useApi } from '../hooks/useApi';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { Card } from '../components/ui/Card';
import { LinkButton } from '../components/ui/Button';
import { EmptyState } from '../components/ui/EmptyState';
import { ErrorState } from '../components/ui/ErrorState';
import { GlobalSearch } from '../components/ui/GlobalSearch';
import { Skeleton, SkeletonCard } from '../components/ui/Skeleton';
import { SectionHeading } from '../components/ui/PageHeader';
import { SampleDataBadge } from '../components/ui/SampleDataBadge';
import { FigureGrid } from '../components/ui/FigureChip';
import { RichSentenceList } from '../components/ui/RichSentence';
import { Reveal } from '../components/ui/Motion';
import { ExposureBars } from '../components/charts/ExposureBars';
import { WatchlistRows } from '../components/WatchlistRows';

/** The lens: a marigold light that follows the pointer across the lattice. */
function useLens() {
  return useCallback((e: PointerEvent<HTMLElement>) => {
    const r = e.currentTarget.getBoundingClientRect();
    e.currentTarget.style.setProperty('--lx', `${e.clientX - r.left}px`);
    e.currentTarget.style.setProperty('--ly', `${e.clientY - r.top}px`);
  }, []);
}

function HeroPortfolio({ data }: { data: HomeResponse }) {
  if (!data.hasHoldings) {
    return (
      <div className="rounded-3xl bg-white/[0.07] p-6 ring-1 ring-inset ring-white/15 backdrop-blur-sm sm:p-8">
        <h2 className="font-display text-2xl font-bold text-white">{copy.home.emptyTitle}</h2>
        <p className="mt-2 text-lg text-lagoon-200">{data.summary[0]?.text ?? copy.home.emptyBody}</p>
        <LinkButton to={ROUTES.connect} variant="accent" className="mt-6">
          {copy.home.emptyAction}
        </LinkButton>
      </div>
    );
  }
  return (
    <div className="rounded-3xl bg-white/[0.07] p-6 ring-1 ring-inset ring-white/15 backdrop-blur-sm sm:p-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="font-display text-xl font-bold text-white">{copy.home.portfolioTitle}</h2>
        <SampleDataBadge show={data.sampleData} tone="dark" />
      </div>
      <RichSentenceList sentences={data.summary} tone="dark" className="mt-4 !text-[1.1rem]" />
      {data.topExposures.length > 0 ? (
        <div className="mt-6 border-t border-white/10 pt-5">
          <ExposureBars lines={data.topExposures.slice(0, 3)} split={false} label={copy.home.exposureTitle} tone="dark" />
        </div>
      ) : null}
      <div className="mt-6 flex flex-wrap items-center gap-x-5 gap-y-2">
        <LinkButton to={ROUTES.portfolio} variant="accent">
          {copy.home.seePortfolio}
        </LinkButton>
        {data.lastImport ? (
          <p className="text-sm text-lagoon-200/90">
            {copy.home.lastImport} {formatDate(data.lastImport.finishedAt)}
          </p>
        ) : null}
      </div>
    </div>
  );
}

function HeroSkeleton() {
  return (
    <div className="space-y-4 rounded-3xl bg-white/[0.07] p-8 ring-1 ring-inset ring-white/15" aria-hidden="true">
      <Skeleton className="h-6 w-1/2 opacity-20" />
      <Skeleton className="h-4 w-full opacity-20" />
      <Skeleton className="h-4 w-5/6 opacity-20" />
      <Skeleton className="h-4 w-4/6 opacity-20" />
    </div>
  );
}

const FACT_TITLE: Record<string, string> = {
  overlap: copy.home.factOverlap,
  cost: copy.home.factCost,
  idle_cash: copy.home.factCash,
};

export default function HomePage() {
  useDocumentTitle(null);
  const { data, loading, error, reload } = useApi((signal) => getHome({ signal }), []);
  const onLens = useLens();

  return (
    <div>
      <section
        aria-labelledby="home-title"
        onPointerMove={onLens}
        className="jali relative isolate overflow-hidden text-white"
      >
        <div aria-hidden="true" className="jali-lens pointer-events-none absolute inset-0 -z-10" />
        {/* The lens ring, drifting behind the content. */}
        <svg
          aria-hidden="true"
          viewBox="0 0 400 400"
          className="pointer-events-none absolute -right-24 -top-24 -z-10 h-[30rem] w-[30rem] animate-drift text-marigold-400/25"
          fill="none"
          stroke="currentColor"
        >
          <circle cx="200" cy="200" r="150" strokeWidth="26" />
          <circle cx="200" cy="200" r="190" strokeWidth="2" strokeDasharray="2 10" />
        </svg>

        <div className="mx-auto grid max-w-page items-center gap-10 px-4 pb-14 pt-10 sm:px-6 sm:pb-20 sm:pt-16 lg:grid-cols-[1.05fr_1fr] lg:gap-14">
          <div>
            <h1
              id="home-title"
              className="animate-rise font-display text-[2.6rem] font-extrabold leading-[0.98] tracking-tight sm:text-6xl lg:text-[4.4rem]"
            >
              {copy.home.title}
            </h1>
            <p className="mt-5 max-w-xl animate-rise text-xl text-lagoon-200 [animation-delay:80ms]">{copy.home.subtitle}</p>
            <div className="relative z-20 mt-8 animate-rise [animation-delay:160ms]">
              <GlobalSearch size="lg" tone="dark" shortcut examples />
            </div>
            <p className="mt-3 animate-rise text-sm text-lagoon-200/80 [animation-delay:220ms]">{copy.home.searchHint}</p>
          </div>

          <div className="animate-rise [animation-delay:260ms]">
            {loading ? <HeroSkeleton /> : null}
            {data ? <HeroPortfolio data={data} /> : null}
          </div>
        </div>
      </section>

      <div className="mx-auto max-w-page px-4 py-12 sm:px-6">
        {loading ? (
          <div className="grid gap-5 md:grid-cols-3">
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </div>
        ) : null}
        {error ? <ErrorState error={error} onRetry={reload} /> : null}
        {data ? (
          <div className="space-y-4">
            {data.hasHoldings ? (
              <>
                <section aria-labelledby="home-exposure">
                  <SectionHeading id="home-exposure" title={copy.home.exposureTitle} hint={copy.home.exposureHint} />
                  <Card>
                    <ExposureBars lines={data.topExposures} label={copy.home.exposureTitle} />
                    <p className="mt-6">
                      <Link className="link-draw" to={ROUTES.portfolio}>
                        {copy.home.exposureMore}
                      </Link>
                    </p>
                  </Card>
                </section>

                <section aria-labelledby="home-facts">
                  <SectionHeading id="home-facts" title={copy.home.factsTitle} />
                  <div className="grid gap-5 md:grid-cols-3">
                    {data.facts.map((f, i) => (
                      <Reveal key={f.id} delay={i * 110} className="h-full">
                        <Card className="h-full" spotlight>
                          <h3 className="flex items-center gap-2 font-display text-lg font-bold text-peacock-900">
                            <span aria-hidden="true" className="h-2.5 w-2.5 rounded-full bg-marigold-400" />
                            {FACT_TITLE[f.id] ?? f.id}
                          </h3>
                          <p className="mt-2 text-[1.02rem] leading-relaxed text-slate-800">{f.sentence.text}</p>
                          <FigureGrid figures={f.figures} bare single />
                        </Card>
                      </Reveal>
                    ))}
                  </div>
                </section>
              </>
            ) : null}

            <section aria-labelledby="home-watchlist">
              <SectionHeading id="home-watchlist" title={copy.home.watchlistTitle} />
              {data.watchlist.length > 0 ? (
                <Card>
                  <WatchlistRows items={data.watchlist} />
                  <p className="mt-4">
                    <Link className="link-draw" to={ROUTES.watchlist}>
                      {copy.home.watchlistAll}
                    </Link>
                  </p>
                </Card>
              ) : (
                <EmptyState title={copy.home.watchlistEmptyTitle}>
                  <p>{copy.home.watchlistEmptyBody}</p>
                </EmptyState>
              )}
            </section>
          </div>
        ) : null}
      </div>
    </div>
  );
}

