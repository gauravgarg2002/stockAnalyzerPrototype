import { useRef } from 'react';
import type { KeyboardEvent } from 'react';

export interface SegmentOption<T extends string> {
  value: T;
  label: string;
}

export interface SegmentedControlProps<T extends string> {
  label: string;
  value: T;
  options: ReadonlyArray<SegmentOption<T>>;
  onChange: (value: T) => void;
  className?: string;
}

/** Radio-group style switch with arrow-key navigation. */
export function SegmentedControl<T extends string>({ label, value, options, onChange, className = '' }: SegmentedControlProps<T>) {
  const refs = useRef<Array<HTMLButtonElement | null>>([]);

  function onKeyDown(e: KeyboardEvent<HTMLDivElement>) {
    const idx = options.findIndex((o) => o.value === value);
    let next = idx;
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') next = (idx + 1) % options.length;
    else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') next = (idx - 1 + options.length) % options.length;
    else return;
    e.preventDefault();
    const opt = options[next];
    if (opt) {
      onChange(opt.value);
      refs.current[next]?.focus();
    }
  }

  return (
    <div
      role="radiogroup"
      aria-label={label}
      onKeyDown={onKeyDown}
      className={`inline-flex max-w-full flex-wrap rounded-xl bg-slate-100 p-1 ${className}`}
    >
      {options.map((o, i) => {
        const selected = o.value === value;
        return (
          <button
            key={o.value}
            ref={(el) => {
              refs.current[i] = el;
            }}
            type="button"
            role="radio"
            aria-checked={selected}
            tabIndex={selected ? 0 : -1}
            onClick={() => onChange(o.value)}
            className={`min-h-[40px] rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
              selected ? 'bg-white text-slate-900 shadow-sm ring-1 ring-slate-300' : 'text-slate-700 hover:text-slate-900'
            }`}
          >
            {o.label}
          </button>
        );
      })}
    </div>
  );
}
