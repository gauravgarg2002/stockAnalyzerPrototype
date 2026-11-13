package com.stockanalyzer.engine;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import java.time.LocalDate;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/** Contract §0.4 vectors (identical in Python and TypeScript). */
class IndianFormatTest {

    @Test
    @DisplayName("formatInr vectors")
    void inr() {
        assertEquals("₹0", IndianFormat.formatInr(0));
        assertEquals("₹999", IndianFormat.formatInr(999));
        assertEquals("₹42,351", IndianFormat.formatInr(42350.75));
        assertEquals("₹99,999", IndianFormat.formatInr(99999.4));
        assertEquals("₹1 lakh", IndianFormat.formatInr(99999.6));
        assertEquals("₹1.2 lakh", IndianFormat.formatInr(120000));
        assertEquals("₹12.4 lakh", IndianFormat.formatInr(1243500));
        assertEquals("₹12.5 lakh", IndianFormat.formatInr(1250000));
        assertEquals("₹1 crore", IndianFormat.formatInr(9999999));
        assertEquals("₹3.4 crore", IndianFormat.formatInr(34000000));
        assertEquals("₹845.3 crore", IndianFormat.formatInr(8453000000.0));
        assertEquals("₹19,32,100 crore", IndianFormat.formatInr(19321000000000.0));
        assertEquals("-₹45,000", IndianFormat.formatInr(-45000));
    }

    @Test
    @DisplayName("formatInr edge cases")
    void inrEdges() {
        assertEquals("₹1 lakh", IndianFormat.formatInr(100000));
        assertEquals("₹0", IndianFormat.formatInr(-0.4));
        assertEquals("₹12.3 lakh", IndianFormat.formatInr(1234567));
        assertEquals("₹1,000 crore", IndianFormat.formatInr(10000000000.0));
        assertEquals("₹999.9 crore", IndianFormat.formatInr(9999000000.0));
        assertEquals("₹1.5 lakh", IndianFormat.formatInr(150000));
        assertEquals("-₹1.2 lakh", IndianFormat.formatInr(-120000));
    }

    @Test
    @DisplayName("formatPrice vectors")
    void price() {
        assertEquals("₹2,410.50", IndianFormat.formatPrice(2410.5));
        assertEquals("₹2.68", IndianFormat.formatPrice(2.675));
        assertEquals("₹12,34,567.89", IndianFormat.formatPrice(1234567.891));
        assertEquals("-₹2,410.50", IndianFormat.formatPrice(-2410.5));
        assertEquals("₹0.00", IndianFormat.formatPrice(0));
    }

    @Test
    @DisplayName("percent formats")
    void percent() {
        assertEquals("12.3%", IndianFormat.formatPct(12.345));
        assertEquals("0.1%", IndianFormat.formatPct(0.05));
        assertEquals("1.3%", IndianFormat.formatPct(1.25));
        assertEquals("-4.1%", IndianFormat.formatPct(-4.1));
        assertEquals("+14.3%", IndianFormat.formatPctChange(14.25));
        assertEquals("-4.1%", IndianFormat.formatPctChange(-4.1));
        assertEquals("0.0%", IndianFormat.formatPctChange(0));
        assertEquals("0.0%", IndianFormat.formatPctChange(-0.04));
    }

    @Test
    @DisplayName("times, count, years, days")
    void others() {
        assertEquals("24.1x", IndianFormat.formatTimes(24.06));
        assertEquals("12,34,567", IndianFormat.formatCount(1234567));
        assertEquals("999", IndianFormat.formatCount(999));
        assertEquals("1 year", IndianFormat.formatYears(1));
        assertEquals("3 years", IndianFormat.formatYears(3));
        assertEquals("7.3 years", IndianFormat.formatYears(7.25));
        assertEquals("1 day", IndianFormat.formatDays(1));
        assertEquals("143 days", IndianFormat.formatDays(143));
        assertEquals("1 month", IndianFormat.formatMonths(1));
        assertEquals("12 months", IndianFormat.formatMonths(12));
    }

    @Test
    @DisplayName("dates")
    void dates() {
        assertEquals("30 Oct 2026", IndianFormat.formatDate(LocalDate.of(2026, 10, 30)));
        assertEquals("5 Jan 2021", IndianFormat.formatDate(LocalDate.of(2021, 1, 5)));
    }

    @Test
    @DisplayName("display() picks the formatter from the unit; null is Not available")
    void display() {
        assertEquals("₹1.2 lakh", IndianFormat.display(120000, Units.INR));
        assertEquals("₹2,410.50", IndianFormat.display(2410.5, Units.INR_PRICE));
        assertEquals("+14.3%", IndianFormat.display(14.25, Units.PCT_CHANGE));
        assertEquals("Not available", IndianFormat.display(null, Units.PCT));
        assertEquals("Large cap", IndianFormat.display("Large cap", Units.TEXT));
        assertEquals("27", IndianFormat.display(27L, Units.COUNT));
        assertThrows(IllegalArgumentException.class, () -> IndianFormat.display(1.0, "BOGUS"));
    }
}
