import { Link } from 'react-router-dom';
import { getActivity } from '../lib/api-client';
import type { ActivityTrigger } from '../lib/api-types';
import { copy, fill } from '../lib/copy';
import { formatDate } from '../lib/dates';
import { formatPctChange } from '../lib/format';
import { ROUTES, stockPath } from '../lib/routes';
import { useApi } from '../hooks/useApi';
import { Card } from './ui/Card';
import { DataTable } from './ui/DataTable';
import { SampleDataBadge } from './ui/SampleDataBadge';
import { SentenceList } from './ui/SentenceList';
import { Skeleton } from './ui/Skeleton';
import { LinkButton } from './ui/Button';

/** A trigger drawn on a small scale around the price when it was set, so the distance is seen, not just read. */
function TriggerCard({ t }: { t: ActivityTrigger }) {
  const ref = t.lastPriceAtSetup;
  const all = [...t.triggerPrices, ...(ref ? [ref] : [])];
  const lo = Math.min(...all) * 0.97;
  const hi = Math.max(...all) * 1.03;
  const x = (v: number) => ((v - lo) / (hi - lo || 1)) * 100;
  return (
    <li className="rounded-2xl bg-paper p-4 ring-1 ring-inset ring-slate-200 transition-colors hover:bg-lagoon-100/60">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <Link to={stockPath(t.symbol)} className="link-draw">
          {t.symbol}
        </Link>
        <span className="text-xs font-semibold text-slate-600">
          {t.kind === 'TWO_LEG' ? copy.activity.triggerTwoLeg : copy.activity.triggerSingle}
        </span>
      </div>
      {ref ? (
        <div className="relative mt-5 h-1.5 rounded-full bg-slate-200" aria-hidden="true">
          <span className="absolute top-1/2 h-4 w-1 -translate-y-1/2 rounded bg-peacock-900" style={{ left: `${x(ref)}%` }} />
          {t.triggerPrices.map((p) => (
            <span key={p} className="absolute top-1/2 h-3.5 w-3.5 -translate-x-1/2 -translate-y-1/2 rotate-45 rounded-[3px] bg-marigold-400 ring-2 ring-white" style={{ left: `${x(p)}%` }} />
          ))}
        </div>
      ) : null}
      <ul className="mt-4 space-y-1 text-sm">
        {t.triggerPrices.map((p, i) => (
          <li key={p} className="flex flex-wrap justify-between gap-2">
            <span className="text-slate-700">
              {copy.activity.triggerAt} <span className="font-semibold tabular-nums text-peacock-900">{t.triggerDisplays[i]}</span>
            </span>
            {ref ? (
              <span className="tabular-nums text-slate-600">
                {fill(copy.activity.triggerFromNow, { pct: formatPctChange((p / ref - 1) * 100) })}
              </span>
            ) : null}
          </li>
        ))}
      </ul>
      <p className="mt-2 text-xs text-slate-600">
        {t.quantity ? fill(copy.activity.triggerShares, { n: String(t.quantity) }) : null}
        {t.createdAt ? `${t.quantity ? ', ' : ''}${formatDate(t.createdAt.slice(0, 10))}` : null}
      </p>
    </li>
  );
}

/** "Today in your Zerodha account": open positions, today's orders and trades, and active price triggers. */
export function AccountActivity() {
  const { data, loading } = useApi((signal) => getActivity({ signal }), []);
  if (loading) {
    return (
      <Card>
        <Skeleton className="h-5 w-1/3" />
        <Skeleton className="mt-4 h-20 w-full" />
      </Card>
    );
  }
  if (!data) return null;

  if (!data.connected) {
    return (
      <Card tone="tint">
        <SentenceList sentences={data.sentences} />
        <LinkButton to={ROUTES.connect} variant="secondary" className="mt-4">
          {copy.activity.connectFirst}
        </LinkButton>
      </Card>
    );
  }

  return (
    <Card>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <SampleDataBadge show={data.sampleData} />
        <p className="text-xs text-slate-600">
          {data.source}, {copy.common.asOf} {formatDate(data.asOf)}
        </p>
      </div>
      <SentenceList sentences={data.sentences} className="mt-3" />

      {data.orders ? (
        <dl className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[
            [copy.activity.ordersComplete, data.orders.complete],
            [copy.activity.ordersOpen, data.orders.open],
            [copy.activity.ordersCancelled, data.orders.cancelled],
            [copy.activity.tradesToday, data.tradesToday],
          ].map(([k, v]) => (
            <div key={String(k)} className="rounded-2xl bg-paper p-3 ring-1 ring-inset ring-slate-200">
              <dt className="text-sm text-slate-600">{k}</dt>
              <dd className="font-display text-2xl font-bold tabular-nums text-peacock-900">{v ?? copy.common.notAvailable}</dd>
            </div>
          ))}
        </dl>
      ) : null}

      <h3 className="mt-7 font-display text-lg font-bold text-peacock-900">{copy.activity.positionsTitle}</h3>
      {data.positions.length > 0 ? (
        <div className="mt-3">
          <DataTable
            table={{
              title: copy.activity.positionsTitle,
              columns: [copy.activity.colSymbol, copy.activity.colProduct, copy.activity.colQty, copy.activity.colAvg, copy.activity.colLast, copy.activity.colPnl],
              rows: data.positions.map((p) => [p.symbol, p.product, String(p.quantity), p.avgPriceDisplay, p.lastPriceDisplay, p.pnlDisplay]),
            }}
          />
        </div>
      ) : (
        <p className="mt-2 text-slate-600">{copy.activity.positionsNone}</p>
      )}

      <h3 className="mt-7 font-display text-lg font-bold text-peacock-900">{copy.activity.triggersTitle}</h3>
      {data.gtts.length > 0 ? (
        <ul className="mt-3 grid gap-3 sm:grid-cols-2">
          {data.gtts.map((t, i) => (
            <TriggerCard key={`${t.symbol}-${i}`} t={t} />
          ))}
        </ul>
      ) : (
        <p className="mt-2 text-slate-600">{copy.activity.triggersNone}</p>
      )}
      <p className="mt-6 text-sm text-slate-600">{copy.activity.hint}</p>
    </Card>
  );
}
