import type { CSSProperties } from 'react';
import type { MixLine } from '../../lib/api-types';
import { useInView } from '../../hooks/useMotion';

// Categories only: peacock, lagoon, marigold, slate-blue, sand, mist. None of them reads as a verdict.
const SHADES = ['#0B3B4F', '#6CB7BE', '#F4A92B', '#5B6C8F', '#C6B48A', '#CCE8EA'];

/** One stacked bar for a mix; segments grow in left to right. Every segment is also written out in the legend. */
export function MixBar({ lines, label }: { lines: MixLine[]; label: string }) {
  const [ref, shown] = useInView<HTMLDivElement>();
  return (
    <div ref={ref}>
      <div
        className="flex h-5 gap-[3px] overflow-hidden rounded-full"
        role="img"
        aria-label={`${label}: ${lines.map((l) => `${l.label} ${l.display}`).join(', ')}`}
      >
        {lines.map((l, i) =>
          l.pct > 0 ? (
            <div
              key={l.key}
              title={`${l.label}: ${l.display}`}
              className="h-full origin-left rounded-sm transition-[transform,filter] duration-700 ease-out first:rounded-l-full last:rounded-r-full hover:brightness-110"
              style={{ width: `${l.pct}%`, background: SHADES[i % SHADES.length], transform: shown ? 'scaleX(1)' : 'scaleX(0)', transitionDelay: `${i * 120}ms` } as CSSProperties}
            />
          ) : null,
        )}
      </div>
      <ul className="mt-4 grid gap-x-8 gap-y-2 text-[0.95rem] sm:grid-cols-2" aria-label={label}>
        {lines.map((l, i) => (
          <li key={l.key} className="flex items-center justify-between gap-3 border-b border-dashed border-slate-200 pb-1.5">
            <span className="flex items-center gap-2.5 text-slate-700">
              <span aria-hidden="true" className="h-3.5 w-3.5 shrink-0 rounded-[5px] ring-1 ring-inset ring-black/10" style={{ background: SHADES[i % SHADES.length] }} />
              {l.label}
            </span>
            <span className="font-semibold tabular-nums text-peacock-900">{l.display}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
