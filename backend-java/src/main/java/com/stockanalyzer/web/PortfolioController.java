package com.stockanalyzer.web;

import com.stockanalyzer.service.PortfolioService;
import com.stockanalyzer.web.dto.PortfolioDto.PortfolioResponse;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api")
public class PortfolioController {

    private final PortfolioService service;

    public PortfolioController(PortfolioService service) { this.service = service; }

    @GetMapping("/portfolio")
    public PortfolioResponse portfolio() { return service.portfolio(); }
}
