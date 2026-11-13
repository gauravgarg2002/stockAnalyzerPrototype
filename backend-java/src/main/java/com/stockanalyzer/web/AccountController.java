package com.stockanalyzer.web;

import com.fasterxml.jackson.databind.JsonNode;
import com.stockanalyzer.python.PythonClient;
import java.util.Locale;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * Read-only "now" data from the connected broker: a live quote for one stock and today's account activity.
 * Passed through uncached, because both are only useful when fresh. Nothing here can place or change an order:
 * the Python side refuses every write call before any network I/O.
 */
@RestController
@RequestMapping("/api")
public class AccountController {

    private final PythonClient python;

    public AccountController(PythonClient python) { this.python = python; }

    @GetMapping("/stocks/{symbol}/quote")
    public JsonNode quote(@PathVariable("symbol") String symbol) {
        String sym = symbol == null ? "" : symbol.trim().toUpperCase(Locale.ROOT);
        if (!sym.matches("[A-Z0-9&\\-]{1,20}")) throw ApiException.badRequest("A valid NSE symbol is required.");
        return python.brokerQuote(sym);
    }

    @GetMapping("/account/activity")
    public JsonNode activity() { return python.brokerActivity(); }
}
