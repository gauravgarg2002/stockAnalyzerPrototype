import type { ReactNode } from 'react';

export interface CardProps {
  as?: 'div' | 'section' | 'article' | 'li';
  className?: string;
  padded?: boolean;
  children: ReactNode;
  labelledBy?: string;
}

export function Card({ as = 'div', className = '', padded = true, children, labelledBy }: CardProps) {
  const Tag = as;
  return (
    <Tag
      aria-labelledby={labelledBy}
      className={`rounded-2xl border border-slate-200 bg-white shadow-sm ${padded ? 'p-4 sm:p-6' : ''} ${className}`}
    >
      {children}
    </Tag>
  );
}
