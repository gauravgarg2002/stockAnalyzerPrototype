import { useEffect, useState } from 'react';
import { postTryItOn } from '../lib/api-client';
import type { InstrumentRef, Kind, TryItOnResponse, TryMode } from '../lib/api-types';
import { copy, fill } from '../lib/copy';
import { parseMoneyInput } from '../lib/format';
import { Button } from './ui/Button';
import { Input } from './ui/Input';
import { MoneyInput } from './ui/MoneyInput';
import { SegmentedControl } from './ui/SegmentedControl';
import { SentenceList } from './ui/SentenceList';
import { SearchCombobox } from './ui/GlobalSearch';
import { ErrorState } from './ui/ErrorState';
import { SampleDataBadge } from './ui/SampleDataBadge';
import { MixBar } from './charts/MixBar';
import { BeforeAfterRow, figureSource } from './charts/BeforeAfter';
import { Skeleton } from './ui/Skeleton';

const MAX_AMOUNT = 1_000_000_000;

export interface TryItOnPanelProps {
  kind?: Kind | null;
  id?: string | null;
  /** Display name of the instrument, when the caller knows it. */
  name?: string;
  /** Called when the person picks a different instrument in the built-in search (page mode). */
  onPick?: (kind: Kind, id: string) => void;
}

/** Form + before/after result. Used on the Try it on page and inside the drawer on check pages. */
export function TryItOnPanel({ kind, id, name, onPick }: TryItOnPanelProps) {
  const [mode, setMode] = useState<TryMode>('SIP');
  const [amount, setAmount] = useState('');
  const [months, setMonths] = useState('12');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [result, setResult] = useState<TryItOnResponse | null>(null);
  const [picked, setPicked] = useState<InstrumentRef | null>(null);

  const targetKind = kind ?? null;
  const targetId = id ?? null;

  // A different instrument means a different question: clear the old answer.
  useEffect(() => {
    setResult(null);
    setError(null);
    setFieldError(null);
  }, [targetKind, targetId]);

  async function run() {
    if (!targetKind || !targetId) return;
    const amountInr = parseMoneyInput(amount);
    if (amountInr === null || amountInr > MAX_AMOUNT) {
      setFieldError(copy.tryIt.amountInvalid);
      return;
    }
    let monthsNum: number | null = null;
    if (mode === 'SIP') {
      monthsNum = Number(months);
      if (!Number.isInteger(monthsNum) || monthsNum < 1 || monthsNum > 60) {
        setFieldError(copy.tryIt.monthsInvalid);
        return;
      }
    }
    setFieldError(null);
    setBusy(true);
    setError(null);
    try {
      const res = await postTryItOn({ kind: targetKind, id: targetId, mode, amountInr, months: monthsNum });
      setResult(res);
    } catch (e) {
      setResult(null);
      setError(e instanceof Error ? e : new Error('failed'));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      {!targetKind || !targetId ? (
        <div className="mb-5">
          <SearchCombobox
            label={copy.tryIt.pickLabel}
            hideLabel={false}
            placeholder={copy.search.placeholder}
            clearOnSelect={false}
            onSelect={(r) => {
              setPicked(r);
              onPick?.(r.kind, r.id);
            }}
          />
          {picked ? null : <p className="mt-2 text-sm text-slate-600">{copy.tryIt.pickHint}</p>}
        </div>
      ) : (
        <p className="mb-4 text-sm text-slate-700">
          {fill(copy.tryIt.intro, { name: name ?? (picked && picked.id === targetId ? picked.name : targetId) })}
        </p>
      )}

      <form
        className="space-y-4"
        onSubmit={(e) => {
          e.preventDefault();
          void run();
        }}
      >
        <SegmentedControl<TryMode>
          label={copy.tryIt.modeLabel}
          value={mode}
          onChange={setMode}
          options={[
            { value: 'SIP', label: copy.tryIt.modeSip },
            { value: 'LUMP_SUM', label: copy.tryIt.modeLump },
          ]}
        />
        <MoneyInput
          label={mode === 'SIP' ? copy.tryIt.amountSip : copy.tryIt.amountLump}
          value={amount}
          onChange={setAmount}
          error={fieldError === copy.tryIt.amountInvalid ? fieldError : null}
        />
        {mode === 'SIP' ? (
          <Input
            label={copy.tryIt.monthsLabel}
            type="number"
            inputMode="numeric"
            min={1}
            max={60}
            step={1}
            value={months}
            onChange={(e) => setMonths(e.target.value)}
            hint={copy.tryIt.monthsHint}
            error={fieldError === copy.tryIt.monthsInvalid ? fieldError : null}
            className="max-w-[10rem]"
          />
        ) : null}
        <Button type="submit" busy={busy} disabled={!targetKind || !targetId}>
          {copy.tryIt.submit}
        </Button>
      </form>

      <div className="mt-6" aria-live="polite">
        {busy ? (
          <div role="status" className="space-y-3">
            <span className="sr-only">{copy.common.loading}</span>
            <Skeleton className="h-5 w-3/4" />
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-20 w-full" />
          </div>
        ) : null}
        {error && !busy ? <ErrorState error={error} onRetry={() => void run()} compact /> : null}
        {result && !busy ? <TryItOnResult result={result} /> : null}
      </div>
    </div>
  );
}

export function TryItOnResult({ result }: { result: TryItOnResponse }) {
  const m = result.metrics;
  const s = result.sentences;
  const o = m.overlap;
  return (
    <div className="space-y-5">
      <div>
        <div className="flex items-center gap-2">
          <h3 className="text-lg font-semibold text-slate-900">{copy.tryIt.resultTitle}</h3>
          <SampleDataBadge show={result.sampleData} />
        </div>
        <SentenceList sentences={[result.assumption]} className="mt-2 text-slate-700" />
      </div>

      <section className="space-y-2">
        {s[0] ? <p className="text-slate-800">{s[0].text}</p> : null}
        <BeforeAfterRow
          title={copy.tryIt.largestCompany}
          before={{ headline: m.largestCompany.before.figure.display, caption: m.largestCompany.before.name }}
          after={{ headline: m.largestCompany.after.figure.display, caption: m.largestCompany.after.name }}
        />
      </section>

      <section className="space-y-2">
        {s[1] ? <p className="text-slate-800">{s[1].text}</p> : null}
        <BeforeAfterRow
          title={copy.tryIt.topSector}
          before={{ headline: m.topSector.before.figure.display, caption: m.topSector.before.name }}
          after={{ headline: m.topSector.after.figure.display, caption: m.topSector.after.name }}
        />
      </section>

      <section className="space-y-2">
        {s[2] ? <p className="text-slate-800">{s[2].text}</p> : null}
        <div className="rounded-xl border border-slate-200 p-4">
          <h3 className="text-sm font-semibold text-slate-800">{copy.tryIt.sizeMix}</h3>
          <div className="mt-3 grid gap-5 sm:grid-cols-2">
            <div>
              <p className="mb-2 text-sm font-semibold text-slate-600">{copy.tryIt.before}</p>
              <MixBar lines={m.sizeMix.before} label={`${copy.tryIt.sizeMix}, ${copy.tryIt.before}`} />
            </div>
            <div>
              <p className="mb-2 text-sm font-semibold text-slate-600">{copy.tryIt.after}</p>
              <MixBar lines={m.sizeMix.after} label={`${copy.tryIt.sizeMix}, ${copy.tryIt.after}`} />
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-2">
        {s[3] ? <p className="text-slate-800">{s[3].text}</p> : null}
        <BeforeAfterRow
          title={copy.tryIt.holdingsCount}
          before={{ headline: m.holdingsCount.before.display }}
          after={{ headline: m.holdingsCount.after.display }}
        />
      </section>

      <section className="space-y-2">
        {s[4] ? <p className="text-slate-800">{s[4].text}</p> : null}
        {o.candidateKind === 'FUND' ? (
          o.fundOverlaps.length > 0 ? (
            <div className="rounded-xl border border-slate-200 p-4">
              <h3 className="text-sm font-semibold text-slate-800">{copy.tryIt.overlapFunds}</h3>
              <ul className="mt-2 divide-y divide-slate-100">
                {o.fundOverlaps.map((f) => (
                  <li key={f.schemeCode} className="flex items-baseline justify-between gap-3 py-2 text-sm">
                    <span className="min-w-0 break-words text-slate-800">{f.name}</span>
                    <span className="shrink-0 font-semibold tabular-nums text-slate-900">{f.overlap.display}</span>
                  </li>
                ))}
              </ul>
            </div>
          ) : null
        ) : (
          <>
            {o.exposureToCandidate ? (
              <BeforeAfterRow
                title={copy.tryIt.exposure}
                before={{ headline: o.exposureToCandidate.before.display }}
                after={{ headline: o.exposureToCandidate.after.display }}
              />
            ) : null}
            {o.stockInFunds.length > 0 ? (
              <div className="rounded-xl border border-slate-200 p-4">
                <h3 className="text-sm font-semibold text-slate-800">{copy.tryIt.insideFunds}</h3>
                <ul className="mt-2 divide-y divide-slate-100">
                  {o.stockInFunds.map((f) => (
                    <li key={f.schemeCode} className="flex items-baseline justify-between gap-3 py-2 text-sm">
                      <span className="min-w-0 break-words text-slate-800">{f.name}</span>
                      <span className="shrink-0 font-semibold tabular-nums text-slate-900">{f.weight.display}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </>
        )}
      </section>

      <section className="space-y-2">
        {s[5] ? <p className="text-slate-800">{s[5].text}</p> : null}
        <BeforeAfterRow
          title={copy.tryIt.yearlyCost}
          before={{ headline: m.yearlyCost.before.display }}
          after={{ headline: m.yearlyCost.after.display, caption: `${copy.tryIt.change}: ${m.yearlyCost.change.display}` }}
        />
      </section>

      <p className="text-xs text-slate-600">{figureSource(m.holdingsCount.after)}</p>
    </div>
  );
}
