package com.stockanalyzer.service;

import com.stockanalyzer.engine.model.Kind;
import com.stockanalyzer.web.ApiException;
import java.util.Locale;

/** Input normalisation shared by the services. */
final class Instruments {
    private Instruments() { }

    static Kind parseKind(String s) {
        if (s != null) {
            String t = s.trim().toUpperCase(Locale.ROOT);
            if (t.equals("STOCK")) return Kind.STOCK;
            if (t.equals("FUND")) return Kind.FUND;
        }
        throw ApiException.badRequest("kind must be STOCK or FUND.");
    }

    /** Stocks are upper-case NSE symbols; funds are scheme codes as typed (trimmed). */
    static String normalize(Kind kind, String id) {
        if (id == null || id.isBlank()) throw ApiException.badRequest("An instrument id is required.");
        String t = id.trim();
        return kind == Kind.STOCK ? t.toUpperCase(Locale.ROOT) : t;
    }

    static void checkAmount(double amount, String field) {
        if (!(amount > 0) || amount > 1e9 || Double.isNaN(amount)) {
            throw ApiException.badRequest(field + " must be more than 0 and at most 1,000,000,000.");
        }
    }
}
