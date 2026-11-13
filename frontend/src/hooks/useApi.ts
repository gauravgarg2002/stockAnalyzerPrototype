import { useCallback, useEffect, useRef, useState } from 'react';
import { ApiError } from '../lib/api-client';

export interface ApiState<T> {
  data: T | null;
  loading: boolean;
  error: ApiError | null;
  reload: () => void;
}

function toApiError(e: unknown): ApiError {
  if (e instanceof ApiError) return e;
  return new ApiError('NETWORK_ERROR', 0, e instanceof Error ? e.message : 'Something went wrong.');
}

/**
 * Runs `fetcher` whenever `deps` change (and on reload()). Cancels the previous request.
 * `data` is null while loading, so pages show a skeleton on every fresh load.
 */
export function useApi<T>(
  fetcher: (signal: AbortSignal) => Promise<T>,
  deps: ReadonlyArray<unknown>,
): ApiState<T> {
  const [state, setState] = useState<{ data: T | null; error: ApiError | null; loading: boolean }>({
    data: null,
    error: null,
    loading: true,
  });
  const [tick, setTick] = useState(0);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  useEffect(() => {
    const controller = new AbortController();
    setState({ data: null, error: null, loading: true });
    fetcherRef
      .current(controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) setState({ data, error: null, loading: false });
      })
      .catch((e: unknown) => {
        if (controller.signal.aborted) return;
        if (e instanceof Error && e.name === 'AbortError') return;
        setState({ data: null, error: toApiError(e), loading: false });
      });
    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);

  const reload = useCallback(() => setTick((t) => t + 1), []);
  return { data: state.data, loading: state.loading, error: state.error, reload };
}
