package com.stockanalyzer.web;

import com.stockanalyzer.service.HoldingsService;
import com.stockanalyzer.web.dto.ConnectDto.HoldingCreated;
import com.stockanalyzer.web.dto.ConnectDto.HoldingsResponse;
import com.stockanalyzer.web.dto.ConnectDto.ManualHoldingRequest;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/holdings")
public class HoldingsController {

    private final HoldingsService service;

    public HoldingsController(HoldingsService service) { this.service = service; }

    @GetMapping
    public HoldingsResponse list() { return service.list(); }

    @PostMapping
    public ResponseEntity<HoldingCreated> add(@RequestBody ManualHoldingRequest request) {
        return ResponseEntity.status(HttpStatus.CREATED).body(service.add(request));
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(@PathVariable("id") long id) {
        service.delete(id);
        return ResponseEntity.noContent().build();
    }
}
