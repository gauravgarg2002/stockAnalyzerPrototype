package com.stockanalyzer.engine.model;

public enum SizeBand {
    LARGE("Large cap"), MID("Mid cap"), SMALL("Small cap"), MICRO("Micro cap");

    private final String label;

    SizeBand(String label) { this.label = label; }

    public String label() { return label; }

    /** Parses LARGE/MID/SMALL/MICRO (case-insensitive); null or unknown gives null. */
    public static SizeBand parse(String s) {
        if (s == null) return null;
        try { return SizeBand.valueOf(s.trim().toUpperCase(java.util.Locale.ROOT)); }
        catch (IllegalArgumentException e) { return null; }
    }
}
