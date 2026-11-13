import { useState } from 'react';
import { Link } from 'react-router-dom';
import { getPortfolio } from '../lib/api-client';
import type { DetailTable, ExposureBreakdown, ExposureLine, PortfolioFact, PortfolioResponse, ReturnRow } from '../lib/api-types';
import { copy, fill } from '../lib/copy';
import { formatDate } from '../lib/dates';
import { formatInr, formatPct } from '../lib/format';
import { ROUTES } from '../lib/routes';
import { useApi } from '../hooks/useApi';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { PageHeader, SectionHeading } from '../components/ui/PageHeader';
import { PageSkeleton } from '../components/ui/Skeleton';
import { ErrorState } from '../components/ui/ErrorState';
import { EmptyState } from '../components/ui/EmptyState';
import { Card } from '../components/ui/Card';
import { LinkButton } from '../components/ui/Button';
import { SentenceList } from '../components/ui/SentenceList';
import { FigureChip, FigureGrid } from '../components/ui/FigureChip';
import { SegmentedControl } from '../components/ui/SegmentedControl';
import { ShowDetails } from '../components/ui/ShowDetails';
import { DataTable } from '../components/ui/DataTable';
import { ExposureBars } from '../components/charts/ExposureBars';
import { MixBar } from '../components/charts/MixBar';
import { PageJump } from '../components/CheckSections';
import { ExplainScope } from '../context/ExplainContext';
import { AccountActivity } from '../components/AccountActivity';

type Dimension = 'company' | 'sector' | 'size';

function exposureTable(title: string, firstCol: string, lines: ExposureLine[]): DetailTable {
  return {
    title,
    columns: [firstCol, copy.exposure.direct, copy.exposure.throughFunds, copy.exposure.total, copy.exposure.viaFunds],
    rows: lines.map((l) => [
      l.name,
      l.directDisplay,
      l.throughFundsDisplay,
      l.display,
      l.viaFunds.length > 0 ? l.viaFunds.map((v) => `${v.name} (${formatInr(v.inr)})`).join('; ') : '–',
    ]),
  };
}

function ExposureSection({ data }: { data: PortfolioResponse }) {
  const [dim, setDim] = useState<Dimension>('company');
  const breakdown: ExposureBreakdown = data.exposure[dim];
  const firstCol = dim === 'company' ? copy.exposure.colCompany : dim === 'sector' ? copy.exposure.colSector : copy.exposure.colSize;
  // Companies: the biggest ten as bars, the rest behind the table.
  const barLines = dim === 'company' ? breakdown.lines.slice(0, 10) : breakdown.lines;
  return (
    <Card>
      <SegmentedControl<Dimension>
        label={copy.exposure.switchLabel}
        value={dim}
        onChange={setDim}
        options={[
          { value: 'company', label: copy.exposure.companies },
          { value: 'sector', label: copy.exposure.sectors },
          { value: 'size', label: copy.exposure.sizes },
        ]}
      />
      <SentenceList sentences={breakdown.sentences} className="mt-4" />
      <div className="mt-5">
        <ExposureBars lines={barLines} label={firstCol} />
      </div>
      <ShowDetails>
        <DataTable table={exposureTable(copy.exposure.tableTitle, firstCol, breakdown.lines)} />
      </ShowDetails>
    </Card>
  );
}

function returnCell(row: ReturnRow) {
  const nifty = row.oneYear.comparisons.find((c) => c.kind === 'INDEX');
  return [row.name, row.oneYear.display, nifty ? nifty.display : copy.common.notAvailable, row.sinceBuy ? row.sinceBuy.display : copy.common.notAvailable, row.gain.display];
}

function findFact(facts: PortfolioFact[], id: PortfolioFact['id']): PortfolioFact | undefined {
  return facts.find((f) => f.id === id);
}

