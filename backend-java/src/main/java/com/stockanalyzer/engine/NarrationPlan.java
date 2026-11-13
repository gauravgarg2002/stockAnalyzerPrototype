package com.stockanalyzer.engine;

import com.stockanalyzer.engine.MixEngine.MixLine;
import com.stockanalyzer.engine.model.Kind;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Builds the /internal/narrate request items (template ids and fact keys exactly as contract §B.12).
 * Java writes no sentences: it only chooses the template and supplies computed facts.
 */
public final class NarrationPlan {
    private NarrationPlan() { }

    public static final String WINDOW_LABEL = "1 year";
    public static final String NONE_NAME = "None";

    // item keys (echoed back by Python)
    public static final String SUMMARY_VALUE = "summary.0";
    public static final String SUMMARY_TOP_EXPOSURE = "summary.1";
    public static final String SUMMARY_RETURNS = "summary.2";
    public static final String FACT_OVERLAP = "fact.overlap";
    public static final String FACT_COST = "fact.cost";
    public static final String FACT_IDLE_CASH = "fact.idle_cash";
    public static final String EXPOSURE_COMPANY = "exposure.company";
    public static final String EXPOSURE_SECTOR = "exposure.sector";
    public static final String EXPOSURE_SIZE = "exposure.size";
    public static final String EXPOSURE_OTHER = "exposure.other";
    public static final String CONCENTRATION = "concentration";
    public static final String MIX_EQUITY_DEBT = "mix.equity_debt";
    public static final String MIX_STOCKS_FUNDS = "mix.stocks_funds";
    public static final String RETURNS_SINCE_BUY = "returns.since_buy";

    public static final String TIO_ASSUMPTION = "assumption";
    public static final String TIO_LARGEST_COMPANY = "largest_company";
    public static final String TIO_TOP_SECTOR = "top_sector";
    public static final String TIO_SIZE_MIX = "size_mix";
    public static final String TIO_HOLDINGS_COUNT = "holdings_count";
    public static final String TIO_OVERLAP = "overlap";
    public static final String TIO_COST = "cost";

    /** Small builder keeping insertion order. */
    private static final class F {
        final Map<String, FactValue> m = new LinkedHashMap<>();

        F text(String k, String v) { m.put(k, new FactValue(v, Units.TEXT)); return this; }

        F inr(String k, long v) { m.put(k, new FactValue(v, Units.INR)); return this; }

        F count(String k, long v) { m.put(k, new FactValue(v, Units.COUNT)); return this; }

        F pct(String k, double v) { m.put(k, new FactValue(v, Units.PCT)); return this; }

        F bp(String k, int bp) { return pct(k, Bp.pct(bp)); }

        F change(String k, double v) { m.put(k, new FactValue(v, Units.PCT_CHANGE)); return this; }
    }

    private static NarrateItem item(String key, String template, F f) {
        return new NarrateItem(key, template, f.m);
    }

