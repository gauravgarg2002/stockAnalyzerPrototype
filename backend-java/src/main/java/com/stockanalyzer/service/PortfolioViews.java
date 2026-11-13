package com.stockanalyzer.service;

import com.stockanalyzer.engine.CostEngine;
import com.stockanalyzer.engine.ExposureBreakdown;
import com.stockanalyzer.engine.ExposureLine;
import com.stockanalyzer.engine.MixEngine;
import com.stockanalyzer.engine.NarrationPlan;
import com.stockanalyzer.engine.OverlapEngine;
import com.stockanalyzer.engine.PortfolioResult;
import com.stockanalyzer.engine.ReturnsEngine;
import com.stockanalyzer.engine.Units;
import com.stockanalyzer.engine.model.Kind;
import com.stockanalyzer.service.PortfolioService.GroupedHolding;
import com.stockanalyzer.service.PortfolioService.Snapshot;
import com.stockanalyzer.python.dto.PyDto.BundleFund;
import com.stockanalyzer.python.dto.PyDto.BundleStock;
import com.stockanalyzer.web.dto.PortfolioDto.CommonHoldingView;
import com.stockanalyzer.web.dto.PortfolioDto.Concentration;
import com.stockanalyzer.web.dto.PortfolioDto.CostFundView;
import com.stockanalyzer.web.dto.PortfolioDto.CostsSection;
import com.stockanalyzer.web.dto.PortfolioDto.DirectTwinView;
import com.stockanalyzer.web.dto.PortfolioDto.Exposure;
import com.stockanalyzer.web.dto.PortfolioDto.FundRef;
import com.stockanalyzer.web.dto.PortfolioDto.HoldingRow;
import com.stockanalyzer.web.dto.PortfolioDto.MixSection;
import com.stockanalyzer.web.dto.PortfolioDto.OverlapPairView;
import com.stockanalyzer.web.dto.PortfolioDto.OverlapSection;
import com.stockanalyzer.web.dto.PortfolioDto.PortfolioResponse;
import com.stockanalyzer.web.dto.PortfolioDto.ReturnRow;
import com.stockanalyzer.web.dto.PortfolioDto.ReturnsSection;
import com.stockanalyzer.web.dto.PortfolioDto.Totals;
import com.stockanalyzer.web.dto.Shared.Comparison;
import com.stockanalyzer.web.dto.Shared.ExposureBreakdownView;
import com.stockanalyzer.web.dto.Shared.ExposureLineView;
import com.stockanalyzer.web.dto.Shared.Figure;
import com.stockanalyzer.web.dto.Shared.MixLineView;
import com.stockanalyzer.web.dto.Shared.PortfolioFact;
import com.stockanalyzer.web.dto.Shared.Sentence;
import com.stockanalyzer.web.dto.Shared.ViaFundView;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Turns engine results and Python sentences into the public portfolio shapes (contract A.2 and A.3). */
final class PortfolioViews {
    private PortfolioViews() { }

    static final String BENCHMARK_NAME = "Nifty 50";
    static final String NIFTY_SAME_DATES = "Nifty 50, same dates";

    // ---- small helpers ------------------------------------------------------------------------------------------

    static List<Sentence> pick(Map<String, Sentence> sentences, String... keys) {
        List<Sentence> out = new ArrayList<>();
        for (String k : keys) {
            Sentence s = sentences.get(k);
            if (s != null) out.add(s);
        }
        return out;
    }

    static ExposureLineView line(ExposureLine l) {
        List<ViaFundView> via = new ArrayList<>();
        for (ExposureLine.ViaFund v : l.viaFunds()) via.add(new ViaFundView(v.schemeCode(), v.name(), v.inr()));
        return new ExposureLineView(l.key(), l.name(), l.kind(), l.symbol(), l.checkAvailable(), l.totalInr(),
                l.directInr(), l.throughFundsInr(), l.totalPct(), l.directPct(), l.throughFundsPct(), l.display(),
                l.directDisplay(), l.throughFundsDisplay(), via);
    }

