// Banned verdict words: identical to docs/api-contract.md §0.6.

export const BANNED_PATTERN =
  '\\b(buy|buys|buying|sell|sells|selling|avoid|avoids|avoided|avoiding|overvalued|undervalued|cheap|expensive|good|bad|recommend|recommends|recommended|recommending|recommendation|recommendations|should|target\\s+prices?)\\b';

export const BANNED_RE = new RegExp(BANNED_PATTERN, 'i');

const BANNED_GLOBAL = new RegExp(BANNED_PATTERN, 'gi');

function escapeRegExp(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/**
 * Returns every banned word found in `text`, after masking each of `names`
 * (instrument, fund or company names) with the token NAME.
 */
export function scan(text: string, names: readonly string[] = []): string[] {
  let masked = text;
  const ordered = [...names].filter((n) => n.length > 0).sort((a, b) => b.length - a.length);
  for (const name of ordered) {
    masked = masked.replace(new RegExp(escapeRegExp(name), 'gi'), 'NAME');
  }
  return Array.from(masked.matchAll(BANNED_GLOBAL), (m) => m[0]);
}

export const hasBannedWord = (text: string, names: readonly string[] = []): boolean =>
  scan(text, names).length > 0;
