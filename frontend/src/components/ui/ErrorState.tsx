import { copy } from '../../lib/copy';
import { ApiError } from '../../lib/api-client';
import { Button } from './Button';

function friendly(error: Error | null | undefined): { title: string; body: string } {
  if (error instanceof ApiError) {
    switch (error.code) {
      case 'NOT_FOUND':
        return copy.errors.notFound;
      case 'NETWORK_ERROR':
        return copy.errors.network;
      case 'UPSTREAM_UNAVAILABLE':
        return copy.errors.upstream;
      case 'BAD_REQUEST':
        return { title: copy.errors.badRequest.title, body: error.message };
      case 'STATEMENT_PASSWORD_INVALID':
        return copy.errors.statementPassword;
      case 'STATEMENT_UNREADABLE':
        return copy.errors.statementUnreadable;
      case 'BROKER_NOT_CONNECTED':
        return copy.errors.brokerNotConnected;
      default:
        return copy.errors.generic;
    }
  }
  return copy.errors.generic;
}

export function errorMessage(error: Error | null | undefined): string {
  return friendly(error).body;
}

export interface ErrorStateProps {
  error?: Error | null;
  onRetry?: () => void;
  title?: string;
  compact?: boolean;
}

export function ErrorState({ error, onRetry, title, compact = false }: ErrorStateProps) {
  const f = friendly(error);
  return (
    <div
      role="alert"
      className={`rounded-sheet border border-slate-200 bg-white text-center shadow-sheet ${compact ? 'px-4 py-6' : 'mt-8 px-6 py-12'}`}
    >
      <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-marigold-50 text-marigold-700 ring-1 ring-inset ring-marigold-200" aria-hidden="true">
        <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="9" />
          <path d="M12 7v6M12 16.5v.5" />
        </svg>
      </div>
      <h2 className="font-display text-xl font-bold text-peacock-900">{title ?? f.title}</h2>
      <p className="mx-auto mt-1 max-w-md text-slate-600">{f.body}</p>
      {onRetry ? (
        <div className="mt-4">
          <Button variant="secondary" onClick={onRetry}>
            {copy.common.retry}
          </Button>
        </div>
      ) : null}
    </div>
  );
}
