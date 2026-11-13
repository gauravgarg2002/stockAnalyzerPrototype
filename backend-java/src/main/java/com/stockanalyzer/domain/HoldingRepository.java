package com.stockanalyzer.domain;

import com.stockanalyzer.engine.model.Kind;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.transaction.annotation.Transactional;

public interface HoldingRepository extends JpaRepository<HoldingEntity, Long> {

    List<HoldingEntity> findAllByOrderByIdAsc();

    List<HoldingEntity> findByKindAndInstrumentIdOrderByIdAsc(Kind kind, String instrumentId);

    @Transactional
    long deleteBySource(HoldingSource source);

    long countBySource(HoldingSource source);

    long countByKind(Kind kind);
}
