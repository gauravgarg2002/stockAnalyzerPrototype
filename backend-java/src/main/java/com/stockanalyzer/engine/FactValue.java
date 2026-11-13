package com.stockanalyzer.engine;

/** A fact for /internal/narrate: value (number or string) and a contract unit. */
public record FactValue(Object value, String unit) { }
