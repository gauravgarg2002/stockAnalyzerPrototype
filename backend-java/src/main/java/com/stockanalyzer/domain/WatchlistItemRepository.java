package com.stockanalyzer.domain;

import com.stockanalyzer.engine.model.Kind;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface WatchlistItemRepository extends JpaRepository<WatchlistItemEntity, Long> {

    List<WatchlistItemEntity> findAllByOrderByCreatedAtDescIdDesc();

    List<WatchlistItemEntity> findTop5ByOrderByCreatedAtDescIdDesc();

    Optional<WatchlistItemEntity> findByKindAndInstrumentId(Kind kind, String instrumentId);
}
