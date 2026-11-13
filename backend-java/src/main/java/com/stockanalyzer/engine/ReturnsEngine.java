package com.stockanalyzer.engine;

import com.stockanalyzer.engine.model.Kind;
import com.stockanalyzer.engine.model.PortfolioInput;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.OptionalDouble;
import java.util.TreeMap;
import java.util.TreeSet;

/** Price/NAV returns (no dividends) against the Nifty 50 price index on the same dates. */
public final class ReturnsEngine {
    private ReturnsEngine() { }

    public static final String NIFTY_ID = "NIFTY50";

    public record PointRequest(String kind, String id, List<LocalDate> dates) { }

    public record HoldingReturn(Kind kind, String id, String name, Double oneYearPct, Double niftyOneYearPct,
                                Double sinceBuyPct, Double niftySinceBuyPct, long costInr, long valueInr, long gainInr) { }

    public record ReturnsResult(Double portfolioOneYearPct, Double niftyOneYearPct, Double portfolioSinceBuyPct,
                                Double niftySinceBuyPct, int sinceBuyCoveredCount, long costInr, long valueInr,
                                long gainInr, List<HoldingReturn> holdings) {
        public boolean oneYearAvailable() { return portfolioOneYearPct != null && niftyOneYearPct != null; }

        public boolean sinceBuyAvailable() { return portfolioSinceBuyPct != null && niftySinceBuyPct != null; }
    }

    public static ReturnsResult empty() {
        return new ReturnsResult(null, null, null, null, 0, 0, 0, 0, List.of());
    }

    /** The price points the engine will ask for, so the caller can fetch them in one call. */
    public static List<PointRequest> pointRequests(PortfolioInput in) {
        LocalDate asOf = in.asOf();
        LocalDate yearAgo = asOf.minusYears(1);
        Map<String, TreeSet<LocalDate>> byInstrument = new TreeMap<>();
        TreeSet<LocalDate> nifty = new TreeSet<>();
        nifty.add(asOf);
        nifty.add(yearAgo);
        for (ValuedPosition vp : ValuedPosition.of(in)) {
            TreeSet<LocalDate> d = byInstrument.computeIfAbsent(vp.kind() + "|" + vp.id(), k -> new TreeSet<>());
            d.add(asOf);
            d.add(yearAgo);
            if (vp.position().firstBuyDate() != null) nifty.add(vp.position().firstBuyDate());
        }
        List<PointRequest> out = new ArrayList<>();
        for (Map.Entry<String, TreeSet<LocalDate>> e : byInstrument.entrySet()) {
            int bar = e.getKey().indexOf('|');
            out.add(new PointRequest(e.getKey().substring(0, bar), e.getKey().substring(bar + 1), new ArrayList<>(e.getValue())));
        }
        out.add(new PointRequest("INDEX", NIFTY_ID, new ArrayList<>(nifty)));
        return out;
    }

    private static Double pct(double ratio) { return Money.round2((ratio - 1.0) * 100.0); }

    private static OptionalDouble pos(OptionalDouble v) { return v.isPresent() && v.getAsDouble() > 0 ? v : OptionalDouble.empty(); }

    public static ReturnsResult compute(List<ValuedPosition> vps, LocalDate asOf, PricePoints points) {
        if (points == null || vps.isEmpty()) {
            return emptyWithTotals(vps);
        }
        LocalDate yearAgo = asOf.minusYears(1);
        OptionalDouble niftyNow = pos(points.value("INDEX", NIFTY_ID, asOf));
        OptionalDouble niftyThen = pos(points.value("INDEX", NIFTY_ID, yearAgo));
        Double niftyOneYear = niftyNow.isPresent() && niftyThen.isPresent()
                ? pct(niftyNow.getAsDouble() / niftyThen.getAsDouble()) : null;

        List<HoldingReturn> rows = new ArrayList<>();
        double sumValue1y = 0, sumBase1y = 0;
        double sumValueAll = 0, sumCostAll = 0;
        double sumValueSb = 0, sumCostSb = 0, niftySb = 0;
        int covered = 0;
        for (ValuedPosition vp : vps) {
            String kind = vp.kind().name();
            OptionalDouble then = pos(points.value(kind, vp.id(), yearAgo));
            OptionalDouble now = pos(points.value(kind, vp.id(), asOf));
            double nowPrice = now.isPresent() ? now.getAsDouble() : vp.price();
            Double oneYear = null;
            if (then.isPresent() && nowPrice > 0) {
                double ratio = nowPrice / then.getAsDouble();
                oneYear = pct(ratio);
                sumValue1y += vp.value();
                sumBase1y += vp.value() / ratio;
            }
            double cost = vp.cost();
            Double sinceBuy = null;
            Double niftySince = null;
            LocalDate buy = vp.position().firstBuyDate();
            if (buy != null && cost > 0) {
                sinceBuy = pct(vp.value() / cost);
                OptionalDouble nb = pos(points.value("INDEX", NIFTY_ID, buy));
                if (nb.isPresent() && niftyNow.isPresent()) {
                    niftySince = pct(niftyNow.getAsDouble() / nb.getAsDouble());
                    covered++;
                    sumValueSb += vp.value();
                    sumCostSb += cost;
                    niftySb += cost * niftyNow.getAsDouble() / nb.getAsDouble();
                }
            }
            sumValueAll += vp.value();
            sumCostAll += cost;
            long costInr = Money.roundRupees(cost);
            long valueInr = Money.roundRupees(vp.value());
            rows.add(new HoldingReturn(vp.kind(), vp.id(), vp.name(), oneYear, niftyOneYear, sinceBuy, niftySince,
                    costInr, valueInr, valueInr - costInr));
        }
        Double pf1y = sumBase1y > 0 ? pct(sumValue1y / sumBase1y) : null;
        Double pfSb = covered > 0 && sumCostSb > 0 ? pct(sumValueSb / sumCostSb) : null;
        Double niftyPfSb = covered > 0 && sumCostSb > 0 ? pct(niftySb / sumCostSb) : null;
        long costInr = Money.roundRupees(sumCostAll);
        long valueInr = Money.roundRupees(sumValueAll);
        return new ReturnsResult(pf1y, niftyOneYear, pfSb, niftyPfSb, covered, costInr, valueInr, valueInr - costInr,
                List.copyOf(rows));
    }

    private static ReturnsResult emptyWithTotals(List<ValuedPosition> vps) {
        List<HoldingReturn> rows = new ArrayList<>();
        double v = 0, c = 0;
        for (ValuedPosition vp : vps) {
            long costInr = Money.roundRupees(vp.cost());
            long valueInr = Money.roundRupees(vp.value());
            v += vp.value();
            c += vp.cost();
            rows.add(new HoldingReturn(vp.kind(), vp.id(), vp.name(), null, null, null, null, costInr, valueInr, valueInr - costInr));
        }
        long costInr = Money.roundRupees(c);
        long valueInr = Money.roundRupees(v);
        return new ReturnsResult(null, null, null, null, 0, costInr, valueInr, valueInr - costInr, List.copyOf(rows));
    }
}
