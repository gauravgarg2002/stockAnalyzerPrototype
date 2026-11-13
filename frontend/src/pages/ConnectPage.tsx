import { useCallback, useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  addHolding,
  deleteHolding,
  disconnectKite,
  getConnection,
  getHoldings,
  getKiteStatus,
  importKite,
  importStatement,
  startKiteConnect,
} from '../lib/api-client';
import type { ConnectionResponse, ImportResponse, InstrumentRef, Kind } from '../lib/api-types';
import { copy, fill } from '../lib/copy';
import { formatTimestamp, formatDate } from '../lib/dates';
import { formatInr, formatQuantity, parseMoneyInput } from '../lib/format';
import { ROUTES } from '../lib/routes';
import { useApi } from '../hooks/useApi';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { PageHeader } from '../components/ui/PageHeader';
import { PageSkeleton } from '../components/ui/Skeleton';
import { ErrorState, errorMessage } from '../components/ui/ErrorState';
import { Card } from '../components/ui/Card';
import { Button, LinkButton } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Input } from '../components/ui/Input';
import { MoneyInput } from '../components/ui/MoneyInput';
import { SegmentedControl } from '../components/ui/SegmentedControl';
import { SearchCombobox } from '../components/ui/GlobalSearch';
import { ShowDetails } from '../components/ui/ShowDetails';

const POLL_MS = 2000;
const POLL_LIMIT_MS = 300_000;

type Flow = 'idle' | 'starting' | 'waiting' | 'importing' | 'failed';

