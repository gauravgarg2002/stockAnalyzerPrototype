// Indian number formatting, matching docs/api-contract.md §0.4 exactly.
// Rounding is HALF_UP on the shortest decimal string of the double (String(x)),
// done with BigInt so no binary floating point error creeps in.

import type { Unit } from './api-types';

export const NOT_AVAILABLE = 'Not available';

/** Expand String(|x|) (which may use exponent notation) to a plain decimal string. */
export function plainDecimal(absX: number): string {
  const s = String(absX);
  const m = /^(\d+)(?:\.(\d+))?e([+-]\d+)$/i.exec(s);
  if (!m) return s;
  const intPart = m[1] ?? '0';
  const fracPart = m[2] ?? '';
  const exp = Number(m[3]);
  const digits = intPart + fracPart;
  const point = intPart.length + exp;
  if (point <= 0) return '0.' + '0'.repeat(-point) + digits;
  if (point >= digits.length) return digits + '0'.repeat(point - digits.length);
  return digits.slice(0, point) + '.' + digits.slice(point);
}

/** |x| scaled by 10^dp and rounded HALF_UP, as a BigInt. */
function scaledRounded(absX: number, dp: number): bigint {
  const s = plainDecimal(absX);
  const dot = s.indexOf('.');
  const intPart = dot === -1 ? s : s.slice(0, dot);
  const fracPart = dot === -1 ? '' : s.slice(dot + 1);
  const frac = fracPart.padEnd(dp + 1, '0');
  let n = BigInt(intPart + frac.slice(0, dp));
  if (frac.charCodeAt(dp) >= 53) n += 1n; // digit '5' or above
  return n;
}

/** Insert the decimal point into a scaled integer. */
function withPoint(n: bigint, dp: number): string {
  if (dp === 0) return n.toString();
  const s = n.toString().padStart(dp + 1, '0');
  return s.slice(0, -dp) + '.' + s.slice(-dp);
}

/** Indian digit grouping of an unsigned integer string: 1234567 -> 12,34,567. */
export function groupIndian(intStr: string): string {
  if (intStr.length <= 3) return intStr;
  const last3 = intStr.slice(-3);
  let rest = intStr.slice(0, -3);
  const parts: string[] = [];
  while (rest.length > 2) {
    parts.unshift(rest.slice(-2));
    rest = rest.slice(0, -2);
  }
  if (rest.length > 0) parts.unshift(rest);
  return parts.join(',') + ',' + last3;
}

function isNum(x: unknown): x is number {
  return typeof x === 'number' && Number.isFinite(x);
}

/** Tenths as text, dropping a trailing ".0": 125n -> "12.5", 120n -> "12". */
function tenthsText(tenths: bigint): string {
  const whole = tenths / 10n;
  const frac = tenths % 10n;
  return frac === 0n ? whole.toString() : `${whole}.${frac}`;
}

export function formatInr(x: number | null | undefined): string {
  if (!isNum(x)) return NOT_AVAILABLE;
  const r = scaledRounded(Math.abs(x), 0);
  const sign = x < 0 && r !== 0n ? '-' : '';
  if (r < 100000n) return `${sign}₹${groupIndian(r.toString())}`;
  const lakhTenths = (r + 5000n) / 10000n;
  if (lakhTenths < 1000n) return `${sign}₹${tenthsText(lakhTenths)} lakh`;
  const croreTenths = (r + 500000n) / 1000000n;
  if (croreTenths < 10000n) return `${sign}₹${tenthsText(croreTenths)} crore`;
  const crore = (r + 5000000n) / 10000000n;
  return `${sign}₹${groupIndian(crore.toString())} crore`;
}

export function formatPrice(x: number | null | undefined): string {
  if (!isNum(x)) return NOT_AVAILABLE;
  const n = scaledRounded(Math.abs(x), 2);
  const [i = '0', f = '00'] = withPoint(n, 2).split('.');
  const sign = x < 0 && n !== 0n ? '-' : '';
  return `${sign}₹${groupIndian(i)}.${f}`;
}

export function formatPct(x: number | null | undefined): string {
  if (!isNum(x)) return NOT_AVAILABLE;
  const n = scaledRounded(Math.abs(x), 1);
  return `${x < 0 && n !== 0n ? '-' : ''}${withPoint(n, 1)}%`;
}

export function formatPctChange(x: number | null | undefined): string {
  if (!isNum(x)) return NOT_AVAILABLE;
  const n = scaledRounded(Math.abs(x), 1);
  const sign = n === 0n ? '' : x < 0 ? '-' : '+';
  return `${sign}${withPoint(n, 1)}%`;
}

