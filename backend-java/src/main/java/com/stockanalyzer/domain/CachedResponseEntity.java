package com.stockanalyzer.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Lob;
import jakarta.persistence.Table;
import java.time.Instant;

@Entity
@Table(name = "cached_response")
public class CachedResponseEntity {

    @Id
    @Column(name = "cache_key", length = 512)
    private String cacheKey;

    @Lob
    @Column(name = "response_json", nullable = false)
    private String json;

    @Column(name = "expires_at", nullable = false)
    private Instant expiresAt;

    public CachedResponseEntity() { }

    public CachedResponseEntity(String cacheKey, String json, Instant expiresAt) {
        this.cacheKey = cacheKey;
        this.json = json;
        this.expiresAt = expiresAt;
    }

    public String getCacheKey() { return cacheKey; }

    public void setCacheKey(String cacheKey) { this.cacheKey = cacheKey; }

    public String getJson() { return json; }

    public void setJson(String json) { this.json = json; }

    public Instant getExpiresAt() { return expiresAt; }

    public void setExpiresAt(Instant expiresAt) { this.expiresAt = expiresAt; }
}