    static ExposureBreakdownView breakdown(ExposureBreakdown b, List<Sentence> sentences) {
        List<ExposureLineView> lines = new ArrayList<>();
        for (ExposureLine l : b.lines()) lines.add(line(l));
        return new ExposureBreakdownView(b.dimension(), b.totalInr(), lines, sentences);
    }

    static List<MixLineView> mix(List<MixEngine.MixLine> lines) {
        List<MixLineView> out = new ArrayList<>();
        for (MixEngine.MixLine l : lines) out.add(new MixLineView(l.key(), l.label(), l.valueInr(), l.pct(), l.display()));
        return out;
    }

    /** The first five COMPANY lines (buckets excluded). */
    static List<ExposureLineView> topCompanies(PortfolioResult r, int n) {
        List<ExposureLineView> out = new ArrayList<>();
        for (ExposureLine l : r.company().lines()) {
            if (l.isBucket()) continue;
            out.add(line(l));
            if (out.size() >= n) break;
        }
        return out;
    }

    static List<Comparison> one(Comparison c) {
        List<Comparison> l = new ArrayList<>();
        l.add(c);
        return l;
    }

    // ---- facts --------------------------------------------------------------------------------------------------

    static List<PortfolioFact> facts(PortfolioResult r, Map<String, Sentence> s) {
        List<PortfolioFact> out = new ArrayList<>();
        if (!r.hasHoldings()) return out;
        String asOf = r.asOf().toString();

        List<Figure> overlapFigs = new ArrayList<>();
        if (!r.overlapPairs().isEmpty()) {
            OverlapEngine.OverlapPair p = r.overlapPairs().get(0);
            overlapFigs.add(Figures.calc("overlap_top_pair", "Highest overlap between two of your funds", p.result().pct(),
                    Units.PCT, p.asOf() == null ? asOf : p.asOf().toString(), List.of(), "fund_overlap"));
        }
        if (s.get(NarrationPlan.FACT_OVERLAP) != null) {
            out.add(new PortfolioFact("overlap", s.get(NarrationPlan.FACT_OVERLAP), overlapFigs));
        }

        CostEngine.CostResult c = r.cost();
        List<Comparison> costCmp = new ArrayList<>();
        if (c.hasRegularWithTwin()) {
            costCmp.add(Figures.cmp("PLAN_TWIN", "Same funds as direct plans", c.totalYearlyInr() - c.regularGapYearlyInr(), Units.INR));
        }
        List<Figure> costFigs = new ArrayList<>();
        costFigs.add(Figures.calc("yearly_fund_cost", "Yearly fund fees", c.totalYearlyInr(), Units.INR, asOf, costCmp, "expense_ratio"));
        costFigs.add(Figures.calc("regular_plan_gap", "Extra yearly fees of regular plans", c.regularGapYearlyInr(), Units.INR, asOf, List.of()));
        if (s.get(NarrationPlan.FACT_COST) != null) out.add(new PortfolioFact("cost", s.get(NarrationPlan.FACT_COST), costFigs));

        List<Figure> idleFigs = new ArrayList<>();
        idleFigs.add(idleCashFigure(r));
        if (s.get(NarrationPlan.FACT_IDLE_CASH) != null) {
            out.add(new PortfolioFact("idle_cash", s.get(NarrationPlan.FACT_IDLE_CASH), idleFigs));
        }
        return out;
    }

    static Figure idleCashFigure(PortfolioResult r) {
        return Figures.calc("idle_cash", "Idle cash in your trading account", Math.round(r.idleCashInr()), Units.INR,
                r.asOf().toString(), one(Figures.cmp("PREVIOUS_PERIOD", "Value of your holdings", r.valueInr(), Units.INR)), "idle_cash");
    }

    // ---- /api/portfolio ------------------------------------------------------------------------------------------

