package com.stockanalyzer.engine.model;

public record StockInfo(String symbol, String name, String sector, SizeBand sizeBand, double lastPrice,
                        boolean checkAvailable) { }
