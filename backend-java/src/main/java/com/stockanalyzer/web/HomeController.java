package com.stockanalyzer.web;

import com.stockanalyzer.service.HomeService;
import com.stockanalyzer.web.dto.PortfolioDto.HomeResponse;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api")
public class HomeController {

    private final HomeService service;

    public HomeController(HomeService service) { this.service = service; }

    @GetMapping("/home")
    public HomeResponse home() { return service.home(); }
}
