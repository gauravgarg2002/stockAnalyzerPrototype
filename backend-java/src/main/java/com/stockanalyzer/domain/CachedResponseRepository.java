package com.stockanalyzer.domain;

import org.springframework.data.jpa.repository.JpaRepository;

public interface CachedResponseRepository extends JpaRepository<CachedResponseEntity, String> { }
