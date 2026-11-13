import type { CSSProperties, ReactNode } from 'react';
import { formatTweened, splitDisplay, useInView, useTween } from '../../hooks/useMotion';

/**
 * Counts a display string up from zero when it scrolls into view ("₹8.2 lakh", "16.2%", "₹2,775").
 * The final text is always exactly the string the backend sent; screen readers get only that text.
 */
export function CountUp({ display, className = '', ms = 900 }: { display: string; className?: string; ms?: number }) {
  const parts = splitDisplay(display);
  const [ref, shown] = useInView<HTMLSpanElement>();
  const current = useTween(parts?.value ?? 0, shown && !!parts, ms);
  if (!parts) return <span className={className}>{display}</span>;
  const done = Math.abs(current - parts.value) < 1e-9;
  return (
    <span ref={ref} className={className}>
      <span aria-hidden="true">{done ? display : formatTweened(parts, current)}</span>
      <span className="sr-only">{display}</span>
    </span>
  );
}

/** Fades and lifts its children in when they scroll into view. `delay` staggers siblings. */
export function Reveal({ children, delay = 0, className = '', as = 'div' }: { children: ReactNode; delay?: number; className?: string; as?: 'div' | 'section' | 'li' }) {
  const [ref, shown] = useInView<HTMLDivElement>();
  const Tag = as as 'div';
  return (
    <Tag
      ref={ref}
      data-shown={shown}
      className={`reveal ${className}`}
      style={{ '--reveal-delay': `${delay}ms` } as CSSProperties}
    >
      {children}
    </Tag>
  );
}
