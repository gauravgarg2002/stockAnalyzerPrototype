package com.stockanalyzer.engine;

import java.time.LocalDate;
import java.util.OptionalDouble;

/** Price/NAV/index value on or before a requested date. kind is STOCK, FUND or INDEX. */
public interface PricePoints {
    OptionalDouble value(String kind, String id, LocalDate requested);
}