    static PortfolioResponse portfolio(Snapshot snap, PortfolioResult r, Map<String, Sentence> s) {
        String asOf = r.asOf().toString();
        Totals totals = new Totals(
                Figures.calc("holdings_value", "Value of your holdings", r.valueInr(), Units.INR, asOf,
                        one(Figures.cmp("PREVIOUS_PERIOD", "Amount you put in", r.investedInr(), Units.INR))),
                Figures.calc("invested", "Amount you put in", r.investedInr(), Units.INR, asOf, List.of()),
                idleCashFigure(r),
                Figures.calc("total_with_cash", "Holdings plus idle cash", r.totalWithCashInr(), Units.INR, asOf,
                        one(Figures.cmp("PREVIOUS_PERIOD", "Holdings without cash", r.valueInr(), Units.INR))));

        List<Sentence> summary = r.hasHoldings()
                ? pick(s, NarrationPlan.SUMMARY_VALUE, NarrationPlan.SUMMARY_TOP_EXPOSURE, NarrationPlan.SUMMARY_RETURNS)
                : pick(s, NarrationPlan.SUMMARY_VALUE);

        Exposure exposure = new Exposure(
                breakdown(r.company(), pick(s, NarrationPlan.EXPOSURE_COMPANY)),
                breakdown(r.sector(), pick(s, NarrationPlan.EXPOSURE_SECTOR)),
                breakdown(r.size(), pick(s, NarrationPlan.EXPOSURE_SIZE, NarrationPlan.EXPOSURE_OTHER)));

        return new PortfolioResponse(snap.sampleData(), asOf, snap.connected(), r.hasHoldings(), totals, summary,
                facts(r, s), exposure, concentration(r, s), overlap(r, s), costs(r, s),
                new MixSection(mix(r.equityDebt()), mix(r.stocksFunds()),
                        pick(s, NarrationPlan.MIX_EQUITY_DEBT, NarrationPlan.MIX_STOCKS_FUNDS)),
                returns(r, s), holdingRows(snap, r));
    }

    private static Concentration concentration(PortfolioResult r, Map<String, Sentence> s) {
        var c = r.concentration();
        String asOf = r.asOf().toString();
        int n = c.holdingCount();
        List<Comparison> largestCmp = new ArrayList<>();
        List<Comparison> top5Cmp = new ArrayList<>();
        if (n > 0) {
            largestCmp.add(Figures.cmp("THRESHOLD", "Equal split across your holdings", c.equalSplitPct(), Units.PCT));
            top5Cmp.add(Figures.cmp("THRESHOLD", "Equal split across your holdings",
                    Math.min(100.0, Math.round(c.equalSplitPct() * 5 * 100.0) / 100.0), Units.PCT));
        }
        return new Concentration(
                Figures.calc("largest_company", "Largest company exposure", c.largestBp() / 100.0, Units.PCT, asOf, largestCmp,
                        "look_through_exposure"),
                Figures.calc("top5_companies", "Five largest companies together", c.top5Bp() / 100.0, Units.PCT, asOf, top5Cmp),
                Figures.calc("top_sector", "Largest sector", c.topSectorBp() / 100.0, Units.PCT, asOf, List.of()),
                Figures.calc("company_count", "Companies you own pieces of", (long) c.companyCount(), Units.COUNT, asOf,
                        one(Figures.cmp("THRESHOLD", "Number of holdings", (long) n, Units.COUNT))),
                Figures.calc("holding_count", "Number of holdings", (long) n, Units.COUNT, asOf, List.of()),
                pick(s, NarrationPlan.CONCENTRATION));
    }

