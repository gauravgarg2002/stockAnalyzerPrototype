import { copy } from '../../lib/copy';
import { formatDate } from '../../lib/dates';
import { useMeta } from '../../context/MetaContext';
import { SampleDataBadge } from './SampleDataBadge';
import { LogoMark } from './LogoMark';

export function Footer() {
  const meta = useMeta();
  return (
    <footer className="jali mt-auto text-lagoon-200">
      <div className="mx-auto flex max-w-page flex-col gap-4 px-4 py-8 text-sm sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <div className="flex items-center gap-3">
          <LogoMark className="h-8 w-8" />
          <p className="font-semibold text-white">{copy.app.disclaimer}</p>
        </div>
        <p className="flex flex-wrap items-center gap-3">
          {meta ? <SampleDataBadge show={meta.sampleData} tone="dark" /> : null}
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
