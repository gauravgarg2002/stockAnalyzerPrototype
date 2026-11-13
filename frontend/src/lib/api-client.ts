// Thin fetch wrapper plus one function per public endpoint (docs/api-contract.md §A).
// Dependency-free: only the platform `fetch` / `FormData` are used.

import type {
  ActivityResponse,
  ApiErrorBody,
  ApiErrorCode,
  ClientErrorCode,
  CompareResponse,
  ConnectionResponse,
  ExplainResponse,
  FundCheckResponse,
  GlossaryResponse,
  HoldingCreated,
  HoldingsResponse,
  HomeResponse,
  ImportResponse,
  Kind,
  KiteDisconnectResponse,
  KiteStartResponse,
  KiteStatusResponse,
  ManualHoldingRequest,
  MetaResponse,
  PortfolioResponse,
  QuoteResponse,
  SearchResponse,
  StockCheckResponse,
  TryItOnRequest,
  TryItOnResponse,
  WatchlistAddRequest,
  WatchlistItemResponse,
  WatchlistResponse,
} from './api-types';

export class ApiError extends Error {
  readonly code: ApiErrorCode | ClientErrorCode;
  readonly status: number;
  readonly details: Record<string, unknown> | null;

  constructor(
    code: ApiErrorCode | ClientErrorCode,
    status: number,
    message: string,
    details: Record<string, unknown> | null = null,
  ) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

type FetchFn = (input: string, init?: RequestInit) => Promise<Response>;

let apiBase = '/api';
let fetchImpl: FetchFn | null = null;

/** Override the base path (default "/api"). */
export function setApiBase(base: string): void {
  apiBase = base.replace(/\/+$/, '');
}

/** Override fetch (tests). Pass null to restore the platform fetch. */
export function setFetch(fn: FetchFn | null): void {
  fetchImpl = fn;
}

export interface RequestOptions {
  signal?: AbortSignal;
}

function isAbort(e: unknown): boolean {
  return typeof e === 'object' && e !== null && (e as { name?: string }).name === 'AbortError';
}

/** Turn an error response into an ApiError, using the contract error body when present. */
export async function parseError(res: Response): Promise<ApiError> {
  let body: unknown = null;
  try {
    body = await res.json();
  } catch {
    body = null;
  }
  const err = (body as Partial<ApiErrorBody> | null)?.error;
  if (err && typeof err.code === 'string' && typeof err.message === 'string') {
    return new ApiError(err.code, res.status, err.message, err.details ?? null);
  }
  const code: ApiErrorCode =
    res.status === 404 ? 'NOT_FOUND' : res.status >= 500 ? (res.status === 502 ? 'UPSTREAM_UNAVAILABLE' : 'INTERNAL') : 'BAD_REQUEST';
  return new ApiError(code, res.status, res.statusText || 'Request failed');
}

async function send<T>(method: string, path: string, init: RequestInit, opts?: RequestOptions): Promise<T> {
  const doFetch: FetchFn = fetchImpl ?? ((input, i) => fetch(input, i));
  let res: Response;
  try {
    res = await doFetch(`${apiBase}${path}`, { ...init, method, signal: opts?.signal });
  } catch (e) {
    if (isAbort(e)) throw e;
    throw new ApiError('NETWORK_ERROR', 0, 'Could not reach the server.');
  }
  if (!res.ok) throw await parseError(res);
  if (res.status === 204) return undefined as T;
  try {
    return (await res.json()) as T;
  } catch {
    throw new ApiError('INVALID_RESPONSE', res.status, 'The server sent a reply that could not be read.');
  }
}

const JSON_HEADERS = { 'Content-Type': 'application/json', Accept: 'application/json' };
const ACCEPT = { Accept: 'application/json' };

export const get = <T>(path: string, opts?: RequestOptions): Promise<T> =>
  send<T>('GET', path, { headers: ACCEPT }, opts);

export const post = <T>(path: string, body?: unknown, opts?: RequestOptions): Promise<T> =>
  send<T>('POST', path, body === undefined ? { headers: ACCEPT } : { headers: JSON_HEADERS, body: JSON.stringify(body) }, opts);

export const patch = <T>(path: string, body: unknown, opts?: RequestOptions): Promise<T> =>
  send<T>('PATCH', path, { headers: JSON_HEADERS, body: JSON.stringify(body) }, opts);

export const del = <T = void>(path: string, opts?: RequestOptions): Promise<T> =>
  send<T>('DELETE', path, { headers: ACCEPT }, opts);

function query(params: Record<string, string | number | null | undefined>): string {
  const parts: string[] = [];
  for (const [k, v] of Object.entries(params)) {
    if (v === null || v === undefined || v === '') continue;
    parts.push(`${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`);
  }
  return parts.length > 0 ? `?${parts.join('&')}` : '';
}

// --------------------------------------------------------------- endpoints

export const getMeta = (o?: RequestOptions) => get<MetaResponse>('/meta', o);
export const getHome = (o?: RequestOptions) => get<HomeResponse>('/home', o);
export const getPortfolio = (o?: RequestOptions) => get<PortfolioResponse>('/portfolio', o);

export const searchInstruments = (q: string, o?: RequestOptions) =>
  get<SearchResponse>(`/search${query({ q: q.trim() })}`, o);

export const getQuote = (symbol: string, o?: RequestOptions) =>
  get<QuoteResponse>(`/stocks/${encodeURIComponent(symbol)}/quote`, o);

export const getActivity = (o?: RequestOptions) => get<ActivityResponse>('/account/activity', o);

export const getStockCheck = (symbol: string, o?: RequestOptions) =>
  get<StockCheckResponse>(`/stocks/${encodeURIComponent(symbol)}/check`, o);

export const getFundCheck = (schemeCode: string, amountInr?: number | null, o?: RequestOptions) =>
  get<FundCheckResponse>(`/funds/${encodeURIComponent(schemeCode)}/check${query({ amount: amountInr })}`, o);

export const getCompare = (kind: Kind, ids: string[], amountInr?: number | null, o?: RequestOptions) =>
  get<CompareResponse>(
    `/compare${query({ kind, ids: ids.join(','), amount: kind === 'FUND' ? amountInr : null })}`,
    o,
  );

export const postTryItOn = (req: TryItOnRequest, o?: RequestOptions) =>
  post<TryItOnResponse>('/try-it-on', req, o);

export const getGlossary = (o?: RequestOptions) => get<GlossaryResponse>('/glossary', o);

export const getExplain = (termId: string, kind?: Kind | null, id?: string | null, o?: RequestOptions) =>
  get<ExplainResponse>(`/explain${query({ term: termId, kind: kind && id ? kind : null, id: kind && id ? id : null })}`, o);

export const getWatchlist = (o?: RequestOptions) => get<WatchlistResponse>('/watchlist', o);
export const addWatchlistItem = (req: WatchlistAddRequest, o?: RequestOptions) =>
  post<WatchlistItemResponse>('/watchlist', req, o);
export const updateWatchlistNote = (id: number, note: string, o?: RequestOptions) =>
  patch<WatchlistItemResponse>(`/watchlist/${id}`, { note }, o);
export const deleteWatchlistItem = (id: number, o?: RequestOptions) => del(`/watchlist/${id}`, o);

export const getConnection = (o?: RequestOptions) => get<ConnectionResponse>('/connection', o);
export const startKiteConnect = (o?: RequestOptions) => post<KiteStartResponse>('/connect/kite/start', undefined, o);
export const getKiteStatus = (o?: RequestOptions) => get<KiteStatusResponse>('/connect/kite/status', o);
export const disconnectKite = (o?: RequestOptions) =>
  post<KiteDisconnectResponse>('/connect/kite/disconnect', undefined, o);

export const importKite = (o?: RequestOptions) => post<ImportResponse>('/import/kite', undefined, o);

export function importStatement(file: Blob, password: string, filename?: string, o?: RequestOptions): Promise<ImportResponse> {
  const form = new FormData();
  if (filename) form.append('file', file, filename);
  else form.append('file', file);
  form.append('password', password);
  // No Content-Type header: the browser sets the multipart boundary.
  return send<ImportResponse>('POST', '/import/statement', { headers: ACCEPT, body: form }, o);
}

export const getHoldings = (o?: RequestOptions) => get<HoldingsResponse>('/holdings', o);
export const addHolding = (req: ManualHoldingRequest, o?: RequestOptions) => post<HoldingCreated>('/holdings', req, o);
export const deleteHolding = (id: number, o?: RequestOptions) => del(`/holdings/${id}`, o);
