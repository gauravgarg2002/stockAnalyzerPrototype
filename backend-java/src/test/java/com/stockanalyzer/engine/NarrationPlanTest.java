package com.stockanalyzer.engine;

import static com.stockanalyzer.engine.EngineFixtures.*;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.stockanalyzer.engine.TryItOnEngine.Mode;
import com.stockanalyzer.engine.model.Kind;
import com.stockanalyzer.engine.model.PortfolioInput;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

class NarrationPlanTest {

    /** Contract §B.12 template list: templateId -> "factKey:UNIT,...". */
    private static final String[][] CONTRACT = {
        {"pf.summary.value", "totalValueInr:INR,stockCount:COUNT,fundCount:COUNT"},
        {"pf.summary.empty", ""},
        {"pf.summary.top_exposure", "companyName:TEXT,companyPct:PCT,directPct:PCT,throughFundsPct:PCT"},
        {"pf.summary.returns", "windowLabel:TEXT,portfolioReturnPct:PCT_CHANGE,niftyReturnPct:PCT_CHANGE"},
        {"pf.summary.returns_unavailable", "windowLabel:TEXT"},
        {"pf.fact.overlap", "fundA:TEXT,fundB:TEXT,overlapPct:PCT,commonCount:COUNT"},
        {"pf.fact.overlap_none", "fundCount:COUNT"},
        {"pf.fact.cost", "yearlyCostInr:INR,regularGapInr:INR"},
        {"pf.fact.cost_direct_only", "yearlyCostInr:INR"},
        {"pf.fact.cost_none", ""},
        {"pf.fact.idle_cash", "idleCashInr:INR,idleCashPct:PCT"},
        {"pf.fact.idle_cash_none", ""},
        {"pf.exposure.company", "companyName:TEXT,companyPct:PCT,directPct:PCT,throughFundsPct:PCT,companyCount:COUNT"},
        {"pf.exposure.sector", "sectorName:TEXT,sectorPct:PCT,sectorCount:COUNT"},
        {"pf.exposure.size", "largePct:PCT,midPct:PCT,smallPct:PCT,microPct:PCT,debtCashPct:PCT"},
        {"pf.exposure.other", "otherPct:PCT"},
        {"pf.concentration", "top5Pct:PCT,holdingCount:COUNT"},
        {"pf.mix.equity_debt", "equityPct:PCT,debtCashPct:PCT,otherPct:PCT"},
        {"pf.mix.stocks_funds", "stocksPct:PCT,fundsPct:PCT"},
        {"pf.returns.since_buy", "portfolioGainPct:PCT_CHANGE,niftySameDatesPct:PCT_CHANGE,coveredCount:COUNT"},
        {"pf.returns.since_buy_unavailable", ""},
        {"tio.assumption.lump_sum", "instrumentName:TEXT,amountInr:INR"},
        {"tio.assumption.sip", "instrumentName:TEXT,amountInr:INR,months:COUNT,totalInr:INR"},
        {"tio.largest_company", "beforeName:TEXT,beforePct:PCT,afterName:TEXT,afterPct:PCT"},
        {"tio.top_sector", "beforeName:TEXT,beforePct:PCT,afterName:TEXT,afterPct:PCT"},
        {"tio.size_mix", "bandName:TEXT,beforePct:PCT,afterPct:PCT"},
        {"tio.holdings_count", "beforeCount:COUNT,afterCount:COUNT"},
        {"tio.holdings_count_same", "count:COUNT"},
        {"tio.overlap_fund", "instrumentName:TEXT,fundName:TEXT,overlapPct:PCT"},
        {"tio.overlap_stock", "instrumentName:TEXT,fundsHoldingCount:COUNT,beforePct:PCT,afterPct:PCT"},
        {"tio.overlap_none_fund", "instrumentName:TEXT"},
        {"tio.overlap_none_stock", "instrumentName:TEXT,beforePct:PCT,afterPct:PCT"},
        {"tio.cost", "beforeInr:INR,afterInr:INR"},
        {"tio.cost_stock", "beforeInr:INR"},
    };

    private static Map<String, String> contract() {
        Map<String, String> m = new HashMap<>();
        for (String[] row : CONTRACT) m.put(row[0], row[1]);
        return m;
    }

    private static String signature(NarrateItem i) {
        List<String> parts = new ArrayList<>();
        for (Map.Entry<String, FactValue> e : i.facts().entrySet()) parts.add(e.getKey() + ":" + e.getValue().unit());
        return String.join(",", parts);
    }

