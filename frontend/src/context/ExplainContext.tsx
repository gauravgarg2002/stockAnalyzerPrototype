import { createContext, useContext } from 'react';
import type { ReactNode } from 'react';
import type { Kind } from '../lib/api-types';

export interface ExplainScopeValue {
  kind: Kind | null;
  id: string | null;
}

const ExplainContext = createContext<ExplainScopeValue>({ kind: null, id: null });

/** Tells every "Explain this" popover underneath which stock or fund the page is about. */
export function ExplainScope({ kind, id, children }: { kind: Kind | null; id: string | null; children: ReactNode }) {
  return <ExplainContext.Provider value={{ kind, id }}>{children}</ExplainContext.Provider>;
}

export function useExplainScope(): ExplainScopeValue {
  return useContext(ExplainContext);
}
