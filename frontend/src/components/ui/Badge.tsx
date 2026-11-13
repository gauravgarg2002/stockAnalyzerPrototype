import type { ReactNode } from 'react';

export function Badge({ children, tone = 'neutral', className = '' }: { children: ReactNode; tone?: 'neutral' | 'accent'; className?: string }) {
  const tones = {
    neutral: 'bg-slate-100 text-slate-700 ring-slate-200',
    accent: 'bg-indigo-50 text-indigo-800 ring-indigo-200',
  };
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${tones[tone]} ${className}`}
    >
      {children}
    </span>
  );
}
