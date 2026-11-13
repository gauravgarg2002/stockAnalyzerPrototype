package com.stockanalyzer.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.stockanalyzer.config.AppProperties;
import com.stockanalyzer.domain.CachedResponseEntity;
import com.stockanalyzer.domain.CachedResponseRepository;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.util.HexFormat;
import java.util.Optional;
import java.util.function.Supplier;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

/** Database-backed response cache with a TTL from cache.javaResponseMinutes. Cleared on any holdings change. */
@Service
public class ResponseCache {

    private static final Logger LOG = LoggerFactory.getLogger(ResponseCache.class);

    private final CachedResponseRepository repo;
    private final ObjectMapper mapper;
    private final AppProperties props;

    public ResponseCache(CachedResponseRepository repo, ObjectMapper mapper, AppProperties props) {
        this.repo = repo;
        this.mapper = mapper;
        this.props = props;
    }

    /** SHA-256 hex of a string, for long cache keys. */
    public static String hash(String s) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            return HexFormat.of().formatHex(md.digest(s.getBytes(StandardCharsets.UTF_8)));
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException(e);
        }
    }

    private static String safeKey(String key) {
        return key.length() <= 500 ? key : "h:" + hash(key);
    }

    /** Returns the cached value for key, or loads, stores and returns it. */
    public <T> T get(String rawKey, Class<T> type, Supplier<T> loader) {
        int minutes = props.cache() == null ? 0 : props.cache().javaResponseMinutes();
        if (minutes <= 0) return loader.get();
        String key = safeKey(rawKey);
        try {
            Optional<CachedResponseEntity> hit = repo.findById(key);
            if (hit.isPresent() && hit.get().getExpiresAt().isAfter(Instant.now())) {
                return mapper.readValue(hit.get().getJson(), type);
            }
        } catch (JsonProcessingException | RuntimeException e) {
            LOG.warn("Ignoring unreadable cache entry {}: {}", key, e.toString());
        }
        T value = loader.get();
        try {
            repo.save(new CachedResponseEntity(key, mapper.writeValueAsString(value),
                    Instant.now().plusSeconds(minutes * 60L)));
        } catch (JsonProcessingException | RuntimeException e) {
            LOG.warn("Could not store cache entry {}: {}", key, e.toString());
        }
        return value;
    }

    /** Removes every cached response (called after any import or holdings change). */
    public void clearAll() {
        try {
            repo.deleteAllInBatch();
        } catch (RuntimeException e) {
            LOG.warn("Could not clear the response cache: {}", e.toString());
        }
    }
}
