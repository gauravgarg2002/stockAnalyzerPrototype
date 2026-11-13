package com.stockanalyzer.web;

import com.stockanalyzer.service.MetaService;
import com.stockanalyzer.web.dto.ConnectDto.MetaResponse;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api")
public class MetaController {

    private final MetaService service;

    public MetaController(MetaService service) { this.service = service; }

    @GetMapping("/meta")
    public MetaResponse meta() { return service.meta(); }
}
