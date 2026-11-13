package com.stockanalyzer.engine;

import java.math.BigDecimal;
import java.math.RoundingMode;

public final class Money {
    private Money() { }

    /** Whole rupees, HALF_UP on the shortest decimal string of the double. */
    public static long roundRupees(double v) {
        return BigDecimal.valueOf(check(v)).setScale(0, RoundingMode.HALF_UP).longValueExact();
    }

    public static double round2(double v) { return roundTo(v, 2); }

    public static double roundTo(double v, int dp) {
        return BigDecimal.valueOf(check(v)).setScale(dp, RoundingMode.HALF_UP).doubleValue();
    }

    private static double check(double v) {
        if (!Double.isFinite(v)) throw new IllegalArgumentException("Not a finite number: " + v);
        return v;
    }
}
