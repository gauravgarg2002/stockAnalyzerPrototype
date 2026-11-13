package com.stockanalyzer.engine.model;

import java.time.LocalDate;
import java.util.List;
import java.util.Map;

/** Everything the engine needs. stocks is keyed by symbol, funds by scheme code. */
public record PortfolioInput(List<Position> positions, Map<String, StockInfo> stocks, Map<String, FundInfo> funds,
                             double idleCashInr, LocalDate asOf) {
    public PortfolioInput withPositions(List<Position> p) {
        return new PortfolioInput(p, stocks, funds, idleCashInr, asOf);
    }
}
