package com.stockanalyzer.engine;

import com.stockanalyzer.engine.model.FundInfo;
import com.stockanalyzer.engine.model.PortfolioInput;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

/** Facade: positions in, every portfolio number out. Pure and deterministic. */
public final class PortfolioEngine {
    private PortfolioEngine() { }

    /** points may be null: returns are then left empty (used by callers that need no returns). */
    public static PortfolioResult compute(PortfolioInput in, PricePoints points) {
        List<ValuedPosition> vps = new ArrayList<>();
        for (ValuedPosition vp : ValuedPosition.of(in)) if (vp.value() > 0) vps.add(vp);
        vps.sort(Comparator.comparingDouble(ValuedPosition::value).reversed()
                .thenComparing(vp -> vp.kind().name()).thenComparing(ValuedPosition::id));

        double v = ValuedPosition.total(vps);
        long valueInr = v > 0 ? Money.roundRupees(v) : 0;
        double invested = 0;
        int stocks = 0, funds = 0;
        List<FundInfo> heldFunds = new ArrayList<>();
        for (ValuedPosition vp : vps) {
            invested += vp.cost();
            if (vp.stock() != null) stocks++;
            else { funds++; heldFunds.add(vp.fund()); }
        }
        int holdingCount = vps.size();

        ExposureEngine.ExposureSet es = ExposureEngine.compute(vps);
        ConcentrationEngine.ConcentrationResult conc = ConcentrationEngine.compute(es, holdingCount);
        List<OverlapEngine.OverlapPair> pairs = OverlapEngine.pairs(heldFunds);
        CostEngine.CostResult cost = CostEngine.compute(vps);
        MixEngine.MixResult mix = MixEngine.compute(vps, valueInr);
        List<MixEngine.MixLine> sizeMix = MixEngine.sizeMix(es.size());
        ReturnsEngine.ReturnsResult returns = ReturnsEngine.compute(vps, in.asOf(), points);

        // holdings: weights and rupees by largest remainder so they add up exactly
        int n = vps.size();
        double[] rawBp = new double[n], rawInr = new double[n], tie = new double[n];
        String[] keys = new String[n];
        for (int i = 0; i < n; i++) {
            ValuedPosition vp = vps.get(i);
            rawBp[i] = vp.value() / v * Bp.FULL;
            rawInr[i] = vp.value() / v * valueInr;
            tie[i] = vp.value();
            keys[i] = vp.kind().name() + "|" + vp.id();
        }
        long[] bps = n == 0 ? new long[0] : Bp.largestRemainder(rawBp, tie, keys, Bp.FULL);
        long[] inrs = n == 0 ? new long[0] : Bp.largestRemainder(rawInr, tie, keys, valueInr);
        List<PortfolioResult.HoldingValue> holdings = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            ValuedPosition vp = vps.get(i);
            holdings.add(new PortfolioResult.HoldingValue(vp.kind(), vp.id(), vp.name(), vp.position().quantity(),
                    vp.position().avgPrice(), vp.price(), inrs[i], (int) bps[i], Money.roundRupees(vp.cost()),
                    vp.position().firstBuyDate()));
        }
        return new PortfolioResult(in.asOf(), holdingCount > 0, valueInr, Money.roundRupees(invested), in.idleCashInr(),
                Money.roundRupees(v + in.idleCashInr()), stocks, funds, holdingCount,
                es.company(), es.sector(), es.size(), conc, pairs, cost, mix.equityDebt(), mix.stocksFunds(), sizeMix,
                List.copyOf(holdings), returns);
    }
}