    private static OverlapSection overlap(PortfolioResult r, Map<String, Sentence> s) {
        List<OverlapPairView> pairs = new ArrayList<>();
        for (OverlapEngine.OverlapPair p : r.overlapPairs()) {
            List<CommonHoldingView> common = new ArrayList<>();
            for (OverlapEngine.CommonHolding h : p.result().topCommon()) {
                common.add(new CommonHoldingView(h.key(), h.name(), h.weightA(), h.weightB(), h.minWeight()));
            }
            Figure fig = Figures.calc("overlap_" + p.schemeCodeA() + "_" + p.schemeCodeB(), "Overlap", p.result().pct(),
                    Units.PCT, p.asOf() == null ? r.asOf().toString() : p.asOf().toString(), List.of(), "fund_overlap");
            pairs.add(new OverlapPairView(new FundRef(p.schemeCodeA(), p.nameA()), new FundRef(p.schemeCodeB(), p.nameB()),
                    fig, p.result().commonCount(), common));
        }
        return new OverlapSection(pairs, r.hasHoldings() ? pick(s, NarrationPlan.FACT_OVERLAP) : List.of());
    }

    private static CostsSection costs(PortfolioResult r, Map<String, Sentence> s) {
        CostEngine.CostResult c = r.cost();
        String asOf = r.asOf().toString();
        List<CostFundView> funds = new ArrayList<>();
        for (CostEngine.FundCost f : c.funds()) {
            boolean hasTwin = f.yearlyGapInr() != null && f.twinSchemeCode() != null;
            List<Comparison> terCmp = new ArrayList<>();
            if (hasTwin) {
                terCmp.add(Figures.cmp("PLAN_TWIN", "Direct plan of the same fund", f.twinTerPct(), Units.PCT));
            } else if (f.categoryMedianTerPct() != null) {
                terCmp.add(Figures.cmp("CATEGORY", "Median of its category", f.categoryMedianTerPct(), Units.PCT));
            }
            funds.add(new CostFundView(f.schemeCode(), f.name(), f.planType(),
                    Figures.calc("fund_value", "Value of this fund", f.valueInr(), Units.INR, asOf, List.of()),
                    Figures.calc("expense_ratio", "Yearly fee (expense ratio)", f.terPct(), Units.PCT, asOf, terCmp, "expense_ratio"),
                    Figures.calc("yearly_cost", "Yearly fee in rupees", f.yearlyCostInr(), Units.INR, asOf, List.of()),
                    hasTwin ? new DirectTwinView(f.twinSchemeCode(), f.twinName(), f.twinTerPct()) : null,
                    hasTwin ? Figures.calc("yearly_gap", "Extra yearly fee compared with the direct plan", f.yearlyGapInr(),
                            Units.INR, asOf, List.of()) : null));
        }
        return new CostsSection(
                Figures.calc("yearly_fund_cost", "Yearly fund fees", c.totalYearlyInr(), Units.INR, asOf, List.of(), "expense_ratio"),
                Figures.calc("regular_plan_gap", "Extra yearly fees of regular plans", c.regularGapYearlyInr(), Units.INR, asOf, List.of()),
                funds, r.hasHoldings() ? pick(s, NarrationPlan.FACT_COST) : List.of());
    }

    // ---- returns ------------------------------------------------------------------------------------------------

    private static Figure oneYearFigure(Double pct, Double nifty, String asOf) {
        return Figures.calc("return_1y", "Change in the last 1 year", pct, Units.PCT_CHANGE, asOf,
                one(Figures.cmp("INDEX", NIFTY_SAME_DATES, nifty, Units.PCT_CHANGE)));
    }

    private static Figure sinceBuyFigure(Double pct, Double nifty, String asOf) {
        if (pct == null) return null;
        return Figures.calc("return_since_buy", "Change since you bought", pct, Units.PCT_CHANGE, asOf,
                one(Figures.cmp("INDEX", NIFTY_SAME_DATES, nifty, Units.PCT_CHANGE)));
    }

    private static Figure gainFigure(long gain, long cost, String asOf) {
        return Figures.calc("gain", "Gain or loss in rupees", gain, Units.INR, asOf,
                one(Figures.cmp("PREVIOUS_PERIOD", "Amount you put in", cost, Units.INR)));
    }

