package com.stockanalyzer.domain;

import com.stockanalyzer.engine.model.Kind;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.LocalDate;
import java.time.OffsetDateTime;

/** One imported or manually added position. Quantity is shares for stocks and units for funds. */
@Entity
@Table(name = "holding")
public class HoldingEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Enumerated(EnumType.STRING)
    @Column(name = "kind", nullable = false, length = 10)
    private Kind kind;

    @Column(name = "instrument_id", nullable = false, length = 64)
    private String instrumentId;

    @Column(name = "name", length = 300)
    private String name;

    @Column(name = "quantity", nullable = false)
    private double quantity;

    @Column(name = "avg_price", nullable = false)
    private double avgPrice;

    @Column(name = "first_buy_date")
    private LocalDate firstBuyDate;

    @Enumerated(EnumType.STRING)
    @Column(name = "source", nullable = false, length = 12)
    private HoldingSource source;

    @Column(name = "sample_data", nullable = false)
    private boolean sampleData;

    @Column(name = "imported_at", nullable = false)
    private OffsetDateTime importedAt;

    public HoldingEntity() { }

    public Long getId() { return id; }

    public void setId(Long id) { this.id = id; }

    public Kind getKind() { return kind; }

    public void setKind(Kind kind) { this.kind = kind; }

    public String getInstrumentId() { return instrumentId; }

    public void setInstrumentId(String instrumentId) { this.instrumentId = instrumentId; }

    public String getName() { return name; }

    public void setName(String name) { this.name = name; }

    public double getQuantity() { return quantity; }

    public void setQuantity(double quantity) { this.quantity = quantity; }

    public double getAvgPrice() { return avgPrice; }

    public void setAvgPrice(double avgPrice) { this.avgPrice = avgPrice; }

    public LocalDate getFirstBuyDate() { return firstBuyDate; }

    public void setFirstBuyDate(LocalDate firstBuyDate) { this.firstBuyDate = firstBuyDate; }

    public HoldingSource getSource() { return source; }

    public void setSource(HoldingSource source) { this.source = source; }

    public boolean isSampleData() { return sampleData; }

    public void setSampleData(boolean sampleData) { this.sampleData = sampleData; }

    public OffsetDateTime getImportedAt() { return importedAt; }

    public void setImportedAt(OffsetDateTime importedAt) { this.importedAt = importedAt; }
}
