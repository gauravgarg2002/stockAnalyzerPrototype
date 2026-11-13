import test from 'node:test';
import assert from 'node:assert/strict';
import { formatDate, formatMonthYear, formatTimestamp } from './dates';

test('formatDate: contract vector and edges', () => {
  assert.equal(formatDate('2026-10-30'), '30 Oct 2026');
  assert.equal(formatDate('2026-01-05'), '5 Jan 2026');
  assert.equal(formatDate('2026-12-31'), '31 Dec 2026');
  assert.equal(formatDate(''), '');
  assert.equal(formatDate(null), '');
  assert.equal(formatDate('not a date'), 'not a date');
  assert.equal(formatDate('2026-13-01'), '2026-13-01');
});

test('formatMonthYear', () => {
  assert.equal(formatMonthYear('2026-10-30'), 'Oct 2026');
});

test('formatTimestamp shows the clock time as written, without time-zone conversion', () => {
  assert.equal(formatTimestamp('2026-10-30T18:42:10+05:30'), '30 Oct 2026, 6:42 pm');
  assert.equal(formatTimestamp('2026-10-30T00:05:00+05:30'), '30 Oct 2026, 12:05 am');
  assert.equal(formatTimestamp('2026-10-30T12:00:00+05:30'), '30 Oct 2026, 12:00 pm');
  assert.equal(formatTimestamp('2026-10-30'), '30 Oct 2026');
});
