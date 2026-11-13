import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { getCompare } from '../lib/api-client';
import type { CompareCell, CompareResponse, Kind } from '../lib/api-types';
import { copy, fill } from '../lib/copy';
import { groupTypedAmount, parseMoneyInput } from '../lib/format';
import { parseIds, parseKind } from '../lib/routes';
import { useApi } from '../hooks/useApi';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { PageHeader } from '../components/ui/PageHeader';
import { PageSkeleton } from '../components/ui/Skeleton';
import { ErrorState } from '../components/ui/ErrorState';
import { EmptyState } from '../components/ui/EmptyState';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { SegmentedControl } from '../components/ui/SegmentedControl';
import { SearchCombobox } from '../components/ui/GlobalSearch';
import { SentenceList } from '../components/ui/SentenceList';
import { FigureGrid } from '../components/ui/FigureChip';
import { MoneyInput } from '../components/ui/MoneyInput';
import { SampleDataBadge } from '../components/ui/SampleDataBadge';

const COLS: Record<number, string> = { 1: 'md:grid-cols-1', 2: 'md:grid-cols-2', 3: 'md:grid-cols-3' };

function CompareResult({ kind, ids, amount, onNames }: { kind: Kind; ids: string[]; amount: number | null; onNames: (names: Record<string, string>) => void }) {
  const { data, loading, error, reload } = useApi((signal) => getCompare(kind, ids, amount, { signal }), [kind, ids.join(','), amount]);
  useEffect(() => {
    if (data) onNames(Object.fromEntries(data.instruments.map((i) => [i.id, i.name])));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data]);
  if (loading) return <PageSkeleton cards={3} title={false} />;
  if (error || !data) return <ErrorState error={error} onRetry={reload} />;
  return <CompareTable data={data} />;
}

function CompareTable({ data }: { data: CompareResponse }) {
  const n = data.instruments.length;
  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-center gap-3">
        <SampleDataBadge show={data.sampleData} />
      </div>
      <section aria-label={copy.compare.whoTitle}>
        <ul className={`grid gap-3 ${COLS[n] ?? 'md:grid-cols-3'}`}>
          {data.instruments.map((ins) => (
            <li key={ins.id} className="rounded-2xl border border-slate-200 bg-white p-4">
              <h2 className="break-words text-lg font-semibold">
                <Link to={ins.checkPath} className="text-indigo-700 underline decoration-indigo-300 underline-offset-2 hover:decoration-indigo-700">
                  {ins.name}
                </Link>
              </h2>
              <p className="text-sm text-slate-600">{ins.subtitle}</p>
            </li>
          ))}
        </ul>
      </section>

      {[...data.rows]
        .sort((a, b) => a.order - b.order)
        .map((row) => (
          <section key={row.id} aria-labelledby={`cmp-${row.id}`}>
            <h2 id={`cmp-${row.id}`} className="mb-3 flex items-start gap-3 text-xl font-semibold text-slate-900">
              <span
                aria-hidden="true"
                className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-indigo-700 text-sm font-semibold text-white"
              >
                {row.order}
              </span>
              {row.question}
            </h2>
            <div className={`grid gap-4 ${COLS[n] ?? 'md:grid-cols-3'}`}>
              {data.instruments.map((ins) => {
                const cell: CompareCell | undefined = row.cells.find((c) => c.instrumentId === ins.id);
                return (
                  <Card key={ins.id} className="h-full">
                    <p className="mb-2 text-sm font-semibold text-slate-700">{ins.name}</p>
                    {cell ? (
                      <>
                        <SentenceList sentences={cell.sentences} />
                        <FigureGrid figures={cell.figures} className="sm:grid-cols-1" />
                      </>
                    ) : (
                      <p className="text-slate-600">{copy.common.notAvailable}</p>
                    )}
                  </Card>
                );
              })}
            </div>
          </section>
        ))}
    </div>
  );
}

