package com.stockanalyzer.engine;

import com.stockanalyzer.engine.model.FundInfo;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

/** Yearly fund cost in rupees and the regular-versus-direct gap. */
public final class CostEngine {
    private CostEngine() { }

    public record FundCost(String schemeCode, String name, String planType, long valueInr, Double terPct,
                           Long yearlyCostInr, String twinSchemeCode, String twinName, Double twinTerPct,
                           Double categoryMedianTerPct, Long yearlyGapInr) { }

    public record CostResult(long totalYearlyInr, long regularGapYearlyInr, boolean hasFunds,
                             boolean hasRegularFunds, boolean hasRegularWithTwin, List<FundCost> funds) { }

    public static CostResult compute(List<ValuedPosition> vps) {
        double total = 0;
        double gapTotal = 0;
        boolean hasRegular = false;
        boolean hasRegularTwin = false;
        List<FundCost> funds = new ArrayList<>();
        List<ValuedPosition> fundPositions = new ArrayList<>();
        for (ValuedPosition vp : vps) if (vp.fund() != null && vp.value() > 0) fundPositions.add(vp);
        fundPositions.sort(Comparator.comparingDouble(ValuedPosition::value).reversed().thenComparing(ValuedPosition::id));
        for (ValuedPosition vp : fundPositions) {
            FundInfo f = vp.fund();
            Long cost = null;
            Long gap = null;
            if (f.terPct() != null) {
                double c = vp.value() * f.terPct() / 100.0;
                total += c;
                cost = Money.roundRupees(c);
            }
            if (f.isRegular()) {
                hasRegular = true;
                if (f.twinSchemeCode() != null && f.twinTerPct() != null && f.terPct() != null) {
                    hasRegularTwin = true;
                    double g = vp.value() * (f.terPct() - f.twinTerPct()) / 100.0;
                    gapTotal += g;
                    gap = Money.roundRupees(g);
                }
            }
            funds.add(new FundCost(f.schemeCode(), f.name(), f.planType(), Money.roundRupees(vp.value()), f.terPct(),
                    cost, f.twinSchemeCode(), f.twinName(), f.twinTerPct(), f.categoryMedianTerPct(), gap));
        }
        return new CostResult(Money.roundRupees(total), Money.roundRupees(gapTotal), !fundPositions.isEmpty(),
                hasRegular, hasRegularTwin, List.copyOf(funds));
    }
}