    private static void assertMatchesContract(List<NarrateItem> items) {
        Map<String, String> c = contract();
        List<String> keys = new ArrayList<>();
        for (NarrateItem i : items) {
            assertTrue(c.get(i.templateId()) != null, "unknown template " + i.templateId());
            assertEquals(c.get(i.templateId()), signature(i));
            assertFalse(keys.contains(i.key()), "duplicate key " + i.key());
            keys.add(i.key());
            for (FactValue f : i.facts().values()) {
                assertNotNull(f.value());
                if (Units.TEXT.equals(f.unit())) assertTrue(f.value() instanceof String);
                else assertTrue(f.value() instanceof Number);
            }
        }
    }

    private static MapPricePoints points() {
        LocalDate ya = AS_OF.minusYears(1);
        MapPricePoints p = new MapPricePoints().put("INDEX", "NIFTY50", AS_OF, 25000.0).put("INDEX", "NIFTY50", ya, 22000.0)
                .put("INDEX", "NIFTY50", D2023, 18000.0).put("INDEX", "NIFTY50", D2021, 17000.0);
        PortfolioInput in = sampleUser();
        for (ValuedPosition vp : ValuedPosition.of(in)) {
            p.put(vp.kind().name(), vp.id(), AS_OF, vp.price());
            p.put(vp.kind().name(), vp.id(), ya, vp.price() * 0.9);
        }
        return p;
    }

    private static Map<String, NarrateItem> byKey(List<NarrateItem> items) {
        Map<String, NarrateItem> m = new LinkedHashMap<>();
        for (NarrateItem i : items) m.put(i.key(), i);
        return m;
    }

    @Test
    @DisplayName("sample portfolio: every item uses a contract template with exactly the contract fact keys and units")
    void portfolioMatchesContract() {
        PortfolioResult r = PortfolioEngine.compute(sampleUser(), points());
        List<NarrateItem> items = NarrationPlan.forPortfolio(r);
        assertMatchesContract(items);
        Map<String, NarrateItem> m = byKey(items);
        for (String k : List.of("summary.0", "summary.1", "summary.2", "fact.overlap", "fact.cost", "fact.idle_cash",
                "exposure.company", "exposure.sector", "exposure.size", "exposure.other", "concentration",
                "mix.equity_debt", "mix.stocks_funds", "returns.since_buy")) {
            assertTrue(m.get(k) != null, "missing key " + k);
        }
        assertEquals("pf.summary.value", m.get("summary.0").templateId());
        assertEquals(r.valueInr(), m.get("summary.0").facts().get("totalValueInr").value());
        assertEquals(6L, ((Number) m.get("summary.0").facts().get("stockCount").value()).longValue());
        assertEquals(4L, ((Number) m.get("summary.0").facts().get("fundCount").value()).longValue());
        assertEquals("pf.summary.returns", m.get("summary.2").templateId());
        assertEquals("1 year", m.get("summary.2").facts().get("windowLabel").value());
        assertEquals("pf.returns.since_buy", m.get("returns.since_buy").templateId());
        assertEquals("pf.exposure.other", m.get("exposure.other").templateId());
    }

    @Test
    @DisplayName("top exposure sentence facts use percent units taken from basis points")
    void topExposureFacts() {
        PortfolioResult r = PortfolioEngine.compute(sampleUser(), points());
        NarrateItem top = byKey(NarrationPlan.forPortfolio(r)).get("summary.1");
        ExposureLine line = r.company().lines().get(0);
        assertEquals(line.name(), top.facts().get("companyName").value());
        assertEquals(line.totalBp() / 100.0, ((Number) top.facts().get("companyPct").value()).doubleValue(), 1e-12);
        assertEquals(line.directBp() / 100.0, ((Number) top.facts().get("directPct").value()).doubleValue(), 1e-12);
        assertEquals(line.throughFundsBp() / 100.0, ((Number) top.facts().get("throughFundsPct").value()).doubleValue(), 1e-12);
        NarrateItem conc = byKey(NarrationPlan.forPortfolio(r)).get("concentration");
        assertEquals(r.concentration().top5Bp() / 100.0, ((Number) conc.facts().get("top5Pct").value()).doubleValue(), 1e-12);
        assertEquals(10L, ((Number) conc.facts().get("holdingCount").value()).longValue());
    }