    public static List<NarrateItem> forPortfolio(PortfolioResult r) {
        List<NarrateItem> items = new ArrayList<>();
        ReturnsEngine.ReturnsResult ret = r.returns();
        if (!r.hasHoldings()) {
            items.add(item(SUMMARY_VALUE, "pf.summary.empty", new F()));
            items.add(item(SUMMARY_RETURNS, "pf.summary.returns_unavailable", new F().text("windowLabel", WINDOW_LABEL)));
            items.addAll(mixItems(r));
            items.add(item(RETURNS_SINCE_BUY, "pf.returns.since_buy_unavailable", new F()));
            return items;
        }
        items.add(item(SUMMARY_VALUE, "pf.summary.value", new F()
                .inr("totalValueInr", r.valueInr()).count("stockCount", r.stockCount()).count("fundCount", r.fundCount())));
        ConcentrationEngine.ConcentrationResult c = r.concentration();
        if (c.largestKey() != null) {
            items.add(item(SUMMARY_TOP_EXPOSURE, "pf.summary.top_exposure", new F()
                    .text("companyName", c.largestName()).bp("companyPct", c.largestBp())
                    .bp("directPct", c.largestDirectBp()).bp("throughFundsPct", c.largestThroughFundsBp())));
        }
        if (ret.oneYearAvailable()) {
            items.add(item(SUMMARY_RETURNS, "pf.summary.returns", new F().text("windowLabel", WINDOW_LABEL)
                    .change("portfolioReturnPct", ret.portfolioOneYearPct()).change("niftyReturnPct", ret.niftyOneYearPct())));
        } else {
            items.add(item(SUMMARY_RETURNS, "pf.summary.returns_unavailable", new F().text("windowLabel", WINDOW_LABEL)));
        }
        items.addAll(factItems(r));
        if (c.largestKey() != null) {
            items.add(item(EXPOSURE_COMPANY, "pf.exposure.company", new F()
                    .text("companyName", c.largestName()).bp("companyPct", c.largestBp())
                    .bp("directPct", c.largestDirectBp()).bp("throughFundsPct", c.largestThroughFundsBp())
                    .count("companyCount", c.companyCount())));
        }
        if (c.topSectorName() != null) {
            items.add(item(EXPOSURE_SECTOR, "pf.exposure.sector", new F()
                    .text("sectorName", c.topSectorName()).bp("sectorPct", c.topSectorBp()).count("sectorCount", c.sectorCount())));
        }
        items.add(item(EXPOSURE_SIZE, "pf.exposure.size", new F()
                .bp("largePct", bpOf(r.sizeMix(), "LARGE")).bp("midPct", bpOf(r.sizeMix(), "MID"))
                .bp("smallPct", bpOf(r.sizeMix(), "SMALL")).bp("microPct", bpOf(r.sizeMix(), "MICRO"))
                .bp("debtCashPct", bpOf(r.sizeMix(), ExposureEngine.DEBT_CASH))));
        int other = bpOf(r.sizeMix(), ExposureEngine.OTHER);
        if (other > 0) items.add(item(EXPOSURE_OTHER, "pf.exposure.other", new F().bp("otherPct", other)));
        if (c.largestKey() != null) {
            items.add(item(CONCENTRATION, "pf.concentration", new F().bp("top5Pct", c.top5Bp()).count("holdingCount", c.holdingCount())));
        }
        items.addAll(mixItems(r));
        if (ret.sinceBuyAvailable()) {
            items.add(item(RETURNS_SINCE_BUY, "pf.returns.since_buy", new F()
                    .change("portfolioGainPct", ret.portfolioSinceBuyPct()).change("niftySameDatesPct", ret.niftySinceBuyPct())
                    .count("coveredCount", ret.sinceBuyCoveredCount())));
        } else {
            items.add(item(RETURNS_SINCE_BUY, "pf.returns.since_buy_unavailable", new F()));
        }
        return items;
    }

    /** Home needs the summary sentences and the three facts only. */
    public static List<NarrateItem> forHome(PortfolioResult r) {
        List<NarrateItem> out = new ArrayList<>();
        for (NarrateItem i : forPortfolio(r)) {
            if (i.key().startsWith("summary.") || (r.hasHoldings() && i.key().startsWith("fact."))) out.add(i);
        }
        if (!r.hasHoldings()) out.removeIf(i -> !i.key().equals(SUMMARY_VALUE));
        return out;
    }

    private static List<NarrateItem> factItems(PortfolioResult r) {
        List<NarrateItem> items = new ArrayList<>();
        // overlap
        if (r.overlapPairs().isEmpty()) {
            items.add(item(FACT_OVERLAP, "pf.fact.overlap_none", new F().count("fundCount", r.fundCount())));
        } else {
            OverlapEngine.OverlapPair p = r.overlapPairs().get(0);
            items.add(item(FACT_OVERLAP, "pf.fact.overlap", new F().text("fundA", p.nameA()).text("fundB", p.nameB())
                    .pct("overlapPct", p.result().pct()).count("commonCount", p.result().commonCount())));
        }
        // cost
        CostEngine.CostResult cost = r.cost();
        if (!cost.hasFunds()) {
            items.add(item(FACT_COST, "pf.fact.cost_none", new F()));
        } else if (!cost.hasRegularFunds()) {
            items.add(item(FACT_COST, "pf.fact.cost_direct_only", new F().inr("yearlyCostInr", cost.totalYearlyInr())));
        } else {
            items.add(item(FACT_COST, "pf.fact.cost", new F().inr("yearlyCostInr", cost.totalYearlyInr())
                    .inr("regularGapInr", cost.regularGapYearlyInr())));
        }
        // idle cash
        if (r.idleCashInr() > 0) {
            items.add(item(FACT_IDLE_CASH, "pf.fact.idle_cash", new F().inr("idleCashInr", Money.roundRupees(r.idleCashInr()))
                    .pct("idleCashPct", r.idleCashPct())));
        } else {
            items.add(item(FACT_IDLE_CASH, "pf.fact.idle_cash_none", new F()));
        }
        return items;
    }

