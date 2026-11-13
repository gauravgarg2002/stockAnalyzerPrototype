package com.stockanalyzer.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.OffsetDateTime;

@Entity
@Table(name = "import_log")
public class ImportLogEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Enumerated(EnumType.STRING)
    @Column(name = "source", nullable = false, length = 12)
    private HoldingSource source;

    @Enumerated(EnumType.STRING)
    @Column(name = "status", nullable = false, length = 10)
    private ImportStatus status;

    @Column(name = "started_at", nullable = false)
    private OffsetDateTime startedAt;

    @Column(name = "finished_at", nullable = false)
    private OffsetDateTime finishedAt;

    @Column(name = "stock_count", nullable = false)
    private int stockCount;

    @Column(name = "fund_count", nullable = false)
    private int fundCount;

    @Column(name = "unmatched_count", nullable = false)
    private int unmatchedCount;

    @Column(name = "message", length = 500)
    private String message;

    @Column(name = "sample_data", nullable = false)
    private boolean sampleData;

    public ImportLogEntity() { }

    public Long getId() { return id; }

    public void setId(Long id) { this.id = id; }

    public HoldingSource getSource() { return source; }

    public void setSource(HoldingSource source) { this.source = source; }

    public ImportStatus getStatus() { return status; }

    public void setStatus(ImportStatus status) { this.status = status; }

    public OffsetDateTime getStartedAt() { return startedAt; }

    public void setStartedAt(OffsetDateTime startedAt) { this.startedAt = startedAt; }

    public OffsetDateTime getFinishedAt() { return finishedAt; }

    public void setFinishedAt(OffsetDateTime finishedAt) { this.finishedAt = finishedAt; }

    public int getStockCount() { return stockCount; }

    public void setStockCount(int stockCount) { this.stockCount = stockCount; }

    public int getFundCount() { return fundCount; }

    public void setFundCount(int fundCount) { this.fundCount = fundCount; }

    public int getUnmatchedCount() { return unmatchedCount; }

    public void setUnmatchedCount(int unmatchedCount) { this.unmatchedCount = unmatchedCount; }

    public String getMessage() { return message; }

    public void setMessage(String message) { this.message = message; }

    public boolean isSampleData() { return sampleData; }

    public void setSampleData(boolean sampleData) { this.sampleData = sampleData; }
}
