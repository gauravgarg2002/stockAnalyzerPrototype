package com.stockanalyzer.engine.model;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** A holding. Quantity is shares (stock) or units (fund). */
public record Position(Kind kind, String id, double quantity, double avgPrice, LocalDate firstBuyDate) {

    /**
     * Aggregates by (kind, id): sums quantity, quantity-weighted average price, earliest non-null buy date.
     * Order of first appearance is kept. Positions with quantity <= 0 are dropped. Idempotent.
     */
    public static List<Position> aggregate(List<Position> positions) {
        Map<String, double[]> sums = new LinkedHashMap<>(); // [qty, qty*avg]
        Map<String, Kind> kinds = new LinkedHashMap<>();
        Map<String, String> ids = new LinkedHashMap<>();
        Map<String, LocalDate> dates = new LinkedHashMap<>();
        for (Position p : positions) {
            if (!(p.quantity() > 0)) continue;
            String k = p.kind() + "|" + p.id();
            double[] s = sums.computeIfAbsent(k, x -> new double[2]);
            s[0] += p.quantity();
            s[1] += p.quantity() * p.avgPrice();
            kinds.putIfAbsent(k, p.kind());
            ids.putIfAbsent(k, p.id());
            if (p.firstBuyDate() != null) dates.merge(k, p.firstBuyDate(), (x, y) -> x.isBefore(y) ? x : y);
        }
        List<Position> out = new ArrayList<>();
        for (Map.Entry<String, double[]> e : sums.entrySet()) {
            String k = e.getKey();
            double[] s = e.getValue();
            out.add(new Position(kinds.get(k), ids.get(k), s[0], s[1] / s[0], dates.get(k)));
        }
        return out;
    }
}
