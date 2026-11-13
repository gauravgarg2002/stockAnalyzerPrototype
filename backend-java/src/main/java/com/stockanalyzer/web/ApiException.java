package com.stockanalyzer.web;

/** An error that maps to the contract error shape (§0.2). details is a Map, a JsonNode or null. */
public class ApiException extends RuntimeException {

    private final int status;
    private final String code;
    private final transient Object details;

    public ApiException(int status, String code, String message, Object details) {
        super(message);
        this.status = status;
        this.code = code;
        this.details = details;
    }

    public int status() { return status; }

    public String code() { return code; }

    public Object details() { return details; }

    public static ApiException badRequest(String message) { return new ApiException(400, "BAD_REQUEST", message, null); }

    public static ApiException badRequest(String message, Object details) { return new ApiException(400, "BAD_REQUEST", message, details); }

    public static ApiException notFound(String message, Object details) { return new ApiException(404, "NOT_FOUND", message, details); }

    public static ApiException brokerNotConnected(String message) { return new ApiException(409, "BROKER_NOT_CONNECTED", message, null); }

    public static ApiException upstreamUnavailable(String message) { return new ApiException(502, "UPSTREAM_UNAVAILABLE", message, null); }

    public static ApiException internal(String message) { return new ApiException(500, "INTERNAL", message, null); }
}
