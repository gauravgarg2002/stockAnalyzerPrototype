package com.stockanalyzer.engine;

import static com.stockanalyzer.engine.EngineFixtures.*;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.stockanalyzer.engine.model.PortfolioInput;
import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

class MixEngineTest {

    private static int sumBp(List<MixEngine.MixLine> l) {
        int s = 0;
        for (MixEngine.MixLine x : l) s += x.bp();
        return s;
    }

    private static long sumInr(List<MixEngine.MixLine> l) {
        long s = 0;
        for (MixEngine.MixLine x : l) s += x.valueInr();
        return s;
    }

    private static long total(PortfolioInput in) {
        return Money.roundRupees(ValuedPosition.total(ValuedPosition.of(in)));
    }

    @Test
    @DisplayName("hand-computed mix: one stock and one hybrid fund")
    void handComputed() {
        // stock 1000, fund 1000 with equity 60 / debt 30 / cash 5 / other 5
        var f = fund("H1", "Hybrid", "Aggressive Hybrid Fund", "DIRECT", 1.0, null, null, 10.0, mix(60, 30, 5, 5), List.of());
        PortfolioInput in = new PortfolioInput(List.of(st("TCS", 1, 1000, null), fu("H1", 100, 10, null)),
                stocks(stock("TCS", "TCS", "IT", com.stockanalyzer.engine.model.SizeBand.LARGE, 1000)), funds(f), 0, AS_OF);
        MixEngine.MixResult m = MixEngine.compute(ValuedPosition.of(in), 2000);
        // equity = 1000 + 600 = 1600 (80%), debt+cash = 350 (17.5%), other = 50 (2.5%)
        assertEquals("EQUITY", m.equityDebt().get(0).key());
        assertEquals("Shares", m.equityDebt().get(0).label());
        assertEquals(8000, m.equityDebt().get(0).bp());
        assertEquals(1600, m.equityDebt().get(0).valueInr());
        assertEquals("DEBT_CASH", m.equityDebt().get(1).key());
        assertEquals("Debt & cash", m.equityDebt().get(1).label());
        assertEquals(1750, m.equityDebt().get(1).bp());
        assertEquals(350, m.equityDebt().get(1).valueInr());
        assertEquals("OTHER", m.equityDebt().get(2).key());
        assertEquals("Other assets", m.equityDebt().get(2).label());
        assertEquals(250, m.equityDebt().get(2).bp());
        assertEquals("₹1,600 (80.0%)", m.equityDebt().get(0).display());
        // stocks 1000 vs funds 1000
        assertEquals("STOCKS", m.stocksFunds().get(0).key());
        assertEquals("Stocks held directly", m.stocksFunds().get(0).label());
        assertEquals(5000, m.stocksFunds().get(0).bp());
        assertEquals("FUNDS", m.stocksFunds().get(1).key());
        assertEquals("Mutual funds", m.stocksFunds().get(1).label());
        assertEquals(5000, m.stocksFunds().get(1).bp());
    }

    @Test
    @DisplayName("sample user mixes add up to 10000 bp and the rupee total")
    void sampleUserMixes() {
        PortfolioInput in = sampleUser();
        long t = total(in);
        MixEngine.MixResult m = MixEngine.compute(ValuedPosition.of(in), t);
        assertEquals(3, m.equityDebt().size());
        assertEquals(2, m.stocksFunds().size());
        assertEquals(10000, sumBp(m.equityDebt()));
        assertEquals(10000, sumBp(m.stocksFunds()));
        assertEquals(t, sumInr(m.equityDebt()));
        assertEquals(t, sumInr(m.stocksFunds()));
        assertTrue(m.equityDebt().get(0).bp() > 8000);
    }

    @Test
    @DisplayName("debt fund only is all Debt & cash; empty portfolio gives zeros with all keys present")
    void debtAndEmpty() {
        PortfolioInput debt = input(List.of(fu("900801", 100, 25, null)));
        MixEngine.MixResult m = MixEngine.compute(ValuedPosition.of(debt), total(debt));
        assertEquals(0, m.equityDebt().get(0).bp());
        assertEquals(10000, m.equityDebt().get(1).bp());
        assertEquals(10000, m.stocksFunds().get(1).bp());
        MixEngine.MixResult e = MixEngine.compute(List.of(), 0);
        assertEquals(3, e.equityDebt().size());
        assertEquals(0, sumBp(e.equityDebt()));
        assertEquals(0, sumInr(e.stocksFunds()));
    }

    @Test
    @DisplayName("size mix always has the six buckets in fixed order and adds up")
    void sizeMixHasSixBuckets() {
        PortfolioInput in = sampleUser();
        ExposureBreakdown size = ExposureEngine.compute(in).size();
        List<MixEngine.MixLine> l = MixEngine.sizeMix(size);
        assertEquals(6, l.size());
        String[] keys = {"LARGE", "MID", "SMALL", "MICRO", "DEBT_CASH", "OTHER"};
        String[] labels = {"Large cap", "Mid cap", "Small cap", "Micro cap", "Debt & cash", "Other / undisclosed"};
        for (int i = 0; i < 6; i++) {
            assertEquals(keys[i], l.get(i).key());
            assertEquals(labels[i], l.get(i).label());
        }
        assertEquals(10000, sumBp(l));
        assertEquals(0, l.get(3).bp()); // no micro cap in this portfolio
        assertEquals(total(in), sumInr(l));
        assertEquals(6, MixEngine.sizeMix(ExposureEngine.compute(input(List.of())).size()).size());
    }
}
