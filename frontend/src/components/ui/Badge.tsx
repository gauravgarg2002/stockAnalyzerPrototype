import type { ReactNode } from 'react';

export function Badge({ children, tone = 'neutral', className = '' }: { children: ReactNode; tone?: 'neutral' | 'accent'; className?: string }) {
  const tones = {
    neutral: 'bg-lagoon-100 text-peacock-800 ring-lagoon-200',
    accent: 'bg-marigold-50 text-marigold-700 ring-marigold-300',
  };
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset ${tones[tone]} ${className}`}
    >
      {children}
    </span>
  );
}
