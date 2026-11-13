import { useId, useState } from 'react';
import type { CSSProperties } from 'react';
import { Link } from 'react-router-dom';
import type { ExposureLine } from '../../lib/api-types';
import { copy, fill } from '../../lib/copy';
import { formatInr } from '../../lib/format';
import { stockPath } from '../../lib/routes';
import { useInView } from '../../hooks/useMotion';
import { CountUp } from '../ui/Motion';

export interface ExposureBarsProps {
  lines: ExposureLine[];
  /** Show the direct / through-funds split in words under each bar. */
  split?: boolean;
  label: string;
  /** Dark variant for use on the peacock-ink hero. */
  tone?: 'light' | 'dark';
}

// "Through funds" is drawn as a lattice-hatched lagoon fill, so the two parts differ by pattern as well as colour.
const HATCH: CSSProperties = {
  backgroundImage: 'repeating-linear-gradient(135deg, rgba(11,59,79,.18) 0 2px, transparent 2px 6px)',
};

function Row({ l, max, split, shown, index, tone }: { l: ExposureLine; max: number; split: boolean; shown: boolean; index: number; tone: 'light' | 'dark' }) {
  const [open, setOpen] = useState(false);
  const panelId = useId();
  const dark = tone === 'dark';
  const directW = shown ? (l.directPct / max) * 100 : 0;
  const fundsW = shown ? (l.throughFundsPct / max) * 100 : 0;
  const delay = index * 90;
  const hasVia = split && l.viaFunds.length > 0;
  return (
    <li className="group/row">
      <div className="flex items-baseline justify-between gap-3">
        <span className={`min-w-0 break-words font-semibold ${dark ? 'text-white' : 'text-peacock-900'}`}>
          {l.checkAvailable && l.symbol && !dark ? (
            <Link to={stockPath(l.symbol)} className="link-draw">
              {l.name}
            </Link>
          ) : (
            l.name
          )}
        </span>
        <span className={`shrink-0 text-right font-display font-bold tabular-nums ${dark ? 'text-marigold-300' : 'text-peacock-900'}`}>
          <CountUp display={l.display} />
        </span>
      </div>
      <div
        aria-hidden="true"
        className={`mt-2 flex h-3.5 overflow-hidden rounded-full ${dark ? 'bg-white/10' : 'bg-slate-100'} transition-[height] duration-200 group-hover/row:h-[18px]`}
      >
        <div
          className={`h-full ${dark ? 'bg-marigold-400' : 'bg-peacock-900'} transition-[width] duration-700 ease-out`}
          style={{ width: `${directW}%`, transitionDelay: `${delay}ms` }}
        />
        <div
          className={`h-full ${dark ? 'bg-lagoon-300' : 'bg-lagoon-300'} transition-[width] duration-700 ease-out`}
          style={{ ...HATCH, width: `${fundsW}%`, transitionDelay: `${delay + 450}ms` }}
        />
      </div>
      {split ? (
        <div className="mt-1.5 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-slate-600">
          <span>
            {copy.exposure.direct}: <span className="font-semibold tabular-nums text-slate-800">{l.directDisplay}</span>
          </span>
          <span>
            {copy.exposure.throughFunds}: <span className="font-semibold tabular-nums text-slate-800">{l.throughFundsDisplay}</span>
          </span>
          {hasVia ? (
            <button
              type="button"
              aria-expanded={open}
              aria-controls={panelId}
              onClick={() => setOpen((o) => !o)}
              className="inline-flex items-center gap-1 rounded-full bg-lagoon-100 px-2.5 py-0.5 text-xs font-semibold text-peacock-800 transition-colors hover:bg-lagoon-200"
            >
              {open ? copy.exposure.hideVia : `${copy.exposure.showVia} (${l.viaFunds.length})`}
              <svg viewBox="0 0 12 12" className={`h-3 w-3 transition-transform duration-300 ${open ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
                <path d="M3 4.5L6 7.5 9 4.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>
          ) : null}
        </div>
      ) : null}
      {hasVia ? (
        <div id={panelId} className="collapsible" data-open={open}>
          <div>
            <div className="mt-2 rounded-xl bg-lagoon-100/70 p-3 text-sm ring-1 ring-inset ring-lagoon-200">
              <p className="text-slate-700">{fill(copy.exposure.viaIntro, { name: l.name })}</p>
              <ul className="mt-1.5 space-y-1">
                {l.viaFunds.map((v) => (
                  <li key={v.name} className="flex items-baseline justify-between gap-3">
                    <span className="min-w-0 text-slate-800">{v.name}</span>
                    <span className="shrink-0 font-semibold tabular-nums text-peacock-900">{formatInr(v.inr)}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      ) : null}
    </li>
  );
}

/**
 * The look-through bars. Each line fills its "held directly" part first, then the hatched "through funds" part
 * slides in after it: the moment the product exists for. Bars are scaled to the largest line.
 */
export function ExposureBars({ lines, split = true, label, tone = 'light' }: ExposureBarsProps) {
  const max = Math.max(0.0001, ...lines.map((l) => l.totalPct));
  const [ref, shown] = useInView<HTMLDivElement>();
  const dark = tone === 'dark';
  return (
    <div ref={ref}>
      <ul className="space-y-5" aria-label={label}>
        {lines.map((l, i) => (
          <Row key={`${l.kind}-${l.key}`} l={l} max={max} split={split} shown={shown} index={i} tone={tone} />
        ))}
      </ul>
      <p className={`mt-5 flex flex-wrap gap-x-5 gap-y-1 text-xs ${dark ? 'text-lagoon-200' : 'text-slate-600'}`} aria-hidden="true">
        <span className="inline-flex items-center gap-1.5">
          <span className={`h-3 w-6 rounded-full ${dark ? 'bg-marigold-400' : 'bg-peacock-900'}`} />
          {copy.exposure.direct}
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="h-3 w-6 rounded-full bg-lagoon-300" style={HATCH} />
          {copy.exposure.throughFunds}
        </span>
      </p>
    </div>
  );
}
