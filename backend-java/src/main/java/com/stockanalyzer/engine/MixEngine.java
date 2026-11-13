package com.stockanalyzer.engine;

import com.stockanalyzer.engine.model.AssetMix;
import java.util.ArrayList;
import java.util.List;

/** Equity/debt/other and stocks/funds mixes; each rounded to exactly 10000 bp and to the rupee total. */
public final class MixEngine {
    private MixEngine() { }

    public record MixLine(String key, String label, long valueInr, int bp, String display) {
        public double pct() { return Bp.pct(bp); }
    }

    public record MixResult(List<MixLine> equityDebt, List<MixLine> stocksFunds) { }

    public static MixResult compute(List<ValuedPosition> vps, long totalInr) {
        double stocks = 0, funds = 0, equity = 0, debt = 0, other = 0;
        for (ValuedPosition vp : vps) {
            if (vp.stock() != null) {
                stocks += vp.value();
                equity += vp.value();
            } else if (vp.fund() != null) {
                funds += vp.value();
                AssetMix m = vp.fund().assetMix();
                equity += vp.value() * m.equityPct() / 100.0;
                debt += vp.value() * (m.debtPct() + m.cashPct()) / 100.0;
                other += vp.value() * m.otherPct() / 100.0;
            }
        }
        List<MixLine> equityDebt = lines(new String[] {"EQUITY", "DEBT_CASH", "OTHER"},
                new String[] {"Shares", "Debt & cash", "Other assets"}, new double[] {equity, debt, other}, totalInr);
        List<MixLine> stocksFunds = lines(new String[] {"STOCKS", "FUNDS"},
                new String[] {"Stocks held directly", "Mutual funds"}, new double[] {stocks, funds}, totalInr);
        return new MixResult(equityDebt, stocksFunds);
    }

    /** All six size buckets (LARGE, MID, SMALL, MICRO, DEBT_CASH, OTHER), zero-filled, from the size breakdown. */
    public static List<MixLine> sizeMix(ExposureBreakdown size) {
        String[] keys = {"LARGE", "MID", "SMALL", "MICRO", ExposureEngine.DEBT_CASH, ExposureEngine.OTHER};
        String[] labels = {"Large cap", "Mid cap", "Small cap", "Micro cap", ExposureEngine.DEBT_CASH_NAME, ExposureEngine.OTHER_NAME};
        List<MixLine> out = new ArrayList<>();
        for (int i = 0; i < keys.length; i++) {
            ExposureLine l = size.find(keys[i]);
            long inr = l == null ? 0 : l.totalInr();
            int bp = l == null ? 0 : l.totalBp();
            out.add(new MixLine(keys[i], labels[i], inr, bp, disp(inr, bp)));
        }
        return out;
    }

    private static List<MixLine> lines(String[] keys, String[] labels, double[] raw, long totalInr) {
        int n = keys.length;
        double denom = 0;
        for (double r : raw) denom += r;
        long[] bps = new long[n];
        long[] inrs = new long[n];
        if (denom > 0 && totalInr > 0) {
            double[] rawBp = new double[n];
            double[] rawInr = new double[n];
            for (int i = 0; i < n; i++) {
                rawBp[i] = raw[i] / denom * Bp.FULL;
                rawInr[i] = raw[i] / denom * totalInr;
            }
            bps = Bp.largestRemainder(rawBp, raw, keys, Bp.FULL);
            inrs = Bp.largestRemainder(rawInr, raw, keys, totalInr);
        }
        List<MixLine> out = new ArrayList<>();
        for (int i = 0; i < n; i++) out.add(new MixLine(keys[i], labels[i], inrs[i], (int) bps[i], disp(inrs[i], (int) bps[i])));
        return List.copyOf(out);
    }

    private static String disp(long inr, int bp) {
        return IndianFormat.formatInr(inr) + " (" + IndianFormat.formatPct(Bp.pct(bp)) + ")";
    }
}
