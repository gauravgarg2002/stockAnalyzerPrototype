package com.stockanalyzer.engine;

import com.stockanalyzer.engine.model.FundConstituent;
import com.stockanalyzer.engine.model.FundInfo;
import com.stockanalyzer.engine.model.PortfolioInput;
import com.stockanalyzer.engine.model.SizeBand;
import com.stockanalyzer.engine.model.StockInfo;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.function.Function;

/** Look-through exposure by company, sector and size (PLAN §3.2). */
public final class ExposureEngine {
    private ExposureEngine() { }

    public static final String DEBT_CASH = "DEBT_CASH";
    public static final String OTHER = "OTHER";
    public static final String DEBT_CASH_NAME = "Debt & cash";
    public static final String OTHER_NAME = "Other / undisclosed";

    public record ExposureSet(ExposureBreakdown company, ExposureBreakdown sector, ExposureBreakdown size) { }

    private record Dim(String key, String name, String kind, String symbol, boolean checkAvailable) { }

    private record Alloc(Dim company, Dim sector, Dim size, double value, boolean direct, String fundCode, String fundName) { }

    private static final Dim DEBT_CASH_DIM = new Dim(DEBT_CASH, DEBT_CASH_NAME, DEBT_CASH, null, false);
    private static final Dim OTHER_DIM = new Dim(OTHER, OTHER_NAME, OTHER, null, false);

    public static ExposureSet compute(PortfolioInput in) {
        return compute(ValuedPosition.of(in));
    }

    public static ExposureSet compute(List<ValuedPosition> vps) {
        List<Alloc> allocs = allocations(vps);
        double v = ValuedPosition.total(vps);
        long totalInr = v > 0 ? Money.roundRupees(v) : 0;
        return new ExposureSet(
                breakdown("COMPANY", allocs, totalInr, Alloc::company),
                breakdown("SECTOR", allocs, totalInr, Alloc::sector),
                breakdown("SIZE", allocs, totalInr, Alloc::size));
    }

    private static Dim sectorDim(String sector) {
        if (sector == null || sector.isBlank()) return OTHER_DIM;
        return new Dim(sector, sector, "SECTOR", null, false);
    }

    private static Dim sizeDim(SizeBand b) {
        if (b == null) return OTHER_DIM;
        return new Dim(b.name(), b.label(), "SIZE", null, false);
    }

    private static List<Alloc> allocations(List<ValuedPosition> vps) {
        List<Alloc> out = new ArrayList<>();
        // stocks first so a company keeps its own name when it also appears inside funds
        for (ValuedPosition vp : vps) {
            StockInfo s = vp.stock();
            if (s == null || !(vp.value() > 0)) continue;
            Dim company = new Dim(s.symbol(), s.name(), "COMPANY", s.symbol(), s.checkAvailable());
            out.add(new Alloc(company, sectorDim(s.sector()), sizeDim(s.sizeBand()), vp.value(), true, null, null));
        }
        for (ValuedPosition vp : vps) {
            FundInfo f = vp.fund();
            if (f == null || !(vp.value() > 0)) continue;
            double value = vp.value();
            double sumW = 0;
            for (FundConstituent c : f.constituents()) if (c.weightPct() > 0) sumW += c.weightPct();
            double debtCash = f.assetMix().debtPct() + f.assetMix().cashPct();
            double bracket = 100.0 - sumW - debtCash;
            double scale = 1.0;
            double otherPct = bracket;
            if (bracket < 0) {
                double target = Math.max(0.0, f.assetMix().equityPct() + f.assetMix().otherPct());
                scale = sumW > 0 ? target / sumW : 0.0;
                otherPct = 0.0;
            }
            for (FundConstituent c : f.constituents()) {
                if (!(c.weightPct() > 0)) continue;
                double amt = value * c.weightPct() * scale / 100.0;
                if (!(amt > 0)) continue;
                Dim company = new Dim(c.key(), c.name(), "COMPANY", c.symbol(), c.checkAvailable());
                out.add(new Alloc(company, sectorDim(c.sector()), sizeDim(c.sizeBand()), amt, false, f.schemeCode(), f.name()));
            }
            if (debtCash > 0) {
                out.add(new Alloc(DEBT_CASH_DIM, DEBT_CASH_DIM, DEBT_CASH_DIM, value * debtCash / 100.0, false, f.schemeCode(), f.name()));
            }
            if (otherPct > 1e-9) {
                out.add(new Alloc(OTHER_DIM, OTHER_DIM, OTHER_DIM, value * otherPct / 100.0, false, f.schemeCode(), f.name()));
            }
        }
        return out;
    }

