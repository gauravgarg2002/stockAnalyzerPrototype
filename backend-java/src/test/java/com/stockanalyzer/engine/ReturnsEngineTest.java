package com.stockanalyzer.engine;

import static com.stockanalyzer.engine.EngineFixtures.*;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.stockanalyzer.engine.model.PortfolioInput;
import java.time.LocalDate;
import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

class ReturnsEngineTest {

    private static final LocalDate YEAR_AGO = AS_OF.minusYears(1);

    /** ITC 100 @ 470 now, 400 a year ago; TCS 10 @ 3925.4 now, 4000 a year ago; Nifty 25000 now, 22000 a year ago, 18000 on 2023-06-05. */
    private static MapPricePoints points() {
        return new MapPricePoints()
                .put("STOCK", "ITC", AS_OF, 470.0).put("STOCK", "ITC", YEAR_AGO, 400.0)
                .put("STOCK", "TCS", AS_OF, 3925.4).put("STOCK", "TCS", YEAR_AGO, 4000.0)
                .put("INDEX", "NIFTY50", AS_OF, 25000.0).put("INDEX", "NIFTY50", YEAR_AGO, 22000.0)
                .put("INDEX", "NIFTY50", D2023, 18000.0);
    }

    private static PortfolioInput twoStocks() {
        return input(List.of(st("ITC", 100, 395.0, D2023), st("TCS", 10, 3410.0, D2023)));
    }

    @Test
    @DisplayName("one-year return per holding and Nifty over the same dates")
    void oneYearPerHolding() {
        PortfolioResult r = PortfolioEngine.compute(twoStocks(), points());
        ReturnsEngine.ReturnsResult ret = r.returns();
        assertEquals(2, ret.holdings().size());
        ReturnsEngine.HoldingReturn itc = ret.holdings().get(0); // larger value first
        assertEquals("ITC", itc.id());
        assertEquals(17.5, itc.oneYearPct(), 1e-9);
        assertEquals(13.64, itc.niftyOneYearPct(), 1e-9);
        ReturnsEngine.HoldingReturn tcs = ret.holdings().get(1);
        assertEquals(-1.86, tcs.oneYearPct(), 1e-9);
        assertEquals(13.64, ret.niftyOneYearPct(), 1e-9);
    }

    @Test
    @DisplayName("portfolio one-year return: today's holdings held for the full year")
    void portfolioOneYear() {
        // value 47000 + 39254 = 86254 ; a year ago the same holdings were worth 40000 + 40000 = 80000
        ReturnsEngine.ReturnsResult ret = PortfolioEngine.compute(twoStocks(), points()).returns();
        assertEquals(7.82, ret.portfolioOneYearPct(), 1e-9);
        assertTrue(ret.oneYearAvailable());
    }

    @Test
    @DisplayName("since-buy return and the same money in Nifty on the same dates")
    void sinceBuy() {
        ReturnsEngine.ReturnsResult ret = PortfolioEngine.compute(twoStocks(), points()).returns();
        // cost 39500 + 34100 = 73600 ; value 86254 ; Nifty: 73600 x 25000/18000 = 102222.2
        assertEquals(17.19, ret.portfolioSinceBuyPct(), 1e-9);
        assertEquals(38.89, ret.niftySinceBuyPct(), 1e-9);
        assertEquals(2, ret.sinceBuyCoveredCount());
        assertEquals(73600, ret.costInr());
        assertEquals(86254, ret.valueInr());
        assertEquals(12654, ret.gainInr());
        ReturnsEngine.HoldingReturn itc = ret.holdings().get(0);
        assertEquals(18.99, itc.sinceBuyPct(), 1e-9);
        assertEquals(38.89, itc.niftySinceBuyPct(), 1e-9);
        assertEquals(39500, itc.costInr());
        assertEquals(47000, itc.valueInr());
        assertEquals(7500, itc.gainInr());
        assertTrue(ret.sinceBuyAvailable());
    }