function ImportSummary({ result }: { result: ImportResponse }) {
  return (
    <div role="status" className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4">
      <p className="font-medium text-slate-900">{result.message}</p>
      <p className="mt-1 text-sm text-slate-700">
        {fill(copy.connect.importCounts, { stocks: String(result.stockCount), funds: String(result.fundCount) })}
        {result.idleCashInr !== null ? ` ${fill(copy.connect.importCash, { cash: formatInr(result.idleCashInr) })}` : ''}
      </p>
      {result.unmatched.length > 0 ? (
        <div className="mt-3">
          <p className="text-sm font-medium text-slate-900">{copy.connect.unmatchedTitle}</p>
          <ul className="mt-1 list-disc space-y-0.5 pl-5 text-sm text-slate-700">
            {result.unmatched.map((u, i) => (
              <li key={`${u.name}-${i}`}>
                {u.name} – {u.reason}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      <p className="mt-2 text-xs text-slate-600">
        {copy.connect.importedAt} {formatTimestamp(result.importedAt)}
      </p>
    </div>
  );
}

function KiteCard({ conn, onChanged }: { conn: ConnectionResponse; onChanged: () => void }) {
  const [params, setParams] = useSearchParams();
  const [flow, setFlow] = useState<Flow>('idle');
  const [message, setMessage] = useState<string | null>(null);
  const [loginUrl, setLoginUrl] = useState<string | null>(null);
  const [result, setResult] = useState<ImportResponse | null>(null);
  const pollRef = useRef<number | null>(null);
  const startedAt = useRef(0);
  const handledReturn = useRef(false);

  const stopPolling = useCallback(() => {
    if (pollRef.current !== null) {
      window.clearTimeout(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  useEffect(() => stopPolling, [stopPolling]);

  const runImport = useCallback(async () => {
    setFlow('importing');
    setMessage(null);
    try {
      const res = await importKite();
      setResult(res);
      setFlow('idle');
      onChanged();
    } catch (e) {
      setMessage(errorMessage(e instanceof Error ? e : null));
      setFlow('failed');
    }
  }, [onChanged]);

  const poll: () => void = useCallback(() => {
    pollRef.current = window.setTimeout(async () => {
      try {
        const s = await getKiteStatus();
        if (s.status === 'CONNECTED') {
          stopPolling();
          await runImport();
          return;
        }
        if (s.status === 'FAILED') {
          stopPolling();
          setMessage(s.message || copy.connect.loginFailed);
          setFlow('failed');
          return;
        }
      } catch {
        // keep trying until the time limit
      }
      if (Date.now() - startedAt.current > POLL_LIMIT_MS) {
        setMessage(copy.connect.loginTimeout);
        setFlow('failed');
        return;
      }
      poll();
    }, POLL_MS);
  }, [runImport, stopPolling]);

  // Coming back from the Kite login page (kite_connect mode) lands on /connect?kite=connected|failed.
  useEffect(() => {
    const returned = params.get('kite');
    if (!returned || handledReturn.current) return;
    handledReturn.current = true;
    setParams({}, { replace: true });
    if (returned === 'connected') void runImport();
    else {
      setMessage(copy.connect.loginFailed);
      setFlow('failed');
    }
  }, [params, setParams, runImport]);

  async function start() {
    setFlow('starting');
    setMessage(null);
    setResult(null);
    try {
      const res = await startKiteConnect();
      if (res.status === 'CONNECTED') {
        await runImport();
      } else if (res.status === 'PENDING_LOGIN' && res.loginUrl) {
        setLoginUrl(res.loginUrl);
        if (res.brokerMode === 'kite_connect') {
          window.location.assign(res.loginUrl);
          return;
        }
        window.open(res.loginUrl, '_blank', 'noopener');
        setFlow('waiting');
        startedAt.current = Date.now();
        poll();
      } else {
        setMessage(res.message);
        setFlow('failed');
      }
    } catch (e) {
      setMessage(errorMessage(e instanceof Error ? e : null));
      setFlow('failed');
    }
  }

  async function disconnect() {
    stopPolling();
    try {
      await disconnectKite();
      setFlow('idle');
      setResult(null);
      onChanged();
    } catch (e) {
      setMessage(errorMessage(e instanceof Error ? e : null));
      setFlow('failed');
    }
  }

  const connected = conn.status === 'CONNECTED';
  const busy = flow === 'starting' || flow === 'importing';

  return (
    <Card as="section" labelledBy="kite-title">
      <div className="flex flex-wrap items-center gap-3">
        <h2 id="kite-title" className="text-xl font-semibold text-slate-900">
          {copy.connect.kiteTitle}
        </h2>
        <Badge tone={connected ? 'accent' : 'neutral'}>
          {connected ? copy.connect.statusConnected : conn.status === 'PENDING_LOGIN' ? copy.connect.statusPending : copy.connect.statusNot}
        </Badge>
      </div>
      <p className="mt-2 text-slate-700">{copy.connect.kiteBody}</p>
      {connected && conn.accountLabel ? <p className="mt-1 text-sm text-slate-600">{conn.accountLabel}</p> : null}

      <div className="mt-4 flex flex-wrap gap-3">
        <Button onClick={() => void start()} busy={busy}>
          {connected ? copy.connect.importAgain : copy.connect.kiteButton}
        </Button>
        {connected ? (
          <Button variant="secondary" onClick={() => void disconnect()}>
            {copy.connect.disconnect}
          </Button>
        ) : null}
      </div>

      <div aria-live="polite">
        {flow === 'waiting' ? (
          <div role="status" className="mt-4 rounded-xl bg-slate-50 p-4 text-slate-800 ring-1 ring-inset ring-slate-200">
            <p>{copy.connect.waiting}</p>
            {loginUrl ? (
              <p className="mt-1 text-sm">
                <a className="font-medium text-indigo-700 underline underline-offset-2" href={loginUrl} target="_blank" rel="noopener noreferrer">
                  {copy.connect.reopenLogin}
                </a>
              </p>
            ) : null}
            <Button
              size="sm"
              variant="ghost"
              className="mt-2"
              onClick={() => {
                stopPolling();
                setFlow('idle');
              }}
            >
              {copy.common.cancel}
            </Button>
          </div>
        ) : null}
        {flow === 'importing' ? <p className="mt-4 text-slate-700">{copy.connect.importing}</p> : null}
        {flow === 'failed' && message ? (
          <p role="alert" className="mt-4 rounded-xl border border-slate-300 bg-white p-3 font-medium text-slate-900">
            {message}
          </p>
        ) : null}
        {result ? <ImportSummary result={result} /> : null}
      </div>
    </Card>
  );
}

function StatementCard({ onChanged }: { onChanged: () => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ImportResponse | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!file) {
      setError(copy.connect.statementNoFile);
      return;
    }
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const res = await importStatement(file, password, file.name);
      setResult(res);
      setPassword('');
      onChanged();
    } catch (err) {
      setError(errorMessage(err instanceof Error ? err : null));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card as="section" labelledBy="statement-title">
      <h2 id="statement-title" className="text-xl font-semibold text-slate-900">
        {copy.connect.statementTitle}
      </h2>
      <p className="mt-2 text-slate-700">{copy.connect.statementBody}</p>
      <form className="mt-4 space-y-4" onSubmit={(e) => void submit(e)}>
        <Input
          label={copy.connect.statementFile}
          type="file"
          accept="application/pdf,.pdf"
          hint={copy.connect.statementFileHint}
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
        <Input
          label={copy.connect.statementPassword}
          type="password"
          autoComplete="off"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          hint={copy.connect.statementPasswordHint}
          className="max-w-sm"
        />
        {error ? (
          <p role="alert" className="font-medium text-slate-900">
            {error}
          </p>
        ) : null}
        <Button type="submit" variant="secondary" busy={busy}>
          {copy.connect.statementButton}
        </Button>
      </form>
      {result ? <ImportSummary result={result} /> : null}
    </Card>
  );
}

function ManualCard({ onChanged }: { onChanged: () => void }) {
  const [kind, setKind] = useState<Kind>('STOCK');
  const [picked, setPicked] = useState<InstrumentRef | null>(null);
  const [quantity, setQuantity] = useState('');
  const [avgPrice, setAvgPrice] = useState('');
  const [date, setDate] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setDone(null);
    const q = Number(quantity.replace(/,/g, ''));
    const p = parseMoneyInput(avgPrice);
    if (!picked) return setError(copy.connect.manualNoInstrument);
    if (!Number.isFinite(q) || q <= 0 || p === null) return setError(copy.connect.manualInvalid);
    setBusy(true);
    setError(null);
    try {
      await addHolding({ kind, instrumentId: picked.id, quantity: q, avgPrice: p, firstBuyDate: date === '' ? null : date });
      setDone(fill(copy.connect.manualAdded, { name: picked.name }));
      setPicked(null);
      setQuantity('');
      setAvgPrice('');
      setDate('');
      onChanged();
    } catch (err) {
      setError(errorMessage(err instanceof Error ? err : null));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card as="section" labelledBy="manual-title">
      <h2 id="manual-title" className="text-xl font-semibold text-slate-900">
        {copy.connect.manualTitle}
      </h2>
      <p className="mt-2 text-slate-700">{copy.connect.manualBody}</p>
      <ShowDetails label={copy.connect.manualOpen} hideLabel={copy.connect.manualClose}>
        <form className="space-y-4" onSubmit={(e) => void submit(e)}>
          <SegmentedControl<Kind>
            label={copy.connect.manualKind}
            value={kind}
            onChange={(k) => {
              setKind(k);
              setPicked(null);
            }}
            options={[
              { value: 'STOCK', label: copy.compare.stocks },
              { value: 'FUND', label: copy.compare.funds },
            ]}
          />
          <div className="max-w-md">
            <SearchCombobox
              key={kind}
              label={copy.connect.manualSearch}
              hideLabel={false}
              kind={kind}
              clearOnSelect={false}
              onSelect={(r) => setPicked(r)}
            />
            {picked ? <p className="mt-1 text-sm text-slate-700">{fill(copy.connect.manualPicked, { name: picked.name })}</p> : null}
          </div>
          <div className="grid gap-4 sm:grid-cols-3">
            <Input
              label={kind === 'STOCK' ? copy.connect.manualQtyStock : copy.connect.manualQtyFund}
              inputMode="decimal"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
            />
            <MoneyInput label={kind === 'STOCK' ? copy.connect.manualPriceStock : copy.connect.manualPriceFund} value={avgPrice} onChange={setAvgPrice} />
            <Input label={copy.connect.manualDate} type="date" value={date} onChange={(e) => setDate(e.target.value)} hint={copy.connect.manualDateHint} />
          </div>
          {error ? (
            <p role="alert" className="font-medium text-slate-900">
              {error}
            </p>
          ) : null}
          {done ? <p role="status" className="text-slate-800">{done}</p> : null}
          <Button type="submit" variant="secondary" busy={busy}>
            {copy.connect.manualButton}
          </Button>
        </form>
      </ShowDetails>
    </Card>
  );
}

function HoldingsList({ refreshKey, onChanged }: { refreshKey: number; onChanged: () => void }) {
  const { data, loading, error, reload } = useApi((signal) => getHoldings({ signal }), [refreshKey]);
  const [confirm, setConfirm] = useState<number | null>(null);
  const [failure, setFailure] = useState<string | null>(null);

  async function remove(id: number) {
    setFailure(null);
    try {
      await deleteHolding(id);
      setConfirm(null);
      onChanged();
    } catch (e) {
      setFailure(errorMessage(e instanceof Error ? e : null));
    }
  }

  if (loading) return <PageSkeleton cards={1} title={false} />;
  if (error || !data) return <ErrorState error={error} onRetry={reload} compact />;
  if (data.holdings.length === 0) return <p className="text-slate-600">{copy.connect.noHoldings}</p>;

  return (
    <div>
      {failure ? (
        <p role="alert" className="mb-2 font-medium text-slate-900">
          {failure}
        </p>
      ) : null}
      <ul className="divide-y divide-slate-100">
        {data.holdings.map((h) => (
          <li key={h.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
            <div className="min-w-0">
              <p className="break-words font-medium text-slate-900">{h.name}</p>
              <p className="text-sm text-slate-600">
                {formatQuantity(h.quantity)} {h.kind === 'STOCK' ? copy.connect.sharesWord : copy.connect.unitsWord} · {copy.connect.sourceNames[h.source]} ·{' '}
                {copy.common.asOf} {formatDate(h.importedAt)}
              </p>
            </div>
            {confirm === h.id ? (
              <span className="flex items-center gap-2">
                <Button size="sm" variant="secondary" onClick={() => void remove(h.id)}>
                  {copy.watchlist.yesRemove}
                </Button>
                <Button size="sm" variant="ghost" onClick={() => setConfirm(null)}>
                  {copy.common.cancel}
                </Button>
              </span>
            ) : (
              <Button size="sm" variant="ghost" aria-label={fill(copy.connect.removeHolding, { name: h.name })} onClick={() => setConfirm(h.id)}>
                {copy.watchlist.remove}
              </Button>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function ConnectPage() {
  useDocumentTitle(copy.connect.title);
  const [refresh, setRefresh] = useState(0);
  const { data: fresh, loading, error, reload } = useApi((signal) => getConnection({ signal }), [refresh]);
  const changed = useCallback(() => setRefresh((n) => n + 1), []);

  // Keep showing the last answer while a refresh is under way, so open forms and results are not thrown away.
  const last = useRef<ConnectionResponse | null>(null);
  if (fresh) last.current = fresh;
  const data = fresh ?? last.current;

  if (!data && loading) return <PageSkeleton cards={3} />;
  if (!data) return <ErrorState error={error} onRetry={reload} />;

  const s = data.holdingsSummary;
  return (
    <div>
      <PageHeader title={copy.connect.title} subtitle={copy.connect.subtitle} sampleData={data.sampleData} />
      <div className="space-y-6">
        <KiteCard conn={data} onChanged={changed} />
        <StatementCard onChanged={changed} />
        <ManualCard onChanged={changed} />

        <Card as="section" labelledBy="imported-title">
          <h2 id="imported-title" className="text-xl font-semibold text-slate-900">
            {copy.connect.importedTitle}
          </h2>
          {s.stockCount + s.fundCount > 0 ? (
            <>
              <p className="mt-2 text-slate-800">
                {fill(copy.connect.importedSummary, { stocks: String(s.stockCount), funds: String(s.fundCount) })}
                {data.lastImportAt ? ` ${copy.connect.lastImport} ${formatTimestamp(data.lastImportAt)}.` : ''}
              </p>
              <p className="mt-1 text-sm text-slate-600">
                {fill(copy.connect.bySource, { kite: String(s.bySource.KITE), statement: String(s.bySource.STATEMENT), manual: String(s.bySource.MANUAL) })}
              </p>
              <div className="mt-4">
                <LinkButton to={ROUTES.portfolio} variant="secondary">
                  {copy.connect.seePortfolio}
                </LinkButton>
              </div>
            </>
          ) : (
            <p className="mt-2 text-slate-700">{copy.connect.nothingImported}</p>
          )}

          {data.imports.length > 0 ? (
            <ShowDetails label={copy.connect.historyOpen} hideLabel={copy.connect.historyClose}>
              <ul className="divide-y divide-slate-100">
                {data.imports.map((i) => (
                  <li key={i.id} className="py-2 text-sm">
                    <p className="text-slate-900">
                      {copy.connect.sourceNames[i.source]} · {formatTimestamp(i.finishedAt)}
                    </p>
                    <p className="text-slate-600">{i.message}</p>
                  </li>
                ))}
              </ul>
            </ShowDetails>
          ) : null}

          <ShowDetails label={copy.connect.holdingsOpen} hideLabel={copy.connect.holdingsClose}>
            <HoldingsList refreshKey={refresh} onChanged={changed} />
          </ShowDetails>
        </Card>
      </div>
    </div>
  );
}
