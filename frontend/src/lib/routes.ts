// Path builders and route patterns shared by links and the router.

import type { Kind } from './api-types';

export const ROUTES = {
  home: '/',
  connect: '/connect',
  portfolio: '/portfolio',
  compare: '/compare',
  watchlist: '/watchlist',
  tryIt: '/try',
  tryItKind: '/try/:kind/:id',
  stock: '/stock/:symbol',
  fund: '/fund/:code',
} as const;

export const stockPath = (symbol: string): string => `/stock/${encodeURIComponent(symbol)}`;

export const fundPath = (code: string): string => `/fund/${encodeURIComponent(code)}`;

export const checkPath = (kind: Kind, id: string): string =>
  kind === 'STOCK' ? stockPath(id) : fundPath(id);

export const tryPath = (kind?: Kind, id?: string): string =>
  kind && id ? `/try/${kind.toLowerCase()}/${encodeURIComponent(id)}` : '/try';

export function comparePath(kind: Kind, ids: string[], amountInr?: number | null): string {
  const params = [`kind=${kind}`];
  if (ids.length > 0) params.push(`ids=${ids.map(encodeURIComponent).join(',')}`);
  if (kind === 'FUND' && amountInr) params.push(`amount=${amountInr}`);
  return `/compare?${params.join('&')}`;
}

/** Accepts "stock" / "FUND" in any case. */
export function parseKind(value: string | null | undefined): Kind | null {
  const v = (value ?? '').toUpperCase();
  return v === 'STOCK' || v === 'FUND' ? v : null;
}

/** Split "A,B,C" from a query string into trimmed, non-empty ids (max 3). */
export function parseIds(value: string | null | undefined): string[] {
  return (value ?? '')
    .split(',')
    .map((s) => s.trim())
    .filter((s) => s.length > 0)
    .slice(0, 3);
}
