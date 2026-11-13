package com.stockanalyzer.engine;

import com.stockanalyzer.engine.model.FundConstituent;
import com.stockanalyzer.engine.model.FundInfo;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/** Fund overlap: for each company held by both funds take the lower weight, then sum. */
public final class OverlapEngine {
    private OverlapEngine() { }

    public record CommonHolding(String key, String name, double weightA, double weightB, double minWeight) { }

    public record OverlapResult(double pct, int commonCount, List<CommonHolding> topCommon) { }

    public record OverlapPair(String schemeCodeA, String nameA, String schemeCodeB, String nameB,
                              OverlapResult result, LocalDate asOf) { }

    private static Map<String, Double> weights(FundInfo f, Map<String, String> names) {
        Map<String, Double> w = new LinkedHashMap<>();
        for (FundConstituent c : f.constituents()) {
            if (!(c.weightPct() > 0)) continue;
            w.merge(c.key(), c.weightPct(), Double::sum);
            names.putIfAbsent(c.key(), c.name());
        }
        return w;
    }

    public static OverlapResult overlap(FundInfo a, FundInfo b) {
        Map<String, String> names = new LinkedHashMap<>();
        Map<String, Double> wa = weights(a, names);
        Map<String, Double> wb = weights(b, new LinkedHashMap<>());
        BigDecimal sum = BigDecimal.ZERO;
        List<CommonHolding> common = new ArrayList<>();
        for (Map.Entry<String, Double> e : wa.entrySet()) {
            Double other = wb.get(e.getKey());
            if (other == null) continue;
            double min = Math.min(e.getValue(), other);
            sum = sum.add(BigDecimal.valueOf(min));
            common.add(new CommonHolding(e.getKey(), names.get(e.getKey()), e.getValue(), other, min));
        }
        common.sort(Comparator.comparingDouble(CommonHolding::minWeight).reversed().thenComparing(CommonHolding::key));
        List<CommonHolding> top = new ArrayList<>(common.subList(0, Math.min(5, common.size())));
        return new OverlapResult(sum.setScale(2, RoundingMode.HALF_UP).doubleValue(), common.size(), top);
    }

    /** Every unordered pair of distinct funds, highest overlap first. */
    public static List<OverlapPair> pairs(List<FundInfo> funds) {
        List<FundInfo> distinct = new ArrayList<>();
        Set<String> seen = new LinkedHashSet<>();
        for (FundInfo f : funds) if (seen.add(f.schemeCode())) distinct.add(f);
        List<OverlapPair> out = new ArrayList<>();
        for (int i = 0; i < distinct.size(); i++) {
            for (int j = i + 1; j < distinct.size(); j++) {
                FundInfo a = distinct.get(i);
                FundInfo b = distinct.get(j);
                out.add(new OverlapPair(a.schemeCode(), a.name(), b.schemeCode(), b.name(), overlap(a, b), oldest(a, b)));
            }
        }
        out.sort(Comparator.comparingDouble((OverlapPair p) -> p.result().pct()).reversed()
                .thenComparing(Comparator.comparingInt((OverlapPair p) -> p.result().commonCount()).reversed())
                .thenComparing(OverlapPair::schemeCodeA).thenComparing(OverlapPair::schemeCodeB));
        return out;
    }

    private static LocalDate oldest(FundInfo a, FundInfo b) {
        LocalDate x = a.portfolioDate();
        LocalDate y = b.portfolioDate();
        if (x == null) return y;
        if (y == null) return x;
        return x.isBefore(y) ? x : y;
    }
}
