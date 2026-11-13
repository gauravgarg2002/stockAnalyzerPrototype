package com.stockanalyzer.engine;

import java.util.Map;

/** One item of a /internal/narrate request (contract §B.12). */
public record NarrateItem(String key, String templateId, Map<String, FactValue> facts) { }
