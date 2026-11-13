import { Link } from 'react-router-dom';
import { getHome } from '../lib/api-client';
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
import { PageSkeleton } from '../components/ui/Skeleton';
import { SectionHeading } from '../components/ui/PageHeader';
import { SentenceList } from '../components/ui/SentenceList';
import { SampleDataBadge } from '../components/ui/SampleDataBadge';
import { FigureGrid } from '../components/ui/FigureChip';
import { ExposureBars } from '../components/charts/ExposureBars';
import { WatchlistRows } from '../components/WatchlistRows';

export default function HomePage() {
  useDocumentTitle(null);
  const { data, loading, error, reload } = useApi((signal) => getHome({ signal }), []);

  return (
    <div>
      <section aria-labelledby="home-title" className="mx-auto max-w-2xl pb-8 pt-2 text-center sm:pt-6">
        <h1 id="home-title" className="text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">
          {copy.home.title}
        </h1>
        <p className="mx-auto mt-2 max-w-xl text-lg text-slate-700">{copy.home.subtitle}</p>
        <div className="mt-6 text-left">
          <GlobalSearch size="lg" />
        </div>
        <p className="mt-2 text-sm text-slate-600">{copy.home.searchHint}</p>
      </section>

      {loading ? <PageSkeleton cards={3} title={false} /> : null}
      {error ? <ErrorState error={error} onRetry={reload} /> : null}
      {data ? (
        <div className="space-y-10">
          <section aria-labelledby="home-portfolio">
            <div className="mb-3 flex flex-wrap items-center gap-3">
              <h2 id="home-portfolio" className="text-xl font-semibold text-slate-900">
                {copy.home.portfolioTitle}
              </h2>
              <SampleDataBadge show={data.sampleData} />
            </div>
            {data.hasHoldings ? (
              <Card>
                <SentenceList sentences={data.summary} size="lg" className="space-y-3" />
                <div className="mt-5 flex flex-wrap items-center gap-x-5 gap-y-2">
                  <LinkButton to={ROUTES.portfolio} variant="secondary">
                    {copy.home.seePortfolio}
                  </LinkButton>
                  {data.lastImport ? (
                    <p className="text-sm text-slate-600">
                      {copy.home.lastImport} {formatDate(data.lastImport.finishedAt)} · {data.lastImport.message}
                    </p>
                  ) : null}
                </div>
              </Card>
            ) : (
              <EmptyState
                title={copy.home.emptyTitle}
                action={<LinkButton to={ROUTES.connect}>{copy.home.emptyAction}</LinkButton>}
              >
                <p>{data.summary[0]?.text ?? copy.home.emptyBody}</p>
              </EmptyState>
            )}
          </section>

          {data.hasHoldings ? (
            <>
              <section aria-labelledby="home-exposure">
                <SectionHeading id="home-exposure" title={copy.home.exposureTitle} hint={copy.home.exposureHint} />
                <Card>
                  <ExposureBars lines={data.topExposures} label={copy.home.exposureTitle} />
                  <p className="mt-4 text-sm">
                    <Link className="font-medium text-indigo-700 underline underline-offset-2" to={ROUTES.portfolio}>
                      {copy.home.exposureMore}
                    </Link>
                  </p>
                </Card>
              </section>

              <section aria-labelledby="home-facts">
                <SectionHeading id="home-facts" title={copy.home.factsTitle} />
                <div className="grid gap-4 md:grid-cols-3">
                  {data.facts.map((f) => (
                    <Card key={f.id} className="h-full">
                      <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-600">
                        {f.id === 'overlap' ? copy.home.factOverlap : f.id === 'cost' ? copy.home.factCost : copy.home.factCash}
                      </h3>
                      <p className="mt-2 text-slate-800">{f.sentence.text}</p>
                      <FigureGrid figures={f.figures} bare className="sm:grid-cols-1" />
                    </Card>
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
                <p className="mt-3 text-sm">
                  <Link className="font-medium text-indigo-700 underline underline-offset-2" to={ROUTES.watchlist}>
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
  );
}
