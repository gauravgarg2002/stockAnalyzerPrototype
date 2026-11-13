package com.stockanalyzer.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.LocalDate;

/** Idle cash in the trading account. Single row with id = 1. */
@Entity
@Table(name = "account_cash")
public class AccountCashEntity {

    public static final long SINGLE_ID = 1L;

    @Id
    private Long id = SINGLE_ID;

    @Column(name = "idle_cash_inr", nullable = false)
    private double idleCashInr;

    @Column(name = "as_of")
    private LocalDate asOf;

    @Column(name = "source", length = 12)
    private String source;

    @Column(name = "sample_data", nullable = false)
    private boolean sampleData;

    public AccountCashEntity() { }

    public Long getId() { return id; }

    public void setId(Long id) { this.id = id; }

    public double getIdleCashInr() { return idleCashInr; }

    public void setIdleCashInr(double idleCashInr) { this.idleCashInr = idleCashInr; }

    public LocalDate getAsOf() { return asOf; }

    public void setAsOf(LocalDate asOf) { this.asOf = asOf; }

    public String getSource() { return source; }

    public void setSource(String source) { this.source = source; }

    public boolean isSampleData() { return sampleData; }

    public void setSampleData(boolean sampleData) { this.sampleData = sampleData; }
}
