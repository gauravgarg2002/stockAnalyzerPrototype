package com.stockanalyzer.engine;

import java.math.BigInteger;
import java.util.Arrays;

/** Basis points (1 bp = 0.01%) and largest-remainder rounding. */
public final class Bp {
    private Bp() { }

    public static final int FULL = 10000;

    /** Percent units for a basis-point count: 1184 gives 11.84. */
    public static double pct(long bp) { return bp / 100.0; }

    /**
     * Largest-remainder rounding. raw[i] are non-negative amounts already scaled so that they add up to
     * (about) target. Returns integers adding up to exactly target. Remainders go to the largest fractional
     * parts; ties are broken by larger tieValue, then by tieKey ascending, then by index.
     */
    public static long[] largestRemainder(double[] raw, double[] tieValue, String[] tieKey, long target) {
        int n = raw.length;
        long[] out = new long[n];
        if (n == 0) return out;
        double[] frac = new double[n];
        long sum = 0;
        for (int i = 0; i < n; i++) {
            double f = Math.floor(Math.max(0.0, raw[i]));
            out[i] = (long) f;
            frac[i] = Math.max(0.0, raw[i]) - f;
            sum += out[i];
        }
        Integer[] order = new Integer[n];
        for (int i = 0; i < n; i++) order[i] = i;
        Arrays.sort(order, (a, b) -> {
            int c = Double.compare(frac[b], frac[a]);
            if (c != 0) return c;
            if (tieValue != null) {
                c = Double.compare(tieValue[b], tieValue[a]);
                if (c != 0) return c;
            }
            if (tieKey != null) {
                c = tieKey[a].compareTo(tieKey[b]);
                if (c != 0) return c;
            }
            return Integer.compare(a, b);
        });
        long rem = target - sum;
        int k = 0;
        while (rem > 0) { out[order[k % n]]++; rem--; k++; }
        k = n - 1;
        int guard = 0;
        while (rem < 0 && guard < 100000) {
            int idx = order[((k % n) + n) % n];
            if (out[idx] > 0) { out[idx]--; rem++; }
            k--;
            guard++;
        }
        return out;
    }

    /** Ties by larger raw value, then index. */
    public static long[] largestRemainder(double[] raw, long target) {
        return largestRemainder(raw, raw, null, target);
    }

    /** Proportional split of target by integer weights (exact arithmetic), largest remainder, ties by index. */
    public static long[] largestRemainder(long[] weights, long target) {
        int n = weights.length;
        long[] out = new long[n];
        BigInteger total = BigInteger.ZERO;
        for (long w : weights) total = total.add(BigInteger.valueOf(Math.max(0, w)));
        if (n == 0 || total.signum() == 0) return out;
        double[] frac = new double[n];
        long sum = 0;
        for (int i = 0; i < n; i++) {
            BigInteger[] qr = BigInteger.valueOf(Math.max(0, weights[i])).multiply(BigInteger.valueOf(target)).divideAndRemainder(total);
            out[i] = qr[0].longValue();
            frac[i] = qr[1].doubleValue() / total.doubleValue();
            sum += out[i];
        }
        Integer[] order = new Integer[n];
        for (int i = 0; i < n; i++) order[i] = i;
        Arrays.sort(order, (a, b) -> {
            int c = Double.compare(frac[b], frac[a]);
            if (c != 0) return c;
            c = Long.compare(weights[b], weights[a]);
            return c != 0 ? c : Integer.compare(a, b);
        });
        long rem = target - sum;
        for (int k = 0; rem > 0; k++, rem--) out[order[k % n]]++;
        return out;
    }

    /** value / total in basis points, unrounded. 0 when total is not positive. */
    public static double rawBp(double value, double total) {
        return total > 0 ? value / total * FULL : 0.0;
    }
}
