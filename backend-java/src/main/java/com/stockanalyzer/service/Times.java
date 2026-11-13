package com.stockanalyzer.service;

import java.time.OffsetDateTime;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.time.temporal.ChronoUnit;

/** Timestamps in Asia/Kolkata, ISO-8601 with offset, whole seconds. */
final class Times {
    private Times() { }

    static final ZoneId IST = ZoneId.of("Asia/Kolkata");

    static OffsetDateTime now() {
        return OffsetDateTime.now(IST).truncatedTo(ChronoUnit.SECONDS);
    }

    static String iso(OffsetDateTime t) {
        return t == null ? null : t.atZoneSameInstant(IST).toOffsetDateTime().format(DateTimeFormatter.ISO_OFFSET_DATE_TIME);
    }
}