    @Test
    @DisplayName("overlap fact uses the highest-overlap pair; cost fact picks the right variant")
    void overlapAndCostVariants() {
        PortfolioResult r = PortfolioEngine.compute(sampleUser(), points());
        Map<String, NarrateItem> m = byKey(NarrationPlan.forPortfolio(r));
        OverlapEngine.OverlapPair pair = r.overlapPairs().get(0);
        assertEquals("pf.fact.overlap", m.get("fact.overlap").templateId());
        assertEquals(pair.nameA(), m.get("fact.overlap").facts().get("fundA").value());
        assertEquals(pair.nameB(), m.get("fact.overlap").facts().get("fundB").value());
        assertEquals(pair.result().pct(), ((Number) m.get("fact.overlap").facts().get("overlapPct").value()).doubleValue(), 1e-12);
        assertEquals("pf.fact.cost", m.get("fact.cost").templateId());
        assertEquals(r.cost().regularGapYearlyInr(), m.get("fact.cost").facts().get("regularGapInr").value());

        PortfolioInput directOnly = input(List.of(fu("900201", 100, 20, null), fu("900301", 100, 20, null)));
        Map<String, NarrateItem> d = byKey(NarrationPlan.forPortfolio(PortfolioEngine.compute(directOnly, null)));
        assertEquals("pf.fact.cost_direct_only", d.get("fact.cost").templateId());
        assertEquals("pf.fact.overlap", d.get("fact.overlap").templateId());

        PortfolioInput oneFund = input(List.of(fu("900201", 100, 20, null), st("TCS", 1, 1, null)));
        Map<String, NarrateItem> o = byKey(NarrationPlan.forPortfolio(PortfolioEngine.compute(oneFund, null)));
        assertEquals("pf.fact.overlap_none", o.get("fact.overlap").templateId());
        assertEquals(1L, ((Number) o.get("fact.overlap").facts().get("fundCount").value()).longValue());

        PortfolioInput noFunds = input(List.of(st("TCS", 1, 1, null)));
        Map<String, NarrateItem> n = byKey(NarrationPlan.forPortfolio(PortfolioEngine.compute(noFunds, null)));
        assertEquals("pf.fact.cost_none", n.get("fact.cost").templateId());
        assertEquals("pf.fact.idle_cash_none", n.get("fact.idle_cash").templateId());
        assertFalse(n.containsKey("exposure.other"), "no undisclosed money in a stocks-only portfolio");
        assertEquals("pf.summary.returns_unavailable", n.get("summary.2").templateId());
        assertEquals("pf.returns.since_buy_unavailable", n.get("returns.since_buy").templateId());
        assertMatchesContract(NarrationPlan.forPortfolio(PortfolioEngine.compute(noFunds, null)));
    }

    @Test
    @DisplayName("idle cash fact: amount and share of holdings plus cash")
    void idleCash() {
        PortfolioResult r = PortfolioEngine.compute(sampleUser(), points());
        NarrateItem idle = byKey(NarrationPlan.forPortfolio(r)).get("fact.idle_cash");
        assertEquals("pf.fact.idle_cash", idle.templateId());
        assertEquals(42351L, idle.facts().get("idleCashInr").value());
        assertEquals(r.idleCashPct(), ((Number) idle.facts().get("idleCashPct").value()).doubleValue(), 1e-12);
        assertTrue(r.idleCashPct() > 0 && r.idleCashPct() < 10);
    }

    @Test
    @DisplayName("empty portfolio uses pf.summary.empty only for home and the *_none variants for the portfolio page")
    void emptyPortfolio() {
        PortfolioResult r = PortfolioEngine.compute(input(List.of()), null);
        List<NarrateItem> home = NarrationPlan.forHome(r);
        assertEquals(1, home.size());
        assertEquals("pf.summary.empty", home.get(0).templateId());
        assertEquals("summary.0", home.get(0).key());
        assertTrue(home.get(0).facts().isEmpty());
        List<NarrateItem> all = NarrationPlan.forPortfolio(r);
        assertMatchesContract(all);
        Map<String, NarrateItem> m = byKey(all);
        assertEquals("pf.summary.empty", m.get("summary.0").templateId());
        assertEquals("pf.summary.returns_unavailable", m.get("summary.2").templateId());
        assertEquals("pf.returns.since_buy_unavailable", m.get("returns.since_buy").templateId());
        assertFalse(m.containsKey("exposure.company"));
        assertFalse(m.containsKey("concentration"));
        assertTrue(m.containsKey("mix.equity_debt"));
    }

    @Test
    @DisplayName("home plan holds only the summary and the three facts")
    void homeSubset() {
        PortfolioResult r = PortfolioEngine.compute(sampleUser(), points());
        List<NarrateItem> home = NarrationPlan.forHome(r);
        assertMatchesContract(home);
        List<String> keys = new ArrayList<>();
        for (NarrateItem i : home) keys.add(i.key());
        assertEquals(List.of("summary.0", "summary.1", "summary.2", "fact.overlap", "fact.cost", "fact.idle_cash"), keys);
    }