    private static List<NarrateItem> mixItems(PortfolioResult r) {
        List<NarrateItem> items = new ArrayList<>();
        items.add(item(MIX_EQUITY_DEBT, "pf.mix.equity_debt", new F()
                .bp("equityPct", bpOf(r.equityDebt(), "EQUITY")).bp("debtCashPct", bpOf(r.equityDebt(), "DEBT_CASH"))
                .bp("otherPct", bpOf(r.equityDebt(), "OTHER"))));
        items.add(item(MIX_STOCKS_FUNDS, "pf.mix.stocks_funds", new F()
                .bp("stocksPct", bpOf(r.stocksFunds(), "STOCKS")).bp("fundsPct", bpOf(r.stocksFunds(), "FUNDS"))));
        return items;
    }

    private static int bpOf(List<MixLine> lines, String key) {
        for (MixLine l : lines) if (l.key().equals(key)) return l.bp();
        return 0;
    }

    public static List<NarrateItem> forTryItOn(TryItOnEngine.TryItOnResult t) {
        List<NarrateItem> items = new ArrayList<>();
        if (t.mode() == TryItOnEngine.Mode.SIP) {
            items.add(item(TIO_ASSUMPTION, "tio.assumption.sip", new F().text("instrumentName", t.name())
                    .inr("amountInr", Money.roundRupees(t.amountInr())).count("months", t.months())
                    .inr("totalInr", t.addedValueInr())));
        } else {
            items.add(item(TIO_ASSUMPTION, "tio.assumption.lump_sum", new F().text("instrumentName", t.name())
                    .inr("amountInr", Money.roundRupees(t.amountInr()))));
        }
        PortfolioResult b = t.before();
        PortfolioResult a = t.after();
        items.add(item(TIO_LARGEST_COMPANY, "tio.largest_company", new F()
                .text("beforeName", nameOr(b.concentration().largestName())).bp("beforePct", b.concentration().largestBp())
                .text("afterName", nameOr(a.concentration().largestName())).bp("afterPct", a.concentration().largestBp())));
        items.add(item(TIO_TOP_SECTOR, "tio.top_sector", new F()
                .text("beforeName", nameOr(b.concentration().topSectorName())).bp("beforePct", b.concentration().topSectorBp())
                .text("afterName", nameOr(a.concentration().topSectorName())).bp("afterPct", a.concentration().topSectorBp())));
        int best = 0, bestAbs = -1;
        for (int i = 0; i < b.sizeMix().size(); i++) {
            int abs = Math.abs(a.sizeMix().get(i).bp() - b.sizeMix().get(i).bp());
            if (abs > bestAbs) { bestAbs = abs; best = i; }
        }
        items.add(item(TIO_SIZE_MIX, "tio.size_mix", new F().text("bandName", b.sizeMix().get(best).label())
                .bp("beforePct", b.sizeMix().get(best).bp()).bp("afterPct", a.sizeMix().get(best).bp())));
        if (t.alreadyHeld()) {
            items.add(item(TIO_HOLDINGS_COUNT, "tio.holdings_count_same", new F().count("count", a.holdingCount())));
        } else {
            items.add(item(TIO_HOLDINGS_COUNT, "tio.holdings_count", new F()
                    .count("beforeCount", b.holdingCount()).count("afterCount", a.holdingCount())));
        }
        if (t.kind() == Kind.FUND) {
            if (t.fundOverlaps().isEmpty() || t.fundOverlaps().get(0).commonCount() == 0) {
                items.add(item(TIO_OVERLAP, "tio.overlap_none_fund", new F().text("instrumentName", t.name())));
            } else {
                TryItOnEngine.FundOverlap top = t.fundOverlaps().get(0);
                items.add(item(TIO_OVERLAP, "tio.overlap_fund", new F().text("instrumentName", t.name())
                        .text("fundName", top.name()).pct("overlapPct", top.pct())));
            }
        } else if (t.stockInFunds().isEmpty()) {
            items.add(item(TIO_OVERLAP, "tio.overlap_none_stock", new F().text("instrumentName", t.name())
                    .bp("beforePct", t.exposureBeforeBp()).bp("afterPct", t.exposureAfterBp())));
        } else {
            items.add(item(TIO_OVERLAP, "tio.overlap_stock", new F().text("instrumentName", t.name())
                    .count("fundsHoldingCount", t.stockInFunds().size())
                    .bp("beforePct", t.exposureBeforeBp()).bp("afterPct", t.exposureAfterBp())));
        }
        if (t.kind() == Kind.FUND) {
            items.add(item(TIO_COST, "tio.cost", new F().inr("beforeInr", b.cost().totalYearlyInr())
                    .inr("afterInr", a.cost().totalYearlyInr())));
        } else {
            items.add(item(TIO_COST, "tio.cost_stock", new F().inr("beforeInr", b.cost().totalYearlyInr())));
        }
        return items;
    }

    private static String nameOr(String n) { return n == null ? NONE_NAME : n; }
}