    private static ReturnsSection returns(PortfolioResult r, Map<String, Sentence> s) {
        ReturnsEngine.ReturnsResult ret = r.returns();
        String asOf = r.asOf().toString();
        ReturnRow portfolio = new ReturnRow("PORTFOLIO", "PORTFOLIO", "All your holdings",
                oneYearFigure(ret.portfolioOneYearPct(), ret.niftyOneYearPct(), asOf),
                sinceBuyFigure(ret.portfolioSinceBuyPct(), ret.niftySinceBuyPct(), asOf),
                gainFigure(ret.gainInr(), ret.costInr(), asOf));
        List<ReturnRow> rows = new ArrayList<>();
        for (ReturnsEngine.HoldingReturn h : ret.holdings()) {
            rows.add(new ReturnRow(h.kind().name(), h.id(), h.name(),
                    oneYearFigure(h.oneYearPct(), h.niftyOneYearPct(), asOf),
                    sinceBuyFigure(h.sinceBuyPct(), h.niftySinceBuyPct(), asOf),
                    gainFigure(h.gainInr(), h.costInr(), asOf)));
        }
        return new ReturnsSection(BENCHMARK_NAME, portfolio, rows,
                pick(s, NarrationPlan.SUMMARY_RETURNS, NarrationPlan.RETURNS_SINCE_BUY));
    }

    // ---- holdings list ------------------------------------------------------------------------------------------

    private static List<HoldingRow> holdingRows(Snapshot snap, PortfolioResult r) {
        Map<String, GroupedHolding> groups = new LinkedHashMap<>();
        for (GroupedHolding g : snap.groups()) groups.put(g.kind() + "|" + g.id(), g);
        String asOf = r.asOf().toString();
        List<HoldingRow> rows = new ArrayList<>();
        for (PortfolioResult.HoldingValue h : r.holdings()) {
            GroupedHolding g = groups.get(h.kind() + "|" + h.id());
            String subtitle;
            Figure last;
            if (h.kind() == Kind.STOCK) {
                BundleStock b = snap.stockBundle().get(h.id());
                subtitle = b == null ? null : b.subtitle();
                List<Comparison> cmp = new ArrayList<>();
                if (b != null && b.priceOneYearAgo() != null) cmp.add(Figures.cmp("PREVIOUS_PERIOD", "1 year ago", b.priceOneYearAgo(), Units.INR_PRICE));
                last = Figures.of("last_price", "Last price", h.lastPrice(), Units.INR_PRICE, b == null ? "Sample data" : b.source(),
                        b == null || b.lastPriceDate() == null ? asOf : b.lastPriceDate(), cmp, null);
            } else {
                BundleFund b = snap.fundBundle().get(h.id());
                subtitle = b == null ? null : b.subtitle();
                List<Comparison> cmp = new ArrayList<>();
                if (b != null && b.navOneYearAgo() != null) cmp.add(Figures.cmp("PREVIOUS_PERIOD", "1 year ago", b.navOneYearAgo(), Units.INR_PRICE));
                last = Figures.of("nav", "NAV (price of one unit)", h.lastPrice(), Units.INR_PRICE, b == null ? "Sample data" : b.source(),
                        b == null || b.navDate() == null ? asOf : b.navDate(), cmp, "nav");
            }
            String path = (h.kind() == Kind.STOCK ? "/stock/" : "/fund/") + h.id();
            rows.add(new HoldingRow(g == null ? List.of() : g.ids(), h.kind().name(), h.id(), h.name(), subtitle,
                    h.quantity(), h.avgPrice(), last,
                    Figures.calc("holding_value", "Value of this holding", h.valueInr(), Units.INR, asOf, List.of()),
                    h.weightPct(), g == null ? List.of() : g.sources(),
                    h.firstBuyDate() == null ? null : h.firstBuyDate().toString(), path));
        }
        return rows;
    }
}
