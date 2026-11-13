import type { DetailTable } from '../../lib/api-types';

export function DataTable({ table }: { table: DetailTable }) {
  return (
    <div
      className="overflow-x-auto rounded-xl border border-slate-200"
      role="region"
      aria-label={table.title}
      tabIndex={0}
    >
      <table className="min-w-full border-collapse text-left text-sm">
        <caption className="bg-slate-50 px-3 py-2 text-left text-sm font-semibold text-slate-800">{table.title}</caption>
        <thead>
          <tr className="border-y border-slate-200 bg-slate-50 text-slate-700">
            {table.columns.map((c, i) => (
              <th key={i} scope="col" className={`px-3 py-2 font-medium ${i > 0 ? 'text-right sm:text-left' : ''}`}>
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {table.rows.map((row, r) => (
            <tr key={r} className="border-b border-slate-100 last:border-0">
              {row.map((cell, c) =>
                c === 0 ? (
                  <th key={c} scope="row" className="px-3 py-2 font-medium text-slate-800">
                    {cell}
                  </th>
                ) : (
                  <td key={c} className="whitespace-nowrap px-3 py-2 text-right text-slate-700 sm:text-left">
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