    @Test
    @DisplayName("unknown buy date: no since-buy figure for that holding and it is left out of the portfolio figure")
    void unknownBuyDate() {
        PortfolioInput in = input(List.of(st("ITC", 100, 395.0, null), st("TCS", 10, 3410.0, D2023)));
        ReturnsEngine.ReturnsResult ret = PortfolioEngine.compute(in, points()).returns();
        assertNull(ret.holdings().get(0).sinceBuyPct());
        assertNull(ret.holdings().get(0).niftySinceBuyPct());
        assertEquals(1, ret.sinceBuyCoveredCount());
        assertEquals(15.11, ret.portfolioSinceBuyPct(), 1e-9); // 39254 / 34100
        assertEquals(38.89, ret.niftySinceBuyPct(), 1e-9);
        PortfolioInput none = input(List.of(st("ITC", 100, 395.0, null)));
        ReturnsEngine.ReturnsResult r2 = PortfolioEngine.compute(none, points()).returns();
        assertNull(r2.portfolioSinceBuyPct());
        assertFalse(r2.sinceBuyAvailable());
        assertEquals(0, r2.sinceBuyCoveredCount());
    }

    @Test
    @DisplayName("under one year of history: one-year figure is null and left out of the portfolio figure")
    void shortHistory() {
        MapPricePoints p = new MapPricePoints()
                .put("STOCK", "ITC", AS_OF, 470.0).put("STOCK", "ITC", YEAR_AGO, 400.0)
                .put("STOCK", "TCS", AS_OF, 3925.4) // no point a year ago
                .put("INDEX", "NIFTY50", AS_OF, 25000.0).put("INDEX", "NIFTY50", YEAR_AGO, 22000.0);
        ReturnsEngine.ReturnsResult ret = PortfolioEngine.compute(twoStocks(), p).returns();
        assertNull(ret.holdings().get(1).oneYearPct());
        assertEquals(17.5, ret.portfolioOneYearPct(), 1e-9); // only ITC counts
        // no Nifty history at all
        ReturnsEngine.ReturnsResult nonifty = PortfolioEngine.compute(twoStocks(), new MapPricePoints()
                .put("STOCK", "ITC", YEAR_AGO, 400.0)).returns();
        assertNull(nonifty.niftyOneYearPct());
        assertFalse(nonifty.oneYearAvailable());
        assertNull(nonifty.portfolioSinceBuyPct());
        // no history for anything
        ReturnsEngine.ReturnsResult nothing = PortfolioEngine.compute(twoStocks(), new MapPricePoints()).returns();
        assertNull(nothing.portfolioOneYearPct());
    }

    @Test
    @DisplayName("without a points source returns are empty but totals are kept")
    void nullPoints() {
        ReturnsEngine.ReturnsResult ret = PortfolioEngine.compute(twoStocks(), null).returns();
        assertNull(ret.portfolioOneYearPct());
        assertEquals(2, ret.holdings().size());
        assertEquals(86254, ret.valueInr());
        assertEquals(0, ReturnsEngine.empty().holdings().size());
    }

    @Test
    @DisplayName("funds use NAV points")
    void funds() {
        PortfolioInput in = input(List.of(fu("900201", 1000, 20.0, D2021)));
        MapPricePoints p = new MapPricePoints()
                .put("FUND", "900201", AS_OF, 21.85).put("FUND", "900201", YEAR_AGO, 19.0)
                .put("INDEX", "NIFTY50", AS_OF, 25000.0).put("INDEX", "NIFTY50", YEAR_AGO, 22000.0).put("INDEX", "NIFTY50", D2021, 17000.0);
        ReturnsEngine.ReturnsResult ret = PortfolioEngine.compute(in, p).returns();
        assertEquals(15.0, ret.holdings().get(0).oneYearPct(), 1e-9); // 21.85 / 19 = 1.15
        assertEquals(9.25, ret.holdings().get(0).sinceBuyPct(), 1e-9);
        assertEquals(47.06, ret.holdings().get(0).niftySinceBuyPct(), 1e-9);
    }

    @Test
    @DisplayName("point requests list every instrument date and the Nifty buy dates, sorted")
    void pointRequests() {
        List<ReturnsEngine.PointRequest> reqs = ReturnsEngine.pointRequests(twoStocks());
        assertEquals(3, reqs.size());
        assertEquals("STOCK", reqs.get(0).kind());
        assertEquals("ITC", reqs.get(0).id());
        assertEquals(List.of(YEAR_AGO, AS_OF), reqs.get(0).dates());
        assertEquals("TCS", reqs.get(1).id());
        ReturnsEngine.PointRequest nifty = reqs.get(2);
        assertEquals("INDEX", nifty.kind());
        assertEquals("NIFTY50", nifty.id());
        assertEquals(List.of(D2023, YEAR_AGO, AS_OF), nifty.dates());
    }
}
