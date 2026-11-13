package com.stockanalyzer.service;

import com.stockanalyzer.engine.IndianFormat;
import com.stockanalyzer.web.dto.Shared.Comparison;
import com.stockanalyzer.web.dto.Shared.Figure;
import java.util.List;

/** Builds Figure and Comparison records; display strings come from the engine's IndianFormat. */
final class Figures {
    private Figures() { }

    static final String CALCULATED = "Calculated from your holdings";

    static Comparison cmp(String kind, String label, Object value, String unit) {
        return new Comparison(kind, label, value, unit, IndianFormat.display(value, unit));
    }

    static Figure of(String id, String label, Object value, String unit, String source, String asOf,
                     List<Comparison> comparisons, String termId) {
        return new Figure(id, label, value, unit, IndianFormat.display(value, unit), source, asOf,
                comparisons == null ? List.of() : comparisons, termId);
    }

    /** A figure computed by Java from the user's holdings. */
    static Figure calc(String id, String label, Object value, String unit, String asOf, List<Comparison> comparisons,
                       String termId) {
        return of(id, label, value, unit, CALCULATED, asOf, comparisons, termId);
    }

    static Figure calc(String id, String label, Object value, String unit, String asOf, List<Comparison> comparisons) {
        return calc(id, label, value, unit, asOf, comparisons, null);
    }
}
