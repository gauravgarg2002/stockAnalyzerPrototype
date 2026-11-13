package com.stockanalyzer.engine;

import static com.stockanalyzer.engine.EngineFixtures.*;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.stockanalyzer.engine.model.FundInfo;
import com.stockanalyzer.engine.model.PortfolioInput;
import com.stockanalyzer.engine.model.Position;
import com.stockanalyzer.engine.model.SizeBand;
import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

class ExposureEngineTest {

    private static long roundedTotal(PortfolioInput in) {
        double v = 0;
        for (ValuedPosition vp : ValuedPosition.of(in)) v += vp.value();
        return Money.roundRupees(v);
    }

    private static void assertConsistent(ExposureBreakdown b, long expectedTotalInr) {
        assertEquals(10000, b.sumBp());
        assertEquals(expectedTotalInr, b.totalInr());
        assertEquals(expectedTotalInr, b.sumInr());
        for (ExposureLine l : b.lines()) {
            assertEquals(l.totalInr(), l.directInr() + l.throughFundsInr());
            assertEquals(l.totalBp(), l.directBp() + l.throughFundsBp());
            assertTrue(l.directBp() >= 0 && l.throughFundsBp() >= 0);
            assertTrue(l.directInr() >= 0 && l.throughFundsInr() >= 0);
            long viaSum = 0;
            for (ExposureLine.ViaFund v : l.viaFunds()) viaSum += v.inr();
            if (l.throughFundsInr() == 0) assertTrue(l.viaFunds().isEmpty() || viaSum <= 5);
        }
        // sorted by totalInr descending with buckets last
        boolean seenBucket = false;
        long prev = Long.MAX_VALUE;
        for (ExposureLine l : b.lines()) {
            if (l.isBucket()) { seenBucket = true; continue; }
            assertFalse(seenBucket);
            assertTrue(l.totalInr() <= prev);
            prev = l.totalInr();
        }
    }

    @Test
    @DisplayName("sample user: company, sector and size each add up to exactly 10000 bp and the rupee total")
    void sampleUserSums() {
        PortfolioInput in = sampleUser();
        ExposureEngine.ExposureSet es = ExposureEngine.compute(in);
        long total = roundedTotal(in);
        assertConsistent(es.company(), total);
        assertConsistent(es.sector(), total);
        assertConsistent(es.size(), total);
        assertEquals("COMPANY", es.company().dimension());
        assertEquals("SECTOR", es.sector().dimension());
        assertEquals("SIZE", es.size().dimension());
    }

    @Test
    @DisplayName("sample user: OTHER bucket is positive and the mid cap fund's unknown company lands in OTHER for size")
    void otherBucket() {
        ExposureEngine.ExposureSet es = ExposureEngine.compute(sampleUser());
        ExposureLine other = es.company().find("OTHER");
        assertNotNull(other);
        assertTrue(other.totalBp() > 0);
        assertEquals("Other / undisclosed", other.name());
        assertEquals("OTHER", other.kind());
        assertEquals(false, other.checkAvailable());
        assertNull(other.symbol());
        ExposureLine debt = es.company().find("DEBT_CASH");
        assertNotNull(debt);
        assertEquals("Debt & cash", debt.name());
        // size: the null-size constituent adds to OTHER, so size OTHER is larger than company OTHER
        assertTrue(es.size().find("OTHER").totalInr() >= other.totalInr());
        // sector: null-sector constituent also goes to OTHER
        assertTrue(es.sector().find("OTHER").totalInr() >= other.totalInr());
        assertEquals("Large cap", es.size().find("LARGE").name());
    }

