package com.stockanalyzer.engine;

import static com.stockanalyzer.engine.EngineFixtures.*;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.stockanalyzer.engine.model.PortfolioInput;
import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

class ConcentrationEngineTest {

    @Test
    @DisplayName("largest company, top five, top sector, counts")
    void sampleConcentration() {
        PortfolioInput in = sampleUser();
        ExposureEngine.ExposureSet es = ExposureEngine.compute(in);
        ConcentrationEngine.ConcentrationResult c = ConcentrationEngine.compute(es, 10);
        ExposureLine top = es.company().lines().get(0);
        assertEquals(top.key(), c.largestKey());
        assertEquals(top.name(), c.largestName());
        assertEquals(top.totalBp(), c.largestBp());
        assertEquals(top.directBp(), c.largestDirectBp());
        assertEquals(top.throughFundsBp(), c.largestThroughFundsBp());
        assertEquals(c.largestBp(), c.largestDirectBp() + c.largestThroughFundsBp());
        int top5 = 0;
        for (int i = 0; i < 5; i++) top5 += es.company().lines().get(i).totalBp();
        assertEquals(top5, c.top5Bp());
        assertTrue(c.top5Bp() >= c.largestBp());
        assertEquals(es.sector().top().name(), c.topSectorName());
        assertEquals(es.sector().top().totalBp(), c.topSectorBp());
        assertEquals(10, c.holdingCount());
        assertEquals(10.0, c.equalSplitPct(), 1e-12);
        int companies = 0;
        for (ExposureLine l : es.company().lines()) if (!l.isBucket()) companies++;
        assertEquals(companies, c.companyCount());
        assertTrue(companies > 50);
    }

    @Test
    @DisplayName("buckets never count as the largest company or sector")
    void bucketsExcluded() {
        PortfolioInput in = input(List.of(fu("900801", 100, 25, null)));
        ExposureEngine.ExposureSet es = ExposureEngine.compute(in);
        ConcentrationEngine.ConcentrationResult c = ConcentrationEngine.compute(es, 1);
        assertNull(c.largestKey());
        assertNull(c.largestName());
        assertEquals(0, c.largestBp());
        assertNull(c.topSectorName());
        assertEquals(0, c.companyCount());
        assertEquals(1, c.holdingCount());
    }

    @Test
    @DisplayName("hand-computed three stock portfolio")
    void handComputed() {
        PortfolioInput in = input(List.of(st("ITC", 100, 1, null), st("TCS", 10, 1, null), st("INFY", 10, 1, null)));
        // ITC 47000 ; TCS 39254 ; INFY 18000 => total 104254
        ExposureEngine.ExposureSet es = ExposureEngine.compute(in);
        ConcentrationEngine.ConcentrationResult c = ConcentrationEngine.compute(es, 3);
        assertEquals("ITC", c.largestKey());
        assertEquals(4508, c.largestBp(), 1); // 47000/104254
        assertEquals(10000, c.top5Bp());
        assertEquals(3, c.companyCount());
        assertEquals("Information Technology", c.topSectorName()); // TCS + INFY = 57254 > ITC 47000
        assertEquals(2, c.sectorCount());
        assertEquals(33.33, c.equalSplitPct(), 1e-12);
    }

    @Test
    @DisplayName("empty portfolio")
    void empty() {
        ConcentrationEngine.ConcentrationResult c = ConcentrationEngine.compute(ExposureEngine.compute(input(List.of())), 0);
        assertNull(c.largestKey());
        assertEquals(0, c.holdingCount());
        assertEquals(0.0, c.equalSplitPct(), 1e-12);
    }
}
