package com.stockanalyzer.engine;

import com.stockanalyzer.engine.model.AssetMix;
import com.stockanalyzer.engine.model.FundConstituent;
import com.stockanalyzer.engine.model.FundInfo;
import com.stockanalyzer.engine.model.Kind;
import com.stockanalyzer.engine.model.PortfolioInput;
import com.stockanalyzer.engine.model.Position;
import com.stockanalyzer.engine.model.SizeBand;
import com.stockanalyzer.engine.model.StockInfo;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Hand-built inputs for engine tests. Illustrative numbers only. */
final class EngineFixtures {
    private EngineFixtures() { }

    static final LocalDate AS_OF = LocalDate.of(2026, 10, 30);

    static StockInfo stock(String symbol, String name, String sector, SizeBand band, double price) {
        return new StockInfo(symbol, name, sector, band, price, true);
    }

    static FundConstituent c(String key, String name, String sector, SizeBand band, double w) {
        return new FundConstituent(key, key, name, sector, band, w, true);
    }

    static AssetMix mix(double eq, double debt, double cash, double other) { return new AssetMix(eq, debt, cash, other); }

    /** n equal-weight filler constituents named PREFIX01.. that add up to totalWeight. */
    static List<FundConstituent> filler(String prefix, int n, double totalWeight, SizeBand band, String sector) {
        List<FundConstituent> out = new ArrayList<>();
        for (int i = 1; i <= n; i++) {
            String k = prefix + (i < 10 ? "0" : "") + i;
            out.add(new FundConstituent(k, k, k + " Ltd", sector, band, totalWeight / n, false));
        }
        return out;
    }

    @SafeVarargs
    static List<FundConstituent> join(List<FundConstituent>... parts) {
        List<FundConstituent> out = new ArrayList<>();
        for (List<FundConstituent> p : parts) out.addAll(p);
        return out;
    }

    static FundInfo fund(String code, String name, String category, String plan, Double ter, String twin, Double twinTer,
                         double nav, AssetMix mix, List<FundConstituent> cs) {
        return new FundInfo(code, name, category, plan, ter, twin, twin == null ? null : "Twin of " + name, twinTer,
                1.0, nav, mix, LocalDate.of(2026, 9, 30), cs);
    }

    static final StockInfo RELIANCE = stock("RELIANCE", "Reliance Industries Ltd", "Oil Gas & Consumable Fuels", SizeBand.LARGE, 2900.0);
    static final StockInfo HDFCBANK = stock("HDFCBANK", "HDFC Bank Ltd", "Financial Services", SizeBand.LARGE, 1700.0);
    static final StockInfo TCS = stock("TCS", "Tata Consultancy Services Ltd", "Information Technology", SizeBand.LARGE, 3925.4);
    static final StockInfo ITC = stock("ITC", "ITC Ltd", "FMCG", SizeBand.LARGE, 470.0);
    static final StockInfo TATASTEEL = stock("TATASTEEL", "Tata Steel Ltd", "Metals & Mining", SizeBand.LARGE, 160.0);
    static final StockInfo DECCANINF = stock("DECCANINF", "Deccan Infra Projects Ltd", "Construction & Engineering", SizeBand.SMALL, 260.0);
    static final StockInfo INFY = stock("INFY", "Infosys Ltd", "Information Technology", SizeBand.LARGE, 1800.0);

    /** Regular plan with a direct twin; portfolio of 96.0 disclosed equity, 3.5 cash, so 0.5 OTHER. */
    static FundInfo flexiRegular() {
        return fund("900101", "Kaveri Flexi Cap Fund - Regular Plan - Growth", "Flexi Cap Fund", "REGULAR", 1.72,
                "900102", 0.68, 62.4012, mix(96.5, 0, 3.5, 0), join(List.of(
                        c("HDFCBANK", "HDFC Bank Ltd", "Financial Services", SizeBand.LARGE, 8.12),
                        c("RELIANCE", "Reliance Industries Ltd", "Oil Gas & Consumable Fuels", SizeBand.LARGE, 6.0),
                        c("TCS", "Tata Consultancy Services Ltd", "Information Technology", SizeBand.LARGE, 5.0),
                        c("INFY", "Infosys Ltd", "Information Technology", SizeBand.LARGE, 4.0)),
                filler("FLX", 20, 72.88, SizeBand.LARGE, "Financial Services")));
    }

    static FundInfo flexiDirect() {
        FundInfo r = flexiRegular();
        return new FundInfo("900102", "Kaveri Flexi Cap Fund - Direct Plan - Growth", r.category(), "DIRECT", 0.68,
                "900101", r.name(), 1.72, 1.0, 66.1, r.assetMix(), r.portfolioDate(), r.constituents());
    }

