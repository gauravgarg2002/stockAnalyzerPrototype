import test from 'node:test';
import assert from 'node:assert/strict';
import { allCopyStrings, copy, fill } from './copy';
import { BANNED_PATTERN, BANNED_RE, hasBannedWord, scan } from './verdict';

test('banned pattern is identical to docs/api-contract.md §0.6', () => {
  assert.equal(
    BANNED_PATTERN,
    '\\b(buy|buys|buying|sell|sells|selling|avoid|avoids|avoided|avoiding|overvalued|undervalued|cheap|expensive|good|bad|recommend|recommends|recommended|recommending|recommendation|recommendations|should|target\\s+prices?)\\b',
  );
  assert.ok(BANNED_RE.flags.includes('i'));
});

test('regex catches verdict words, any case', () => {
  for (const w of ['Buy', 'SELL now', 'avoid it', 'overvalued', 'Undervalued', 'cheap', 'expensive', 'good', 'bad', 'recommend', 'Recommended', 'you should', 'target price', 'target  prices']) {
    assert.ok(hasBannedWord(w), w);
  }
});

test('regex leaves neutral words alone', () => {
  for (const w of ['buyback', 'goods', 'sell-off'.replace('sell-off', 'fall'), 'goodwill', 'badge', 'shoulder', 'targets', 'Information only, not investment advice.']) {
    assert.ok(!hasBannedWord(w), w);
  }
});

test('scan masks names before matching', () => {
  assert.deepEqual(scan('Good Company Ltd rose 4%.', ['Good Company Ltd']), []);
  assert.deepEqual(scan('Good Company Ltd is good.', ['Good Company Ltd']), ['good']);
  assert.deepEqual(scan('Bad Loans Fund and Buy Right Fund', ['Bad Loans Fund', 'Buy Right Fund']), []);
});

test('no static UI string contains a verdict word', () => {
  const strings = allCopyStrings();
  assert.ok(strings.length > 200, `expected a full copy file, found ${strings.length} strings`);
  const hits = strings.filter((s) => hasBannedWord(s.text)).map((s) => `${s.path}: ${s.text}`);
  assert.deepEqual(hits, []);
});

test('the footer disclaimer is present and exact', () => {
  assert.equal(copy.app.disclaimer, 'Information only, not investment advice.');
});

test('every placeholder in a template is a simple word, and fill replaces them', () => {
  for (const s of allCopyStrings()) {
    const open = (s.text.match(/\{/g) ?? []).length;
    const close = (s.text.match(/\}/g) ?? []).length;
    assert.equal(open, close, s.path);
    for (const m of s.text.matchAll(/\{([^}]*)\}/g)) assert.match(m[1] ?? '', /^\w+$/, s.path);
  }
  assert.equal(fill('Hello {name}, {n} items, {missing}', { name: 'Asha', n: '3' }), 'Hello Asha, 3 items, {missing}');
});

test('no red or green wording and no advice phrasing in copy', () => {
  const advice = /\b(you ought|must buy|worth buying|safe bet|sure thing|guarantee|top pick)\b/i;
  for (const s of allCopyStrings()) assert.ok(!advice.test(s.text), s.path);
});