    @Test
    @DisplayName("a company held directly and through funds is split into direct and through-funds with fund detail")
    void directVersusThroughFunds() {
        ExposureEngine.ExposureSet es = ExposureEngine.compute(sampleUser());
        ExposureLine hdfc = es.company().find("HDFCBANK");
        assertNotNull(hdfc);
        assertTrue(hdfc.directInr() > 0);
        assertTrue(hdfc.throughFundsInr() > 0);
        assertEquals("HDFCBANK", hdfc.symbol());
        assertTrue(hdfc.checkAvailable());
        assertTrue(hdfc.viaFunds().size() >= 3);
        for (int i = 1; i < hdfc.viaFunds().size(); i++) {
            assertTrue(hdfc.viaFunds().get(i - 1).inr() >= hdfc.viaFunds().get(i).inr());
        }
        // 60 shares at 1700 = 102000 held directly
        assertEquals(102000, hdfc.directInr(), 1);
        // a stock-only company has no fund exposure
        ExposureLine tata = es.company().find("TATASTEEL");
        assertEquals(0, tata.throughFundsInr());
        assertTrue(tata.viaFunds().isEmpty());
        assertEquals("Tata Steel Ltd", tata.name());
        // a filler company only exists inside funds
        ExposureLine idx = es.company().find("IDX01");
        assertEquals(0, idx.directInr());
        assertEquals(idx.totalInr(), idx.throughFundsInr());
        assertFalse(idx.checkAvailable());
    }

    @Test
    @DisplayName("hand-computed fund: constituents, debt and cash, and the undisclosed remainder")
    void handComputedFund() {
        // 100 units at 10 = 1000. A 50%, B 30%, debt 10%, cash 5% => OTHER 5%
        FundInfo f = fund("F1", "Test Fund", "Flexi Cap Fund", "DIRECT", 1.0, null, null, 10.0, mix(85, 10, 5, 0),
                List.of(c("A", "A Ltd", "S1", SizeBand.LARGE, 50), c("B", "B Ltd", "S2", SizeBand.MID, 30)));
        PortfolioInput in = new PortfolioInput(List.of(fu("F1", 100, 10, null)), stocks(), funds(f), 0, AS_OF);
        ExposureEngine.ExposureSet es = ExposureEngine.compute(in);
        assertEquals(1000, es.company().totalInr());
        assertEquals(5000, es.company().find("A").totalBp());
        assertEquals(500, es.company().find("A").totalInr());
        assertEquals(3000, es.company().find("B").totalBp());
        assertEquals(1500, es.company().find("DEBT_CASH").totalBp());
        assertEquals(500, es.company().find("OTHER").totalBp());
        assertEquals(50, es.company().find("OTHER").totalInr());
        assertEquals(0, es.company().find("A").directBp());
        assertEquals(5000, es.company().find("A").throughFundsBp());
        assertEquals("₹500 (50.0%)", es.company().find("A").display());
        assertEquals("₹0 (0.0%)", es.company().find("A").directDisplay());
        assertEquals(5000, es.size().find("LARGE").totalBp());
        assertEquals(3000, es.size().find("MID").totalBp());
        assertEquals(5000, es.sector().find("S1").totalBp());
        assertEquals(4, es.company().lines().size());
        assertEquals("A", es.company().lines().get(0).key());
        assertEquals("OTHER", es.company().lines().get(3).key());
    }

    @Test
    @DisplayName("overshooting disclosed weights are scaled down and OTHER disappears")
    void overshoot() {
        PortfolioInput in = input(List.of(fu("900999", 1000, 10, null), st("TCS", 10, 3000, null)));
        ExposureEngine.ExposureSet es = ExposureEngine.compute(in);
        long total = roundedTotal(in);
        assertConsistent(es.company(), total);
        assertConsistent(es.sector(), total);
        assertConsistent(es.size(), total);
        assertNull(es.company().find("OTHER"));
        // fund value 10000; HDFCBANK 50 of 105 weight scaled to 90 => 50 * 90/105 = 42.857% of 10000
        long hdfc = es.company().find("HDFCBANK").totalInr();
        assertEquals(4286, hdfc, 2);
        // cash 10% of the fund is still reported
        assertEquals(1000, es.company().find("DEBT_CASH").totalInr(), 1);
    }

    @Test
    @DisplayName("debt-only portfolio is entirely Debt & cash in every dimension")
    void debtOnly() {
        PortfolioInput in = input(List.of(fu("900801", 4000, 24, null)));
        ExposureEngine.ExposureSet es = ExposureEngine.compute(in);
        for (ExposureBreakdown b : List.of(es.company(), es.sector(), es.size())) {
            assertEquals(1, b.lines().size());
            assertEquals("DEBT_CASH", b.lines().get(0).key());
            assertEquals(10000, b.sumBp());
            assertEquals(100000, b.sumInr());
        }
    }

