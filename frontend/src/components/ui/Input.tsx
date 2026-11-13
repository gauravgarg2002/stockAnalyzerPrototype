import { forwardRef, useId } from 'react';
import type { InputHTMLAttributes, TextareaHTMLAttributes } from 'react';

const FIELD =
  'block w-full rounded-lg border border-slate-400 bg-white px-3 py-2 text-base text-slate-900 placeholder:text-slate-500 focus:border-indigo-700 disabled:bg-slate-100';

export interface InputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'id'> {
  label: string;
  hint?: string;
  error?: string | null;
  hideLabel?: boolean;
  id?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { label, hint, error, hideLabel = false, id, className = '', ...rest },
  ref,
) {
  const auto = useId();
  const inputId = id ?? auto;
  const hintId = `${inputId}-hint`;
  const errorId = `${inputId}-error`;
  const describedBy = [hint ? hintId : null, error ? errorId : null].filter(Boolean).join(' ') || undefined;
  return (
    <div className={className}>
      <label htmlFor={inputId} className={hideLabel ? 'sr-only' : 'mb-1 block text-sm font-medium text-slate-800'}>
        {label}
      </label>
      <input
        ref={ref}
        id={inputId}
        aria-describedby={describedBy}
        aria-invalid={error ? true : undefined}
        className={FIELD}
        {...rest}
      />
      {hint ? (
        <p id={hintId} className="mt-1 text-sm text-slate-600">
          {hint}
        </p>
      ) : null}
      {error ? (
        <p id={errorId} className="mt-1 text-sm font-medium text-slate-900">
          {error}
        </p>
      ) : null}
    </div>
  );
});

export interface TextAreaProps extends Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, 'id'> {
  label: string;
  hint?: string;
  id?: string;
  counter?: string;
}

export function TextArea({ label, hint, id, counter, className = '', ...rest }: TextAreaProps) {
  const auto = useId();
  const areaId = id ?? auto;
  const hintId = `${areaId}-hint`;
  return (
    <div className={className}>
      <label htmlFor={areaId} className="mb-1 block text-sm font-medium text-slate-800">
        {label}
      </label>
      <textarea id={areaId} aria-describedby={hint ? hintId : undefined} className={FIELD} rows={3} {...rest} />
      <div className="mt-1 flex justify-between gap-3 text-sm text-slate-600">
        {hint ? <p id={hintId}>{hint}</p> : <span />}
        {counter ? <p aria-hidden="true">{counter}</p> : null}
      </div>
    </div>
  );
}
