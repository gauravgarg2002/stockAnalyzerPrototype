import { copy } from '../../lib/copy';

export function Skeleton({ className = '' }: { className?: string }) {
  return <div aria-hidden="true" className={`animate-pulse rounded-md bg-slate-200 motion-reduce:animate-none ${className}`} />;
}

export function SkeletonText({ lines = 3 }: { lines?: number }) {
  return (
    <div className="space-y-2" aria-hidden="true">
      {Array.from({ length: lines }, (_, i) => (
        <Skeleton key={i} className={`h-4 ${i === lines - 1 ? 'w-2/3' : 'w-full'}`} />
      ))}
    </div>
  );
}

export function SkeletonCard({ lines = 3 }: { lines?: number }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6" aria-hidden="true">
      <Skeleton className="mb-4 h-5 w-1/2" />
      <SkeletonText lines={lines} />
      <div className="mt-4 grid grid-cols-2 gap-3">
        <Skeleton className="h-16" />
        <Skeleton className="h-16" />
      </div>
    </div>
  );
}

/** Page-level loading placeholder; announces itself once to screen readers. */
export function PageSkeleton({ cards = 3, title = true }: { cards?: number; title?: boolean }) {
  return (
    <div role="status" aria-live="polite" aria-busy="true">
      <span className="sr-only">{copy.common.loading}</span>
      {title ? (
        <div className="mb-6 space-y-3" aria-hidden="true">
          <Skeleton className="h-8 w-2/3 max-w-md" />
          <Skeleton className="h-4 w-1/2 max-w-xs" />
        </div>
      ) : null}
      <div className="space-y-4">
        {Array.from({ length: cards }, (_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    </div>
  );
}
