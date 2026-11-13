package com.stockanalyzer.domain;

import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ImportLogRepository extends JpaRepository<ImportLogEntity, Long> {

    List<ImportLogEntity> findTop10ByOrderByIdDesc();

    List<ImportLogEntity> findTop1ByOrderByIdDesc();

    long countBySourceAndStatusNot(HoldingSource source, ImportStatus status);
}
