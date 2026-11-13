import test from 'node:test';
import assert from 'node:assert/strict';
import { checkPath, comparePath, fundPath, parseIds, parseKind, stockPath, tryPath } from './routes';

test('path builders', () => {
  assert.equal(stockPath('TCS'), '/stock/TCS');
  assert.equal(stockPath('M&M'), '/stock/M%26M');
  assert.equal(fundPath('900101'), '/fund/900101');
  assert.equal(checkPath('STOCK', 'INFY'), '/stock/INFY');
  assert.equal(checkPath('FUND', '900201'), '/fund/900201');
  assert.equal(tryPath('FUND', '900701'), '/try/fund/900701');
  assert.equal(tryPath(), '/try');
  assert.equal(comparePath('STOCK', ['TCS', 'INFY']), '/compare?kind=STOCK&ids=TCS,INFY');
  assert.equal(comparePath('FUND', ['900101', '900201'], 100000), '/compare?kind=FUND&ids=900101,900201&amount=100000');
  assert.equal(comparePath('STOCK', ['TCS', 'INFY'], 5), '/compare?kind=STOCK&ids=TCS,INFY');
});

test('parsers', () => {
  assert.equal(parseKind('stock'), 'STOCK');
  assert.equal(parseKind('FUND'), 'FUND');
  assert.equal(parseKind('index'), null);
  assert.equal(parseKind(null), null);
  assert.deepEqual(parseIds('A, B,,C,D'), ['A', 'B', 'C']);
  assert.deepEqual(parseIds(null), []);
});
