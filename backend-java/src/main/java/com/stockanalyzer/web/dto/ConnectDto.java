package com.stockanalyzer.web.dto;

import com.stockanalyzer.web.dto.Shared.ImportLogEntry;
import java.util.List;
import java.util.Map;

/** Contract A.1, A.11 (connection), A.12 and A.13. */
public final class ConnectDto {
    private ConnectDto() { }

    public record MetaResponse(boolean sampleData, String asOf, Map<String, String> adapters, boolean llmEnabled,
                               String disclaimer, long defaultIllustrativeAmountInr) { }

    public record HoldingsSummary(int stockCount, int fundCount, Map<String, Integer> bySource) { }

    public record ConnectionResponse(boolean sampleData, String brokerMode, String status, String accountLabel,
                                     String loginUrl, String lastImportAt, List<ImportLogEntry> imports,
                                     HoldingsSummary holdingsSummary) { }

    public record StartResponse(boolean sampleData, String brokerMode, String status, String loginUrl, String message) { }

    public record StatusResponse(boolean sampleData, String brokerMode, String status, String accountLabel,
                                 String message) { }

    public record UnmatchedView(String name, String isin, String reason) { }

    public record ImportResult(boolean sampleData, long importId, String source, String status, String importedAt,
                               int stockCount, int fundCount, Double idleCashInr, List<UnmatchedView> unmatched,
                               String message) { }

    public record HoldingView(long id, String kind, String instrumentId, String name, double quantity, double avgPrice,
                              String firstBuyDate, String source, String importedAt) { }

    public record HoldingsResponse(boolean sampleData, List<HoldingView> holdings) { }

    public record HoldingCreated(boolean sampleData, long id, String kind, String instrumentId, String name,
                                 double quantity, double avgPrice, String firstBuyDate, String source,
                                 String importedAt) { }

    public record ManualHoldingRequest(String kind, String instrumentId, Double quantity, Double avgPrice,
                                       String firstBuyDate) { }

    public record WatchlistCreateRequest(String kind, String instrumentId, String note) { }

    public record WatchlistPatchRequest(String note) { }

    public record WatchlistResponse(boolean sampleData, List<Shared.WatchlistItem> items) { }
}
