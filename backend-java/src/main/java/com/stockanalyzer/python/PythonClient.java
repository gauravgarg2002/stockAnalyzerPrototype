package com.stockanalyzer.python;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.stockanalyzer.engine.NarrateItem;
import com.stockanalyzer.python.dto.PyDto.BrokerPortfolio;
import com.stockanalyzer.python.dto.PyDto.BrokerStatus;
import com.stockanalyzer.python.dto.PyDto.BundleRequest;
import com.stockanalyzer.python.dto.PyDto.BundleResponse;
import com.stockanalyzer.python.dto.PyDto.FundCheckRequest;
import com.stockanalyzer.python.dto.PyDto.Health;
import com.stockanalyzer.python.dto.PyDto.LoginCompleteRequest;
import com.stockanalyzer.python.dto.PyDto.NarrateRequest;
import com.stockanalyzer.python.dto.PyDto.NarrateResponse;
import com.stockanalyzer.python.dto.PyDto.PointsRequest;
import com.stockanalyzer.python.dto.PyDto.PointsResponse;
import com.stockanalyzer.python.dto.PyDto.StatementRequest;
import com.stockanalyzer.python.dto.PyDto.StatementResponse;
import com.stockanalyzer.web.ApiException;
import java.util.List;
import java.util.Locale;
import java.util.function.Supplier;
import java.util.regex.Pattern;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestClientResponseException;

/**
 * Typed calls to the Python service (contract §B). Python errors are re-emitted unchanged as ApiException with the
 * same status, code, message and details; an unreachable Python service becomes 502 UPSTREAM_UNAVAILABLE.
 * Only read-style paths exist here. Nothing can place, modify or cancel an order: the guard below refuses any
 * path that looks like one, and the Python side has its own broker guard.
 */
@Component
public class PythonClient {

    private static final Pattern FORBIDDEN_PATH = Pattern.compile("(?i)(order|gtt|place|modify|cancel)");

    private final RestClient rest;
    private final RestClient restLong;
    private final ObjectMapper mapper;

    public PythonClient(@Qualifier("pythonRestClient") RestClient rest,
                        @Qualifier("pythonLongRestClient") RestClient restLong,
                        ObjectMapper mapper) {
        this.rest = rest;
        this.restLong = restLong;
        this.mapper = mapper;
    }

    // ---- plumbing -------------------------------------------------------------------------------------------

    private static void guard(String pathTemplate) {
        if (FORBIDDEN_PATH.matcher(pathTemplate).find()) {
            throw ApiException.internal("Refused to call " + pathTemplate);
        }
    }

    private <T> T call(Supplier<T> action) {
        try {
            return action.get();
        } catch (RestClientResponseException e) {
            throw translate(e);
        } catch (ResourceAccessException e) {
            throw ApiException.upstreamUnavailable("The data service did not answer. Please try again in a moment.");
        } catch (RestClientException e) {
            throw ApiException.upstreamUnavailable("The data service returned something unexpected.");
        }
    }

    private ApiException translate(RestClientResponseException e) {
        int status = e.getStatusCode().value();
        try {
            JsonNode root = mapper.readTree(e.getResponseBodyAsString());
            JsonNode err = root == null ? null : root.get("error");
            if (err != null && err.hasNonNull("code")) {
                String message = err.hasNonNull("message") ? err.get("message").asText() : "The data service reported an error.";
                JsonNode details = err.get("details");
                Object d = details == null || details.isNull() ? null : details;
                return new ApiException(status, err.get("code").asText(), message, d);
            }
        } catch (Exception ignored) {
            // fall through to the generic mapping
        }
        return ApiException.upstreamUnavailable("The data service returned an error (" + status + ").");
    }

    private <T> T get(String uri, Class<T> type, Object... vars) {
        guard(uri);
        return call(() -> rest.get().uri(uri, vars).retrieve().body(type));
    }

