import { useEffect, useState } from 'react';
import { getQuote } from '../lib/api-client';
import type { QuoteResponse } from '../lib/api-types';
import { copy, fill } from '../lib/copy';
import { SampleDataBadge } from './ui/SampleDataBadge';

const REFRESH_MS = 60_000;

function timeOf(iso: string | null | undefined): string {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' });
}

/**
 * Live price strip for the stock check header: the price now, its move since the previous close, and where it sits
 * inside today's low–high range. Refreshes every minute while the tab is visible. Says plainly when no live price exists.
 */
export function LiveQuote({ symbol }: { symbol: string }) {
  const [q, setQ] = useState<QuoteResponse | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    getQuote(symbol, { signal: controller.signal })
      .then(setQ)
      .catch(() => setQ((prev) => prev ?? { sampleData: false, available: false, symbol }));
    return () => controller.abort();
  }, [symbol, tick]);

  useEffect(() => {
    const t = window.setInterval(() => {
      if (document.visibilityState === 'visible') setTick((n) => n + 1);
    }, REFRESH_MS);
    return () => window.clearInterval(t);
  }, []);

  if (!q) {
    return <div aria-hidden="true" className="h-[118px] max-w-2xl rounded-3xl bg-white/[0.06] ring-1 ring-inset ring-white/10" />;
  }

  if (!q.available) {
    return (
      <p className="flex max-w-2xl flex-wrap items-center gap-2 rounded-2xl bg-white/[0.06] px-4 py-3 text-sm text-lagoon-200 ring-1 ring-inset ring-white/10">
        <span aria-hidden="true" className="h-2 w-2 rounded-full bg-white/30" />
        {q.reason ?? copy.common.notAvailable} {copy.live.unavailableHint}
      </p>
    );
  }

  const pos = typeof q.rangePosition === 'number' ? Math.min(1, Math.max(0, q.rangePosition)) : null;

  return (
    <section aria-label={copy.live.title} className="max-w-3xl rounded-3xl bg-white/[0.07] p-5 ring-1 ring-inset ring-white/15 backdrop-blur-sm sm:p-6">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <span className="inline-flex items-center gap-2 text-sm font-semibold text-lagoon-200">
          <span aria-hidden="true" className="relative flex h-2.5 w-2.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-marigold-400 opacity-75" />
            <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-marigold-400" />
          </span>
          {copy.live.title}
        </span>
        <SampleDataBadge show={q.sampleData} tone="dark" />
        <span className="text-xs text-lagoon-200/80">
          {q.source}
          {q.asOf ? `, ${fill(copy.live.updated, { time: timeOf(q.asOf) })}` : ''}
        </span>
      </div>

      <div className="mt-3 grid gap-6 sm:grid-cols-[auto_1fr] sm:items-end">
        <div>
          <p key={q.lastPriceDisplay} className="animate-pop font-display text-4xl font-extrabold tabular-nums text-white sm:text-5xl">
            {q.lastPriceDisplay}
          </p>
          <p className="mt-1 text-sm text-lagoon-200">
            <span className="font-semibold tabular-nums text-marigold-300">{q.changeDisplay}</span> {copy.live.changeVsPrev}
          </p>
        </div>

        {pos !== null ? (
          <div>
            <p className="mb-2 text-sm font-semibold text-lagoon-200">{copy.live.todayRange}</p>
            <div className="relative h-2.5 rounded-full bg-white/15" aria-hidden="true">
              <div className="absolute inset-y-0 left-0 rounded-full bg-lagoon-300/60 transition-[width] duration-700" style={{ width: `${pos * 100}%` }} />
              <span
                className="absolute top-1/2 h-5 w-5 -translate-x-1/2 -translate-y-1/2 rounded-full border-[3px] border-peacock-900 bg-marigold-400 shadow-lens transition-[left] duration-700"
                style={{ left: `${pos * 100}%` }}
              />
            </div>
            <div className="mt-2 flex justify-between text-xs text-lagoon-200">
              <span>
                {copy.live.low} <span className="font-semibold tabular-nums text-white">{q.lowDisplay}</span>
              </span>
              <span>
                {copy.live.high} <span className="font-semibold tabular-nums text-white">{q.highDisplay}</span>
              </span>
            </div>
          </div>
        ) : null}
      </div>

      <dl className="mt-5 grid grid-cols-3 gap-3 border-t border-white/10 pt-4 text-sm">
        {[
          [copy.live.open, q.openDisplay],
          [copy.live.prevClose, q.prevCloseDisplay],
          [copy.live.volume, q.volumeDisplay],
        ].map(([k, v]) => (
          <div key={k}>
            <dt className="text-lagoon-200/90">{k}</dt>
            <dd className="font-semibold tabular-nums text-white">{v ?? copy.common.notAvailable}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
