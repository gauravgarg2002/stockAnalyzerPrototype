import type { Sentence } from '../../lib/api-types';

export function SentenceList({ sentences, size = 'md', className = '' }: { sentences: Sentence[]; size?: 'md' | 'lg'; className?: string }) {
  return (
    <div className={`space-y-2 text-slate-800 ${size === 'lg' ? 'text-lg leading-relaxed' : 'text-base leading-relaxed'} ${className}`}>
      {sentences.map((s, i) => (
        <p key={`${s.templateId}-${i}`}>{s.text}</p>
      ))}
    </div>
  );
}
