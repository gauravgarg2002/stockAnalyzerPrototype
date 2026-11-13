import type { ReactNode } from 'react';
import { useSpotlight } from '../../hooks/useMotion';

export interface CardProps {
  as?: 'div' | 'section' | 'article' | 'li';
  className?: string;
  padded?: boolean;
  children: ReactNode;
  labelledBy?: string;
  /** A soft light follows the pointer across the card. */
  spotlight?: boolean;
  tone?: 'sheet' | 'tint';
}

/** A white "sheet" with a crisp stacked edge; `tint` is the quieter lagoon-washed tier. */
export function Card({ as = 'div', className = '', padded = true, children, labelledBy, spotlight = false, tone = 'sheet' }: CardProps) {
  const Tag = as;
  const onMove = useSpotlight<HTMLElement>();
  const surface =
    tone === 'tint'
      ? 'rounded-2xl bg-lagoon-100/70 ring-1 ring-inset ring-lagoon-200'
      : 'rounded-sheet border border-slate-200 bg-white shadow-sheet';
  return (
    <Tag
      aria-labelledby={labelledBy}
      onPointerMove={spotlight ? onMove : undefined}
      className={`${surface} ${spotlight ? 'spotlight transition-shadow duration-300 hover:shadow-lift' : ''} ${padded ? 'p-5 sm:p-7' : ''} ${className}`}
    >
      {children}
    </Tag>
  );
}
