package com.stockanalyzer.engine;

import static com.stockanalyzer.engine.EngineFixtures.*;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.stockanalyzer.engine.TryItOnEngine.Mode;
import com.stockanalyzer.engine.TryItOnEngine.TryItOnResult;
import com.stockanalyzer.engine.model.Kind;
import com.stockanalyzer.engine.model.PortfolioInput;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

class TryItOnEngineTest {

    @Test
    @DisplayName("before snapshot is exactly the portfolio engine result")
    void beforeEqualsPortfolio() {
        PortfolioInput in = sampleUser();
        TryItOnResult r = TryItOnEngine.run(in, Kind.STOCK, "INFY", Mode.LUMP_SUM, 50000, null);
        assertEquals(PortfolioEngine.compute(in, null), r.before());
    }

    @Test
    @DisplayName("lump sum into a new stock adds a holding and keeps every dimension at 10000 bp")
    void lumpSumNewStock() {
        PortfolioInput in = sampleUser();
        TryItOnResult r = TryItOnEngine.run(in, Kind.STOCK, "INFY", Mode.LUMP_SUM, 100000, 12);
        assertFalse(r.alreadyHeld());
        assertEquals(Mode.LUMP_SUM, r.mode());
        assertNull(r.months());
        assertEquals(100000, r.addedValueInr());
        assertEquals("Infosys Ltd", r.name());
        assertEquals(r.before().holdingCount() + 1, r.after().holdingCount());
        assertEquals(10, r.before().holdingCount());
        assertEquals(10000, r.after().company().sumBp());
        assertEquals(10000, r.after().sector().sumBp());
        assertEquals(10000, r.after().size().sumBp());
        assertEquals(r.after().valueInr(), r.after().company().sumInr());
        assertEquals(r.before().valueInr() + 100000, r.after().valueInr(), 1);
        assertEquals(r.before().cost().totalYearlyInr(), r.after().cost().totalYearlyInr()); // a stock adds no fund fee
        assertTrue(r.fundOverlaps().isEmpty());
    }

    @Test
    @DisplayName("SIP adds amount x months (default 12)")
    void sip() {
        PortfolioInput in = sampleUser();
        TryItOnResult r = TryItOnEngine.run(in, Kind.FUND, "900801", Mode.SIP, 5000, 12);
        assertEquals(60000, r.addedValueInr());
        assertEquals(12, r.months().intValue());
        assertEquals(r.before().valueInr() + 60000, r.after().valueInr(), 1);
        TryItOnResult d = TryItOnEngine.run(in, Kind.FUND, "900801", Mode.SIP, 5000, null);
        assertEquals(60000, d.addedValueInr());
        assertEquals(12, d.months().intValue());
        TryItOnResult m = TryItOnEngine.run(in, Kind.FUND, "900801", Mode.SIP, 2500, 60);
        assertEquals(150000, m.addedValueInr());
        assertEquals(1, TryItOnEngine.run(in, Kind.FUND, "900801", Mode.SIP, 2500, 1).months().intValue());
        // a debt fund adds 0.38% of 60000 in fees
        assertEquals(r.before().cost().totalYearlyInr() + 228, r.after().cost().totalYearlyInr(), 1);
        assertTrue(r.after().cost().totalYearlyInr() > r.before().cost().totalYearlyInr());
    }

    @Test
    @DisplayName("adding to a held fund keeps the holding count")
    void addToHeld() {
        PortfolioInput in = sampleUser();
        TryItOnResult r = TryItOnEngine.run(in, Kind.FUND, "900101", Mode.LUMP_SUM, 100000, null);
        assertTrue(r.alreadyHeld());
        assertEquals(r.before().holdingCount(), r.after().holdingCount());
        assertEquals(r.before().fundCount(), r.after().fundCount());
        assertEquals(r.before().valueInr() + 100000, r.after().valueInr(), 1);
        assertTrue(r.after().cost().totalYearlyInr() > r.before().cost().totalYearlyInr());
        TryItOnResult s = TryItOnEngine.run(in, Kind.STOCK, "TCS", Mode.LUMP_SUM, 10000, null);
        assertTrue(s.alreadyHeld());
        assertEquals(10, s.after().holdingCount());
    }

