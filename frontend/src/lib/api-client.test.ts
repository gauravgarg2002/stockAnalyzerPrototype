import test from 'node:test';
import assert from 'node:assert/strict';
import {
  ApiError,
  addHolding,
  deleteWatchlistItem,
  getCompare,
  getExplain,
  getFundCheck,
  getHome,
  importStatement,
  postTryItOn,
  searchInstruments,
  setApiBase,
  setFetch,
  updateWatchlistNote,
} from './api-client';

interface Call {
  url: string;
  init: RequestInit | undefined;
}

function fake(status: number, body: unknown): { calls: Call[] } {
  const calls: Call[] = [];
  setFetch(async (input, init) => {
    calls.push({ url: input, init });
    return new Response(body === undefined ? null : JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' },
    });
  });
  return { calls };
}

test.afterEach(() => {
  setFetch(null);
  setApiBase('/api');
});

test('GET builds the contract URLs', async () => {
  const f = fake(200, { ok: true });
  await getHome();
  await searchInstruments('  tata ');
  await getFundCheck('900101');
  await getFundCheck('900101', 115448);
  await getCompare('FUND', ['900101', '900201'], 100000);
  await getCompare('STOCK', ['TCS', 'INFY'], 100000);
  await getExplain('pe_ratio', 'STOCK', 'TCS');
  await getExplain('pe_ratio');
  assert.deepEqual(
    f.calls.map((c) => c.url),
    [
      '/api/home',
      '/api/search?q=tata',
      '/api/funds/900101/check',
      '/api/funds/900101/check?amount=115448',
      '/api/compare?kind=FUND&ids=900101%2C900201&amount=100000',
      '/api/compare?kind=STOCK&ids=TCS%2CINFY',
      '/api/explain?term=pe_ratio&kind=STOCK&id=TCS',
      '/api/explain?term=pe_ratio',
    ],
  );
  assert.equal(f.calls[0]?.init?.method, 'GET');
});

test('POST and PATCH send JSON bodies', async () => {
  const f = fake(200, {});
  await postTryItOn({ kind: 'FUND', id: '900701', mode: 'SIP', amountInr: 5000, months: 12 });
  await updateWatchlistNote(3, 'why');
  await addHolding({ kind: 'FUND', instrumentId: '900401', quantity: 120.5, avgPrice: 88.1, firstBuyDate: null });
  assert.equal(f.calls[0]?.url, '/api/try-it-on');
  assert.equal(f.calls[0]?.init?.method, 'POST');
  assert.deepEqual(JSON.parse(String(f.calls[0]?.init?.body)), { kind: 'FUND', id: '900701', mode: 'SIP', amountInr: 5000, months: 12 });
  assert.equal(f.calls[1]?.url, '/api/watchlist/3');
  assert.equal(f.calls[1]?.init?.method, 'PATCH');
  assert.deepEqual(JSON.parse(String(f.calls[1]?.init?.body)), { note: 'why' });
  assert.equal(f.calls[2]?.url, '/api/holdings');
});

test('DELETE with 204 resolves to undefined', async () => {
  const f = fake(204, undefined);
  const r = await deleteWatchlistItem(9);
  assert.equal(r, undefined);
  assert.equal(f.calls[0]?.init?.method, 'DELETE');
  assert.equal(f.calls[0]?.url, '/api/watchlist/9');
});

test('statement upload is multipart with file and password and no JSON content type', async () => {
  const f = fake(200, { importId: 1 });
  await importStatement(new Blob(['%PDF-1.7'], { type: 'application/pdf' }), 'SECRET', 'cas.pdf');
  const init = f.calls[0]?.init;
  assert.equal(f.calls[0]?.url, '/api/import/statement');
  assert.ok(init?.body instanceof FormData);
  const form = init.body as FormData;
  assert.equal(form.get('password'), 'SECRET');
  assert.ok(form.get('file') instanceof Blob);
  assert.ok(!('Content-Type' in ((init.headers as Record<string, string>) ?? {})));
});

test('contract error bodies become ApiError with code, status and details', async () => {
  fake(404, { error: { code: 'NOT_FOUND', message: 'No stock found for symbol XYZ.', details: { symbol: 'XYZ' } } });
  await assert.rejects(
    () => getHome(),
    (e: unknown) => {
      assert.ok(e instanceof ApiError);
      assert.equal(e.code, 'NOT_FOUND');
      assert.equal(e.status, 404);
      assert.equal(e.message, 'No stock found for symbol XYZ.');
      assert.deepEqual(e.details, { symbol: 'XYZ' });
      return true;
    },
  );
});

test('non-contract error bodies still give a sensible ApiError', async () => {
  fake(502, 'not json');
  await assert.rejects(
    () => getHome(),
    (e: unknown) => e instanceof ApiError && e.code === 'UPSTREAM_UNAVAILABLE' && e.status === 502,
  );
  fake(500, { error: 'boom' });
  await assert.rejects(() => getHome(), (e: unknown) => e instanceof ApiError && e.code === 'INTERNAL');
});

test('network failure becomes NETWORK_ERROR; abort passes through', async () => {
  setFetch(async () => {
    throw new TypeError('Failed to fetch');
  });
  await assert.rejects(() => getHome(), (e: unknown) => e instanceof ApiError && e.code === 'NETWORK_ERROR' && e.status === 0);
  setFetch(async () => {
    const err = new Error('aborted');
    err.name = 'AbortError';
    throw err;
  });
  await assert.rejects(() => getHome(), (e: unknown) => e instanceof Error && e.name === 'AbortError');
});

test('setApiBase changes the prefix', async () => {
  const f = fake(200, {});
  setApiBase('http://localhost:8080/api/');
  await getHome();
  assert.equal(f.calls[0]?.url, 'http://localhost:8080/api/home');
});