    private static final class Acc {
        final Dim dim;
        double direct;
        double through;
        final Map<String, double[]> via = new LinkedHashMap<>();
        final Map<String, String> viaNames = new LinkedHashMap<>();

        Acc(Dim dim) { this.dim = dim; }

        double total() { return direct + through; }
    }

    private static ExposureBreakdown breakdown(String dimension, List<Alloc> allocs, long totalInr,
                                               Function<Alloc, Dim> sel) {
        Map<String, Acc> accs = new LinkedHashMap<>();
        for (Alloc a : allocs) {
            Dim d = sel.apply(a);
            Acc acc = accs.computeIfAbsent(d.key(), k -> new Acc(d));
            if (a.direct()) {
                acc.direct += a.value();
            } else {
                acc.through += a.value();
                acc.via.computeIfAbsent(a.fundCode(), k -> new double[1])[0] += a.value();
                acc.viaNames.putIfAbsent(a.fundCode(), a.fundName());
            }
        }
        if (accs.isEmpty() || totalInr <= 0) return new ExposureBreakdown(dimension, 0, List.of());

        List<Acc> list = new ArrayList<>(accs.values());
        int n = list.size();
        double denom = 0;
        for (Acc a : list) denom += a.total();
        double[] rawBp = new double[n];
        double[] rawInr = new double[n];
        double[] tieVal = new double[n];
        String[] keys = new String[n];
        for (int i = 0; i < n; i++) {
            Acc a = list.get(i);
            rawBp[i] = a.total() / denom * Bp.FULL;
            rawInr[i] = a.total() / denom * totalInr;
            tieVal[i] = a.total();
            keys[i] = a.dim.key();
        }
        long[] bps = Bp.largestRemainder(rawBp, tieVal, keys, Bp.FULL);
        long[] inrs = Bp.largestRemainder(rawInr, tieVal, keys, totalInr);

        List<ExposureLine> lines = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            Acc a = list.get(i);
            int totalBp = (int) bps[i];
            long lineInr = inrs[i];
            int directBp = (int) Math.max(0, Math.min(totalBp, halfUp(a.direct / denom * Bp.FULL)));
            long directInr = Math.max(0, Math.min(lineInr, halfUp(a.direct / denom * totalInr)));
            int throughBp = totalBp - directBp;
            long throughInr = lineInr - directInr;
            List<ExposureLine.ViaFund> via = new ArrayList<>();
            for (Map.Entry<String, double[]> e : a.via.entrySet()) {
                via.add(new ExposureLine.ViaFund(e.getKey(), a.viaNames.get(e.getKey()),
                        Money.roundRupees(e.getValue()[0])));
            }
            via.sort(Comparator.comparingLong(ExposureLine.ViaFund::inr).reversed()
                    .thenComparing(ExposureLine.ViaFund::schemeCode));
            lines.add(new ExposureLine(a.dim.key(), a.dim.name(), a.dim.kind(), a.dim.symbol(),
                    a.dim.checkAvailable(), lineInr, directInr, throughInr, totalBp, directBp, throughBp,
                    disp(lineInr, totalBp), disp(directInr, directBp), disp(throughInr, throughBp), via));
        }
        lines.sort(Comparator
                .comparingInt((ExposureLine l) -> bucketRank(l))
                .thenComparing(Comparator.comparingLong(ExposureLine::totalInr).reversed())
                .thenComparing(ExposureLine::key));
        return new ExposureBreakdown(dimension, totalInr, List.copyOf(lines));
    }

    private static int bucketRank(ExposureLine l) {
        if (DEBT_CASH.equals(l.kind())) return 1;
        if (OTHER.equals(l.kind())) return 2;
        return 0;
    }

    private static long halfUp(double v) {
        return BigDecimal.valueOf(v).setScale(0, RoundingMode.HALF_UP).longValue();
    }

    private static String disp(long inr, int bp) {
        return IndianFormat.formatInr(inr) + " (" + IndianFormat.formatPct(Bp.pct(bp)) + ")";
    }
}
