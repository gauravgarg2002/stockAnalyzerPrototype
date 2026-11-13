package com.stockanalyzer.web;

import com.fasterxml.jackson.databind.JsonNode;
import com.stockanalyzer.service.CheckService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/** Search, stock and fund checks, compare, glossary and explain (contract A.4 to A.10). */
@RestController
@RequestMapping("/api")
public class CheckController {

    private final CheckService service;

    public CheckController(CheckService service) { this.service = service; }

    @GetMapping("/search")
    public JsonNode search(@RequestParam(name = "q", required = false) String q) { return service.search(q); }

    @GetMapping("/stocks/{symbol}/check")
    public JsonNode stockCheck(@PathVariable("symbol") String symbol) { return service.stockCheck(symbol); }

    @GetMapping("/funds/{schemeCode}/check")
    public JsonNode fundCheck(@PathVariable("schemeCode") String schemeCode,
                              @RequestParam(name = "amount", required = false) Double amount) {
        return service.fundCheck(schemeCode, amount);
    }

    @GetMapping("/compare")
    public JsonNode compare(@RequestParam(name = "kind") String kind,
                            @RequestParam(name = "ids") String ids,
                            @RequestParam(name = "amount", required = false) Double amount) {
        return service.compare(kind, ids, amount);
    }

    @GetMapping("/glossary")
    public JsonNode glossary() { return service.glossary(); }

    @GetMapping("/explain")
    public JsonNode explain(@RequestParam(name = "term") String term,
                            @RequestParam(name = "kind", required = false) String kind,
                            @RequestParam(name = "id", required = false) String id) {
        return service.explain(term, kind, id);
    }
}
