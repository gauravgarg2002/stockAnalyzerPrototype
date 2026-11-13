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
    <Card as="article" labelledBy={headingId} className="h-full" spotlight>
      <div className="flex items-start justify-between gap-2">
        <h3 id={headingId} className="flex items-baseline gap-2.5 font-display text-lg font-bold leading-snug text-peacock-900">
          <span aria-hidden="true" className="font-display text-sm font-extrabold tabular-nums text-marigold-600">
            {String(fact.order).padStart(2, '0')}
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
