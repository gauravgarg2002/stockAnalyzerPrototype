package com.stockanalyzer.engine;

import static com.stockanalyzer.engine.EngineFixtures.*;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.stockanalyzer.engine.model.PortfolioInput;
import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

class CostEngineTest {

    private static CostEngine.CostResult cost(PortfolioInput in) {
        return CostEngine.compute(ValuedPosition.of(in));
    }

    @Test
    @DisplayName("regular plan: yearly cost and gap against the direct twin, in rupees")
    void regularVersusDirect() {
        // 1,000 units x 62.4012 = 62,401.2 ; TER 1.72% => 1,073.30 ; gap (1.72-0.68)% => 648.97
        PortfolioInput in = input(List.of(fu("900101", 1000, 60, null)));
        CostEngine.CostResult r = cost(in);
        assertEquals(1073, r.totalYearlyInr());
        assertEquals(649, r.regularGapYearlyInr());
        assertTrue(r.hasFunds());
        assertTrue(r.hasRegularFunds());
        assertTrue(r.hasRegularWithTwin());
        CostEngine.FundCost f = r.funds().get(0);
        assertEquals("900101", f.schemeCode());
        assertEquals(62401, f.valueInr());
        assertEquals(1073, f.yearlyCostInr().longValue());
        assertEquals(649, f.yearlyGapInr().longValue());
        assertEquals("900102", f.twinSchemeCode());
        assertEquals(0.68, f.twinTerPct(), 1e-12);
    }

    @Test
    @DisplayName("direct plans have no gap; totals add the funds")
    void directOnly() {
        // 900201: 3120.5 x 21.85 = 68,182.925 x 0.18% = 122.73 ; 900301: 410.112 x 98.3 = 40,314.1 x 0.74% = 298.33
        PortfolioInput in = input(List.of(fu("900201", 3120.5, 21, null), fu("900301", 410.112, 98, null)));
        CostEngine.CostResult r = cost(in);
        assertEquals(421, r.totalYearlyInr()); // 122.73 + 298.34 = 421.07
        assertEquals(0, r.regularGapYearlyInr());
        assertFalse(r.hasRegularFunds());
        assertNull(r.funds().get(0).yearlyGapInr());
        assertNull(r.funds().get(1).yearlyGapInr());
    }

    @Test
    @DisplayName("stocks do not cost anything and no funds gives zero")
    void noFunds() {
        CostEngine.CostResult r = cost(input(List.of(st("TCS", 10, 3000, null))));
        assertFalse(r.hasFunds());
        assertEquals(0, r.totalYearlyInr());
        assertEquals(0, r.regularGapYearlyInr());
        assertTrue(r.funds().isEmpty());
    }

    @Test
    @DisplayName("regular and direct plans together; funds are listed by value, largest first")
    void mixedPlans() {
        PortfolioInput in = input(List.of(fu("900101", 1000, 60, null), fu("900102", 5000, 60, null)));
        CostEngine.CostResult r = cost(in);
        assertEquals("900102", r.funds().get(0).schemeCode()); // 5000 x 66.1 is larger
        // regular 62,401.2 x 1.72% = 1,073.30 ; direct 330,500 x 0.68% = 2,247.40 => 3,320.70
        assertEquals(3321, r.totalYearlyInr());
        assertEquals(649, r.regularGapYearlyInr());
    }

    @Test
    @DisplayName("unknown expense ratio is left out of the total")
    void unknownTer() {
        var f = fund("U1", "Unknown TER", "Flexi Cap Fund", "DIRECT", null, null, null, 10.0, mix(100, 0, 0, 0), List.of());
        PortfolioInput in = new PortfolioInput(List.of(fu("U1", 100, 10, null)), stocks(), funds(f), 0, AS_OF);
        CostEngine.CostResult r = cost(in);
        assertEquals(0, r.totalYearlyInr());
        assertNull(r.funds().get(0).yearlyCostInr());
        assertEquals(1000, r.funds().get(0).valueInr());
    }
}