    @Test
    @DisplayName("try-it-on: SIP into a new fund")
    void tioFundSip() {
        TryItOnEngine.TryItOnResult t = TryItOnEngine.run(sampleUser(), Kind.FUND, "900801", Mode.SIP, 5000, 12);
        List<NarrateItem> items = NarrationPlan.forTryItOn(t);
        assertMatchesContract(items);
        List<String> keys = new ArrayList<>();
        for (NarrateItem i : items) keys.add(i.key());
        assertEquals(List.of("assumption", "largest_company", "top_sector", "size_mix", "holdings_count", "overlap", "cost"), keys);
        Map<String, NarrateItem> m = byKey(items);
        assertEquals("tio.assumption.sip", m.get("assumption").templateId());
        assertEquals(5000L, m.get("assumption").facts().get("amountInr").value());
        assertEquals(12L, ((Number) m.get("assumption").facts().get("months").value()).longValue());
        assertEquals(60000L, m.get("assumption").facts().get("totalInr").value());
        assertEquals("tio.holdings_count", m.get("holdings_count").templateId());
        assertEquals(10L, ((Number) m.get("holdings_count").facts().get("beforeCount").value()).longValue());
        assertEquals(11L, ((Number) m.get("holdings_count").facts().get("afterCount").value()).longValue());
        assertEquals("tio.overlap_none_fund", m.get("overlap").templateId());
        assertEquals("tio.cost", m.get("cost").templateId());
        assertEquals(t.after().cost().totalYearlyInr(), m.get("cost").facts().get("afterInr").value());
    }

    @Test
    @DisplayName("try-it-on: lump sum into a held fund with overlap")
    void tioHeldFund() {
        TryItOnEngine.TryItOnResult t = TryItOnEngine.run(sampleUser(), Kind.FUND, "900102", Mode.LUMP_SUM, 100000, null);
        Map<String, NarrateItem> m = byKey(NarrationPlan.forTryItOn(t));
        assertMatchesContract(NarrationPlan.forTryItOn(t));
        assertEquals("tio.assumption.lump_sum", m.get("assumption").templateId());
        assertEquals("tio.overlap_fund", m.get("overlap").templateId());
        assertEquals(t.fundOverlaps().get(0).name(), m.get("overlap").facts().get("fundName").value());
        TryItOnEngine.TryItOnResult same = TryItOnEngine.run(sampleUser(), Kind.FUND, "900101", Mode.LUMP_SUM, 100000, null);
        Map<String, NarrateItem> s = byKey(NarrationPlan.forTryItOn(same));
        assertEquals("tio.holdings_count_same", s.get("holdings_count").templateId());
        assertEquals(10L, ((Number) s.get("holdings_count").facts().get("count").value()).longValue());
    }

    @Test
    @DisplayName("try-it-on: stock inside funds, stock outside funds, size band with the largest change")
    void tioStock() {
        TryItOnEngine.TryItOnResult t = TryItOnEngine.run(sampleUser(), Kind.STOCK, "INFY", Mode.LUMP_SUM, 100000, null);
        Map<String, NarrateItem> m = byKey(NarrationPlan.forTryItOn(t));
        assertMatchesContract(NarrationPlan.forTryItOn(t));
        assertEquals("tio.overlap_stock", m.get("overlap").templateId());
        assertEquals(2L, ((Number) m.get("overlap").facts().get("fundsHoldingCount").value()).longValue());
        assertEquals("tio.cost_stock", m.get("cost").templateId());
        assertEquals("tio.size_mix", m.get("size_mix").templateId());
        // INFY is large cap: the Large cap share changes the most
        assertEquals("Large cap", m.get("size_mix").facts().get("bandName").value());

        PortfolioInput in = sampleUser();
        PortfolioInput withNew = new PortfolioInput(in.positions(),
                stocksPlus(in, stock("NEWCO", "New Co Ltd", "Chemicals", com.stockanalyzer.engine.model.SizeBand.MICRO, 100)),
                in.funds(), in.idleCashInr(), in.asOf());
        TryItOnEngine.TryItOnResult n = TryItOnEngine.run(withNew, Kind.STOCK, "NEWCO", Mode.LUMP_SUM, 300000, null);
        Map<String, NarrateItem> nm = byKey(NarrationPlan.forTryItOn(n));
        assertEquals("tio.overlap_none_stock", nm.get("overlap").templateId());
        assertEquals("Micro cap", nm.get("size_mix").facts().get("bandName").value());
        assertEquals(0.0, ((Number) nm.get("overlap").facts().get("beforePct").value()).doubleValue(), 1e-12);
        assertTrue(((Number) nm.get("overlap").facts().get("afterPct").value()).doubleValue() > 0);
        assertMatchesContract(NarrationPlan.forTryItOn(n));
    }

    private static Map<String, com.stockanalyzer.engine.model.StockInfo> stocksPlus(PortfolioInput in,
            com.stockanalyzer.engine.model.StockInfo extra) {
        Map<String, com.stockanalyzer.engine.model.StockInfo> m = new TreeMap<>(in.stocks());
        m.put(extra.symbol(), extra);
        return m;
    }
}