    private <T> T post(RestClient client, String uri, Object body, Class<T> type, Object... vars) {
        guard(uri);
        return call(() -> {
            RestClient.RequestBodySpec spec = client.post().uri(uri, vars).contentType(MediaType.APPLICATION_JSON);
            if (body != null) spec.body(body);
            return spec.retrieve().body(type);
        });
    }

    // ---- B.1 .. B.9 -------------------------------------------------------------------------------------------

    public Health health() { return get("/internal/health", Health.class); }

    public JsonNode search(String q, int limit) {
        return get("/internal/search?q={q}&limit={limit}", JsonNode.class, q, limit);
    }

    public JsonNode stockCheck(String symbol) { return get("/internal/stocks/{symbol}/check", JsonNode.class, symbol); }

    public JsonNode fundCheck(String schemeCode, FundCheckRequest request) {
        return post(rest, "/internal/funds/{code}/check", request, JsonNode.class, schemeCode);
    }

    public JsonNode compare(String kind, String idsCsv, Double amountInr) {
        if (amountInr == null) {
            return get("/internal/compare?kind={kind}&ids={ids}", JsonNode.class, kind, idsCsv);
        }
        return get("/internal/compare?kind={kind}&ids={ids}&amountInr={amount}", JsonNode.class, kind, idsCsv,
                String.format(Locale.ROOT, "%.2f", amountInr));
    }

    public JsonNode glossary() { return get("/internal/glossary", JsonNode.class); }

    public JsonNode explain(String term, String kind, String id) {
        if (kind == null || id == null) {
            return get("/internal/explain?term={term}", JsonNode.class, term);
        }
        return get("/internal/explain?term={term}&kind={kind}&id={id}", JsonNode.class, term, kind, id);
    }

    public BundleResponse bundle(List<String> stocks, List<String> funds) {
        return post(rest, "/internal/instruments/bundle", new BundleRequest(stocks, funds), BundleResponse.class);
    }

    public PointsResponse points(PointsRequest request) {
        return post(rest, "/internal/prices/points", request, PointsResponse.class);
    }

    public NarrateResponse narrate(List<NarrateItem> items, boolean useLlm) {
        return post(rest, "/internal/narrate", new NarrateRequest(items, useLlm), NarrateResponse.class);
    }

    // ---- B.10 broker (60 s timeout) -----------------------------------------------------------------------------

    public BrokerStatus brokerLoginStart() {
        return post(restLong, "/internal/broker/login/start", null, BrokerStatus.class);
    }

    public BrokerStatus brokerLoginStatus() {
        guard("/internal/broker/login/status");
        return call(() -> restLong.get().uri("/internal/broker/login/status").retrieve().body(BrokerStatus.class));
    }

    public BrokerStatus brokerLoginComplete(String requestToken) {
        return post(restLong, "/internal/broker/login/complete", new LoginCompleteRequest(requestToken), BrokerStatus.class);
    }

    public BrokerStatus brokerLogout() {
        return post(restLong, "/internal/broker/logout", null, BrokerStatus.class);
    }

    /** Live quote for one stock from the connected broker. Never cached: it is the "now" price. */
    public JsonNode brokerQuote(String symbol) {
        return get("/internal/broker/quote?symbol={symbol}", JsonNode.class, symbol);
    }

    /** Today's positions, orders, trades and price triggers from the connected broker (read-only). */
    public JsonNode brokerActivity() { return get("/internal/broker/activity", JsonNode.class); }

    public BrokerPortfolio brokerPortfolio() {
        guard("/internal/broker/portfolio");
        return call(() -> restLong.get().uri("/internal/broker/portfolio").retrieve().body(BrokerPortfolio.class));
    }

    // ---- B.11 statements (60 s timeout) -------------------------------------------------------------------------

    public StatementResponse parseStatement(StatementRequest request) {
        return post(restLong, "/internal/statements/parse", request, StatementResponse.class);
    }
}
