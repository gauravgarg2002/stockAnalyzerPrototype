import { useMemo, useState } from 'react';
import { Area, ComposedChart, CartesianGrid, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { PriceHistory } from '../../lib/api-types';
import { formatAxisNumber, formatPctChange, formatPrice } from '../../lib/format';
import { formatDate, formatMonthYear, yearOf } from '../../lib/dates';
import { copy, fill } from '../../lib/copy';
import { prefersReducedMotion } from '../../hooks/useMotion';
import { ShowDetails } from '../ui/ShowDetails';
import { DataTable } from '../ui/DataTable';
import { SegmentedControl } from '../ui/SegmentedControl';

interface Row {
  date: string;
  value: number;
  benchmark: number | null;
}

type Range = '1Y' | '3Y' | '5Y' | 'ALL';
const YEARS: Record<Range, number | null> = { '1Y': 1, '3Y': 3, '5Y': 5, ALL: null };

const PEACOCK = '#0B3B4F';
const LAGOON = '#3B97A2';
const MARIGOLD = '#F4A92B';

function TooltipBox({ active, payload, label, name, benchmark }: { active?: boolean; payload?: Array<{ dataKey?: string | number; value?: unknown }>; label?: unknown; name: string; benchmark: string }) {
  if (!active || !payload || payload.length === 0) return null;
  const v = payload.find((p) => p.dataKey === 'value');
  const b = payload.find((p) => p.dataKey === 'benchmark');
  return (
    <div className="rounded-2xl border border-slate-200 bg-white/95 px-4 py-3 text-sm shadow-lift backdrop-blur">
      <p className="font-semibold text-slate-600">{formatDate(String(label))}</p>
      {v ? (
        <p className="mt-1 flex items-center gap-2">
          <span aria-hidden="true" className="h-2.5 w-2.5 rounded-full" style={{ background: PEACOCK }} />
          <span className="text-slate-700">{name}</span>
          <span className="ml-auto pl-4 font-display font-bold tabular-nums text-peacock-900">{formatPrice(Number(v.value))}</span>
        </p>
      ) : null}
      {b && b.value !== null && b.value !== undefined ? (
        <p className="mt-0.5 flex items-center gap-2">
          <span aria-hidden="true" className="h-2.5 w-2.5 rounded-full" style={{ background: LAGOON }} />
          <span className="text-slate-700">{benchmark}</span>
          <span className="ml-auto pl-4 font-semibold tabular-nums text-slate-700">{formatPrice(Number(b.value))}</span>
        </p>
      ) : null}
    </div>
  );
}

/** Instrument as a peacock area, benchmark (rebased by the backend) as a dashed lagoon line. Pick the period to show. */
export function PriceChart({ history, name }: { history: PriceHistory; name: string }) {
  const all = useMemo<Row[]>(() => {
    const bench = new Map(history.benchmark.points.map((p) => [p.date, p.value] as const));
    return history.points.map((p) => ({ date: p.date, value: p.value, benchmark: bench.get(p.date) ?? null }));
  }, [history]);

  const last = all[all.length - 1];
  const spanYears = all.length > 1 && last ? (Date.parse(last.date) - Date.parse(all[0]!.date)) / (365.25 * 864e5) : 0;
  const ranges = (['1Y', '3Y', '5Y'] as Range[]).filter((r) => (YEARS[r] ?? 0) < spanYears + 0.25);
  const [range, setRange] = useState<Range>('ALL');

  const rows = useMemo(() => {
    const years = YEARS[range];
    if (!years || !last) return all;
    const cutoff = Date.parse(last.date) - years * 365.25 * 864e5;
    return all.filter((r) => Date.parse(r.date) >= cutoff);
  }, [all, range, last]);

  // Last close of each calendar year, for the accessible table.
  const yearly = useMemo(() => {
    const byYear = new Map<string, Row>();
    for (const r of all) byYear.set(yearOf(r.date), r);
    return {
      title: copy.chart.tableTitle,
      columns: [copy.chart.colDate, name, history.benchmark.name],
      rows: Array.from(byYear.values()).map((r) => [
        formatDate(r.date),
        formatPrice(r.value),
        r.benchmark === null ? copy.common.notAvailable : formatPrice(r.benchmark),
      ]),
    };
  }, [all, name, history.benchmark.name]);

  const first = rows[0];
  const end = rows[rows.length - 1];
  const summary =
    first && end
      ? fill(copy.chart.summary, {
          name,
          from: formatDate(first.date),
          to: formatDate(end.date),
          start: formatPrice(first.value),
          end: formatPrice(end.value),
          benchmark: history.benchmark.name,
        })
      : copy.chart.empty;

  if (all.length === 0) {
    return <p className="text-slate-600">{copy.chart.empty}</p>;
  }

  const benchStart = rows.find((r) => r.benchmark !== null)?.benchmark ?? null;
  const benchEnd = [...rows].reverse().find((r) => r.benchmark !== null)?.benchmark ?? null;
  const change = first && end && first.value ? end.value / first.value - 1 : null;
  const benchChange = benchStart && benchEnd ? benchEnd / benchStart - 1 : null;
  const animate = !prefersReducedMotion();

  return (
    <figure className="m-0">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        {ranges.length > 0 ? (
          <SegmentedControl<Range>
            label={copy.chart.periodLabel}
            value={range}
            onChange={setRange}
            options={[...ranges.map((r) => ({ value: r, label: r })), { value: 'ALL' as Range, label: copy.chart.all }]}
          />
        ) : (
          <span />
        )}
        <dl className="flex flex-wrap gap-x-6 gap-y-1 text-sm" aria-label={copy.chart.periodChange}>
          <div className="flex items-baseline gap-2">
            <dt className="text-slate-600">{name}</dt>
            <dd key={`${range}-v`} className="animate-pop font-display text-lg font-bold tabular-nums text-peacock-900">
              {formatPctChange(change)}
            </dd>
          </div>
          <div className="flex items-baseline gap-2">
            <dt className="text-slate-600">{history.benchmark.name}</dt>
            <dd key={`${range}-b`} className="animate-pop font-display text-lg font-bold tabular-nums text-slate-700">
              {formatPctChange(benchChange)}
            </dd>
          </div>
        </dl>
      </div>
      <div role="img" aria-label={summary} className="h-72 w-full sm:h-96">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart key={range} data={rows} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
            <defs>
              <linearGradient id="pf-area" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={PEACOCK} stopOpacity={0.28} />
                <stop offset="100%" stopColor={PEACOCK} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="#D4DFDC" strokeDasharray="2 6" vertical={false} />
            <XAxis
              dataKey="date"
              tickFormatter={(d: string) => formatMonthYear(d)}
              tick={{ fill: '#4A6265', fontSize: 12 }}
              minTickGap={56}
              tickLine={false}
              axisLine={{ stroke: '#B6C6C2' }}
            />
            <YAxis
              width={52}
              domain={['auto', 'auto']}
              tickFormatter={(v: number) => formatAxisNumber(v)}
              tick={{ fill: '#4A6265', fontSize: 12 }}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip
              cursor={{ stroke: MARIGOLD, strokeWidth: 1.5, strokeDasharray: '3 3' }}
              content={<TooltipBox name={name} benchmark={history.benchmark.name} />}
            />
            <Line
              type="monotone"
              dataKey="benchmark"
              stroke={LAGOON}
              strokeWidth={2}
              strokeDasharray="6 5"
              dot={false}
              activeDot={{ r: 4, fill: LAGOON, stroke: '#fff', strokeWidth: 2 }}
              isAnimationActive={animate}
              animationDuration={900}
              connectNulls
            />
            <Area
              type="monotone"
              dataKey="value"
              stroke={PEACOCK}
              strokeWidth={2.6}
              fill="url(#pf-area)"
              dot={false}
              activeDot={{ r: 6, fill: MARIGOLD, stroke: PEACOCK, strokeWidth: 2.5 }}
              isAnimationActive={animate}
              animationDuration={1100}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <figcaption className="mt-3 flex flex-wrap items-center gap-x-6 gap-y-1 text-sm text-slate-700">
        <span className="inline-flex items-center gap-2">
          <svg width="28" height="10" aria-hidden="true">
            <line x1="0" y1="5" x2="28" y2="5" stroke={PEACOCK} strokeWidth="3" strokeLinecap="round" />
          </svg>
          {name}
        </span>
        <span className="inline-flex items-center gap-2">
          <svg width="28" height="10" aria-hidden="true">
            <line x1="0" y1="5" x2="28" y2="5" stroke={LAGOON} strokeWidth="2" strokeDasharray="6 5" />
          </svg>
          {fill(copy.chart.benchmarkLegend, { benchmark: history.benchmark.name })}
        </span>
        <span className="text-xs text-slate-600">
          {history.source}, {copy.common.asOf} {formatDate(history.asOf)}
        </span>
      </figcaption>
      <ShowDetails>
        <DataTable table={yearly} />
      </ShowDetails>
    </figure>
  );
}