    /** Nifty-like index fund: 99.5 disclosed of 99.7 equity. */
    static FundInfo indexFund() {
        return fund("900201", "Narmada Nifty 50 Index Fund - Direct Plan - Growth", "Index Fund", "DIRECT", 0.18, null, null,
                21.85, mix(99.7, 0, 0.3, 0), join(List.of(
                        c("HDFCBANK", "HDFC Bank Ltd", "Financial Services", SizeBand.LARGE, 12.95),
                        c("RELIANCE", "Reliance Industries Ltd", "Oil Gas & Consumable Fuels", SizeBand.LARGE, 10.5),
                        c("TCS", "Tata Consultancy Services Ltd", "Information Technology", SizeBand.LARGE, 4.0),
                        c("INFY", "Infosys Ltd", "Information Technology", SizeBand.LARGE, 5.5),
                        c("ITC", "ITC Ltd", "FMCG", SizeBand.LARGE, 3.7)),
                filler("IDX", 45, 62.85, SizeBand.LARGE, "Financial Services")));
    }

    /** Mid cap fund with a constituent that has no sector and no size band. */
    static FundInfo midcap() {
        return fund("900301", "Godavari Midcap Fund - Direct Plan - Growth", "Mid Cap Fund", "DIRECT", 0.74, null, null,
                98.3, mix(95, 0, 5, 0), join(List.of(
                        c("VOLTAS", "Voltas Ltd", "Consumer Durables", SizeBand.MID, 3.0),
                        c("FEDERALBNK", "Federal Bank Ltd", "Financial Services", SizeBand.MID, 4.0),
                        c("HDFCBANK", "HDFC Bank Ltd", "Financial Services", SizeBand.LARGE, 1.5),
                        new FundConstituent("NAME:MYSTERY CO", null, "Mystery Co", null, null, 1.0, false)),
                filler("MID", 25, 85.0, SizeBand.MID, "Capital Markets")));
    }

    static FundInfo elss() {
        return fund("900501", "Krishna ELSS Tax Saver Fund - Direct Plan - Growth", "ELSS", "DIRECT", 0.82, null, null,
                41.2, mix(97, 0, 3, 0), join(List.of(
                        c("HDFCBANK", "HDFC Bank Ltd", "Financial Services", SizeBand.LARGE, 7.0),
                        c("TCS", "Tata Consultancy Services Ltd", "Information Technology", SizeBand.LARGE, 3.0)),
                filler("ELS", 30, 86.0, SizeBand.LARGE, "Healthcare")));
    }

    /** Debt fund: debt 93 cash 7, no equity constituents. */
    static FundInfo debtFund() {
        return fund("900801", "Ganga Short Duration Fund - Direct Plan - Growth", "Short Duration Fund", "DIRECT", 0.38, null, null,
                25.0, mix(0, 93, 7, 0), List.of());
    }

    /** Disclosed weights add up to 105 although only 90 is equity: engine must scale them. */
    static FundInfo overshootFund() {
        return fund("900999", "Overshoot Fund - Direct Plan - Growth", "Flexi Cap Fund", "DIRECT", 0.9, null, null,
                10.0, mix(90, 0, 10, 0), join(List.of(
                        c("HDFCBANK", "HDFC Bank Ltd", "Financial Services", SizeBand.LARGE, 50.0)),
                filler("OVS", 11, 55.0, SizeBand.MID, "Capital Goods")));
    }

    static Map<String, StockInfo> stocks(StockInfo... s) {
        Map<String, StockInfo> m = new LinkedHashMap<>();
        for (StockInfo x : s) m.put(x.symbol(), x);
        return m;
    }

    static Map<String, FundInfo> funds(FundInfo... f) {
        Map<String, FundInfo> m = new LinkedHashMap<>();
        for (FundInfo x : f) m.put(x.schemeCode(), x);
        return m;
    }

    static Position st(String sym, double qty, double avg, LocalDate buy) { return new Position(Kind.STOCK, sym, qty, avg, buy); }

    static Position fu(String code, double units, double avg, LocalDate buy) { return new Position(Kind.FUND, code, units, avg, buy); }

    static final LocalDate D2023 = LocalDate.of(2023, 6, 5);
    static final LocalDate D2021 = LocalDate.of(2021, 12, 1);

    /** 6 stocks and 4 funds, like the sample user. */
    static PortfolioInput sampleUser() {
        List<Position> ps = List.of(
                st("RELIANCE", 40, 2380.0, D2023), st("HDFCBANK", 60, 1520.0, D2023), st("TCS", 15, 3410.0, D2023),
                st("ITC", 300, 395.0, null), st("TATASTEEL", 500, 118.0, D2023), st("DECCANINF", 400, 212.0, null),
                fu("900101", 1850.234, 62.4, D2021), fu("900201", 3120.5, 21.85, D2021),
                fu("900301", 410.112, 98.3, null), fu("900501", 980.0, 41.2, D2021));
        return new PortfolioInput(ps,
                stocks(RELIANCE, HDFCBANK, TCS, ITC, TATASTEEL, DECCANINF, INFY),
                funds(flexiRegular(), flexiDirect(), indexFund(), midcap(), elss(), debtFund(), overshootFund()),
                42350.75, AS_OF);
    }

    static PortfolioInput input(List<Position> ps) {
        return new PortfolioInput(ps,
                stocks(RELIANCE, HDFCBANK, TCS, ITC, TATASTEEL, DECCANINF, INFY),
                funds(flexiRegular(), flexiDirect(), indexFund(), midcap(), elss(), debtFund(), overshootFund()),
                0.0, AS_OF);
    }
}
