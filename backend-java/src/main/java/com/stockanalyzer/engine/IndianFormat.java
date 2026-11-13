package com.stockanalyzer.engine;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;

/** Contract §0.4 formatting. Rounding is HALF_UP on the shortest decimal string of the double. */
public final class IndianFormat {
    private IndianFormat() { }

    public static final String NOT_AVAILABLE = "Not available";
    private static final String[] MONTHS = {"Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"};
    private static final BigDecimal LAKH = new BigDecimal("100000");
    private static final BigDecimal CRORE = new BigDecimal("10000000");
    private static final BigDecimal HUNDRED = new BigDecimal("100");
    private static final BigDecimal THOUSAND = new BigDecimal("1000");

    private static BigDecimal bd(double v) { return BigDecimal.valueOf(v); }

    /** Indian digit grouping of a non-negative integer string: 1234567 gives 12,34,567. */
    static String group(String digits) {
        int n = digits.length();
        if (n <= 3) return digits;
        StringBuilder sb = new StringBuilder(digits.substring(n - 3));
        int i = n - 3;
        while (i > 0) {
            int start = Math.max(0, i - 2);
            sb.insert(0, digits.substring(start, i) + ",");
            i = start;
        }
        return sb.toString();
    }

    private static String dropZero(BigDecimal oneDp) {
        String s = oneDp.toPlainString();
        return s.endsWith(".0") ? s.substring(0, s.length() - 2) : s;
    }

    public static String formatInr(double amount) {
        BigDecimal r = bd(amount).setScale(0, RoundingMode.HALF_UP);
        boolean neg = r.signum() < 0;
        BigDecimal a = r.abs();
        String body;
        if (a.compareTo(LAKH) < 0) {
            body = "₹" + group(a.toPlainString());
        } else {
            BigDecimal lakh = a.divide(LAKH).setScale(1, RoundingMode.HALF_UP);
            if (lakh.compareTo(HUNDRED) < 0) {
                body = "₹" + dropZero(lakh) + " lakh";
            } else {
                BigDecimal crore = a.divide(CRORE).setScale(1, RoundingMode.HALF_UP);
                if (crore.compareTo(THOUSAND) < 0) {
                    body = "₹" + dropZero(crore) + " crore";
                } else {
                    body = "₹" + group(a.divide(CRORE).setScale(0, RoundingMode.HALF_UP).toPlainString()) + " crore";
                }
            }
        }
        return neg ? "-" + body : body;
    }

    public static String formatPrice(double price) {
        BigDecimal r = bd(price).setScale(2, RoundingMode.HALF_UP);
        boolean neg = r.signum() < 0;
        String plain = r.abs().toPlainString();
        int dot = plain.indexOf('.');
        String body = "₹" + group(plain.substring(0, dot)) + plain.substring(dot);
        return neg ? "-" + body : body;
    }

    public static String formatPct(double pct) {
        return bd(pct).setScale(1, RoundingMode.HALF_UP).toPlainString() + "%";
    }

    public static String formatPctChange(double pct) {
        BigDecimal r = bd(pct).setScale(1, RoundingMode.HALF_UP);
        return (r.signum() > 0 ? "+" : "") + r.toPlainString() + "%";
    }

    public static String formatTimes(double v) {
        return bd(v).setScale(1, RoundingMode.HALF_UP).toPlainString() + "x";
    }

    public static String formatCount(double v) {
        BigDecimal r = bd(v).setScale(0, RoundingMode.HALF_UP);
        String s = group(r.abs().toPlainString());
        return r.signum() < 0 ? "-" + s : s;
    }

    private static String withUnit(double v, String one, String many) {
        BigDecimal r = bd(v).setScale(1, RoundingMode.HALF_UP);
        String s = dropZero(r);
        return s + " " + (s.equals("1") ? one : many);
    }

    public static String formatYears(double v) { return withUnit(v, "year", "years"); }

    public static String formatMonths(double v) { return withUnit(v, "month", "months"); }

    public static String formatDays(double v) { return withUnit(v, "day", "days"); }

    public static String formatDate(LocalDate d) {
        return d.getDayOfMonth() + " " + MONTHS[d.getMonthValue() - 1] + " " + d.getYear();
    }

    /** Display string for a value of the given unit. Null gives "Not available". */
    public static String display(Object value, String unit) {
        if (value == null) return NOT_AVAILABLE;
        if (Units.TEXT.equals(unit)) return String.valueOf(value);
        double v = ((Number) value).doubleValue();
        switch (unit) {
            case Units.INR: return formatInr(v);
            case Units.INR_PRICE: return formatPrice(v);
            case Units.PCT: return formatPct(v);
            case Units.PCT_CHANGE: return formatPctChange(v);
            case Units.TIMES: return formatTimes(v);
            case Units.YEARS: return formatYears(v);
            case Units.MONTHS: return formatMonths(v);
            case Units.DAYS: return formatDays(v);
            case Units.COUNT: return formatCount(v);
            default: throw new IllegalArgumentException("Unknown unit: " + unit);
        }
    }
}
