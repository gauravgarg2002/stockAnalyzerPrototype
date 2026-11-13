package com.stockanalyzer.engine;

import java.util.List;

/** One line of an exposure breakdown. kind: COMPANY, SECTOR, SIZE, DEBT_CASH, OTHER. */
public record ExposureLine(String key, String name, String kind, String symbol, boolean checkAvailable,
                           long totalInr, long directInr, long throughFundsInr,
                           int totalBp, int directBp, int throughFundsBp,
                           String display, String directDisplay, String throughFundsDisplay,
                           List<ViaFund> viaFunds) {

    public record ViaFund(String schemeCode, String name, long inr) { }

    public boolean isBucket() { return "DEBT_CASH".equals(kind) || "OTHER".equals(kind); }

    public double totalPct() { return Bp.pct(totalBp); }

    public double directPct() { return Bp.pct(directBp); }

    public double throughFundsPct() { return Bp.pct(throughFundsBp); }
}
