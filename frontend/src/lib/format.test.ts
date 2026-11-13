import test from 'node:test';
import assert from 'node:assert/strict';
import {
  formatCount,
  formatDays,
  formatInr,
  formatMonths,
  formatPct,
  formatPctChange,
  formatPrice,
  formatQuantity,
  formatTimes,
  formatValue,
  formatYears,
  groupIndian,
  groupTypedAmount,
  parseMoneyInput,
  plainDecimal,
} from './format';

test('formatInr: contract vectors', () => {
  const cases: Array<[number, string]> = [
    [0, '₹0'],
    [999, '₹999'],
    [42350.75, '₹42,351'],
    [99999.4, '₹99,999'],
    [99999.6, '₹1 lakh'],
    [120000, '₹1.2 lakh'],
    [1243500, '₹12.4 lakh'],
    [1250000, '₹12.5 lakh'],
    [9999999, '₹1 crore'],
    [34000000, '₹3.4 crore'],
    [8453000000, '₹845.3 crore'],
    [19321000000000, '₹19,32,100 crore'],
    [-45000, '-₹45,000'],
  ];
  for (const [input, expected] of cases) assert.equal(formatInr(input), expected, `formatInr(${input})`);
});

test('formatInr: edges around the lakh and crore cut-offs', () => {
  assert.equal(formatInr(100000), '₹1 lakh');
  assert.equal(formatInr(9995000), '₹1 crore'); // 99.95 lakh rounds up to 100.0 lakh -> crore
  assert.equal(formatInr(9949999), '₹99.5 lakh');
  assert.equal(formatInr(-0.2), '₹0');
  assert.equal(formatInr(-1243500), '-₹12.4 lakh');
  assert.equal(formatInr(1e15), '₹10,00,00,000 crore');
  assert.equal(formatInr(12.5e12), '₹12,50,000 crore');
  assert.equal(formatInr(null), 'Not available');
  assert.equal(formatInr(Number.NaN), 'Not available');
});

test('formatPrice: contract vectors', () => {
  assert.equal(formatPrice(2410.5), '₹2,410.50');
  assert.equal(formatPrice(2.675), '₹2.68');
  assert.equal(formatPrice(1234567.891), '₹12,34,567.89');
  assert.equal(formatPrice(0), '₹0.00');
  assert.equal(formatPrice(-12.345), '-₹12.35');
});

test('formatPct and formatPctChange: contract vectors', () => {
  assert.equal(formatPct(12.345), '12.3%');
  assert.equal(formatPct(0.05), '0.1%');
  assert.equal(formatPct(1.25), '1.3%');
  assert.equal(formatPct(-4.1), '-4.1%');
  assert.equal(formatPctChange(14.25), '+14.3%');
  assert.equal(formatPctChange(-4.1), '-4.1%');
  assert.equal(formatPctChange(0), '0.0%');
  assert.equal(formatPctChange(0.04), '0.0%');
  assert.equal(formatPctChange(-0.04), '0.0%');
});

test('formatTimes, formatCount', () => {
  assert.equal(formatTimes(24.06), '24.1x');
  assert.equal(formatCount(1234567), '12,34,567');
  assert.equal(formatCount(0), '0');
  assert.equal(formatCount(999), '999');
  assert.equal(formatCount(1000), '1,000');
});

test('formatYears, formatMonths, formatDays: contract vectors', () => {
  assert.equal(formatYears(1), '1 year');
  assert.equal(formatYears(3), '3 years');
  assert.equal(formatYears(7.25), '7.3 years');
  assert.equal(formatYears(0.96), '1 year');
  assert.equal(formatYears(1.04), '1 year');
  assert.equal(formatDays(1), '1 day');
  assert.equal(formatDays(143), '143 days');
  assert.equal(formatMonths(1), '1 month');
  assert.equal(formatMonths(12.5), '12.5 months');
});

test('rounding works on the shortest decimal string, including exponent notation', () => {
  assert.equal(plainDecimal(1e21), '1000000000000000000000');
  assert.equal(plainDecimal(1.5e-7), '0.00000015');
  assert.equal(plainDecimal(123.456), '123.456');
  assert.equal(formatPct(1.005), '1.0%'); // 1.005 -> one decimal place: 1.0
  assert.equal(formatPrice(1.005), '₹1.01'); // HALF_UP on "1.005"
  assert.equal(formatPrice(1e-7), '₹0.00');
});

test('groupIndian', () => {
  assert.equal(groupIndian('1'), '1');
  assert.equal(groupIndian('1234'), '1,234');
  assert.equal(groupIndian('123456'), '1,23,456');
  assert.equal(groupIndian('12345678'), '1,23,45,678');
});

test('formatValue dispatches on unit', () => {
  assert.equal(formatValue('INR', 1250000), '₹12.5 lakh');
  assert.equal(formatValue('INR_PRICE', 2410.5), '₹2,410.50');
  assert.equal(formatValue('PCT', 12.345), '12.3%');
  assert.equal(formatValue('PCT_CHANGE', 14.25), '+14.3%');
  assert.equal(formatValue('TIMES', 24.06), '24.1x');
  assert.equal(formatValue('YEARS', 1), '1 year');
  assert.equal(formatValue('MONTHS', 3), '3 months');
  assert.equal(formatValue('DAYS', 143), '143 days');
  assert.equal(formatValue('COUNT', 1234567), '12,34,567');
  assert.equal(formatValue('TEXT', 'Regular plan'), 'Regular plan');
  assert.equal(formatValue('TEXT', null), 'Not available');
  assert.equal(formatValue('INR', null), 'Not available');
});

test('formatQuantity keeps up to three decimals', () => {
  assert.equal(formatQuantity(15), '15');
  assert.equal(formatQuantity(1850.234), '1,850.234');
  assert.equal(formatQuantity(3120.5), '3,120.5');
  assert.equal(formatQuantity(1234567), '12,34,567');
});

test('parseMoneyInput and groupTypedAmount', () => {
  assert.equal(parseMoneyInput('1,50,000'), 150000);
  assert.equal(parseMoneyInput('₹ 25000'), 25000);
  assert.equal(parseMoneyInput('2500.50'), 2500.5);
  assert.equal(parseMoneyInput(''), null);
  assert.equal(parseMoneyInput('abc'), null);
  assert.equal(parseMoneyInput('0'), null);
  assert.equal(parseMoneyInput('-5'), null);
  assert.equal(groupTypedAmount('150000'), '1,50,000');
  assert.equal(groupTypedAmount('1,50,0000'), '15,00,000');
  assert.equal(groupTypedAmount('2500.5'), '2,500.5');
  assert.equal(groupTypedAmount('abc'), '');
});
