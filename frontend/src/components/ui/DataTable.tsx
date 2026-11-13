import type { DetailTable } from '../../lib/api-types';

export function DataTable({ table }: { table: DetailTable }) {
  return (
    <div
      className="overflow-x-auto rounded-2xl border border-slate-200 bg-white"
      role="region"
      aria-label={table.title}
      tabIndex={0}
    >
      <table className="min-w-full border-collapse text-left text-sm">
        <caption className="bg-peacock-900 px-4 py-2.5 text-left text-sm font-semibold text-white">{table.title}</caption>
        <thead>
          <tr className="border-b border-slate-200 bg-lagoon-100/70 text-peacock-900">
            {table.columns.map((c, i) => (
              <th key={i} scope="col" className={`px-4 py-2.5 font-semibold ${i > 0 ? 'text-right sm:text-left' : ''}`}>
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {table.rows.map((row, r) => (
            <tr key={r} className="border-b border-slate-100 transition-colors last:border-0 hover:bg-marigold-50">
              {row.map((cell, c) =>
                c === 0 ? (
                  <th key={c} scope="row" className="px-4 py-2.5 font-medium text-slate-800">
                    {cell}
                  </th>
                ) : (
                  <td key={c} className="whitespace-nowrap px-4 py-2.5 text-right tabular-nums text-slate-700 sm:text-left">
                    {cell}
                  </td>
                ),
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