export default function ComparePage() {
  useDocumentTitle(copy.compare.title);
  const [params, setParams] = useSearchParams();
  const kind: Kind = parseKind(params.get('kind')) ?? 'STOCK';
  const ids = parseIds(params.get('ids'));
  const amountParam = params.get('amount');
  const amount = amountParam ? parseMoneyInput(amountParam) : null;
  const [names, setNames] = useState<Record<string, string>>({});
  const [draft, setDraft] = useState(amount ? groupTypedAmount(String(amount)) : '');

  function update(next: { kind?: Kind; ids?: string[]; amount?: number | null }) {
    const k = next.kind ?? kind;
    const list = next.ids ?? ids;
    const a = next.amount === undefined ? amount : next.amount;
    const p: Record<string, string> = { kind: k };
    if (list.length > 0) p.ids = list.join(',');
    if (k === 'FUND' && a) p.amount = String(a);
    setParams(p, { replace: false });
  }

  const full = ids.length >= 3;

  return (
    <div>
      <PageHeader title={copy.compare.title} subtitle={copy.compare.subtitle} />

      <Card className="mb-8">
        <SegmentedControl<Kind>
          label={copy.compare.kindLabel}
          value={kind}
          onChange={(k) => {
            if (k !== kind) update({ kind: k, ids: [] });
          }}
          options={[
            { value: 'STOCK', label: copy.compare.stocks },
            { value: 'FUND', label: copy.compare.funds },
          ]}
        />

        <h2 className="mb-2 mt-5 text-base font-semibold text-slate-900">{copy.compare.chosenTitle}</h2>
        {ids.length > 0 ? (
          <ul className="flex flex-wrap gap-2">
            {ids.map((id) => (
              <li key={id} className="inline-flex items-center gap-1 rounded-full bg-slate-100 py-1 pl-3 pr-1 text-sm text-slate-900">
                <span className="max-w-[16rem] truncate">{names[id] ?? id}</span>
                <button
                  type="button"
                  aria-label={fill(copy.compare.removeOne, { name: names[id] ?? id })}
                  onClick={() => update({ ids: ids.filter((x) => x !== id) })}
                  className="inline-flex h-8 w-8 items-center justify-center rounded-full text-slate-700 hover:bg-slate-200"
                >
                  <span aria-hidden="true">✕</span>
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-slate-600">{copy.compare.noneChosen}</p>
        )}

        <div className="mt-4 max-w-md">
          {full ? (
            <p className="text-sm text-slate-600">{copy.compare.fullHint}</p>
          ) : (
            <SearchCombobox
              key={`${kind}-${ids.length}`}
              label={copy.compare.addLabel}
              hideLabel={false}
              kind={kind}
              placeholder={kind === 'STOCK' ? copy.compare.addPlaceholderStock : copy.compare.addPlaceholderFund}
              onSelect={(r) => {
                if (ids.includes(r.id)) return;
                setNames((cur) => ({ ...cur, [r.id]: r.name }));
                update({ ids: [...ids, r.id] });
              }}
            />
          )}
        </div>

        {kind === 'FUND' ? (
          <form
            className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-end"
            onSubmit={(e) => {
              e.preventDefault();
              update({ amount: parseMoneyInput(draft) });
            }}
          >
            <MoneyInput label={copy.compare.amountLabel} value={draft} onChange={setDraft} hint={copy.compare.amountHint} className="sm:w-64" />
            <Button type="submit" variant="secondary">
              {copy.fund.amountApply}
            </Button>
          </form>
        ) : null}
      </Card>

      {ids.length >= 2 ? (
        <CompareResult kind={kind} ids={ids} amount={amount} onNames={(m) => setNames((cur) => ({ ...cur, ...m }))} />
      ) : (
        <EmptyState title={copy.compare.emptyTitle}>
          <p>{copy.compare.emptyBody}</p>
        </EmptyState>
      )}
    </div>
  );
}
