import type { Answer } from '../../lib/api-types';
import { Card } from './Card';
import { SentenceList } from './SentenceList';
import { FigureGrid } from './FigureChip';
import { ShowDetails } from './ShowDetails';
import { DataTable } from './DataTable';

/** One of the five questions: sentences first, then figures, then the full table behind a toggle. */
export function AnswerCard({ answer, headingId }: { answer: Answer; headingId: string }) {
  return (
    <Card as="article" labelledBy={headingId}>
      <div className="flex items-start gap-3">
        <span
          aria-hidden="true"
          className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-indigo-700 text-sm font-semibold text-white"
        >
          {answer.order}
        </span>
        <h3 id={headingId} className="text-lg font-semibold leading-snug text-slate-900">
          {answer.question}
        </h3>
      </div>
      <SentenceList sentences={answer.sentences} className="mt-3" />
      <FigureGrid figures={answer.figures} />
      {answer.details ? (
        <ShowDetails>
          <DataTable table={answer.details} />
        </ShowDetails>
      ) : null}
    </Card>
  );
}
