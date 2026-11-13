import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { deleteWatchlistItem, getWatchlist, updateWatchlistNote } from '../lib/api-client';
import type { WatchlistItem } from '../lib/api-types';
import { copy } from '../lib/copy';
import { formatDate } from '../lib/dates';
import { useApi } from '../hooks/useApi';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { PageHeader } from '../components/ui/PageHeader';
import { PageSkeleton } from '../components/ui/Skeleton';
import { ErrorState, errorMessage } from '../components/ui/ErrorState';
import { EmptyState } from '../components/ui/EmptyState';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { TextArea } from '../components/ui/Input';
import { GlobalSearch } from '../components/ui/GlobalSearch';
import { Badge } from '../components/ui/Badge';

function WatchlistCard({ item, onChanged, onRemoved }: { item: WatchlistItem; onChanged: (i: WatchlistItem) => void; onRemoved: (id: number) => void }) {
  const [editing, setEditing] = useState(false);
  const [note, setNote] = useState(item.note);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);

  async function saveNote() {
    setBusy(true);
    setError(null);
    try {
      const updated = await updateWatchlistNote(item.id, note.trim());
      onChanged(updated);
      setEditing(false);
    } catch (e) {
      setError(errorMessage(e instanceof Error ? e : null));
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    setBusy(true);
    setError(null);
    try {
      await deleteWatchlistItem(item.id);
      onRemoved(item.id);
    } catch (e) {
      setError(errorMessage(e instanceof Error ? e : null));
      setBusy(false);
    }
  }

  return (
    <Card as="li">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="text-lg font-semibold text-slate-900">
            <Link to={item.checkPath} className="text-indigo-700 underline decoration-indigo-300 underline-offset-2 hover:decoration-indigo-700">
              {item.name}
            </Link>
          </h2>
          <p className="text-sm text-slate-600">
            {item.subtitle} · <Badge>{item.kind === 'STOCK' ? copy.search.stockTag : copy.search.fundTag}</Badge>
          </p>
        </div>
        {item.latest ? (
          <div className="text-right">
            <p className="text-sm text-slate-700">{item.latest.label}</p>
            <p className="text-xl font-semibold tabular-nums text-slate-900">{item.latest.display}</p>
            {item.latest.comparisons[0] ? (
              <p className="text-sm text-slate-600">
                {item.latest.comparisons[0].label}: <span className="tabular-nums">{item.latest.comparisons[0].display}</span>
              </p>
            ) : null}
            <p className="text-xs text-slate-600">
              {item.latest.source} · {copy.common.asOf} {formatDate(item.latest.asOf)}
            </p>
          </div>
        ) : null}
      </div>

      <div className="mt-4">
        <h3 className="text-sm font-medium text-slate-700">{copy.watchlist.noteTitle}</h3>
        {editing ? (
          <form
            className="mt-2"
            onSubmit={(e) => {
              e.preventDefault();
              void saveNote();
            }}
          >
            <TextArea
              label={copy.watchlist.noteLabel}
              value={note}
              maxLength={1000}
              counter={`${note.length}/1000`}
              onChange={(e) => setNote(e.target.value)}
            />
            <div className="mt-2 flex gap-3">
              <Button type="submit" size="sm" busy={busy}>
                {copy.common.save}
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => {
                  setNote(item.note);
                  setEditing(false);
                }}
              >
                {copy.common.cancel}
              </Button>
            </div>
          </form>
        ) : (
          <p className="mt-1 whitespace-pre-wrap text-slate-800">{item.note !== '' ? item.note : copy.watchlist.noNote}</p>
        )}
      </div>

      {error ? (
        <p role="alert" className="mt-2 text-sm font-medium text-slate-900">
          {error}
        </p>
      ) : null}

      <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-slate-100 pt-3">
        {!editing ? (
          <Button size="sm" variant="secondary" onClick={() => setEditing(true)}>
            {copy.watchlist.editNote}
          </Button>
        ) : null}
        {confirming ? (
          <>
            <span className="text-sm text-slate-700">{copy.watchlist.confirmRemove}</span>
            <Button size="sm" variant="secondary" busy={busy} onClick={() => void remove()}>
              {copy.watchlist.yesRemove}
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setConfirming(false)}>
              {copy.common.cancel}
            </Button>
          </>
        ) : (
          <Button size="sm" variant="ghost" onClick={() => setConfirming(true)}>
            {copy.watchlist.remove}
          </Button>
        )}
        <span className="ml-auto text-xs text-slate-600">
          {copy.watchlist.saved} {formatDate(item.createdAt)}
        </span>
      </div>
    </Card>
  );
}

export default function WatchlistPage() {
  useDocumentTitle(copy.watchlist.title);
  const { data, loading, error, reload } = useApi((signal) => getWatchlist({ signal }), []);
  const [items, setItems] = useState<WatchlistItem[] | null>(null);

  useEffect(() => {
    if (data) setItems(data.items);
  }, [data]);

  const list = items ?? data?.items ?? null;

  return (
    <div>
      <PageHeader title={copy.watchlist.title} subtitle={copy.watchlist.subtitle} sampleData={data?.sampleData} />
      {loading ? <PageSkeleton cards={3} title={false} /> : null}
      {error ? <ErrorState error={error} onRetry={reload} /> : null}
      {list && list.length === 0 ? (
        <EmptyState title={copy.watchlist.emptyTitle}>
          <p>{copy.watchlist.emptyBody}</p>
          <div className="mt-4 text-left">
            <GlobalSearch />
          </div>
        </EmptyState>
      ) : null}
      {list && list.length > 0 ? (
        <ul className="space-y-4">
          {list.map((it) => (
            <WatchlistCard
              key={it.id}
              item={it}
              onChanged={(u) => setItems((cur) => (cur ?? list).map((x) => (x.id === u.id ? { ...x, ...u } : x)))}
              onRemoved={(id) => setItems((cur) => (cur ?? list).filter((x) => x.id !== id))}
            />
          ))}
        </ul>
      ) : null}
    </div>
  );
}
