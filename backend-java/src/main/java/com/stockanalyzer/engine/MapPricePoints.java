package com.stockanalyzer.engine;

import java.time.LocalDate;
import java.util.HashMap;
import java.util.Map;
import java.util.OptionalDouble;

/** In-memory PricePoints keyed by (kind, id, requestedDate). */
public final class MapPricePoints implements PricePoints {
    private final Map<String, Double> map = new HashMap<>();

    private static String k(String kind, String id, LocalDate d) { return kind + "|" + id + "|" + d; }

    /** value may be null (no data on or before that date). */
    public MapPricePoints put(String kind, String id, LocalDate requested, Double value) {
        if (value != null) map.put(k(kind, id, requested), value);
        return this;
    }

    @Override
    public OptionalDouble value(String kind, String id, LocalDate requested) {
        Double v = map.get(k(kind, id, requested));
        return v == null ? OptionalDouble.empty() : OptionalDouble.of(v);
    }
}
