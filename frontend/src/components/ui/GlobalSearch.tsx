import { useEffect, useId, useRef, useState } from 'react';
import type { KeyboardEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { searchInstruments } from '../../lib/api-client';
import type { Kind, SearchResult } from '../../lib/api-types';
import { copy, fill } from '../../lib/copy';
import { useDebounce } from '../../hooks/useDebounce';
import { Badge } from './Badge';

export interface SearchComboboxProps {
  label: string;
  placeholder?: string;
  onSelect: (result: SearchResult) => void;
  size?: 'md' | 'lg';
  /** Only offer stocks or only funds. */
  kind?: Kind;
  hideLabel?: boolean;
  clearOnSelect?: boolean;
  className?: string;
  autoFocus?: boolean;
}

/** Combobox: type to search, arrow keys to move, Enter to choose, Esc to close. */
export function SearchCombobox({
  label,
  placeholder,
  onSelect,
  size = 'md',
  kind,
  hideLabel = true,
  clearOnSelect = true,
  className = '',
  autoFocus = false,
}: SearchComboboxProps) {
  const uid = useId();
  const inputId = `${uid}-input`;
  const listId = `${uid}-list`;
  const [text, setText] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const [loading, setLoading] = useState(false);
  const [failed, setFailed] = useState(false);
  const debounced = useDebounce(text.trim(), 200);
  const wrapRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (debounced === '') {
      setResults([]);
      setLoading(false);
      setFailed(false);
      return undefined;
    }
    const controller = new AbortController();
    setLoading(true);
    setFailed(false);
    searchInstruments(debounced, { signal: controller.signal })
      .then((r) => {
        const list = kind ? r.results.filter((x) => x.kind === kind) : r.results;
        setResults(list);
        setActive(list.length > 0 ? 0 : -1);
        setLoading(false);
      })
      .catch((e: unknown) => {
        if (e instanceof Error && e.name === 'AbortError') return;
        setResults([]);
        setFailed(true);
        setLoading(false);
      });
    return () => controller.abort();
  }, [debounced, kind]);

  function choose(r: SearchResult) {
    onSelect(r);
    setOpen(false);
    setActive(-1);
    if (clearOnSelect) {
      setText('');
      setResults([]);
    } else {
      setText(r.name);
    }
  }

  function onKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (!open) setOpen(true);
      if (results.length > 0) setActive((a) => (a + 1) % results.length);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (!open) setOpen(true);
      if (results.length > 0) setActive((a) => (a <= 0 ? results.length - 1 : a - 1));
    } else if (e.key === 'Enter') {
      const r = results[active];
      if (open && r) {
        e.preventDefault();
        choose(r);
      }
    } else if (e.key === 'Escape') {
      if (open) {
        e.preventDefault();
        setOpen(false);
      } else if (text !== '') {
        setText('');
      }
    }
  }

  const q = text.trim();
  const showPopup = open && q !== '';
  const settled = debounced === q && !loading;
  const statusText = !showPopup
    ? ''
    : loading || !settled
      ? copy.search.searching
      : failed
        ? copy.search.error
        : results.length === 0
          ? fill(copy.search.noResults, { q })
          : fill(copy.search.count, { n: String(results.length) });

  const big = size === 'lg';
  return (
    <div ref={wrapRef} className={`relative ${className}`}>
      <label htmlFor={inputId} className={hideLabel ? 'sr-only' : 'mb-1 block text-sm font-medium text-slate-800'}>
        {label}
      </label>
      <div className="relative">
        <svg
          className={`pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-600 ${big ? 'h-6 w-6' : 'h-5 w-5'}`}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          aria-hidden="true"
        >
          <circle cx="11" cy="11" r="7" />
          <path d="M20 20l-3.5-3.5" />
        </svg>
        <input
          id={inputId}
          type="text"
          role="combobox"
          aria-expanded={showPopup && results.length > 0}
          aria-controls={listId}
          aria-autocomplete="list"
          aria-activedescendant={showPopup && active >= 0 && results[active] ? `${uid}-opt-${active}` : undefined}
          autoComplete="off"
          spellCheck={false}
          autoFocus={autoFocus}
          placeholder={placeholder ?? copy.search.placeholder}
          value={text}
          onChange={(e) => {
            setText(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onBlur={() => setOpen(false)}
          onKeyDown={onKeyDown}
          className={`block w-full rounded-xl border border-slate-400 bg-white pl-10 pr-3 text-slate-900 placeholder:text-slate-600 focus:border-indigo-700 ${
            big ? 'min-h-[56px] text-lg shadow-sm sm:pl-12' : 'min-h-[44px] text-base'
          }`}
        />
      </div>
      <div role="status" aria-live="polite" className="sr-only">
        {statusText}
      </div>
      {showPopup ? (
        <div className="absolute left-0 right-0 z-40 mt-2 max-h-80 overflow-auto rounded-xl border border-slate-200 bg-white shadow-lg">
          {results.length > 0 ? (
            <ul id={listId} role="listbox" aria-label={label}>
              {results.map((r, i) => (
                <li
                  key={`${r.kind}-${r.id}`}
                  id={`${uid}-opt-${i}`}
                  role="option"
                  aria-selected={i === active}
                  onMouseDown={(e) => e.preventDefault()}
                  onMouseEnter={() => setActive(i)}
                  onClick={() => choose(r)}
                  className={`flex cursor-pointer items-center justify-between gap-3 px-4 py-3 ${
                    i === active ? 'bg-indigo-50' : ''
                  }`}
                >
                  <span className="min-w-0">
                    <span className="block truncate font-medium text-slate-900">{r.name}</span>
                    <span className="block truncate text-sm text-slate-600">{r.subtitle}</span>
                  </span>
                  <Badge>{r.kind === 'STOCK' ? copy.search.stockTag : copy.search.fundTag}</Badge>
                </li>
              ))}
            </ul>
          ) : (
            <p id={listId} className="px-4 py-3 text-sm text-slate-700">
              {statusText}
            </p>
          )}
        </div>
      ) : null}
    </div>
  );
}

/** Header / home search: choosing a result opens its check page. */
export function GlobalSearch({ size = 'md', className = '', autoFocus = false }: { size?: 'md' | 'lg'; className?: string; autoFocus?: boolean }) {
  const navigate = useNavigate();
  return (
    <SearchCombobox
      label={copy.search.label}
      size={size}
      className={className}
      autoFocus={autoFocus}
      hideLabel
      onSelect={(r) => navigate(r.checkPath)}
    />
  );
}