export default function PortfolioPage() {
  useDocumentTitle(copy.portfolio.title);
  const { data, loading, error, reload } = useApi((signal) => getPortfolio({ signal }), []);

  if (loading) return <PageSkeleton cards={5} />;
  if (error || !data) return <ErrorState error={error} onRetry={reload} />;

  if (!data.hasHoldings) {
    return (
      <div>
        <PageHeader title={copy.portfolio.title} subtitle={copy.portfolio.subtitle} sampleData={data.sampleData} />
        <EmptyState
          title={copy.portfolio.emptyTitle}
          action={<LinkButton to={ROUTES.connect}>{copy.portfolio.emptyAction}</LinkButton>}
        >
          <p>{data.summary[0]?.text ?? copy.portfolio.emptyBody}</p>
        </EmptyState>
      </div>
    );
  }

  const { totals, concentration, overlap, costs, mix, returns } = data;
  const overlapFact = findFact(data.facts, 'overlap');
  const costFact = findFact(data.facts, 'cost');
  const cashFact = findFact(data.facts, 'idle_cash');

  const returnsTable: DetailTable = {
    title: copy.portfolio.returnsTableTitle,
    columns: [copy.portfolio.colHolding, copy.portfolio.colOneYear, fill(copy.portfolio.colNiftySame, { benchmark: returns.benchmarkName }), copy.portfolio.colSinceBuy, copy.portfolio.colGain],
    rows: returns.holdings.map(returnCell),
  };

  return (
    <ExplainScope kind={null} id={null}>
      <PageHeader title={copy.portfolio.title} subtitle={copy.portfolio.subtitle} sampleData={data.sampleData} asOf={data.asOf} />

      <PageJump
        items={[
          { id: 'worth', label: copy.portfolio.jumpWorth },
          { id: 'own', label: copy.portfolio.jumpOwn },
          { id: 'overlap', label: copy.portfolio.jumpOverlap },
          { id: 'cost', label: copy.portfolio.jumpCost },
          { id: 'mix', label: copy.portfolio.jumpMix },
          { id: 'returns', label: copy.portfolio.jumpReturns },
          { id: 'cash', label: copy.portfolio.jumpCash },
          { id: 'today', label: copy.portfolio.jumpToday },
          { id: 'holdings', label: copy.portfolio.jumpHoldings },
        ]}
      />

      <div className="space-y-10">
        <section aria-labelledby="worth" className="scroll-mt-24">
          <SectionHeading id="worth" title={copy.portfolio.worthTitle} />
          <Card>
            <SentenceList sentences={data.summary} size="lg" className="space-y-3" />
            <FigureGrid figures={[totals.holdingsValue, totals.invested]} />
          </Card>
        </section>

        <section aria-labelledby="own" className="scroll-mt-24">
          <SectionHeading id="own" title={copy.portfolio.ownTitle} hint={copy.portfolio.ownHint} />
          <ExposureSection data={data} />
          <Card className="mt-4">
            <h3 className="text-lg font-semibold text-slate-900">{copy.portfolio.concentrationTitle}</h3>
            <SentenceList sentences={concentration.sentences} className="mt-2" />
            <FigureGrid
              figures={[concentration.largestCompany, concentration.top5Companies, concentration.topSector, concentration.companyCount, concentration.holdingCount]}
            />
          </Card>
        </section>

        <section aria-labelledby="overlap" className="scroll-mt-24">
          <SectionHeading id="overlap" title={copy.portfolio.overlapTitle} hint={copy.portfolio.overlapHint} />
          <Card>
            {overlapFact ? <p className="text-slate-800">{overlapFact.sentence.text}</p> : <SentenceList sentences={overlap.sentences} />}
            {overlap.pairs.length > 0 ? (
              <ul className="mt-4 divide-y divide-slate-100">
                {overlap.pairs.map((p) => (
                  <li key={`${p.fundA.schemeCode}-${p.fundB.schemeCode}`} className="py-4">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <p className="min-w-0 flex-1 break-words text-slate-900">
                        <span className="font-medium">{p.fundA.name}</span>
                        <span className="text-slate-600"> {copy.portfolio.andWord} </span>
                        <span className="font-medium">{p.fundB.name}</span>
                      </p>
                      <div className="text-right">
                        <p className="text-xl font-semibold tabular-nums text-slate-900">{p.overlap.display}</p>
                        <p className="text-sm text-slate-600">{fill(copy.portfolio.commonCount, { n: String(p.commonCount) })}</p>
                      </div>
                    </div>
                    <p className="mt-1 text-xs text-slate-600">
                      {p.overlap.source}, {copy.common.asOf} {formatDate(p.overlap.asOf)}
                    </p>
                    {p.topCommon.length > 0 ? (
                      <ShowDetails>
                        <DataTable
                          table={{
                            title: copy.portfolio.commonTableTitle,
                            columns: [copy.portfolio.colCompany, copy.portfolio.colWeightA, copy.portfolio.colWeightB, copy.portfolio.colCounted],
                            rows: p.topCommon.map((c) => [c.name, formatPct(c.weightA), formatPct(c.weightB), formatPct(c.minWeight)]),
                          }}
                        />
                      </ShowDetails>
                    ) : null}
                  </li>
                ))}
              </ul>
            ) : null}
          </Card>
        </section>

        <section aria-labelledby="cost" className="scroll-mt-24">
          <SectionHeading id="cost" title={copy.portfolio.costTitle} hint={copy.portfolio.costHint} />
          <Card>
            {costFact ? <p className="text-slate-800">{costFact.sentence.text}</p> : <SentenceList sentences={costs.sentences} />}
            <FigureGrid figures={[costs.totalYearly, costs.regularGapYearly]} />
            {costs.funds.length > 0 ? (
              <ShowDetails>
                <DataTable
                  table={{
                    title: copy.portfolio.costTableTitle,
                    columns: [copy.portfolio.colFund, copy.portfolio.colPlan, copy.portfolio.colValue, copy.portfolio.colTer, copy.portfolio.colYearly, copy.portfolio.colGap],
                    rows: costs.funds.map((f) => [
                      f.name,
                      f.planType === 'DIRECT' ? copy.fund.directPlan : copy.fund.regularPlan,
                      f.value.display,
                      f.expenseRatio.display,
                      f.yearlyCost.display,
                      f.yearlyGap ? f.yearlyGap.display : '–',
                    ]),
                  }}
                />
              </ShowDetails>
            ) : null}
          </Card>
        </section>

        <section aria-labelledby="mix" className="scroll-mt-24">
          <SectionHeading id="mix" title={copy.portfolio.mixTitle} />
          <Card>
            <SentenceList sentences={mix.sentences} />
            <div className="mt-5 grid gap-8 md:grid-cols-2">
              <div>
                <h3 className="mb-3 text-sm font-semibold text-slate-800">{copy.portfolio.mixEquityDebt}</h3>
                <MixBar lines={mix.equityDebt} label={copy.portfolio.mixEquityDebt} />
              </div>
              <div>
                <h3 className="mb-3 text-sm font-semibold text-slate-800">{copy.portfolio.mixStocksFunds}</h3>
                <MixBar lines={mix.stocksFunds} label={copy.portfolio.mixStocksFunds} />
              </div>
            </div>
          </Card>
        </section>

        <section aria-labelledby="returns" className="scroll-mt-24">
          <SectionHeading id="returns" title={fill(copy.portfolio.returnsTitle, { benchmark: returns.benchmarkName })} hint={copy.portfolio.returnsHint} />
          <Card>
            <SentenceList sentences={returns.sentences} />
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <FigureChip figure={returns.portfolio.oneYear} />
              {returns.portfolio.sinceBuy ? <FigureChip figure={returns.portfolio.sinceBuy} /> : null}
              <FigureChip figure={returns.portfolio.gain} />
            </div>
            <ShowDetails>
              <DataTable table={returnsTable} />
            </ShowDetails>
          </Card>
        </section>

        <section aria-labelledby="cash" className="scroll-mt-24">
          <SectionHeading id="cash" title={copy.portfolio.cashTitle} />
          <Card>
            {cashFact ? <p className="text-slate-800">{cashFact.sentence.text}</p> : null}
            <FigureGrid figures={[totals.idleCash, totals.totalWithCash]} />
          </Card>
        </section>

        <section aria-labelledby="today" className="scroll-mt-24">
          <SectionHeading id="today" title={copy.activity.title} hint={copy.activity.hint} />
          <AccountActivity />
        </section>

        <section aria-labelledby="holdings" className="scroll-mt-24">
          <SectionHeading id="holdings" title={copy.portfolio.holdingsTitle} hint={copy.portfolio.holdingsHint} />
          <Card padded={false}>
            <ul className="divide-y divide-slate-100">
              {data.holdings.map((h) => (
                <li key={`${h.kind}-${h.id}`} className="flex flex-wrap items-start justify-between gap-3 px-4 py-4 sm:px-6">
                  <div className="min-w-0">
                    <Link to={h.checkPath} className="font-medium text-indigo-700 underline decoration-indigo-300 underline-offset-2 hover:decoration-indigo-700">
                      {h.name}
                    </Link>
                    <p className="text-sm text-slate-600">{h.subtitle}</p>
                    <p className="mt-1 text-xs text-slate-600">
                      {h.lastPrice.label}: {h.lastPrice.display}
                      {h.firstBuyDate ? ` · ${copy.portfolio.since} ${formatDate(h.firstBuyDate)}` : ''}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-semibold tabular-nums text-slate-900">{h.value.display}</p>
                    <p className="text-sm tabular-nums text-slate-600">{fill(copy.portfolio.weight, { pct: formatPct(h.weightPct) })}</p>
                  </div>
                </li>
              ))}
            </ul>
          </Card>
        </section>
      </div>
    </ExplainScope>
  );
}
