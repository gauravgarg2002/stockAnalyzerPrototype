package com.stockanalyzer.engine.model;

/** An equity holding inside a fund; weightPct is percent of the fund. */
public record FundConstituent(String key, String symbol, String name, String sector, SizeBand sizeBand,
                              double weightPct, boolean checkAvailable) { }
