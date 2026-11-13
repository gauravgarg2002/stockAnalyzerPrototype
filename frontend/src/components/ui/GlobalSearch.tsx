import { useEffect, useId, useRef, useState } from 'react';
import type { CSSProperties } from 'react';
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
  /** 'dark' sits on the peacock-ink header or hero. */
  tone?: 'light' | 'dark';
  /** Pressing "/" anywhere focuses this box. Give it to one box per screen. */
  shortcut?: boolean;
  /** Cycle through example searches in the empty box. */
  examples?: boolean;
}

/** Cycles the placeholder through example searches while the box is empty and not focused. */
function useRotatingPlaceholder(enabled: boolean, paused: boolean): string | null {
  const [i, setI] = useState(0);
  useEffect(() => {
    if (!enabled || paused) return undefined;
    const t = window.setInterval(() => setI((n) => (n + 1) % copy.search.examples.length), 2600);
    return () => window.clearInterval(t);
  }, [enabled, paused]);
  return enabled ? `${copy.search.tryPrefix}“${copy.search.examples[i]}”` : null;
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
  tone = 'light',
  shortcut = false,
  examples = false,
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
  const inputRef = useRef<HTMLInputElement>(null);
  const [focused, setFocused] = useState(false);
  const rotating = useRotatingPlaceholder(examples, focused || text !== '');

  useEffect(() => {
    if (!shortcut) return undefined;
    function onKey(e: globalThis.KeyboardEvent) {
      if (e.key !== '/' || e.metaKey || e.ctrlKey || e.altKey) return;
      const t = e.target as HTMLElement | null;
      if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return;
      e.preventDefault();
      inputRef.current?.focus();
    }
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [shortcut]);

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
  const dark = tone === 'dark';
  return (
    <div ref={wrapRef} className={`relative ${className}`}>
      <label htmlFor={inputId} className={hideLabel ? 'sr-only' : 'mb-1 block text-sm font-medium text-slate-800'}>
        {label}
      </label>
      <div className="relative">
        <svg
          className={`pointer-events-none absolute top-1/2 -translate-y-1/2 transition-colors ${big ? 'left-4 h-6 w-6' : 'left-3 h-5 w-5'} ${
            dark && !focused ? 'text-lagoon-200' : 'text-peacock-700'
          }`}
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
          ref={inputRef}
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
          placeholder={rotating ?? placeholder ?? copy.search.placeholder}
          value={text}
          onChange={(e) => {
            setText(e.target.value);
            setOpen(true);
          }}
          onFocus={() => {
            setOpen(true);
            setFocused(true);
          }}
          onBlur={() => {
            setOpen(false);
            setFocused(false);
          }}
          onKeyDown={onKeyDown}
          className={`block w-full rounded-2xl border-2 pr-14 transition-[background-color,border-color,box-shadow] duration-200 focus:outline-none ${
            big ? 'min-h-[64px] pl-14 text-xl font-medium shadow-lift' : 'min-h-[44px] pl-10 text-base'
          } ${
            dark
              ? 'border-white/15 bg-white/10 text-white placeholder:text-lagoon-200/80 hover:bg-white/15 focus:border-marigold-400 focus:bg-white focus:text-peacock-950 focus:placeholder:text-slate-500'
              : 'border-slate-300 bg-white text-peacock-950 placeholder:text-slate-500 hover:border-peacock-400 focus:border-marigold-400 focus:shadow-lens'
          }`}
        />
        {shortcut && !focused && text === '' ? (
          <kbd
            aria-hidden="true"
            title={copy.search.shortcutHint}
            className={`pointer-events-none absolute right-3 top-1/2 hidden -translate-y-1/2 rounded-md border px-2 py-0.5 font-sans text-xs font-semibold sm:block ${
              dark ? 'border-white/20 text-lagoon-200' : 'border-slate-300 text-slate-500'
            }`}
          >
            /
          </kbd>
        ) : null}
      </div>
      <div role="status" aria-live="polite" className="sr-only">
        {statusText}
      </div>
      {showPopup ? (
        <div className="absolute left-0 right-0 z-40 mt-2 max-h-96 animate-pop overflow-auto rounded-2xl border border-slate-200 bg-white p-1.5 text-left shadow-lift">
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
                  style={{ animationDelay: `${i * 35}ms` } as CSSProperties}
                  className={`flex animate-rise cursor-pointer items-center justify-between gap-3 rounded-xl px-3.5 py-3 transition-colors ${
                    i === active ? 'bg-lagoon-100' : ''
                  }`}
                >
                  <span
                    aria-hidden="true"
                    className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl font-display text-sm font-extrabold ${
                      r.kind === 'STOCK' ? 'bg-peacock-900 text-marigold-400' : 'bg-marigold-400 text-peacock-900'
                    }`}
                  >
                    {r.name.replace(/^the\s+/i, '').slice(0, 1).toUpperCase()}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate font-semibold text-peacock-950">{r.name}</span>
                    <span className="block truncate text-sm text-slate-600">{r.subtitle}</span>
                  </span>
                  <Badge>{r.kind === 'STOCK' ? copy.search.stockTag : copy.search.fundTag}</Badge>
                </li>
              ))}
            </ul>
          ) : (
            <p id={listId} className="px-3.5 py-3 text-sm text-slate-700">
              {statusText}
            </p>
          )}
        </div>
      ) : null}
    </div>
  );
}

/** Header / home search: choosing a result opens its check page. */
export function GlobalSearch({
  size = 'md',
  className = '',
  autoFocus = false,
  tone = 'light',
  shortcut = false,
  examples = false,
}: {
  size?: 'md' | 'lg';
  className?: string;
  autoFocus?: boolean;
  tone?: 'light' | 'dark';
  shortcut?: boolean;
  examples?: boolean;
}) {
  const navigate = useNavigate();
  return (
    <SearchCombobox
      label={copy.search.label}
      size={size}
      className={className}
      autoFocus={autoFocus}
      tone={tone}
      shortcut={shortcut}
      examples={examples}
      hideLabel
      onSelect={(r) => navigate(r.checkPath)}
    />
  );
}
