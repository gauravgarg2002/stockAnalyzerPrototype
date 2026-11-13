package com.stockanalyzer.engine;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

class BpTest {

    private static long sum(long[] a) {
        long s = 0;
        for (long x : a) s += x;
        return s;
    }

    @Test
    @DisplayName("largest remainder always adds up to the target")
    void sumsToTarget() {
        double[] raw = {3333.3333, 3333.3333, 3333.3334};
        long[] r = Bp.largestRemainder(raw, 10000);
        assertEquals(10000, sum(r));
        // the largest fraction (.3334) gets the extra unit
        assertEquals(3333, r[0]);
        assertEquals(3333, r[1]);
        assertEquals(3334, r[2]);
    }

    @Test
    @DisplayName("ties on the remainder go to the larger value, then the key ascending")
    void tieBreaks() {
        double[] raw = {2.5, 2.5, 5.0};
        double[] tie = {2.5, 2.5, 5.0};
        long[] r = Bp.largestRemainder(raw, tie, new String[] {"B", "A", "C"}, 10);
        assertEquals(10, sum(r));
        // equal fractions .5/.5: one unit to give, key A wins over B
        assertEquals(2, r[0]);
        assertEquals(3, r[1]);
        assertEquals(5, r[2]);

        double[] raw2 = {1.5, 1.5};
        long[] r2 = Bp.largestRemainder(raw2, new double[] {1.0, 2.0}, new String[] {"A", "B"}, 3);
        assertEquals(1, r2[0]);
        assertEquals(2, r2[1]); // larger value wins the tie
    }

    @Test
    @DisplayName("three equal parts of 10000 give 3334 / 3333 / 3333")
    void thirds() {
        long[] r = Bp.largestRemainder(new double[] {10000 / 3.0, 10000 / 3.0, 10000 / 3.0},
                new double[] {1, 1, 1}, new String[] {"A", "B", "C"}, 10000);
        assertEquals(10000, sum(r));
        assertEquals(3334, r[0]);
        assertEquals(3333, r[1]);
        assertEquals(3333, r[2]);
    }

    @Test
    @DisplayName("empty input and zero target")
    void empty() {
        assertEquals(0, Bp.largestRemainder(new double[0], 10000).length);
        assertEquals(0, sum(Bp.largestRemainder(new double[] {0.0, 0.0}, 0)));
    }

    @Test
    @DisplayName("overshooting floors are trimmed back to the target")
    void overshoot() {
        long[] r = Bp.largestRemainder(new double[] {5.0, 5.0, 1.0}, new double[] {5, 5, 1}, new String[] {"A", "B", "C"}, 10);
        assertEquals(10, sum(r));
    }

    @Test
    @DisplayName("integer weights split exactly")
    void integerWeights() {
        long[] r = Bp.largestRemainder(new long[] {1, 1, 1}, 10000);
        assertEquals(10000, sum(r));
        assertEquals(3334, r[0]);
        long[] r2 = Bp.largestRemainder(new long[] {50, 30, 20}, 10000);
        assertEquals(5000, r2[0]);
        assertEquals(3000, r2[1]);
        assertEquals(2000, r2[2]);
        assertEquals(0, sum(Bp.largestRemainder(new long[] {0, 0}, 100)));
    }

    @Test
    @DisplayName("basis points to percent units")
    void pct() {
        assertEquals(11.84, Bp.pct(1184), 1e-12);
        assertEquals(100.0, Bp.pct(10000), 1e-12);
        assertEquals(2500.0, Bp.rawBp(25, 100), 1e-9);
        assertEquals(0.0, Bp.rawBp(25, 0), 1e-12);
        assertTrue(Bp.FULL == 10000);
    }
}
