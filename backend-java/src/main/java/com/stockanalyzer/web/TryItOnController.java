package com.stockanalyzer.web;

import com.stockanalyzer.service.TryItOnService;
import com.stockanalyzer.web.dto.TryItOnDto.Request;
import com.stockanalyzer.web.dto.TryItOnDto.Response;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api")
public class TryItOnController {

    private final TryItOnService service;

    public TryItOnController(TryItOnService service) { this.service = service; }

    @PostMapping("/try-it-on")
    public Response tryItOn(@RequestBody Request request) { return service.run(request); }
}
