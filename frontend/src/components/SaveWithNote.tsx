import { useState } from 'react';
import { Link } from 'react-router-dom';
import { addWatchlistItem } from '../lib/api-client';
import type { Kind } from '../lib/api-types';
import { copy, fill } from '../lib/copy';
import { ROUTES } from '../lib/routes';
import { Button } from './ui/Button';
import { TextArea } from './ui/Input';
import { errorMessage } from './ui/ErrorState';

const MAX_NOTE = 1000;

export interface SaveWithNoteProps {
  kind: Kind;
  instrumentId: string;
  name: string;
  watchlistItemId: number | null;
  existingNote: string | null;
}

/** "Save with a note": adds the item to the watchlist with the reason the person gives. */
export function SaveWithNote({ kind, instrumentId, name, watchlistItemId, existingNote }: SaveWithNoteProps) {
  const [open, setOpen] = useState(false);
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const alreadySaved = watchlistItemId !== null || saved;

  async function save() {
    setBusy(true);
    setError(null);
    try {
      await addWatchlistItem({ kind, instrumentId, note: note.trim() });
      setSaved(true);
      setOpen(false);
    } catch (e) {
      setError(errorMessage(e instanceof Error ? e : null));
    } finally {
      setBusy(false);
    }
  }

  if (alreadySaved) {
    const shownNote = saved ? note.trim() : existingNote;
    return (
      <div role="status" className="rounded-xl border border-slate-200 bg-white p-3 text-sm text-slate-700">
        <p className="font-medium text-slate-900">{copy.save.saved}</p>
        {shownNote ? <p className="mt-0.5">“{shownNote}”</p> : null}
        <Link to={ROUTES.watchlist} className="mt-1 inline-block font-medium text-indigo-700 underline underline-offset-2">
          {copy.save.viewWatchlist}
        </Link>
      </div>
    );
  }

  return (
    <div>
      <Button variant="secondary" aria-expanded={open} onClick={() => setOpen((o) => !o)}>
        {copy.save.button}
      </Button>
      {open ? (
        <form
          className="mt-3 w-full max-w-md rounded-xl border border-slate-200 bg-white p-4 text-left"
          onSubmit={(e) => {
            e.preventDefault();
            void save();
          }}
        >
          <TextArea
            label={fill(copy.save.label, { name })}
            hint={copy.save.hint}
            value={note}
            maxLength={MAX_NOTE}
            counter={`${note.length}/${MAX_NOTE}`}
            onChange={(e) => setNote(e.target.value)}
            placeholder={copy.save.placeholder}
          />
          {error ? (
            <p role="alert" className="mt-2 text-sm font-medium text-slate-900">
              {error}
            </p>
          ) : null}
          <div className="mt-3 flex gap-3">
            <Button type="submit" busy={busy}>
              {copy.save.submit}
            </Button>
            <Button variant="ghost" onClick={() => setOpen(false)}>
              {copy.common.cancel}
            </Button>
          </div>
        </form>
      ) : null}
    </div>
  );
}
