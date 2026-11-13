import { useEffect, useState } from 'react';
import type { Answer, Drawdown, Fact, Kind, PriceHistory, UserBlock } from '../lib/api-types';
import { copy, fill } from '../lib/copy';
import { formatDate } from '../lib/dates';
import { formatQuantity } from '../lib/format';
import { AnswerCard } from './ui/AnswerCard';
import { Card } from './ui/Card';
import { FactCard } from './ui/FactCard';
import { FigureChip } from './ui/FigureChip';
import { SectionHeading } from './ui/PageHeader';
import { SentenceList } from './ui/SentenceList';
import { Button } from './ui/Button';
import { PriceChart } from './charts/PriceChart';
import { SaveWithNote } from './SaveWithNote';

/** Which of the given section ids is currently being read (the last one whose top has passed the bar). */
function useCurrentSection(ids: string[]): string | null {
  const [current, setCurrent] = useState<string | null>(null);
  const key = ids.join('|');
  useEffect(() => {
    function onScroll() {
      let found: string | null = null;
      for (const id of key.split('|')) {
        const el = document.getElementById(id);
        if (el && el.getBoundingClientRect().top < 180) found = id;
      }
      setCurrent(found);
    }
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, [key]);
  return current;
}

/** "On this page" jump links, the same on every stock and fund check. Sticks under the header and follows your place. */
export function PageJump({ items }: { items: Array<{ id: string; label: string }> }) {
  const current = useCurrentSection(items.map((i) => i.id));
  return (
    <nav
      aria-label={copy.check.onThisPage}
      className="sticky top-[64px] z-20 -mx-4 mb-8 overflow-x-auto bg-paper/85 px-4 py-2.5 backdrop-blur-md sm:mx-0 sm:rounded-2xl sm:px-2 max-md:top-[118px]"
    >
      <ul className="flex min-w-max gap-1.5">
        {items.map((i) => {
          const on = current === i.id;
          return (
            <li key={i.id}>
              <a
                href={`#${i.id}`}
                aria-current={on ? 'location' : undefined}
                className={`inline-flex min-h-[38px] items-center rounded-full px-4 text-sm font-semibold transition-all duration-300 ${
                  on ? 'bg-peacock-900 text-white shadow-sheet' : 'bg-white text-peacock-800 ring-1 ring-inset ring-slate-200 hover:ring-peacock-700'
                }`}
              >
                {on ? <span aria-hidden="true" className="mr-2 h-1.5 w-1.5 rounded-full bg-marigold-400" /> : null}
                {i.label}
              </a>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

export function AnswersSection({ answers }: { answers: Answer[] }) {
  return (
    <section aria-labelledby="answers" className="scroll-mt-24">
      <SectionHeading id="answers" title={copy.check.answersTitle} hint={copy.check.answersHint} />
      <div className="space-y-4">
        {[...answers]
          .sort((a, b) => a.order - b.order)
          .map((a) => (
            <AnswerCard key={a.id} answer={a} headingId={`answer-${a.id}`} />
          ))}
      </div>
    </section>
  );
}

export function FactsSection({ facts }: { facts: Fact[] }) {
  return (
    <section aria-labelledby="facts" className="scroll-mt-24">
      <SectionHeading id="facts" title={copy.check.factsTitle} hint={copy.check.factsHint} />
      <div className="grid gap-4 md:grid-cols-2">
        {[...facts]
          .sort((a, b) => a.order - b.order)
          .map((f) => (
            <FactCard key={f.id} fact={f} headingId={`fact-${f.id}`} />
          ))}
      </div>
    </section>
  );
}

function DrawdownDates({ drawdown }: { drawdown: Drawdown }) {
  const rows: Array<[string, string]> = [
    [copy.check.peak, drawdown.peakDate ? formatDate(drawdown.peakDate) : copy.common.notAvailable],
    [copy.check.lowest, drawdown.troughDate ? formatDate(drawdown.troughDate) : copy.common.notAvailable],
    [copy.check.recovered, drawdown.recoveryDate ? formatDate(drawdown.recoveryDate) : copy.check.notRecovered],
  ];
  return (
    <dl className="mt-4 grid grid-cols-3 gap-3 text-sm">
      {rows.map(([k, v]) => (
        <div key={k}>
          <dt className="text-slate-600">{k}</dt>
          <dd className="font-medium tabular-nums text-slate-900">{v}</dd>
        </div>
      ))}
    </dl>
  );
}

export function PriceSection({ history, drawdown, name, label }: { history: PriceHistory; drawdown: Drawdown; name: string; label: string }) {
  return (
    <section aria-labelledby="price" className="scroll-mt-24">
      <SectionHeading id="price" title={label} hint={copy.check.priceHint} />
      <Card>
        <PriceChart history={history} name={name} />
      </Card>
      <Card className="mt-4">
        <h3 className="font-display text-xl font-bold text-peacock-900">{copy.check.worstFallTitle}</h3>
        <SentenceList sentences={drawdown.sentences} className="mt-2" />
        <div className="mt-4 max-w-sm">
          <FigureChip figure={drawdown.worstFall} />
        </div>
        <DrawdownDates drawdown={drawdown} />
      </Card>
    </section>
  );
}

export interface CheckActionsProps {
  kind: Kind;
  instrumentId: string;
  name: string;
  user: UserBlock;
  onTry: () => void;
}

/** "Try it on my portfolio" and "Save with a note", plus a line about what the person already holds. */
export function CheckActions({ kind, instrumentId, name, user, onTry }: CheckActionsProps) {
  return (
    <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:flex-wrap sm:items-start">
      <Button onClick={onTry}>{copy.check.tryButton}</Button>
      <SaveWithNote
        kind={kind}
        instrumentId={instrumentId}
        name={name}
        watchlistItemId={user.watchlistItemId}
        existingNote={user.note}
      />
    </div>
  );
}

export function HoldingLine({ kind, user }: { kind: Kind; user: UserBlock }) {
  if (!user.holds || user.quantity === null || !user.holdingValue) return null;
  const template = kind === 'STOCK' ? copy.check.youHoldStock : copy.check.youHoldFund;
  return (
    <p className="mb-6 flex flex-wrap items-center gap-x-2 rounded-2xl bg-lagoon-100/80 px-4 py-3 text-slate-800 ring-1 ring-inset ring-lagoon-200">
      <span aria-hidden="true" className="h-2 w-2 rounded-full bg-peacock-700" />
      {fill(template, { quantity: formatQuantity(user.quantity), value: user.holdingValue.display })}
      <span className="ml-2 text-xs text-slate-600">{user.holdingValue.source}</span>
    </p>
  );
}
