package com.stockanalyzer.python.dto;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.stockanalyzer.engine.NarrateItem;
import com.stockanalyzer.web.dto.Shared.Sentence;
import java.util.List;
import java.util.Map;

/** Records mirroring contract §B.1, B.8, B.9, B.10, B.11 and B.12. Unknown JSON fields are ignored. */
public final class PyDto {
    private PyDto() { }

    // B.1
    @JsonIgnoreProperties(ignoreUnknown = true)
    public record Health(String status, boolean sampleData, String asOf, String version, Map<String, String> adapters,
                         String statementParser, boolean llmEnabled) { }

    // B.8
    public record BundleRequest(List<String> stocks, List<String> funds) { }

    @JsonIgnoreProperties(ignoreUnknown = true)
    public record BundleStock(String symbol, String name, String isin, String sector, String industry, String sizeBand,
                              String subtitle, Double lastPrice, String lastPriceDate, Double priceOneYearAgo,
                              String source, boolean checkAvailable) { }

    @JsonIgnoreProperties(ignoreUnknown = true)
    public record BundleAssetMix(double equityPct, double debtPct, double cashPct, double otherPct) { }

    @JsonIgnoreProperties(ignoreUnknown = true)
    public record BundleHolding(String key, String symbol, String isin, String name, String sector, String sizeBand,
                                Double weightPct, boolean checkAvailable) { }

    @JsonIgnoreProperties(ignoreUnknown = true)
    public record BundleFund(String schemeCode, String isin, String name, String subtitle, String amc, String category,
                             String categoryGroup, String planType, Double terPct, Double categoryMedianTerPct,
                             String twinSchemeCode, String twinName, Double twinTerPct, Double nav, String navDate,
                             Double navOneYearAgo, BundleAssetMix assetMix, String portfolioDate,
                             List<BundleHolding> holdings, String source) { }

    @JsonIgnoreProperties(ignoreUnknown = true)
    public record NotFound(String kind, String id) { }

    @JsonIgnoreProperties(ignoreUnknown = true)
    public record BundleResponse(boolean sampleData, String asOf, List<BundleStock> stocks, List<BundleFund> funds,
                                 List<NotFound> notFound) { }

    // B.9
    public record PointsItem(String kind, String id, List<String> dates) { }

    public record PointsRequest(List<PointsItem> items) { }

    @JsonIgnoreProperties(ignoreUnknown = true)
    public record PointValue(String requestedDate, String date, Double value) { }

    @JsonIgnoreProperties(ignoreUnknown = true)
    public record PointsResultItem(String kind, String id, List<PointValue> values) { }

    @JsonIgnoreProperties(ignoreUnknown = true)
    public record PointsResponse(boolean sampleData, String asOf, List<PointsResultItem> items) { }

    // B.10
    @JsonIgnoreProperties(ignoreUnknown = true)
    public record BrokerStatus(boolean sampleData, String brokerMode, String status, String loginUrl,
                               String accountLabel, String message) { }

    public record LoginCompleteRequest(String requestToken) { }

    @JsonIgnoreProperties(ignoreUnknown = true)
    public record Unmatched(String name, String isin, String reason) { }

    @JsonIgnoreProperties(ignoreUnknown = true)
    public record BrokerStock(String symbol, String isin, Double quantity, Double avgPrice, Double lastPrice,
                              String firstBuyDate) { }

    @JsonIgnoreProperties(ignoreUnknown = true)
    public record BrokerFund(String schemeCode, String isin, String name, Double units, Double avgNav, Double lastNav,
                             String firstBuyDate) { }

    @JsonIgnoreProperties(ignoreUnknown = true)
    public record BrokerPortfolio(boolean sampleData, String source, String asOf, String accountLabel,
                                  List<BrokerStock> stocks, List<BrokerFund> funds, Double idleCashInr,
                                  List<Unmatched> unmatched) { }

    // B.11
    public record StatementRequest(String filename, String fileBase64, String password) { }

    @JsonIgnoreProperties(ignoreUnknown = true)
    public record StatementFund(String schemeCode, String isin, String name, String amc, Double units, Double nav,
                                String navDate, Double valueInr, Double avgCostNav) { }

    @JsonIgnoreProperties(ignoreUnknown = true)
    public record StatementResponse(boolean sampleData, String parser, String statementType, String statementDate,
                                    List<StatementFund> funds, List<Unmatched> unmatched) { }

    // B.12
    public record NarrateRequest(List<NarrateItem> items, boolean useLlm) { }

    @JsonIgnoreProperties(ignoreUnknown = true)
    public record NarrateResultItem(String key, Sentence sentence) { }

    @JsonIgnoreProperties(ignoreUnknown = true)
    public record NarrateResponse(boolean sampleData, List<NarrateResultItem> items) { }

    // B.4 request
    public record FundCheckUserFund(String schemeCode, String name, double overlapPct, int commonCount) { }

    public record FundCheckRequest(double amountInr, String amountBasis, List<FundCheckUserFund> userFunds) { }
}