    @Test
    @DisplayName("stocks-only portfolio is all direct")
    void stocksOnly() {
        PortfolioInput in = input(List.of(st("RELIANCE", 10, 2000, null), st("TCS", 5, 3000, null), st("ITC", 100, 400, null)));
        ExposureEngine.ExposureSet es = ExposureEngine.compute(in);
        long total = roundedTotal(in);
        assertConsistent(es.company(), total);
        assertConsistent(es.sector(), total);
        assertConsistent(es.size(), total);
        for (ExposureLine l : es.company().lines()) {
            assertEquals(0, l.throughFundsBp());
            assertEquals(l.totalBp(), l.directBp());
            assertEquals(l.totalInr(), l.directInr());
        }
        assertEquals(3, es.company().lines().size());
        assertEquals(10000, es.size().find("LARGE").totalBp());
        assertEquals("ITC", es.company().lines().get(0).key()); // 100 x 470 = 47000 is largest
    }

    @Test
    @DisplayName("several mixed portfolios all sum to exactly 100%")
    void manyPortfolios() {
        List<List<Position>> portfolios = List.of(
                List.of(st("RELIANCE", 1, 1, null), fu("900101", 10, 1, null)),
                List.of(st("ITC", 333, 1, null), st("TCS", 7, 1, null), st("INFY", 13, 1, null), fu("900301", 77.7, 1, null)),
                List.of(fu("900101", 1, 1, null), fu("900102", 1, 1, null), fu("900201", 1, 1, null), fu("900801", 1, 1, null)),
                List.of(st("DECCANINF", 3, 1, null), fu("900999", 3, 1, null), fu("900501", 17.123, 1, null)),
                List.of(st("TATASTEEL", 1, 1, null)));
        for (List<Position> p : portfolios) {
            PortfolioInput in = input(p);
            ExposureEngine.ExposureSet es = ExposureEngine.compute(in);
            long total = roundedTotal(in);
            assertConsistent(es.company(), total);
            assertConsistent(es.sector(), total);
            assertConsistent(es.size(), total);
        }
    }

    @Test
    @DisplayName("three equal holdings: tie goes to the key that sorts first")
    void tie() {
        PortfolioInput eq = new PortfolioInput(List.of(st("ITC", 1000, 1, null), st("TCS", 1000, 1, null), st("INFY", 1000, 1, null)),
                stocks(stock("ITC", "ITC", "A", SizeBand.LARGE, 10), stock("TCS", "TCS", "B", SizeBand.LARGE, 10),
                        stock("INFY", "INFY", "C", SizeBand.LARGE, 10)), funds(), 0, AS_OF);
        ExposureBreakdown b = ExposureEngine.compute(eq).company();
        assertEquals(10000, b.sumBp());
        assertEquals("INFY", b.lines().get(0).key());
        assertEquals(3334, b.lines().get(0).totalBp());
        assertEquals(3333, b.lines().get(1).totalBp());
        assertEquals(30000, b.totalInr());
    }

    @Test
    @DisplayName("empty portfolio gives empty breakdowns")
    void empty() {
        PortfolioInput in = input(List.of());
        ExposureEngine.ExposureSet es = ExposureEngine.compute(in);
        assertEquals(0, es.company().lines().size());
        assertEquals(0, es.company().totalInr());
        assertEquals(0, es.sector().sumBp());
        // unknown instruments are ignored
        PortfolioInput unknown = input(List.of(st("NOPE", 5, 1, null)));
        assertEquals(0, ExposureEngine.compute(unknown).company().lines().size());
    }

    @Test
    @DisplayName("positions of the same instrument are aggregated")
    void aggregates() {
        PortfolioInput in = input(List.of(st("TCS", 10, 3000, null), st("TCS", 5, 3300, D2023), st("ITC", 100, 400, null)));
        List<Position> agg = Position.aggregate(in.positions());
        assertEquals(2, agg.size());
        assertEquals(15.0, agg.get(0).quantity(), 1e-9);
        assertEquals(3100.0, agg.get(0).avgPrice(), 1e-9);
        assertEquals(D2023, agg.get(0).firstBuyDate());
        long tcs = ExposureEngine.compute(in).company().find("TCS").totalInr();
        assertEquals(Money.roundRupees(15 * 3925.4), tcs, 1);
    }
}
