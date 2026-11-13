package com.stockanalyzer.web.dto;

import com.stockanalyzer.web.dto.Shared.Figure;
import com.stockanalyzer.web.dto.Shared.InstrumentRef;
import com.stockanalyzer.web.dto.Shared.MixLineView;
import com.stockanalyzer.web.dto.Shared.Sentence;
import java.util.List;

/** Contract A.8. */
public final class TryItOnDto {
    private TryItOnDto() { }

    public record Request(String kind, String id, String mode, Double amountInr, Integer months) { }

    public record Input(String mode, double amountInr, Integer months, long addedValueInr, String addedValueDisplay,
                        boolean alreadyHeld) { }

    public record NamedFigure(String name, Figure figure) { }

    public record NamedBeforeAfter(NamedFigure before, NamedFigure after) { }

    public record SizeMixBeforeAfter(List<MixLineView> before, List<MixLineView> after) { }

    public record FigureBeforeAfter(Figure before, Figure after) { }

    public record FundOverlapView(String schemeCode, String name, Figure overlap) { }

    public record StockInFundView(String schemeCode, String name, Figure weight) { }

    public record OverlapMetrics(String candidateKind, List<FundOverlapView> fundOverlaps,
                                 List<StockInFundView> stockInFunds, FigureBeforeAfter exposureToCandidate) { }

    public record CostMetrics(Figure before, Figure after, Figure change) { }

    public record Metrics(NamedBeforeAfter largestCompany, NamedBeforeAfter topSector, SizeMixBeforeAfter sizeMix,
                          FigureBeforeAfter holdingsCount, OverlapMetrics overlap, CostMetrics yearlyCost) { }

    public record Response(boolean sampleData, String asOf, InstrumentRef instrument, Input input,
                           Sentence assumption, Metrics metrics, List<Sentence> sentences) { }
}
