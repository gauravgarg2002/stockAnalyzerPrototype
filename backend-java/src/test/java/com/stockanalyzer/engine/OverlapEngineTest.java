package com.stockanalyzer.engine;

import static com.stockanalyzer.engine.EngineFixtures.*;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.stockanalyzer.engine.model.FundInfo;
import com.stockanalyzer.engine.model.SizeBand;
import java.time.LocalDate;
import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

class OverlapEngineTest {

    private static FundInfo f(String code, List<com.stockanalyzer.engine.model.FundConstituent> cs) {
        return fund(code, "Fund " + code, "Flexi Cap Fund", "DIRECT", 1.0, null, null, 10.0, mix(90, 0, 10, 0), cs);
    }

    private static com.stockanalyzer.engine.model.FundConstituent w(String key, double weight) {
        return c(key, key + " Ltd", "S", SizeBand.LARGE, weight);
    }

    @Test
    @DisplayName("A{X:10,Y:5} and B{X:4,Z:7} overlap by 4.00 (lower weight of the common stock)")
    void basicFormula() {
        FundInfo a = f("A", List.of(w("X", 10), w("Y", 5)));
        FundInfo b = f("B", List.of(w("X", 4), w("Z", 7)));
        OverlapEngine.OverlapResult r = OverlapEngine.overlap(a, b);
        assertEquals(4.00, r.pct(), 1e-12);
        assertEquals(1, r.commonCount());
        assertEquals(1, r.topCommon().size());
        assertEquals("X", r.topCommon().get(0).key());
        assertEquals(10.0, r.topCommon().get(0).weightA(), 1e-12);
        assertEquals(4.0, r.topCommon().get(0).weightB(), 1e-12);
        assertEquals(4.0, r.topCommon().get(0).minWeight(), 1e-12);
    }

    @Test
    @DisplayName("identical funds overlap by the sum of their weights")
    void identical() {
        FundInfo a = f("A", List.of(w("X", 10), w("Y", 5.25), w("Z", 1.1)));
        FundInfo b = f("B", List.of(w("X", 10), w("Y", 5.25), w("Z", 1.1)));
        assertEquals(16.35, OverlapEngine.overlap(a, b).pct(), 1e-9);
        assertEquals(3, OverlapEngine.overlap(a, b).commonCount());
    }

    @Test
    @DisplayName("disjoint funds overlap by 0")
    void disjoint() {
        FundInfo a = f("A", List.of(w("X", 10)));
        FundInfo b = f("B", List.of(w("Y", 10)));
        OverlapEngine.OverlapResult r = OverlapEngine.overlap(a, b);
        assertEquals(0.0, r.pct(), 1e-12);
        assertEquals(0, r.commonCount());
        assertTrue(r.topCommon().isEmpty());
    }

    @Test
    @DisplayName("overlap is symmetric")
    void symmetric() {
        FundInfo a = flexiRegular();
        FundInfo b = indexFund();
        assertEquals(OverlapEngine.overlap(a, b).pct(), OverlapEngine.overlap(b, a).pct(), 1e-12);
        assertEquals(OverlapEngine.overlap(a, b).commonCount(), OverlapEngine.overlap(b, a).commonCount());
        // HDFCBANK 8.12 vs 12.95, RELIANCE 6 vs 10.5, TCS 5 vs 4, INFY 4 vs 5.5 => 8.12 + 6 + 4 + 4 = 22.12
        assertEquals(22.12, OverlapEngine.overlap(a, b).pct(), 1e-9);
    }

    @Test
    @DisplayName("twin plans overlap by the full disclosed equity")
    void twins() {
        FundInfo reg = flexiRegular();
        FundInfo dir = flexiDirect();
        double disclosed = 0;
        for (var cc : reg.constituents()) disclosed += cc.weightPct();
        OverlapEngine.OverlapResult r = OverlapEngine.overlap(reg, dir);
        assertEquals(disclosed, r.pct(), 0.005);
        assertEquals(reg.constituents().size(), r.commonCount());
    }

    @Test
    @DisplayName("result is rounded half-up to 2 dp and top common holdings are the 5 largest by lower weight")
    void roundingAndTop() {
        FundInfo a = f("A", List.of(w("A1", 1.005), w("A2", 9), w("A3", 8), w("A4", 7), w("A5", 6), w("A6", 5), w("A7", 4)));
        FundInfo b = f("B", List.of(w("A1", 1.0), w("A2", 20), w("A3", 20), w("A4", 20), w("A5", 20), w("A6", 20), w("A7", 20)));
        OverlapEngine.OverlapResult r = OverlapEngine.overlap(a, b);
        assertEquals(40.0, r.pct(), 1e-9); // 1.0 + 9+8+7+6+5+4 = 40.0
        assertEquals(7, r.commonCount());
        assertEquals(5, r.topCommon().size());
        assertEquals("A2", r.topCommon().get(0).key());
        assertEquals("A6", r.topCommon().get(4).key());
        FundInfo a2 = f("A", List.of(w("X", 0.125)));
        FundInfo b2 = f("B", List.of(w("X", 0.5)));
        assertEquals(0.13, OverlapEngine.overlap(a2, b2).pct(), 1e-12);
    }

    @Test
    @DisplayName("pairs cover every unordered pair of distinct funds, highest overlap first, with the oldest portfolio date")
    void pairs() {
        FundInfo a = flexiRegular();
        FundInfo b = flexiDirect();
        FundInfo c3 = indexFund();
        FundInfo d = debtFund();
        List<OverlapEngine.OverlapPair> pairs = OverlapEngine.pairs(List.of(a, b, c3, d, a));
        assertEquals(6, pairs.size()); // C(4,2)
        assertEquals("900101", pairs.get(0).schemeCodeA());
        assertEquals("900102", pairs.get(0).schemeCodeB()); // twins first
        for (int i = 1; i < pairs.size(); i++) {
            assertTrue(pairs.get(i - 1).result().pct() >= pairs.get(i).result().pct());
        }
        assertEquals(0.0, pairs.get(5).result().pct(), 1e-12);
        FundInfo older = new FundInfo(c3.schemeCode(), c3.name(), c3.category(), c3.planType(), c3.terPct(), null, null, null,
                null, c3.nav(), c3.assetMix(), LocalDate.of(2026, 8, 31), c3.constituents());
        assertEquals(LocalDate.of(2026, 8, 31), OverlapEngine.pairs(List.of(a, older)).get(0).asOf());
        assertTrue(OverlapEngine.pairs(List.of(a)).isEmpty());
        assertTrue(OverlapEngine.pairs(List.of()).isEmpty());
    }

    @Test
    @DisplayName("duplicate keys inside one fund are added together")
    void duplicateKeys() {
        FundInfo a = f("A", List.of(w("X", 3), w("X", 2)));
        FundInfo b = f("B", List.of(w("X", 10)));
        assertEquals(5.0, OverlapEngine.overlap(a, b).pct(), 1e-12);
    }
}
