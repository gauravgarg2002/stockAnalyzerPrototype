package com.stockanalyzer.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

/**
 * The shared config file (contract §C) bound at the root. Only the sections Java uses are listed; the other
 * sections (screener, nse, mfapi, amfi, mfdata, sizeBands) belong to the Python service and are ignored here.
 * Defaults live in application.yml and equal config/app-config.example.yaml.
 */
@ConfigurationProperties
public record AppProperties(App app, Ports ports, Services services, Adapters adapters, Kite kite, Llm llm,
                            Cache cache, Storage storage) {

    public record App(String sampleAsOf, long defaultIllustrativeAmountInr, String disclaimer) { }

    public record Ports(int frontend, int java, int python) { }

    public record Services(String pythonBaseUrl, String frontendBaseUrl) { }

    public record Adapters(String broker, String fundamentals, String prices, String surveillance, String fundNav,
                           String fundMeta, String fundHoldings, String statement) { }

    public record Kite(String mcpUrl, String apiKey, String apiSecret, String redirectUrl, int loginTimeoutSeconds) { }

    public record Llm(String provider, String model, String apiKey, int timeoutSeconds) { }

    public record Cache(String dir, int fundamentalsHours, int pricesHours, int fundDataHours, int surveillanceHours,
                        int javaResponseMinutes) { }

    public record Storage(String h2Path) { }

    /** True when an LLM provider is configured, so narrate may be asked to use it. */
    public boolean llmConfigured() {
        return llm != null && llm.provider() != null && !llm.provider().isBlank() && !"none".equalsIgnoreCase(llm.provider());
    }
}
