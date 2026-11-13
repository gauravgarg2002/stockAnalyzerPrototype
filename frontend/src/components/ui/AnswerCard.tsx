import type { Answer } from '../../lib/api-types';
import { Card } from './Card';
import { SentenceList } from './SentenceList';
import { FigureGrid } from './FigureChip';
import { ShowDetails } from './ShowDetails';
import { DataTable } from './DataTable';

/** One of the five questions: sentences first, then figures, then the full table behind a toggle. */
export function AnswerCard({ answer, headingId }: { answer: Answer; headingId: string }) {
  return (
    <Card as="article" labelledBy={headingId} spotlight>
      <div className="flex items-start gap-4">
        <span
          aria-hidden="true"
          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-peacock-900 font-display text-xl font-extrabold text-marigold-400 shadow-sheet"
        >
          {answer.order}
        </span>
        <h3 id={headingId} className="pt-1.5 font-display text-xl font-bold leading-snug text-peacock-900 sm:text-[1.4rem]">
          {answer.question}
        </h3>
      </div>
      <div className="sm:pl-[3.75rem]">
        <SentenceList sentences={answer.sentences} className="mt-3" />
        <FigureGrid figures={answer.figures} />
        {answer.details ? (
          <ShowDetails>
            <DataTable table={answer.details} />
          </ShowDetails>
        ) : null}
      </div>
    </Card>
  );
}
