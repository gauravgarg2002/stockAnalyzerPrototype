package com.stockanalyzer.web.dto;

import com.stockanalyzer.web.dto.Shared.ExposureBreakdownView;
import com.stockanalyzer.web.dto.Shared.ExposureLineView;
import com.stockanalyzer.web.dto.Shared.Figure;
import com.stockanalyzer.web.dto.Shared.ImportLogEntry;
import com.stockanalyzer.web.dto.Shared.MixLineView;
import com.stockanalyzer.web.dto.Shared.PortfolioFact;
import com.stockanalyzer.web.dto.Shared.Sentence;
import com.stockanalyzer.web.dto.Shared.WatchlistItem;
import java.util.List;

/** Contract A.2 and A.3. */
public final class PortfolioDto {
    private PortfolioDto() { }

    public record HomeResponse(boolean sampleData, String asOf, boolean connected, boolean hasHoldings,
                               List<Sentence> summary, List<ExposureLineView> topExposures, List<PortfolioFact> facts,
                               List<WatchlistItem> watchlist, ImportLogEntry lastImport) { }

    public record Totals(Figure holdingsValue, Figure invested, Figure idleCash, Figure totalWithCash) { }

    public record Exposure(ExposureBreakdownView company, ExposureBreakdownView sector, ExposureBreakdownView size) { }

    public record Concentration(Figure largestCompany, Figure top5Companies, Figure topSector, Figure companyCount,
                                Figure holdingCount, List<Sentence> sentences) { }

    public record FundRef(String schemeCode, String name) { }

    public record CommonHoldingView(String key, String name, double weightA, double weightB, double minWeight) { }

    public record OverlapPairView(FundRef fundA, FundRef fundB, Figure overlap, int commonCount,
                                  List<CommonHoldingView> topCommon) { }

    public record OverlapSection(List<OverlapPairView> pairs, List<Sentence> sentences) { }

    public record DirectTwinView(String schemeCode, String name, Double terPct) { }

    public record CostFundView(String schemeCode, String name, String planType, Figure value, Figure expenseRatio,
                               Figure yearlyCost, DirectTwinView directTwin, Figure yearlyGap) { }

    public record CostsSection(Figure totalYearly, Figure regularGapYearly, List<CostFundView> funds,
                               List<Sentence> sentences) { }

    public record MixSection(List<MixLineView> equityDebt, List<MixLineView> stocksFunds, List<Sentence> sentences) { }

    public record ReturnRow(String kind, String id, String name, Figure oneYear, Figure sinceBuy, Figure gain) { }

    public record ReturnsSection(String benchmarkName, ReturnRow portfolio, List<ReturnRow> holdings,
                                 List<Sentence> sentences) { }

    public record HoldingRow(List<Long> holdingIds, String kind, String id, String name, String subtitle,
                             double quantity, double avgPrice, Figure lastPrice, Figure value, double weightPct,
                             List<String> sources, String firstBuyDate, String checkPath) { }

    public record PortfolioResponse(boolean sampleData, String asOf, boolean connected, boolean hasHoldings,
                                    Totals totals, List<Sentence> summary, List<PortfolioFact> facts,
                                    Exposure exposure, Concentration concentration, OverlapSection overlap,
                                    CostsSection costs, MixSection mix, ReturnsSection returns,
                                    List<HoldingRow> holdings) { }
}
