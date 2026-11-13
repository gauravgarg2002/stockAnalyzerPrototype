import { Input } from './Input';
import { formatInr, groupTypedAmount, parseMoneyInput } from '../../lib/format';
import { copy, fill } from '../../lib/copy';

export interface MoneyInputProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  hint?: string;
  error?: string | null;
  id?: string;
  className?: string;
  placeholder?: string;
}

/** Rupee amount box: digits only, Indian grouping as you type, and an echo like "₹1.2 lakh". */
export function MoneyInput({ label, value, onChange, hint, error, id, className, placeholder }: MoneyInputProps) {
  const parsed = parseMoneyInput(value);
  const echo = parsed !== null ? fill(copy.common.amountEcho, { amount: formatInr(parsed) }) : hint;
  return (
    <Input
      id={id}
      label={label}
      className={className}
      inputMode="decimal"
      autoComplete="off"
      placeholder={placeholder ?? copy.common.amountPlaceholder}
      value={value}
      onChange={(e) => onChange(groupTypedAmount(e.target.value))}
      hint={echo}
      error={error}
    />
  );
}
