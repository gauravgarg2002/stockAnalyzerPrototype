import type { Sentence } from '../../lib/api-types';
import { CountUp } from './Motion';

// Rupee amounts (with lakh / crore), signed or plain percentages. Plain counts are left as text.
const FIGURE = /(₹\s?[\d,]+(?:\.\d+)?(?:\s(?:lakh|crore))?|[+\-−]?\d[\d,]*(?:\.\d+)?%)/g;

/** A sentence whose figures are lifted out, highlighted and counted up. The words are exactly the backend's. */
export function RichSentence({ text, tone = 'light' }: { text: string; tone?: 'light' | 'dark' }) {
  const parts = text.split(FIGURE);
  const mark =
    tone === 'dark'
      ? 'rounded-md bg-marigold-400/15 px-1 font-display font-bold text-marigold-300'
      : 'rounded-md bg-marigold-100 px-1 font-display font-bold text-peacock-900';
  return (
    <>
      {parts.map((p, i) =>
        i % 2 === 1 ? (
          <span key={i} className={`whitespace-nowrap tabular-nums ${mark}`}>
            <CountUp display={p} ms={1100} />
          </span>
        ) : (
          <span key={i}>{p}</span>
        ),
      )}
    </>
  );
}

export function RichSentenceList({ sentences, tone = 'light', className = '' }: { sentences: Sentence[]; tone?: 'light' | 'dark'; className?: string }) {
  return (
    <div className={`space-y-3 text-[1.2rem] leading-relaxed ${tone === 'dark' ? 'text-lagoon-100' : 'text-slate-800'} ${className}`}>
      {sentences.map((s, i) => (
        <p key={`${s.templateId}-${i}`}>
          <RichSentence text={s.text} tone={tone} />
        </p>
      ))}
    </div>
  );
}
