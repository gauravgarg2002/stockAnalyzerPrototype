package com.stockanalyzer.engine;

import java.util.List;

/** dimension: COMPANY, SECTOR or SIZE. Lines sum to exactly 10000 bp and totalInr (or are empty). */
public record ExposureBreakdown(String dimension, long totalInr, List<ExposureLine> lines) {

    public int sumBp() {
        int s = 0;
        for (ExposureLine l : lines) s += l.totalBp();
        return s;
    }

    public long sumInr() {
        long s = 0;
        for (ExposureLine l : lines) s += l.totalInr();
        return s;
    }

    public ExposureLine find(String key) {
        for (ExposureLine l : lines) if (l.key().equals(key)) return l;
        return null;
    }

    /** First line that is not a bucket, or null. */
    public ExposureLine top() {
        for (ExposureLine l : lines) if (!l.isBucket()) return l;
        return null;
    }
}
