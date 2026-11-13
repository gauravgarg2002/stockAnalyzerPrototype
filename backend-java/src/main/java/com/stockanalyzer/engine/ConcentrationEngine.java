package com.stockanalyzer.engine;

/** Concentration facts taken from the exposure breakdowns. */
public final class ConcentrationEngine {
    private ConcentrationEngine() { }

    public record ConcentrationResult(String largestKey, String largestName, int largestBp, int largestDirectBp,
                                      int largestThroughFundsBp, int top5Bp, String topSectorName, int topSectorBp,
                                      int companyCount, int sectorCount, int holdingCount, double equalSplitPct) { }

    public static ConcentrationResult compute(ExposureEngine.ExposureSet es, int holdingCount) {
        ExposureLine top = es.company().top();
        int top5 = 0;
        int companies = 0;
        for (ExposureLine l : es.company().lines()) {
            if (l.isBucket()) continue;
            if (companies < 5) top5 += l.totalBp();
            companies++;
        }
        ExposureLine sec = es.sector().top();
        int sectors = 0;
        for (ExposureLine l : es.sector().lines()) if (!l.isBucket()) sectors++;
        double equal = holdingCount > 0 ? Money.round2(100.0 / holdingCount) : 0.0;
        return new ConcentrationResult(
                top == null ? null : top.key(), top == null ? null : top.name(),
                top == null ? 0 : top.totalBp(), top == null ? 0 : top.directBp(), top == null ? 0 : top.throughFundsBp(),
                top5, sec == null ? null : sec.name(), sec == null ? 0 : sec.totalBp(),
                companies, sectors, holdingCount, equal);
    }
}
