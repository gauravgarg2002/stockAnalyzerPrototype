package com.stockanalyzer.engine;

import com.stockanalyzer.engine.model.FundConstituent;
import com.stockanalyzer.engine.model.FundInfo;
import com.stockanalyzer.engine.model.Kind;
import com.stockanalyzer.engine.model.PortfolioInput;
import com.stockanalyzer.engine.model.Position;
import com.stockanalyzer.engine.model.StockInfo;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

/**
 * What-if: add a lump sum, or a SIP of months x amount, to a candidate at today's price. New money; nothing is
 * taken from other holdings. The candidate must be present in the input's stocks/funds maps.
 */
public final class TryItOnEngine {
    private TryItOnEngine() { }

    public enum Mode { LUMP_SUM, SIP }

    public record FundOverlap(String schemeCode, String name, double pct, int commonCount) { }

    public record StockInFund(String schemeCode, String name, double weightPct) { }

    public record TryItOnResult(Kind kind, String id, String name, Mode mode, Integer months, double amountInr,
                                long addedValueInr, boolean alreadyHeld,
                                PortfolioResult before, PortfolioResult after,
                                List<FundOverlap> fundOverlaps, List<StockInFund> stockInFunds,
                                int exposureBeforeBp, int exposureAfterBp) { }

    public static TryItOnResult run(PortfolioInput input, Kind kind, String id, Mode mode, double amountInr, Integer months) {
        if (!(amountInr > 0)) throw new IllegalArgumentException("amountInr must be positive");
        int m = 1;
        if (mode == Mode.SIP) {
            m = months == null ? 12 : months;
            if (m < 1 || m > 60) throw new IllegalArgumentException("months must be 1 to 60");
        }
        double added = mode == Mode.SIP ? amountInr * m : amountInr;

        String name;
        double price;
        FundInfo candidateFund = null;
        if (kind == Kind.STOCK) {
            StockInfo s = input.stocks().get(id);
            if (s == null) throw new IllegalArgumentException("Unknown stock " + id);
            name = s.name();
            price = s.lastPrice();
        } else {
            candidateFund = input.funds().get(id);
            if (candidateFund == null) throw new IllegalArgumentException("Unknown fund " + id);
            name = candidateFund.name();
            price = candidateFund.nav();
        }
        if (!(price > 0)) throw new IllegalArgumentException("No price for " + id);

        List<Position> held = Position.aggregate(input.positions());
        boolean alreadyHeld = false;
        for (Position p : held) if (p.kind() == kind && p.id().equals(id)) alreadyHeld = true;

        PortfolioResult before = PortfolioEngine.compute(input.withPositions(held), null);
        List<Position> afterPositions = new ArrayList<>(held);
        afterPositions.add(new Position(kind, id, added / price, price, null));
        PortfolioResult after = PortfolioEngine.compute(input.withPositions(afterPositions), null);

        List<FundOverlap> fundOverlaps = new ArrayList<>();
        List<StockInFund> stockInFunds = new ArrayList<>();
        int exposureBefore = 0, exposureAfter = 0;
        for (ValuedPosition vp : ValuedPosition.of(input.withPositions(held))) {
            FundInfo f = vp.fund();
            if (f == null || !(vp.value() > 0)) continue;
            if (kind == Kind.FUND) {
                if (f.schemeCode().equals(id)) continue;
                OverlapEngine.OverlapResult r = OverlapEngine.overlap(candidateFund, f);
                fundOverlaps.add(new FundOverlap(f.schemeCode(), f.name(), r.pct(), r.commonCount()));
            } else {
                double w = 0;
                for (FundConstituent c : f.constituents()) if (id.equals(c.key()) && c.weightPct() > 0) w += c.weightPct();
                if (w > 0) stockInFunds.add(new StockInFund(f.schemeCode(), f.name(), Money.round2(w)));
            }
        }
        fundOverlaps.sort(Comparator.comparingDouble(FundOverlap::pct).reversed().thenComparing(FundOverlap::schemeCode));
        stockInFunds.sort(Comparator.comparingDouble(StockInFund::weightPct).reversed().thenComparing(StockInFund::schemeCode));
        if (kind == Kind.STOCK) {
            ExposureLine b = before.company().find(id);
            ExposureLine a = after.company().find(id);
            exposureBefore = b == null ? 0 : b.totalBp();
            exposureAfter = a == null ? 0 : a.totalBp();
        }
        return new TryItOnResult(kind, id, name, mode, mode == Mode.SIP ? m : null, amountInr,
                Money.roundRupees(added), alreadyHeld, before, after, fundOverlaps, stockInFunds,
                exposureBefore, exposureAfter);
    }
}
