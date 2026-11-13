package com.stockanalyzer.engine;

import com.stockanalyzer.engine.model.Kind;
import java.time.LocalDate;
import java.util.List;

/** All numbers needed for /api/portfolio and /api/home. */
public record PortfolioResult(
        LocalDate asOf, boolean hasHoldings,
        long valueInr, long investedInr, double idleCashInr, long totalWithCashInr,
        int stockCount, int fundCount, int holdingCount,
        ExposureBreakdown company, ExposureBreakdown sector, ExposureBreakdown size,
        ConcentrationEngine.ConcentrationResult concentration,
        List<OverlapEngine.OverlapPair> overlapPairs,
        CostEngine.CostResult cost,
        List<MixEngine.MixLine> equityDebt, List<MixEngine.MixLine> stocksFunds, List<MixEngine.MixLine> sizeMix,
        List<HoldingValue> holdings,
        ReturnsEngine.ReturnsResult returns) {

    /** weightBp: share of holdings value, largest remainder, sums to 10000. */
    public record HoldingValue(Kind kind, String id, String name, double quantity, double avgPrice, double lastPrice,
                               long valueInr, int weightBp, long costInr,
                               LocalDate firstBuyDate) {
        public double weightPct() { return Bp.pct(weightBp); }
    }

    /** Idle cash as a percent of holdings plus idle cash (2 dp). 0 when there is neither. */
    public double idleCashPct() {
        double total = valueInr + idleCashInr;
        return total > 0 ? Money.round2(idleCashInr / total * 100.0) : 0.0;
    }
}
