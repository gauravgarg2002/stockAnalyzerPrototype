import { useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { getFundCheck } from '../lib/api-client';
import { copy, fill } from '../lib/copy';
import { parseMoneyInput, groupTypedAmount } from '../lib/format';
import { comparePath, fundPath } from '../lib/routes';
import { useApi } from '../hooks/useApi';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { ExplainScope } from '../context/ExplainContext';
import { PageHeader } from '../components/ui/PageHeader';
import { PageSkeleton } from '../components/ui/Skeleton';
import { ErrorState } from '../components/ui/ErrorState';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Drawer } from '../components/ui/Drawer';
import { FigureChip } from '../components/ui/FigureChip';
import { MoneyInput } from '../components/ui/MoneyInput';
import { TryItOnPanel } from '../components/TryItOnPanel';
import { AnswersSection, CheckActions, FactsSection, HoldingLine, PageJump, PriceSection } from '../components/CheckSections';

export default function FundCheckPage() {
  const { code = '' } = useParams();
  const [params, setParams] = useSearchParams();
  const amountParam = params.get('amount');
  const amount = amountParam ? parseMoneyInput(amountParam) : null;
  const { data, loading, error, reload } = useApi((signal) => getFundCheck(code, amount, { signal }), [code, amount]);
  const [tryOpen, setTryOpen] = useState(false);
  const [draft, setDraft] = useState(amount ? groupTypedAmount(String(amount)) : '');
  const [draftError, setDraftError] = useState<string | null>(null);
  useDocumentTitle(data ? data.instrument.shortName : copy.check.fundTitleFallback);

  function applyAmount() {
    if (draft.trim() === '') {
      setDraftError(null);
      setParams({}, { replace: true });
      return;
    }
    const n = parseMoneyInput(draft);
    if (n === null) {
      setDraftError(copy.fund.amountInvalid);
      return;
    }
    setDraftError(null);
    setParams({ amount: String(n) }, { replace: true });
  }

  if (loading) return <PageSkeleton cards={4} />;
  if (error || !data) return <ErrorState error={error} onRetry={reload} />;

  const { instrument: ins } = data;
  const basisText =
    data.amount.basis === 'HOLDING'
      ? copy.fund.basisHolding
      : data.amount.basis === 'USER_INPUT'
        ? copy.fund.basisUser
        : copy.fund.basisIllustrative;

  return (
    <ExplainScope kind="FUND" id={ins.schemeCode}>
      <PageHeader
        eyebrow={copy.check.fundEyebrow}
        title={ins.name}
        subtitle={`${ins.category} · ${ins.planType === 'DIRECT' ? copy.fund.directPlan : copy.fund.regularPlan} · ${ins.amc}`}
        sampleData={data.sampleData}
        asOf={data.asOf}
      />

      <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:max-w-2xl">
        <FigureChip figure={ins.nav} />
        <div className="rounded-xl bg-slate-50 p-3 ring-1 ring-inset ring-slate-200">
          <p className="text-sm text-slate-700">{copy.fund.benchmarkLabel}</p>
          <p className="mt-1 text-xl font-semibold text-slate-900">{ins.benchmark.name}</p>
        </div>
      </div>

      <Card className="mb-6">
        <h2 className="text-base font-semibold text-slate-900">{copy.fund.amountTitle}</h2>
        <p className="mt-1 text-slate-800">
          {fill(basisText, { amount: data.amount.display })}
        </p>
        <form
          className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-end"
          onSubmit={(e) => {
            e.preventDefault();
            applyAmount();
          }}
        >
          <MoneyInput
            label={copy.fund.amountLabel}
            value={draft}
            onChange={setDraft}
            error={draftError}
            className="sm:w-64"
          />
          <Button type="submit" variant="secondary">
            {copy.fund.amountApply}
          </Button>
        </form>
      </Card>

      {ins.twin ? (
        <p className="mb-6 text-slate-800">
          {fill(copy.fund.twinLine, { plan: ins.twin.planType === 'DIRECT' ? copy.fund.directPlan : copy.fund.regularPlan })}{' '}
          <Link className="font-medium text-indigo-700 underline underline-offset-2" to={fundPath(ins.twin.schemeCode)}>
            {ins.twin.name}
          </Link>
        </p>
      ) : null}

      <HoldingLine kind="FUND" user={data.user} />
      <CheckActions kind="FUND" instrumentId={ins.schemeCode} name={ins.name} user={data.user} onTry={() => setTryOpen(true)} />

      <PageJump
        items={[
          { id: 'answers', label: copy.check.jumpAnswers },
          { id: 'facts', label: copy.check.jumpFacts },
          { id: 'price', label: copy.check.jumpPriceFund },
        ]}
      />

      <div className="space-y-10">
        <AnswersSection answers={data.answers} />
        <FactsSection facts={data.facts} />
        <PriceSection history={data.priceHistory} drawdown={data.drawdown} name={ins.shortName} label={copy.check.priceTitleFund} />
        <p className="text-sm">
          <Link className="font-medium text-indigo-700 underline underline-offset-2" to={comparePath('FUND', [ins.schemeCode], data.amount.amountInr)}>
            {copy.fund.compareLink}
          </Link>
        </p>
      </div>

      <Drawer open={tryOpen} onClose={() => setTryOpen(false)} title={copy.tryIt.drawerTitle}>
        <TryItOnPanel kind="FUND" id={ins.schemeCode} />
      </Drawer>
    </ExplainScope>
  );
}
