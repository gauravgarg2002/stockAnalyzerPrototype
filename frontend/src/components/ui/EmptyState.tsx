import type { ReactNode } from 'react';

export function EmptyState({ title, children, action, icon }: { title: string; children?: ReactNode; action?: ReactNode; icon?: ReactNode }) {
  return (
    <div className="rounded-sheet border-2 border-dashed border-lagoon-300 bg-white/70 px-6 py-12 text-center">
      <div className="mx-auto mb-4 flex h-14 w-14 animate-drift items-center justify-center rounded-2xl bg-peacock-900 text-marigold-400" aria-hidden="true">
        {icon ?? (
          <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7z" />
          </svg>
        )}
      </div>
      <h2 className="font-display text-xl font-bold text-peacock-900">{title}</h2>
      {children ? <div className="mx-auto mt-2 max-w-md text-slate-600">{children}</div> : null}
      {action ? <div className="mt-5 flex flex-wrap justify-center gap-3">{action}</div> : null}
    </div>
  );
}