    @Test
    @DisplayName("fund overlap list excludes the candidate itself and is sorted")
    void overlapExcludesSelf() {
        PortfolioInput in = sampleUser();
        TryItOnResult held = TryItOnEngine.run(in, Kind.FUND, "900101", Mode.LUMP_SUM, 1000, null);
        assertEquals(3, held.fundOverlaps().size());
        for (TryItOnEngine.FundOverlap o : held.fundOverlaps()) assertFalse(o.schemeCode().equals("900101"));
        for (int i = 1; i < held.fundOverlaps().size(); i++) {
            assertTrue(held.fundOverlaps().get(i - 1).pct() >= held.fundOverlaps().get(i).pct());
        }
        TryItOnResult twin = TryItOnEngine.run(in, Kind.FUND, "900102", Mode.LUMP_SUM, 1000, null);
        assertEquals(4, twin.fundOverlaps().size());
        assertEquals("900101", twin.fundOverlaps().get(0).schemeCode()); // twin plan, near-total overlap
        assertEquals(96.0, twin.fundOverlaps().get(0).pct(), 1e-9); // all disclosed equity
        assertTrue(twin.stockInFunds().isEmpty());
        assertEquals(0, twin.exposureBeforeBp());
        TryItOnResult debt = TryItOnEngine.run(in, Kind.FUND, "900801", Mode.LUMP_SUM, 1000, null);
        for (TryItOnEngine.FundOverlap o : debt.fundOverlaps()) assertEquals(0.0, o.pct(), 1e-12);
    }

    @Test
    @DisplayName("stock candidate: weight inside each held fund and total exposure before and after")
    void stockCandidate() {
        PortfolioInput in = sampleUser();
        TryItOnResult r = TryItOnEngine.run(in, Kind.STOCK, "INFY", Mode.LUMP_SUM, 100000, null);
        // INFY is 4.0 in the regular flexi fund and 5.5 in the index fund; not in the mid cap or ELSS funds
        assertEquals(2, r.stockInFunds().size());
        assertEquals("900201", r.stockInFunds().get(0).schemeCode());
        assertEquals(5.5, r.stockInFunds().get(0).weightPct(), 1e-12);
        assertEquals("900101", r.stockInFunds().get(1).schemeCode());
        assertEquals(4.0, r.stockInFunds().get(1).weightPct(), 1e-12);
        assertTrue(r.exposureBeforeBp() > 0);
        assertTrue(r.exposureAfterBp() > r.exposureBeforeBp());
        TryItOnResult none = TryItOnEngine.run(in, Kind.STOCK, "DECCANINF", Mode.LUMP_SUM, 1000, null);
        assertTrue(none.stockInFunds().isEmpty());
        assertTrue(none.alreadyHeld());
    }

    @Test
    @DisplayName("largest company and size mix change as expected for a big purchase")
    void concentrationChanges() {
        PortfolioInput in = sampleUser();
        TryItOnResult r = TryItOnEngine.run(in, Kind.STOCK, "INFY", Mode.LUMP_SUM, 5000000, null);
        assertEquals("INFY", r.after().concentration().largestKey());
        assertTrue(r.after().concentration().largestBp() > r.before().concentration().largestBp());
        assertEquals("Information Technology", r.after().concentration().topSectorName());
        assertEquals(6, r.after().sizeMix().size());
        assertTrue(r.after().sizeMix().get(0).bp() > r.before().sizeMix().get(0).bp());
    }

    @Test
    @DisplayName("works on an empty portfolio")
    void emptyPortfolio() {
        PortfolioInput in = input(java.util.List.of());
        TryItOnResult r = TryItOnEngine.run(in, Kind.STOCK, "TCS", Mode.LUMP_SUM, 39254, null);
        assertEquals(0, r.before().holdingCount());
        assertEquals(1, r.after().holdingCount());
        assertEquals("TCS", r.after().concentration().largestKey());
        assertEquals(10000, r.after().company().sumBp());
        assertEquals(10000, r.exposureAfterBp());
    }

    @Test
    @DisplayName("invalid input is rejected")
    void invalid() {
        PortfolioInput in = sampleUser();
        assertThrows(IllegalArgumentException.class, () -> TryItOnEngine.run(in, Kind.STOCK, "TCS", Mode.LUMP_SUM, 0, null));
        assertThrows(IllegalArgumentException.class, () -> TryItOnEngine.run(in, Kind.STOCK, "TCS", Mode.LUMP_SUM, -5, null));
        assertThrows(IllegalArgumentException.class, () -> TryItOnEngine.run(in, Kind.FUND, "900801", Mode.SIP, 100, 61));
        assertThrows(IllegalArgumentException.class, () -> TryItOnEngine.run(in, Kind.FUND, "900801", Mode.SIP, 100, 0));
        assertThrows(IllegalArgumentException.class, () -> TryItOnEngine.run(in, Kind.STOCK, "NOPE", Mode.LUMP_SUM, 100, null));
        assertThrows(IllegalArgumentException.class, () -> TryItOnEngine.run(in, Kind.FUND, "NOPE", Mode.LUMP_SUM, 100, null));
    }
}
