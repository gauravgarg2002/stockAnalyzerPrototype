import { useEffect } from 'react';
import { copy } from '../lib/copy';

export function useDocumentTitle(title: string | null | undefined): void {
  useEffect(() => {
    document.title = title ? `${title} · ${copy.app.name}` : copy.app.name;
  }, [title]);
}
