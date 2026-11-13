import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { getStockCheck } from '../lib/api-client';
import { copy, fill } from '../lib/copy';
import { comparePath, stockPath } from '../lib/routes';
import { useApi } from '../hooks/useApi';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { ExplainScope } from '../context/ExplainContext';
import { PageHeader, SectionHeading } from '../components/ui/PageHeader';
import { PageSkeleton } from '../components/ui/Skeleton';
import { ErrorState } from '../components/ui/ErrorState';
import { Card } from '../components/ui/Card';
import { Drawer } from '../components/ui/Drawer';
import { FigureChip } from '../components/ui/FigureChip';
import { Badge } from '../components/ui/Badge';
import { TryItOnPanel } from '../components/TryItOnPanel';
import { AnswersSection, CheckActions, FactsSection, HoldingLine, PageJump, PriceSection } from '../components/CheckSections';

export default function StockCheckPage() {
  const { symbol = '' } = useParams();
  const { data, loading, error, reload } = useApi((signal) => getStockCheck(symbol, { signal }), [symbol]);
  const [tryOpen, setTryOpen] = useState(false);
  useDocumentTitle(data ? data.instrument.name : copy.check.stockTitleFallback);

  if (loading) return <PageSkeleton cards={4} />;
  if (error || !data) return <ErrorState error={error} onRetry={reload} />;

  const { instrument: ins, peers } = data;
  const comparable = peers.members.filter((m) => m.checkAvailable && m.symbol !== ins.symbol);

  return (
    <ExplainScope kind="STOCK" id={ins.symbol}>
      <PageHeader
        eyebrow={copy.check.stockEyebrow}
        title={ins.name}
        subtitle={`${ins.sector} · ${ins.industry}`}
        sampleData={data.sampleData}
        asOf={data.asOf}
      />

      <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:max-w-2xl">
        <FigureChip figure={ins.lastPrice} />
        <FigureChip figure={ins.marketCap} />
      </div>
      {ins.fictional ? <p className="mb-6 text-sm text-slate-700"><Badge>{copy.check.fictional}</Badge></p> : null}

      <HoldingLine kind="STOCK" user={data.user} />
      <CheckActions kind="STOCK" instrumentId={ins.symbol} name={ins.name} user={data.user} onTry={() => setTryOpen(true)} />

      <PageJump
        items={[
          { id: 'answers', label: copy.check.jumpAnswers },
          { id: 'facts', label: copy.check.jumpFacts },
          { id: 'price', label: copy.check.jumpPrice },
          { id: 'peers', label: copy.check.jumpPeers },
        ]}
      />

      <div className="space-y-10">
        <AnswersSection answers={data.answers} />
        <FactsSection facts={data.facts} />
        <PriceSection history={data.priceHistory} drawdown={data.drawdown} name={ins.name} label={copy.check.priceTitleStock} />

        <section aria-labelledby="peers" className="scroll-mt-24">
          <SectionHeading id="peers" title={copy.check.peersTitle} hint={fill(copy.check.peersHint, { group: peers.groupName })} />
          <Card>
            <ul className="divide-y divide-slate-100">
              {peers.members.map((m) => (
                <li key={m.symbol} className="flex flex-wrap items-center justify-between gap-2 py-3">
                  <span className="font-medium text-slate-900">{m.name}</span>
                  <span className="flex gap-3 text-sm">
                    {m.checkAvailable ? (
                      <>
                        <Link className="font-medium text-indigo-700 underline underline-offset-2" to={stockPath(m.symbol)}>
                          {copy.check.openCheck}
                        </Link>
                        <Link
                          className="font-medium text-indigo-700 underline underline-offset-2"
                          to={comparePath('STOCK', [ins.symbol, m.symbol])}
                        >
                          {copy.check.compareWith}
                        </Link>
                      </>
                    ) : (
                      <span className="text-slate-600">{copy.check.checkNotAvailable}</span>
                    )}
                  </span>
                </li>
              ))}
            </ul>
            {comparable.length >= 2 ? (
              <p className="mt-3 text-sm">
                <Link
                  className="font-medium text-indigo-700 underline underline-offset-2"
                  to={comparePath('STOCK', [ins.symbol, ...comparable.slice(0, 2).map((m) => m.symbol)])}
                >
                  {copy.check.compareAll}
                </Link>
              </p>
            ) : null}
          </Card>
        </section>
      </div>

      <Drawer open={tryOpen} onClose={() => setTryOpen(false)} title={copy.tryIt.drawerTitle}>
        <TryItOnPanel kind="STOCK" id={ins.symbol} />
      </Drawer>
    </ExplainScope>
  );
}
