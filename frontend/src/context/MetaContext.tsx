import { createContext, useContext, useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { getMeta } from '../lib/api-client';
import type { MetaResponse } from '../lib/api-types';

const MetaContext = createContext<MetaResponse | null>(null);

/** Loads /api/meta once. The app works without it, so a failure is silent. */
export function MetaProvider({ children }: { children: ReactNode }) {
  const [meta, setMeta] = useState<MetaResponse | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    getMeta({ signal: controller.signal })
      .then(setMeta)
      .catch(() => setMeta(null));
    return () => controller.abort();
  }, []);
  return <MetaContext.Provider value={meta}>{children}</MetaContext.Provider>;
}

export function useMeta(): MetaResponse | null {
  return useContext(MetaContext);
}
