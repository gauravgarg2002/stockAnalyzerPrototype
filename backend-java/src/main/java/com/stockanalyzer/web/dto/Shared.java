package com.stockanalyzer.web.dto;

import java.util.List;

/** Shared public shapes (contract §0.3). Nulls are always serialised. */
public final class Shared {
    private Shared() { }

    public record Comparison(String kind, String label, Object value, String unit, String display) { }

    /** value is a Long (INR), Double, or String (TEXT); null shows as "Not available". */
    public record Figure(String id, String label, Object value, String unit, String display, String source,
                         String asOf, List<Comparison> comparisons, String termId) { }

    public record Sentence(String text, String templateId, String generator) { }

    public record InstrumentRef(String kind, String id, String name, String subtitle) { }

    public record ViaFundView(String schemeCode, String name, long inr) { }

    public record ExposureLineView(String key, String name, String kind, String symbol, boolean checkAvailable,
                                   long totalInr, long directInr, long throughFundsInr,
                                   double totalPct, double directPct, double throughFundsPct,
                                   String display, String directDisplay, String throughFundsDisplay,
                                   List<ViaFundView> viaFunds) { }

    public record ExposureBreakdownView(String dimension, long totalInr, List<ExposureLineView> lines,
                                        List<Sentence> sentences) { }

    public record MixLineView(String key, String label, long valueInr, double pct, String display) { }

    public record PortfolioFact(String id, Sentence sentence, List<Figure> figures) { }

    public record WatchlistItem(long id, String kind, String instrumentId, String name, String subtitle, String note,
                                String createdAt, String updatedAt, Figure latest, String checkPath) { }

    public record WatchlistItemResponse(boolean sampleData, long id, String kind, String instrumentId, String name,
                                        String subtitle, String note, String createdAt, String updatedAt,
                                        Figure latest, String checkPath) { }

    public record ImportLogEntry(long id, String source, String status, String startedAt, String finishedAt,
                                 int stockCount, int fundCount, int unmatchedCount, String message,
                                 boolean sampleData) { }

    /** The "user" block added to stock and fund checks. */
    public record UserBlock(boolean holds, Double quantity, Figure holdingValue, Long watchlistItemId, String note) { }
}
