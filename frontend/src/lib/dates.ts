// Date display helpers. Dates arrive as "YYYY-MM-DD", timestamps as ISO-8601 with offset.
// Everything is parsed from the text itself so the result never depends on the viewer's time zone.

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'] as const;

const DATE_RE = /^(\d{4})-(\d{2})-(\d{2})/;

/** "2026-10-30" -> "30 Oct 2026". Unparseable input is returned unchanged. */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '';
  const m = DATE_RE.exec(iso);
  if (!m) return iso;
  const month = MONTHS[Number(m[2]) - 1];
  if (!month) return iso;
  return `${Number(m[3])} ${month} ${m[1]}`;
}

/** "2026-10-30" -> "Oct 2026" (chart ticks). */
export function formatMonthYear(iso: string | null | undefined): string {
  if (!iso) return '';
  const m = DATE_RE.exec(iso);
  if (!m) return iso;
  const month = MONTHS[Number(m[2]) - 1];
  return month ? `${month} ${m[1]}` : iso;
}

/** "2026-10-30T18:42:10+05:30" -> "30 Oct 2026, 6:42 pm" (the clock time as written). */
export function formatTimestamp(iso: string | null | undefined): string {
  if (!iso) return '';
  const m = /^(\d{4}-\d{2}-\d{2})T(\d{2}):(\d{2})/.exec(iso);
  if (!m) return formatDate(iso);
  const hour24 = Number(m[2]);
  const suffix = hour24 >= 12 ? 'pm' : 'am';
  const hour12 = hour24 % 12 === 0 ? 12 : hour24 % 12;
  return `${formatDate(m[1])}, ${hour12}:${m[3]} ${suffix}`;
}

/** Calendar year of an ISO date, as a string. */
export function yearOf(iso: string): string {
  return iso.slice(0, 4);
}
