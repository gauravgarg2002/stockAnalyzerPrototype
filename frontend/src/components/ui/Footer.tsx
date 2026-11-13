import { copy } from '../../lib/copy';
import { formatDate } from '../../lib/dates';
import { useMeta } from '../../context/MetaContext';
import { SampleDataBadge } from './SampleDataBadge';

export function Footer() {
  const meta = useMeta();
  return (
    <footer className="border-t border-slate-200 bg-white">
      <div className="mx-auto flex max-w-page flex-col gap-2 px-4 py-6 text-sm text-slate-700 sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <p className="font-medium">{copy.app.disclaimer}</p>
        <p className="flex flex-wrap items-center gap-2 text-slate-600">
          {meta ? <SampleDataBadge show={meta.sampleData} /> : null}
          {meta ? (
            <span>
              {copy.common.dataAsOf} {formatDate(meta.asOf)}
            </span>
          ) : null}
          <span>{copy.app.sourcesNote}</span>
        </p>
      </div>
    </footer>
  );
}