export function formatTimes(x: number | null | undefined): string {
  if (!isNum(x)) return NOT_AVAILABLE;
  const n = scaledRounded(Math.abs(x), 1);
  return `${x < 0 && n !== 0n ? '-' : ''}${withPoint(n, 1)}x`;
}

export function formatCount(x: number | null | undefined): string {
  if (!isNum(x)) return NOT_AVAILABLE;
  const n = scaledRounded(Math.abs(x), 0);
  return `${x < 0 && n !== 0n ? '-' : ''}${groupIndian(n.toString())}`;
}

function formatDuration(x: number | null | undefined, one: string, many: string): string {
  if (!isNum(x)) return NOT_AVAILABLE;
  const n = scaledRounded(Math.abs(x), 1);
  const text = tenthsText(n);
  const sign = x < 0 && n !== 0n ? '-' : '';
  return `${sign}${text} ${text === '1' ? one : many}`;
}

export const formatYears = (x: number | null | undefined): string => formatDuration(x, 'year', 'years');
export const formatMonths = (x: number | null | undefined): string => formatDuration(x, 'month', 'months');
export const formatDays = (x: number | null | undefined): string => formatDuration(x, 'day', 'days');

/** Format by contract unit. TEXT passes strings through. Null gives "Not available". */
export function formatValue(unit: Unit, value: number | string | null | undefined): string {
  if (value === null || value === undefined) return NOT_AVAILABLE;
  if (unit === 'TEXT') return String(value);
  if (typeof value !== 'number') return String(value);
  switch (unit) {
    case 'INR':
      return formatInr(value);
    case 'INR_PRICE':
      return formatPrice(value);
    case 'PCT':
      return formatPct(value);
    case 'PCT_CHANGE':
      return formatPctChange(value);
    case 'TIMES':
      return formatTimes(value);
    case 'YEARS':
      return formatYears(value);
    case 'MONTHS':
      return formatMonths(value);
    case 'DAYS':
      return formatDays(value);
    case 'COUNT':
      return formatCount(value);
  }
}

/** Compact axis label for chart ticks, e.g. 12500 -> "12.5k". Display only. */
export function formatAxisNumber(x: number): string {
  if (!Number.isFinite(x)) return '';
  const a = Math.abs(x);
  if (a >= 1e7) return `${trimZero((x / 1e7).toFixed(1))}Cr`;
  if (a >= 1e5) return `${trimZero((x / 1e5).toFixed(1))}L`;
  if (a >= 1e3) return `${trimZero((x / 1e3).toFixed(1))}k`;
  return trimZero(x.toFixed(a < 10 ? 2 : 0));
}

function trimZero(s: string): string {
  return s.includes('.') ? s.replace(/\.?0+$/, '') : s;
}

/**
 * Parse what a person types into an amount box: "1,50,000", "₹ 25000", "2500.50".
 * Returns null for empty, non-numeric or non-positive input.
 */
export function parseMoneyInput(text: string): number | null {
  const cleaned = text.replace(/[₹,\s]/g, '');
  if (cleaned === '' || !/^\d*\.?\d+$|^\d+\.$/.test(cleaned)) return null;
  const n = Number(cleaned);
  return Number.isFinite(n) && n > 0 ? n : null;
}

/** Insert Indian grouping into the digits a person is typing, keeping any decimal part. */
export function groupTypedAmount(text: string): string {
  const cleaned = text.replace(/[^\d.]/g, '');
  const dot = cleaned.indexOf('.');
  const intPart = (dot === -1 ? cleaned : cleaned.slice(0, dot)).replace(/^0+(?=\d)/, '');
  const frac = dot === -1 ? '' : '.' + cleaned.slice(dot + 1).replace(/\./g, '').slice(0, 2);
  return groupIndian(intPart) + frac;
}

/** Share counts and fund units: whole numbers get grouping, fractions keep up to 3 decimals. */
export function formatQuantity(x: number | null | undefined): string {
  if (!isNum(x)) return NOT_AVAILABLE;
  const n = scaledRounded(Math.abs(x), 3);
  const [i = '0', f = '000'] = withPoint(n, 3).split('.');
  const frac = f.replace(/0+$/, '');
  const sign = x < 0 && n !== 0n ? '-' : '';
  return `${sign}${groupIndian(i)}${frac ? '.' + frac : ''}`;
}
