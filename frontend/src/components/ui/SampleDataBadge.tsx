import { copy } from '../../lib/copy';

/** Small badge shown whenever a response has sampleData: true. */
export function SampleDataBadge({ show, tone = 'light' }: { show: boolean | undefined; tone?: 'light' | 'dark' }) {
  if (!show) return null;
  const cls =
    tone === 'dark'
      ? 'bg-marigold-400/15 text-marigold-200 ring-marigold-400/40'
      : 'bg-marigold-50 text-marigold-700 ring-marigold-300';
  return (
    <span
      title={copy.common.sampleDataHint}
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset ${cls}`}
    >
      <svg viewBox="0 0 16 16" className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
        <path d="M6 2v4.5L2.8 12a1.5 1.5 0 0 0 1.3 2.2h7.8A1.5 1.5 0 0 0 13.2 12L10 6.5V2M5 2h6" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      {copy.common.sampleData}
    </span>
  );
}
