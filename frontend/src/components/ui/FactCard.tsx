import type { Fact } from '../../lib/api-types';
import { copy } from '../../lib/copy';
import { Badge } from './Badge';
import { Card } from './Card';
import { SentenceList } from './SentenceList';
import { FigureGrid } from './FigureChip';
import { ExplainPopover } from './ExplainPopover';
import { ShowDetails } from './ShowDetails';
import { DataTable } from './DataTable';

/** One of the eight fixed facts. Same layout for every stock and every fund. */
export function FactCard({ fact, headingId }: { fact: Fact; headingId: string }) {
  return (
    <Card as="article" labelledBy={headingId} className="h-full">
      <div className="flex items-start justify-between gap-2">
        <h3 id={headingId} className="text-base font-semibold leading-snug text-slate-900">
          <span className="mr-2 text-slate-600" aria-hidden="true">
            {fact.order}.
          </span>
          {fact.title}
        </h3>
        {fact.termId ? <ExplainPopover termId={fact.termId} label={fact.title} /> : null}
      </div>
      {!fact.available ? (
        <div className="mt-2">
          <Badge>{copy.common.notAvailable}</Badge>
        </div>
      ) : null}
      <SentenceList sentences={fact.sentences} className="mt-3" />
      <FigureGrid figures={fact.figures} single />
      {fact.details ? (
        <ShowDetails>
          <DataTable table={fact.details} />
        </ShowDetails>
      ) : null}
    </Card>
  );
}
