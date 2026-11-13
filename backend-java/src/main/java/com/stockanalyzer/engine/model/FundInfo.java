package com.stockanalyzer.engine.model;

import java.time.LocalDate;
import java.util.List;

/**
 * Fund data needed by the engine. Beyond the PLAN record: twinName, categoryMedianTerPct and portfolioDate
 * (all needed by contract A.3 fields). terPct and twinTerPct may be null (unknown).
 */
public record FundInfo(String schemeCode, String name, String category, String planType, Double terPct,
                       String twinSchemeCode, String twinName, Double twinTerPct, Double categoryMedianTerPct,
                       double nav, AssetMix assetMix, LocalDate portfolioDate,
                       List<FundConstituent> constituents) {
    public boolean isRegular() { return "REGULAR".equals(planType); }
}
