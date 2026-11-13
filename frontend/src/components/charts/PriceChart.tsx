import { useMemo } from 'react';
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { PriceHistory } from '../../lib/api-types';
import { formatAxisNumber, formatPrice } from '../../lib/format';
import { formatDate, formatMonthYear, yearOf } from '../../lib/dates';
import { copy, fill } from '../../lib/copy';
import { ShowDetails } from '../ui/ShowDetails';
import { DataTable } from '../ui/DataTable';

interface Row {
  date: string;
  value: number;
  benchmark: number | null;
}

/** Instrument in slate-700, benchmark (rebased by the backend) dashed in slate-400. */
export function PriceChart({ history, name }: { history: PriceHistory; name: string }) {
  const rows = useMemo<Row[]>(() => {
    const bench = new Map(history.benchmark.points.map((p) => [p.date, p.value] as const));
    return history.points.map((p) => ({ date: p.date, value: p.value, benchmark: bench.get(p.date) ?? null }));
  }, [history]);

  // Last close of each calendar year, for the accessible table.
  const yearly = useMemo(() => {
    const byYear = new Map<string, Row>();
    for (const r of rows) byYear.set(yearOf(r.date), r);
    return {
      title: copy.chart.tableTitle,
      columns: [copy.chart.colDate, name, history.benchmark.name],
      rows: Array.from(byYear.values()).map((r) => [
        formatDate(r.date),
        formatPrice(r.value),
        r.benchmark === null ? copy.common.notAvailable : formatPrice(r.benchmark),
      ]),
    };
  }, [rows, name, history.benchmark.name]);

  const first = rows[0];
  const last = rows[rows.length - 1];
  const summary =
    first && last
      ? fill(copy.chart.summary, {
          name,
          from: formatDate(first.date),
          to: formatDate(last.date),
          start: formatPrice(first.value),
          end: formatPrice(last.value),
          benchmark: history.benchmark.name,
        })
      : copy.chart.empty;

  if (rows.length === 0) {
    return <p className="text-slate-600">{copy.chart.empty}</p>;
  }

  return (
    <figure className="m-0">
      <div role="img" aria-label={summary} className="h-64 w-full sm:h-80">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="date"
              tickFormatter={(d: string) => formatMonthYear(d)}
              tick={{ fill: '#475569', fontSize: 12 }}
              minTickGap={48}
              tickLine={false}
              axisLine={{ stroke: '#cbd5e1' }}
            />
            <YAxis
              width={48}
              domain={['auto', 'auto']}
              tickFormatter={(v: number) => formatAxisNumber(v)}
              tick={{ fill: '#475569', fontSize: 12 }}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip
              formatter={(value: unknown, key: unknown) => [
                formatPrice(Number(value)),
                key === 'benchmark' ? history.benchmark.name : name,
              ]}
              labelFormatter={(label: unknown) => formatDate(String(label))}
              contentStyle={{ borderRadius: 12, borderColor: '#cbd5e1', fontSize: 13 }}
            />
            <Line
              type="monotone"
              dataKey="benchmark"
              stroke="#94a3b8"
              strokeWidth={2}
              strokeDasharray="6 4"
              dot={false}
              isAnimationActive={false}
              connectNulls
            />
            <Line
              type="monotone"
              dataKey="value"
              stroke="#334155"
              strokeWidth={2.5}
              dot={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <figcaption className="mt-2 flex flex-wrap items-center gap-x-5 gap-y-1 text-sm text-slate-700">
        <span className="inline-flex items-center gap-2">
          <svg width="28" height="8" aria-hidden="true">
            <line x1="0" y1="4" x2="28" y2="4" stroke="#334155" strokeWidth="3" />
          </svg>
          {name}
        </span>
        <span className="inline-flex items-center gap-2">
          <svg width="28" height="8" aria-hidden="true">
            <line x1="0" y1="4" x2="28" y2="4" stroke="#94a3b8" strokeWidth="2" strokeDasharray="6 4" />
          </svg>
          {fill(copy.chart.benchmarkLegend, { benchmark: history.benchmark.name })}
        </span>
        <span className="text-xs text-slate-600">
          {history.source} · {copy.common.asOf} {formatDate(history.asOf)}
        </span>
      </figcaption>
      <ShowDetails>
        <DataTable table={yearly} />
      </ShowDetails>
    </figure>
  );
}
