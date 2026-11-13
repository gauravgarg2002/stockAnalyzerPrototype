package com.stockanalyzer.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.client.RestClient;

/** RestClients for the Python service: 10 s timeout, and 60 s for broker and statement calls. */
@Configuration
public class HttpClientConfig {

    private static RestClient build(RestClient.Builder builder, String baseUrl, int readTimeoutMillis) {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(5000);
        factory.setReadTimeout(readTimeoutMillis);
        return builder.baseUrl(baseUrl).requestFactory(factory).build();
    }

    @Bean(name = "pythonRestClient")
    public RestClient pythonRestClient(RestClient.Builder builder, AppProperties props) {
        return build(builder, props.services().pythonBaseUrl(), 10_000);
    }

    @Bean(name = "pythonLongRestClient")
    public RestClient pythonLongRestClient(RestClient.Builder builder, AppProperties props) {
        return build(builder, props.services().pythonBaseUrl(), 60_000);
    }
}
